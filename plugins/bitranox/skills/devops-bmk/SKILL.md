---
name: devops-bmk
description: >-
  Use when installing, configuring or running bmk - the bitranox cross-OS
  build/test/release task runner - in a project: bootstrapping it with uv,
  deploying its Makefile (bmk install), running make test / push / bump /
  release / ship, fixing missing external tools (bmk ensure), reading its
  JSON-by-default vs --human output, layered config with --profile / --set,
  or defining custom staged pipelines. Works on Linux, macOS and Windows.
---

# devops-bmk

Install, configure and use **bmk** -- a cross-OS CLI task runner that orchestrates a project's
**build, test, clean, release** and custom staged commands from a single thin `Makefile`. It runs
a pure-Python stage runner (no shell/PowerShell scripts), so the same commands work natively on
Linux, macOS and Windows. Source and docs: https://github.com/bitranox/bmk

**Mental model:** you install bmk once with `uv`, drop a bmk-managed `Makefile` into the project,
and from then on you drive everything through `make <target>` (which delegates to bmk). Each command
runs a **pipeline** of stages grouped by an order number: stages run sequentially and fail-fast;
stages sharing the same order run in parallel.

## When to use

- Setting up bmk in a new or existing project (`uv tool install bmk --with .`, then `bmk install`).
- Running the standard dev loop: `make test`, `make push`, `make bump-patch`, `make release`, `make ship`.
- A tool the pipeline needs is missing (shellcheck, shfmt, pwsh, ...) -> `bmk ensure`.
- Output is empty/terse and you want the full verbose run -> `--human` / `BMK_OUTPUT_FORMAT=text`.
- Customising the config (profiles, `--set` overrides) or adding a `custom` pipeline.

**Not for:** developing bmk's own source (that is the bmk repo's `CLAUDE.md`/`CONTRIBUTING.md`). This
skill is about *using* bmk as a task runner in any project.

## 1. Install

bmk installs as a persistent `uv tool` together with the current project's dependencies, so the
tools it drives (pytest, pyright, pip-audit, ...) can resolve the full dependency tree.

```bash
# Install uv first if needed (https://astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS/Linux
# Windows (PowerShell): powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install bmk + this project's deps into a persistent venv
uv tool install bmk --with .

bmk --version        # verify
```

Alternatives: `pipx install bmk`, `pip install bmk`, or `pip install "git+https://github.com/bitranox/bmk"`.
The persistent venv lives at `~/.local/share/uv/tools/bmk/` -- no project `.venv` is needed, which
works on network shares that do not support symlinks.

## 2. Bootstrap the Makefile

```bash
bmk install        # writes / updates a bmk-managed Makefile in the current directory
make test          # from now on, drive everything through make
```

The Makefile keeps bmk + the project's deps in sync automatically before every target, so once it
is in place you rarely call `bmk` directly. On **Windows** you still need a `make` implementation
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

## Troubleshooting

| Symptom                                      | Cause / fix                                                                                 |
|----------------------------------------------|---------------------------------------------------------------------------------------------|
| `make test` prints almost nothing            | JSON mode succeeding (output shown only on failure). Use `--human` to see it.               |
| A stage fails: `<tool>` not found            | Install it with `make ensure` (section 5).                                                  |
| `make: command not found` (Windows)          | Install a `make` (`choco install make` / GnuWin32). bmk itself needs no shell.              |
| `bmk: command not found` after install       | Ensure `~/.local/bin` is on PATH; re-run `uv tool install bmk --with .`.                    |
| Tools resolve the wrong deps / import errors | Re-sync the tool venv: `uv tool install --reinstall bmk --with .`.                          |
| Private GitHub deps fail to resolve          | `git config --global url."https://<TOKEN>@github.com/<ORG>/".insteadOf ...` before install. |

## Further reading

Self-contained above; for depth, read these (WebFetch the URL, or the local clone if you have it):

| Topic                            | URL                                                        |
|----------------------------------|------------------------------------------------------------|
| Overview + full command table    | https://github.com/bitranox/bmk/blob/master/README.md      |
| Every install method             | https://github.com/bitranox/bmk/blob/master/INSTALL.md     |
| Configuration reference          | https://github.com/bitranox/bmk/blob/master/CONFIG.md      |
| Development / architecture notes | https://github.com/bitranox/bmk/blob/master/DEVELOPMENT.md |
