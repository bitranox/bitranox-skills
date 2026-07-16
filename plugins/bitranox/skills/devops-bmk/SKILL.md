---
name: devops-bmk
description: Use when installing, configuring or running bmk - the bitranox cross-OS build/test/release task runner - in a project (bootstrapping it with uv, deploying its Makefile via bmk install, running make test / push / bump / release / ship, fixing missing external tools with bmk ensure, reading its JSON-by-default vs --human output, layered config with --profile / --set, or defining custom staged pipelines). Works on Linux, macOS and Windows.
---

# devops-bmk

Install, configure and use **bmk** -- a cross-OS CLI task runner that orchestrates a project's
**build, test, clean, release** and custom staged commands from a single thin `Makefile`. It runs
a pure-Python stage runner (no shell/PowerShell scripts), so the same commands work natively on
Linux, macOS and Windows. Source and docs: https://github.com/bitranox/bmk

**Mental model:** you install bmk once with `uv` to bootstrap, drop a bmk-managed `Makefile` into
the project, and from then on drive everything through `make <target>`. The Makefile keeps bmk
itself installed (bmk alone, in uv's own tool dir, shared by every project) and delegates to it.
Your project's dependencies live in your project's own `.venv`, which bmk provisions separately.
Each command runs a **pipeline** of stages grouped by an order number: stages run sequentially and
fail-fast; stages sharing the same order run in parallel.

## When to use

- Setting up bmk in a new or existing project (`uvx bmk install`).
- Running the standard dev loop: `make test`, `make push`, `make bump-patch`, `make release`, `make ship`.
- A tool the pipeline needs is missing (shellcheck, shfmt, pwsh, ...) -> `bmk ensure`.
- Output is empty/terse and you want the full verbose run -> `--human` / `BMK_OUTPUT_FORMAT=text`.
- Customising the config (profiles, `--set` overrides) or adding a `custom` pipeline.

**Not for:** developing bmk's own source (that is the bmk repo's `CLAUDE.md`/`CONTRIBUTING.md`). This
skill is about *using* bmk as a task runner in any project.

## 1. Install

uv is the only prerequisite. You never install bmk yourself: run `bmk install` once, ephemerally,
to drop the Makefile in - from then on the Makefile installs and manages bmk per project.

```bash
# Install uv first if needed (https://astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS/Linux
# Windows (PowerShell): powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

cd your-project
uvx bmk install            # writes the Makefile; installs nothing permanently
make test                  # from here on, everything goes through make
```

You do not need `uv tool install bmk` yourself: once the Makefile is in place it keeps bmk
installed for you (see below). `uvx bmk install` is only the bootstrap that writes the Makefile.

### bmk's env holds bmk alone, and is shared

Once a project has the Makefile (section 2), every `make` first runs

```bash
uv tool install --reinstall --force --refresh-package bmk "bmk>=<minimum>"
```

which installs **bmk on its own** into uv's default tool dir and runs it from there
(`$(uv tool dir --bin)/bmk`). Note what is *not* in that command: your project. The env holds
bmk's toolchain and nothing of yours, which is exactly why one env can serve every repo on the
machine - there is nothing project-specific in it to collide.

Do **not** add `--with .` / `--with-editable ".[dev]"`, and do not redirect it per project with
`UV_TOOL_DIR`. Resolving bmk *together with* a project is what caused, in order: one of your
dependencies capping one of bmk's and silently pinning bmk to an ancient release; a yanked
transitive making bmk itself uninstallable; and the tests running in that co-resolved env while
pyright and pip-audit inspected your real `.venv`, so the suite and the audit described different
environments.

- The install runs on **every** `make`, deliberately. `--reinstall` re-resolves the spec, so a new
  bmk release is picked up with nothing to remember; `--refresh-package bmk` refreshes uv's cached
  index, without which a release published minutes ago stays invisible and you silently keep the
  old bmk. It costs a second or two per invocation. Do not gate it behind a stamp file.
- Right after a release there is a brief window where uv's index still reports only the previous
  version; the next `make` picks the new one up.

### The project venv `.venv`

This is where **your** dependencies live. Before any command that touches the Python environment
(`test`, `push`, `deps`, `build`, ...), bmk creates the project's own `.venv` if it is missing and
syncs it to `pyproject.toml`. pytest, pyright and pip-audit all resolve **that** venv, never bmk's
own and never whatever venv happens to be active in your shell -- so the environment you test in,
type-check in and audit are one and the same, and no project can quietly install its dependencies
into an environment it does not own.

**Which Python it is built on: the newest your classifiers declare, at its latest patch.**

```toml
[project]
requires-python = ">=3.10"                     # a FLOOR - says nothing about the newest
classifiers = [
  "Programming Language :: Python :: 3",       # ignored: no minor
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.14",    # <- .venv is built on 3.14, latest patch
]
```

The classifiers are where a project states the versions it supports, and your CI workflow already
builds its test matrix from the same entries - so your venv and your CI matrix cannot drift apart
about what "newest supported" means. `requires-python` cannot serve: `>=3.10` never names the top.

Before those commands bmk runs `uv python install <X.Y>` and `uv python upgrade <X.Y>`. Both
matter: `install` fetches a version you just added to the classifiers, and `upgrade` is what moves
an already-installed minor onto a newer patch (`install` alone keeps the version it has). Current
and offline, this costs about 0.1s.

**A new patch costs you nothing.** uv builds a venv against the minor alias, so
`uv python upgrade` moves your existing venv onto the new patch by itself; bmk checks the
interpreter, sees it is current, and does nothing. (`pyvenv.cfg` still names the old patch after
that - it is written once at creation. bmk asks the interpreter, not that text, so it does not
rebuild a venv uv has already migrated.)

A **minor** change is the one that cannot be done in place: move `3.14` to `3.15` in your
classifiers and the venv is **rebuilt**. The path never changes, so nothing pointing at it breaks.
If uv cannot say what it would provide, your venv is left alone; bmk never rebuilds on a guess.
Declare no `:: Python :: X.Y` classifier and bmk picks no version at all - uv's default stands.

The same classifiers drive `make test-all`: it provisions one `.venv-<minor>` per declared version
and runs pytest + pyright in each, in parallel, so you can reproduce CI's matrix locally before you
push. Plain `make test` stays on the newest version only; with no `:: Python :: X.Y` classifier,
`test-all` tests the default interpreter once and prints a WARNING naming the version it used.

The sync is exact *and* upgrading: it removes packages the manifest no longer asks for and
re-resolves the ones it does. A venv left to drift makes the gates lie -- pip-audit reports CVEs for
packages the project does not actually resolve, while the real resolution stays hidden. The
trade-off: **packages you installed into the venv by hand do not survive a sync.**

| Env var                  | Effect                                                             |
|--------------------------|--------------------------------------------------------------------|
| `UV_PROJECT_ENVIRONMENT` | Venv path (absolute, or relative to the project). Default `.venv`. |
| `BMK_NO_VENV_SYNC=1`     | Skip provisioning entirely; use the environment as-is.             |

Set `UV_PROJECT_ENVIRONMENT` when one checkout is used from more than one OS (a share mounted on
both Linux and Windows): a single venv cannot serve both, so give each its own (e.g. `.venv-win`).
If provisioning fails, bmk falls back to its own interpreter rather than failing the command.

`clean` does not delete the venv (that would throw away what bmk just built and force a full
re-resolve); `make clean-all` removes every `.venv*` alongside the build artifacts when you do
want them gone. bmk also keeps venvs out of git: it adds a single `.venv*` glob to `.gitignore`
when nothing already ignores them (one line covers `.venv` and every `.venv-<minor>` the matrix
creates), and if git is *tracking* a venv it drops it from the index (`git rm --cached`) while
leaving the files on disk, announcing that it did. A tracked venv would otherwise show thousands
of modified files after every sync.

## 2. Bootstrap the Makefile

```bash
bmk install        # writes / updates a bmk-managed Makefile in the current directory
make test          # from now on, drive everything through make
```

The Makefile keeps bmk installed and your project's `.venv` synced to `pyproject.toml`, so once it
is in place you rarely call `bmk` directly. On **Windows** you still need a `make` implementation
(`choco install make`, or GnuWin32 Make) -- bmk itself needs no shell.

## 3. Everyday commands

Drive these with `make <target>` (or call `bmk <command>` directly). Arguments after the target are
forwarded (e.g. `make push fix login bug`). Most have short aliases.

| Target / command                        | What it does                                                                   |
|-----------------------------------------|--------------------------------------------------------------------------------|
| `make test` \| `t`                      | Full test pipeline: lint, format-check, type-check, security, tests + coverage |
| `make test-human` \| `th`               | Same, forced human-readable (verbose) output                                   |
| `make test-all`                         | Run pytest + pyright on EVERY declared Python version in parallel (the matrix) |
| `make testintegration` \| `ti`          | Integration tests only (`pytest -m integration`)                               |
| `make bump-patch` / `-minor` / `-major` | Bump version in `pyproject.toml` and update the changelog                      |
| `make commit` \| `c` `[MESSAGE...]`     | Git commit with a timestamped message                                          |
| `make push` \| `p` `[MESSAGE...]`       | Run tests, commit, then push to the remote                                     |
| `make release` \| `r`                   | Tag `vX.Y.Z`, push, create the GitHub release via `gh`                         |
| `make ship` \| `sh`                     | push -> wait for CI -> release -> wait for the release workflow                |
| `make build` \| `bld`                   | Build wheel + sdist                                                            |
| `make clean` \| `cl`                    | Remove build artifacts and caches                                              |
| `make clean-all`                        | Remove build artifacts, caches AND every virtualenv (`.venv*`)                 |
| `make dependencies` \| `deps` `[-u]`    | Check (or `--update`) project dependencies                                     |
| `make ensure`                           | Install missing external tools for this OS (see section 5)                     |
| `make custom <name> [args...]`          | Run a user-defined pipeline (section 6)                                        |
| `make help`                             | List available targets                                                         |

Run `bmk --help` or `bmk <command> --help` for the complete, current list (there are also `config`,
`config-deploy`, `send-email`, `run`, `info`, `logdemo`, ...).

## 4. Output format: JSON by default

`bmk test` / `bmk testintegration` default to **machine-readable JSON** and stay silent on success --
tool output is captured and shown **only when a stage fails**. To get the full verbose run:

- `make test-human` / any command with `--human`, **or**
- set `BMK_OUTPUT_FORMAT=text`.

Precedence: `--human` (forces text) > `BMK_OUTPUT_FORMAT` > default (`json`). If a run "does nothing
visible", that is JSON mode succeeding -- add `--human` to watch it work.

## 5. Missing external tools: `bmk ensure`

Some pipeline stages call external tools (git, pwsh, shellcheck, shfmt, bashate, PSScriptAnalyzer).
If a run complains one is missing:

```bash
make ensure                 # install everything missing for this OS
bmk ensure --dry-run        # just report what would be installed
bmk ensure --strict         # non-zero exit if anything is still missing
```

## 6. Configuration and custom pipelines

**Layered config** is merged from defaults + files + env by `lib_layered_config`. Inspect and override:

```bash
make config                                   # show the merged config
bmk --profile production test                 # load a named profile
bmk --set email.from_address=me@example.com test   # one-off override (repeatable)
```

**Custom pipelines:** add, remove or replace stages under `[tool.bmk.pipelines.<prefix>]` in the
project's `pyproject.toml` (or `bmk_makescripts/stages.toml`). Each stage is a declarative argv list.
Run one with `bmk custom <name>` / `make custom <name>`. This is the only override mechanism.

**Test markers: what `make test` runs.** `make test` runs `pytest -m "not <exclude-markers>"`,
where `exclude-markers` comes from `[tool.scripts.test].exclude-markers` and **defaults to
`"integration"`**. So out of the box `make test` runs your unit tests AND `local_only` tests and
skips `integration`; `make testintegration` runs `-m integration`; a CI job typically runs
`pytest -m "not local_only"`. The local-vs-CI difference is intentional - `make test` is not meant
to be identical to CI.

| Marker                                                              | Meaning                                                                    | Where it runs                                                    |
|---------------------------------------------------------------------|----------------------------------------------------------------------------|------------------------------------------------------------------|
| `local_only`                                                        | needs a local resource the CI runners lack (a service, device, OS feature) | `make test` LOCALLY (guard with `skipif`); excluded from CI      |
| `integration`                                                       | long-running / external                                                    | `make testintegration` only; skipped by `make test`              |
| `os_agnostic` / `os_windows` / `os_macos` / `os_posix` / `os_linux` | labels the target OS                                                       | a label only - pair each with its own `skipif(sys.platform ...)` |

Raise `exclude-markers` only to skip MORE from `make test` - e.g. a project whose `local_only`
tests MUTATE the host and are unsafe on a real dev machine can tag them `mutating` and set
`exclude-markers = "mutating"` (a common project-specific marker). Do NOT set it to "match CI" -
that drops the fast local coverage `local_only` exists to provide.

bmk runs pytest in **this project's own `.venv`** (section 1), which it syncs with the project's
`[dev]` extra, so `[dev]`-only test-import deps (fakes, test-support libraries, property-test
helpers) are present. That is the same venv pyright and pip-audit resolve, so the suite, the type
check and the audit all describe one environment.

## Troubleshooting

| Symptom                                                                             | Cause / fix                                                                                                                                                                                                                                    |
|-------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make test` prints almost nothing                                                   | JSON mode succeeding (output shown only on failure). Use `--human` to see it.                                                                                                                                                                  |
| A stage fails: `<tool>` not found                                                   | Install it with `make ensure` (section 5).                                                                                                                                                                                                     |
| `make: command not found` (Windows)                                                 | Install a `make` (`choco install make` / GnuWin32). bmk itself needs no shell.                                                                                                                                                                 |
| `bmk: command not found`                                                            | uv's tool bin dir is not on your PATH. You do not need it there - inside a project use `make <target>` (the Makefile calls the absolute path); to bootstrap a new one use `uvx bmk install`. To put it on PATH anyway: `uv tool update-shell`. |
| Tools resolve the wrong deps / import errors                                        | Rebuild the PROJECT's venv (that is what the gates resolve): `rm -rf .venv && make test`.                                                                                                                                                      |
| `make` keeps using an old bmk right after a release                                 | uv's cached index has not caught up. The Makefile already passes `--refresh-package bmk`; just re-run `make`.                                                                                                                                  |
| `make test` runs host-mutating `local_only` tests you want only on a throwaway host | Tag those tests `mutating` and set `[tool.scripts.test].exclude-markers = "mutating"` (section 6). `make test` running `local_only` is by design - do NOT exclude `local_only` to "match CI".                                                  |
| `make test` fails on a `[dev]`-only import                                          | bmk runs pytest in this project's `.venv`, synced with the `[dev]` extra. Rebuild it: `rm -rf .venv && make test`.                                                                                                                             |
| Private GitHub deps fail to resolve                                                 | `git config --global url."https://<TOKEN>@github.com/<ORG>/".insteadOf ...` before install.                                                                                                                                                    |

## Further reading

Self-contained above; for depth, read these (WebFetch the URL, or the local clone if you have it):

| Topic                            | URL                                                        |
|----------------------------------|------------------------------------------------------------|
| Overview + full command table    | https://github.com/bitranox/bmk/blob/master/README.md      |
| Every install method             | https://github.com/bitranox/bmk/blob/master/INSTALL.md     |
| Configuration reference          | https://github.com/bitranox/bmk/blob/master/CONFIG.md      |
| Development / architecture notes | https://github.com/bitranox/bmk/blob/master/DEVELOPMENT.md |
