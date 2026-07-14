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
the project, and from then on drive everything through `make <target>`. The Makefile installs bmk
into the project's own `.venv-bmk` and delegates to it. Each command
runs a **pipeline** of stages grouped by an order number: stages run sequentially and fail-fast;
stages sharing the same order run in parallel.

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

Prefer `uvx` over `uv tool install bmk`. A machine-wide bmk is not used by anything - `make` runs
`./.venv-bmk/bin/bmk` - so it only sits on PATH going stale, and then `bmk --version` reports a
version no project is actually using.

### bmk's own env is per project

Once a project has the Makefile (section 2), `make` installs bmk into **that project's**
`.venv-bmk`, together with the project's dependencies, and runs `./.venv-bmk/bin/bmk` directly -
never a bare `bmk` from PATH. This matters because the env carries the project's dependencies: one
machine-wide env cannot serve two projects, so whichever ran `make` last would win and the other
would silently get the wrong dependency tree.

- The install runs on **every** `make`: `uv tool install --reinstall bmk` re-resolves the
  unpinned spec against PyPI, so a new bmk release and any dependency change are picked up
  automatically, before bmk starts. It costs a couple of seconds per invocation.
- `.venv-bmk` is disposable: delete it and the next `make` rebuilds it. It is kept out of git
  automatically.

### The project venv `.venv`

Separate from `.venv-bmk` above: before any command that touches the Python environment (`test`,
`push`, `deps`, `build`, ...), bmk creates the project's own `.venv` if it is missing and syncs it
to `pyproject.toml`. Every install and every gate targets **that** venv, never bmk's own and never
whatever venv happens to be active in your shell -- so no project can quietly install its
dependencies into a shared environment it does not own.

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
re-resolve); remove it by hand when you want it gone. bmk also keeps the venv out of git: it adds
the venv names to `.gitignore` when nothing already ignores them, and if git is *tracking* a venv
it drops it from the index (`git rm --cached`) while leaving the files on disk, announcing that it
did. A tracked venv would otherwise show thousands of modified files after every sync.

## 2. Bootstrap the Makefile

```bash
bmk install        # writes / updates a bmk-managed Makefile in the current directory
make test          # from now on, drive everything through make
```

The Makefile keeps bmk + the project's deps in sync in the project's own `.venv-bmk`, rebuilding
only when `pyproject.toml` changes, so once it is in place you rarely call `bmk` directly. On **Windows** you still need a `make` implementation
(`choco install make`, or GnuWin32 Make) -- bmk itself needs no shell.

## 3. Everyday commands

Drive these with `make <target>` (or call `bmk <command>` directly). Arguments after the target are
forwarded (e.g. `make push fix login bug`). Most have short aliases.

| Target / command                        | What it does                                                                   |
|-----------------------------------------|--------------------------------------------------------------------------------|
| `make test` \| `t`                      | Full test pipeline: lint, format-check, type-check, security, tests + coverage |
| `make test-human` \| `th`               | Same, forced human-readable (verbose) output                                   |
| `make testintegration` \| `ti`          | Integration tests only (`pytest -m integration`)                               |
| `make bump-patch` / `-minor` / `-major` | Bump version in `pyproject.toml` and update the changelog                      |
| `make commit` \| `c` `[MESSAGE...]`     | Git commit with a timestamped message                                          |
| `make push` \| `p` `[MESSAGE...]`       | Run tests, commit, then push to the remote                                     |
| `make release` \| `r`                   | Tag `vX.Y.Z`, push, create the GitHub release via `gh`                         |
| `make ship` \| `sh`                     | push -> wait for CI -> release -> wait for the release workflow                |
| `make build` \| `bld`                   | Build wheel + sdist                                                            |
| `make clean` \| `cl`                    | Remove build artifacts and caches                                              |
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

bmk runs pytest in this project's own `.venv-bmk` (section 1), which is installed with the project's
`[dev]` extra, so `[dev]`-only test-import deps (fakes, test-support libraries, property-test
helpers) are present and `make test` matches CI.

## Troubleshooting

| Symptom                                                                             | Cause / fix                                                                                                                                                                                   |
|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make test` prints almost nothing                                                   | JSON mode succeeding (output shown only on failure). Use `--human` to see it.                                                                                                                 |
| A stage fails: `<tool>` not found                                                   | Install it with `make ensure` (section 5).                                                                                                                                                    |
| `make: command not found` (Windows)                                                 | Install a `make` (`choco install make` / GnuWin32). bmk itself needs no shell.                                                                                                                |
| `bmk: command not found`                                                            | Expected - bmk is not meant to be on PATH. Inside a project use `make <target>` (it runs `./.venv-bmk/bin/bmk`); to bootstrap a new one use `uvx bmk install`.                                |
| Tools resolve the wrong deps / import errors                                        | Rebuild this project's bmk env: `rm -rf .venv-bmk && make test`.                                                                                                                              |
| `make test` runs host-mutating `local_only` tests you want only on a throwaway host | Tag those tests `mutating` and set `[tool.scripts.test].exclude-markers = "mutating"` (section 6). `make test` running `local_only` is by design - do NOT exclude `local_only` to "match CI". |
| `make test` fails on a `[dev]`-only import                                          | bmk runs pytest in this project's `.venv-bmk`, installed with the `[dev]` extra. Rebuild it: `rm -rf .venv-bmk && make test`.                                                                 |
| Private GitHub deps fail to resolve                                                 | `git config --global url."https://<TOKEN>@github.com/<ORG>/".insteadOf ...` before install.                                                                                                   |

## Further reading

Self-contained above; for depth, read these (WebFetch the URL, or the local clone if you have it):

| Topic                            | URL                                                        |
|----------------------------------|------------------------------------------------------------|
| Overview + full command table    | https://github.com/bitranox/bmk/blob/master/README.md      |
| Every install method             | https://github.com/bitranox/bmk/blob/master/INSTALL.md     |
| Configuration reference          | https://github.com/bitranox/bmk/blob/master/CONFIG.md      |
| Development / architecture notes | https://github.com/bitranox/bmk/blob/master/DEVELOPMENT.md |
