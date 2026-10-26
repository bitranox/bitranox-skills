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
to drop the Makefile in - from then on the Makefile installs and updates bmk for you, in one env
shared by every project on the machine (see below).

```bash
# Install uv first if needed (https://astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh          # macOS/Linux
# Windows (PowerShell): powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

cd your-project
uvx bmk install            # writes the Makefile and .bmk-cooldown.mk; installs nothing permanently
make test                  # from here on, everything goes through make
```

You do not need `uv tool install bmk` yourself: once the Makefile is in place it keeps bmk
installed for you (see below). `uvx bmk install` is only the bootstrap that writes the Makefile
and its companion `.bmk-cooldown.mk`. **Commit both**: they are versioned as a pair (the Makefile's
first line carries the version), and `bmk install`, or a `make` that finds the Makefile outdated,
rewrites them together (a `make` only in JSON mode or when answered; section 4).

### bmk's env holds bmk alone, and is shared

Once a project has the Makefile (section 2), every `make` first runs

```bash
uv tool upgrade bmk        # falls back to `uv tool install --reinstall --force` if damaged
```

which keeps **bmk on its own** in uv's default tool dir and runs it from there
(`$(uv tool dir --bin)/bmk`). Note what is *not* in that command: your project. The env holds
bmk's toolchain and nothing of yours, which is exactly why one env can serve every repo on the
machine - there is nothing project-specific in it to collide.

Do **not** add `--with .` / `--with-editable ".[dev]"`, and do not redirect it per project with
`UV_TOOL_DIR`. Resolving bmk *together with* a project is what caused, in order: one of your
dependencies capping one of bmk's and silently pinning bmk to an ancient release; a yanked
transitive making bmk itself uninstallable; and the tests running in that co-resolved env while
pyright and pip-audit inspected your real `.venv`, so the suite and the audit described different
environments.

- It runs on **every** `make`, deliberately, so a new bmk release is picked up with nothing to
  remember and no version marker to go stale. Do not gate it behind a stamp file: make would skip
  it and the env would silently pin itself to whatever bmk it first saw.
- It **upgrades**; it does not reinstall on the common path. `uv tool upgrade` revalidates the
  index on every run and is a near no-op when bmk is already current. A
  `--reinstall --force` on every `make` would tear the shared env down, deleting the site-packages
  out from under a bmk still *running* in another repo.
  `--refresh` is not needed and uv rejects it (exit 2); offline it simply answers
  "Nothing to upgrade".
- **The rebuild waits for the bmk processes using that env.** Every bmk holds a shared lock on
  the tools root for its lifetime; the upgrade takes the same lock exclusively. Readers do not
  exclude each other, so two repos still gate at the same time - only a *mutation* waits. The
  wait is bounded: an upgrade that cannot get the lock is skipped (the first `make` after the
  running bmk processes exit takes it), while a repair that cannot get it fails rather than
  continuing on a damaged env. Set `BMK_TOOL_LOCK=0` to disable it. **You do not need a
  caller-side lock** (a `flock` around `make`, a coordinator mutex) to stop two repos colliding
  here - and a caller-side one is worse, because it serialises whole gates where bmk serialises
  only the provisioning.
- Two writers stay out of reach by construction: a repo whose Makefile predates this is unguarded
  until a `make` regenerates it (section 4: a text-mode `make` without a terminal never does),
  and a hand-run `uv tool install bmk` always is. So when a
  command fails and the env turns out to have been replaced mid-run, bmk says so on stderr rather
  than leaving an ImportError inside its own dependencies to look like a flake.
- **A `ModuleNotFoundError` whose traceback runs through bmk's own entry point and names a module
  inside bmk's dependencies is bmk's env, not your code.** Before every target the Makefile runs
  `bmk_selfcheck`, which compares each installed package's file list against the disk and
  reinstalls on a missing file, so the next `make` repairs it. Meanwhile check your change with the
  project venv's own tools (`.venv/bin/python -m pytest`, `-m pyright`), then re-run `make` once.
- **`[bmk] another bmk is using the shared tool environment; waited 10s ... and gave up. Nothing
  was changed.`** speaks only for the bmk upgrade, which is skipped; the target you ran continues
  and its result is its own. Do not re-run a `release` or bump past a version on that line: check
  the outcome where it lands (`git ls-remote --tags origin v<version>`, `gh release view
  v<version>`, the release workflow, PyPI).
- **A repo still running the old bmk after a release is usually that skip, not uv's cache.**
  Every running bmk holds the shared lock for its whole run, a hung one included (one waiting on
  the Makefile prompt, section 4), so every `make` elsewhere skips the upgrade until those
  processes exit, and re-running alone does not help. Grep the `make` output for
  `another bmk is using the shared tool environment`, then look for live bmk processes (a working
  directory in another repo, an age far beyond a gate's runtime): let them finish, or answer or
  kill a hung one, and the next `make` upgrades. Do not reach for uv cache flags: `uv tool upgrade`
  already revalidates the index on every run, so a `--no-cache` upgrade that works right after
  those processes exited gets credit it did not earn, and a hand-run upgrade takes no bmk lock.
- Right after a release there is a brief window where uv's index still reports only the previous
  version; the next `make` picks the new one up.
- **bmk's env resolves under bmk's own supply-chain cooldown**, read from `.bmk-cooldown.mk` beside
  the Makefile. The file holds uv flags - bmk's cooldown window plus `false`
  exemptions for bmk and its own libraries - so a dependency release does not reach the env that
  runs every repo's ruff, pyright and pip-audit a minute after its upload. Do not hand-edit it;
  `bmk install` rewrites it. When the window cannot be met (a fresh install whose bmk floor is
  younger than the window), the `make` installs without it and says so on stderr, and the next
  `make` has the window again. A repo without the file installs bmk with no cooldown.

### The project venv `.venv`

This is where **your** dependencies live. Before any command that touches the Python environment
(`test`, `push`, `deps`, `build`, ...), bmk creates the project's own `.venv` if it is missing,
locks the project (`uv lock`) and syncs the venv from that lock (`uv sync --locked`), so it holds
exactly what `uv.lock` pins and CI installs. pytest, pyright and pip-audit all resolve **that**
venv, never bmk's own and never whatever venv happens to be active in your shell -- so the
environment you test in, type-check in and audit are one and the same, and no project can quietly
install its dependencies into an environment it does not own.

**One bmk provisions a venv at a time.** The sync is serialised by an exclusive lock scoped to
that one venv path, so a subagent's `make test` beside yours - or `test-all` beside `test` - cannot
reinstall packages under a running gate. Unguarded, the loser would not crash: provisioning
degrades rather than raising, so it would silently test a different environment. `BMK_VENV_LOCK_TIMEOUT`
(default 600s) bounds the wait and `BMK_VENV_LOCK_DIR` says where the lock files live (outside every
repository). Because the scope is one venv path, `test-all` still provisions its versions in
parallel.

**Which Python it is built on: the newest your classifiers declare, on the patch uv builds it on.**

```toml
[project]
requires-python = ">=3.10"                     # a FLOOR - says nothing about the newest
classifiers = [
  "Programming Language :: Python :: 3",       # ignored: no minor
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.14",    # <- .venv is built on 3.14 (latest patch under uv's default python-preference)
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
Which interpreter counts is uv's choice, so "latest patch" holds only under uv's default
`python-preference`: bmk rebuilds only when the venv differs from what `uv venv --python X.Y`
would use, which `uv python find --system --show-version X.Y` reports. Under
`UV_PYTHON_PREFERENCE=system` the venv stays on the distro Python instead of rebuilding every run.
Declare no `:: Python :: X.Y` classifier and bmk picks no version at all - uv's default stands.

The same classifiers drive `make test-all`: it provisions one `.venv-<minor>` per declared version
and runs pytest + pyright in each, in parallel by default, so you can reproduce CI's Python-version
matrix locally before you push. Each cell's pyright makes the same per-OS runs as `make test`'s
pyright stage (section "Proving a gate"), so a type error on any OS in `[tool.ci].os` fails the cell
for that Python version; pytest runs on the host OS only. A project whose suite binds fixed ports or
shares a test database sets `[tool.scripts.test-all] workers = 1` in its `pyproject.toml` (or
`BMK_TEST_ALL_WORKERS=1` for one run) to run the version cells serially instead. Inside a cell,
pytest runs across processes when that cell's pytest loads pytest-xdist; pytest-cov is not needed,
since a cell measures no coverage and checks no floor, and a cell without xdist runs serially
without a hint. `[tool.scripts.test] workers = "auto"` (the default) is divided between the cells
running at once (CPU count // cells, at least 1); an explicit count goes to EVERY cell unchanged, so
six cells with `workers = 8` start 48 workers. Plain `make test`
stays on the newest version only; with no `:: Python :: X.Y` classifier, `test-all` tests the
default interpreter once and prints a WARNING naming the version it used.

Free-threaded cells come from `[tool.ci] free-threaded`, the same key CI's `X.Yt` jobs come from:
each `"X.Y"` it lists adds a second `test-all` cell (pytest + pyright, like every cell) on that
version's free-threaded build (`3.15t`, venv `.venv-3.15t`), next after the regular cell in the cell
order. `make test` is unaffected. An entry CI would refuse is refused before anything installs
(exit 2): a value that is not an array, an entry that is not an `"X.Y"` string (so `"3.15t"` is
refused), and a version no `Programming Language :: Python :: X.Y` classifier declares. A missing
`Programming Language :: Python :: Free Threading :: <level>` classifier only prints a WARNING; the
run goes on.

```toml
[project]
classifiers = [
  "Programming Language :: Python :: 3.15",
  "Programming Language :: Python :: Free Threading :: 2 - Beta",
]

[tool.ci]
free-threaded = ["3.15"]
```

The venv is synced FROM THE LOCK, not from `pyproject.toml`: `uv lock` brings `uv.lock` in line
with the manifest, then `uv sync --locked` makes the venv exactly what the lock pins. Installing
from the manifest instead (`uv pip install --upgrade`) keeps any installed release that still
satisfies it, even one newer than your `[tool.uv]` cooldown admits, so the gates would check a
different tree from the one the lock pins and CI installs. The sync is exact: it removes every
package the lock does not pin for the extras bmk requests. A venv left to drift makes the gates
lie -- pip-audit reports CVEs for packages the project does not actually resolve, while the real
resolution stays hidden. The trade-off: **packages you installed into the venv by hand do not
survive a sync.**

Only when no lock can be made (a `[venv] uv lock failed` line, below) does bmk fall back to
installing from `pyproject.toml`, with `--exact --upgrade`. Moving the lock onto newer releases is
not provisioning's job: provisioning's `uv lock` only brings an existing lock in line with the
manifest, and `make test`'s first stage, `update_deps` (it runs the `deps_update` pipeline), runs
`uv lock --upgrade` and then re-syncs the venv from the new lock.

| Env var                  | Effect                                                                                                    |
|--------------------------|-----------------------------------------------------------------------------------------------------------|
| `UV_PROJECT_ENVIRONMENT` | Venv path (absolute, or relative to the project). Default `.venv`.                                        |
| `BMK_NO_VENV_SYNC=1`     | Skip provisioning and the `deps_update` re-sync (it still upgrades `uv.lock`); use the environment as-is. |

Set `UV_PROJECT_ENVIRONMENT` when one checkout is used from more than one OS (a share mounted on
both Linux and Windows): a single venv cannot serve both, so give each its own (e.g. `.venv-win`).
If provisioning fails, the command still runs: the gates use the venv as the failed step left it, or
bmk's own interpreter when no real venv (no `pyvenv.cfg`) is left at that path. `make test` (and
`make push`, which runs it after its own `deps` check) is the exception whenever a venv is still
there to sync: its first stage, `update_deps`, runs the `deps_update` pipeline, which re-syncs from
the lock its `uv lock --upgrade` produced and fails the run if that sync fails. When this run's
provisioning already failed and the upgrade left `uv.lock` byte-for-byte unchanged, it does not
retry; it fails with one line, `<project>: venv provisioning already failed above; uv.lock unchanged
by the update, not retrying`, and the report to read is the `[venv]` one printed before the
pipeline. A failed provisioning that left no venv passes that stage, and the gates fall back to
bmk's own interpreter.

**A gate reporting versions that disagree with `pyproject.toml`** (pip-audit flagging a version the
manifest excludes, or the project's own package at an old version) is not cured by deleting
`.venv`: the next env-touching `make` re-syncs it, and deleting it only forces a full re-resolve.
When the mismatch survives a re-run, check `BMK_NO_VENV_SYNC`, then read the stderr of a run that
showed it (send stderr to a file for an unattended run). Every failed provisioning step prints a
`[venv]` header, in every output mode: in JSON mode a colon and all of uv's own stderr follow it,
indented (the header stands alone when uv printed nothing); in text mode the header comes alone,
after uv's live output.

| Header                                                                                                         | Means                                                                 |
|----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| `[venv] uv venv failed for <venv> (exit <rc>; venv afterwards: <state>)`                                       | The venv could not be created; nothing was synced.                    |
| `[venv] uv lock failed in <project> (exit <rc>); provisioning <venv> from pyproject.toml instead`              | No lock could be made, so bmk falls back to the manifest install.     |
| `[venv] uv pip install (fallback from pyproject.toml) failed for <venv> (exit <rc>; venv afterwards: <state>)` | That fallback failed too.                                             |
| `[venv] uv sync from uv.lock failed for <venv> (exit <rc>; venv afterwards: <state>)`                          | The lock was made but the venv could not be synced; no fallback runs. |

A `[venv] uv lock failed` line WITHOUT `(exit <rc>)` means uv never ran: another bmk held the
project's lock, and an earlier stderr line says so (`[venv] another bmk is still locking ...`).
`<state>` says what the gates ran in: `venv` is the unsynced venv (the stale versions you see),
while `directory without pyvenv.cfg`, `empty directory` or `absent` means bmk's own interpreter, so
pip-audit audited bmk's packages rather than the project's.
Do not re-run just to see the error: a sync failure can be intermittent, and a re-run that passes
leaves nothing to read. Only when no failed run's stderr was kept, run again with stderr going to a
file; for a `[venv]` failure a text-mode re-run adds nothing, since JSON mode already prints uv's
stderr under the header.

To resync by hand, do what bmk does: `uv lock`, then
`UV_PROJECT_ENVIRONMENT=.venv uv sync --locked --python <X.Y> --no-default-groups --extra dev`.
`<X.Y>` is your highest `:: Python :: X.Y` classifier. With none, bmk asks for what the venv's own
interpreter (`.venv/bin/python`, on Windows `.venv\Scripts\python.exe`) reports: `pypy@X.Y` for
PyPy (its `--version` output names PyPy; `X.Y` is the Python version on the first line, not PyPy's
own: `pypy@3.11`), `X.Yt` for a free-threaded build (`3.13t`, where
`.venv/bin/python -c "import sysconfig; print(sysconfig.get_config_var('Py_GIL_DISABLED'))"`
prints `1`), otherwise the bare minor (`.venv/bin/python --version` printing `Python 3.10.19`
means `--python 3.10`). Use these and nothing else: a bare minor for a PyPy or free-threaded venv
lets a recreate fall back to uv's default CPython. bmk passes the interpreter's path only when that
interpreter cannot report its version (then uv could not build from it either); never type the path
by hand, on any version, because on CPython 3.10 and older it leaves an empty venv when uv
recreates it. Pass
`--extra dev` only if the project declares a `dev` extra, since uv refuses an undeclared one
(exit 2), and `--no-default-groups` keeps `[dependency-groups]` out, as bmk does. For a
`test-all` cell use its `.venv-<minor>` and that minor, and for another venv path the one
`UV_PROJECT_ENVIRONMENT` names. The sync uninstalls whatever no extra on that command line pulls
in. The manifest install, `uv pip install --python .venv/bin/python --exact --upgrade -e ".[dev]"`
(`-e .` for a project without a `dev` extra), is the right resync ONLY after a `[venv] uv lock
failed` line, never after a sync failure: it keeps releases newer than the lock pins, which is the
drift the lock-first sync exists to prevent.

`clean` does not delete the venv (that would throw away what bmk just built and force a full
re-resolve); `make clean-all` removes every `.venv*` alongside the build artifacts when you do
want them gone. bmk also keeps venvs out of git: it adds a single `.venv*` glob to `.gitignore`
when nothing already ignores them (one line covers `.venv` and every `.venv-<minor>` the matrix
creates), and if git is *tracking* a venv it drops it from the index (`git rm --cached`) while
leaving the files on disk, announcing that it did. A tracked venv would otherwise show thousands
of modified files after every sync.

## 2. Bootstrap the Makefile

```bash
uvx bmk install    # writes / updates a bmk-managed Makefile in the current directory
                   # (`uvx` so this works before bmk is on PATH; plain `bmk install` once it is)
make test          # from now on, drive everything through make
```

The Makefile keeps bmk installed and your project's `.venv` synced from `uv.lock` (which bmk keeps
in line with `pyproject.toml`), so once it is in place you rarely call `bmk` directly. On
**Windows** you still need a `make` implementation. On a non-admin box install it user-scope with
`winget install --id ezwinports.make -e --scope user` (run `make` from Git Bash so the Makefile's
`SHELL := /bin/bash` resolves); `choco install make` needs an elevated shell. bmk itself needs no
shell.

## 3. Everyday commands

Drive these with `make <target>` (or call `bmk <command>` directly). Arguments after the target are
forwarded (e.g. `make push fix login bug`). Most have short aliases.

| Target / command                        | What it does                                                                               |
|-----------------------------------------|--------------------------------------------------------------------------------------------|
| `make test` \| `t`                      | Full test pipeline: lint, format-check, type-check, security, tests + coverage             |
| `make test-human` \| `th`               | Same, forced human-readable (verbose) output                                               |
| `make test-all`                         | Run pytest + pyright on EVERY declared Python version, plus each free-threaded `X.Yt` cell |
| `make testintegration` \| `ti`          | Integration tests only (`pytest -m integration`)                                           |
| `make codecov` \| `cov`                 | Upload the coverage report to Codecov                                                      |
| `make bump-patch` / `-minor` / `-major` | Bump version in `pyproject.toml` and update the changelog (rules below)                    |
| `make commit` \| `c` `[MESSAGE...]`     | Git commit with a timestamped message                                                      |
| `make push` \| `p` `[MESSAGE...]`       | Run tests, commit, then push to the remote                                                 |
| `make release` \| `r`                   | Tag `v` + the current version, push, create the GitHub release via `gh`                    |
| `make ship` \| `sh`                     | push -> wait for CI -> release -> wait for the release workflow                            |
| `make build` \| `bld`                   | Build wheel + sdist                                                                        |
| `make clean` \| `cl`                    | Remove build artifacts and caches                                                          |
| `make clean-all`                        | Remove build artifacts, caches AND every virtualenv (`.venv*`)                             |
| `make dependencies` \| `deps` `[-u]`    | Check (or `--update`) project dependencies                                                 |
| `make ensure`                           | Install missing external tools for this OS (see section 5)                                 |
| `make custom <name> [args...]`          | Run a user-defined pipeline (section 6)                                                    |
| `make help`                             | List available targets                                                                     |

**`release` does not bump; `push` always commits.**

- `release` tags `v` + the version already in `pyproject.toml`, on HEAD, and refuses a dirty tree;
  it pushes the CHECKED-OUT branch (`[release] Pushing branch <branch> to <remote>`), then the
  tag, so a local release commit needs no separate push.
- **Release from a checkout on the default branch.** Run on a topic branch (a worktree is the usual
  case), `release` creates or updates THAT branch on the remote, a public one included, where it
  reads as real work; nothing in the output flags it. Fast-forwarding the default branch first does
  not prevent it. Afterwards run `git ls-remote --heads origin <branch>`; if the branch is there at
  the same commit as `origin/<default>`, delete it with `git push origin --delete <branch>`.
- When the `pyproject.toml` version is committed but not yet tagged
  (`git tag --list "v<version>"` is empty), release it directly: running `bump` first moves past
  it and that version is never published.
- `release` counts only TRACKED changes as dirty (`git diff`, `git diff --cached`); an untracked
  file does not stop it. On `[release] Working tree not clean. Commit or stash changes first.`, do
  not commit an edit that is not part of this release to get past it: the tag lands on HEAD, so it
  would land on a commit CI never ran. Copy the edit aside (or `git stash push -m <name>`, then
  pop the `stash@{N}` that `git stash list` shows under that name, never a bare `pop`: the stash
  list is shared by every worktree), run `release`, then restore it. An edit that belongs in the
  release, bmk's own Makefile or floor churn from a `make test` included, is committed (with git
  and those paths, since `push` would sweep in untracked files too) and pushed first; `release`
  never checks CI, so you wait until CI is green on that commit before running it.
- `push` stages with `git add -A`, so every untracked, non-ignored file rides along; check
  `git status` first. With nothing staged it makes an empty commit, so a `push` after the release
  commit is already pushed leaves `release` tagging that empty commit. That is expected, not a
  broken release.
- **On an already-committed tree, the `push` commit's subject is the only record of what the push
  carried.** That empty commit is titled `<timestamp> - <message>`, where the message is the
  trailing words (`make push fix login bug`), else `MSG="..."` (the safe channel for punctuation,
  exported as `BMK_COMMIT_MESSAGE`), else a prompt on a terminal, else the literal `chores`. Pass a
  message that names what the push carries, or skip `push`: run `make test`, commit what it
  changed (Makefile, dependency floors), then a plain `git push` only if it passed, so the history
  keeps only the commits that carry work.
- **A message with punctuation goes in `MSG="..."`, never `ARGS=` or trailing words.** `ARGS=`
  and trailing words are pasted into the recipe text and parsed by bash; `MSG=` is exported to bmk
  through the environment and never touches a command line. How far `ARGS` breaks depends on the
  recipe, and the remedy is the same either way:
  - Quoted recipe (`$(BMK) push "$(ARGS)"`, the current `push` and `commit`): `(` and `;`
    survive, but make eats a `$` (`$HOME` becomes `OME`), a backtick executes, a nested `"`
    vanishes, quotes nested as `ARGS="'...'"` land literally in the subject, and a newline is
    refused.
  - Unquoted recipe (`$(BMK) ship $(ARGS)`, and any older Makefile; check with
    `grep -A1 '^push:' Makefile`): bash re-parses the words bare, so `(` is a syntax error with
    nothing committed, and `;` runs the rest as a command while `push` still commits and pushes
    the truncated subject.

  Pass anything beyond plain words, hyphens and commas (a conventional-commit subject included)
  as `MSG="..."`, with no `ARGS=` and no trailing words beside it (those win over `MSG`), and read
  `git log -1 --format=%s` back. A Makefile that lacks the `MSG` block
  (`grep -n BMK_COMMIT_MESSAGE Makefile` finds nothing) ignores `MSG` and commits a default
  subject: refresh it first with `uvx bmk install` (section 2).
- **Gate the bumped tree, not the tree before the bump.** A bump is a code change, and a test that
  pins the version (a skill's `uvx --from 'pkg>=X'` floors equal to `[project].version`, an
  `__init__conf__` constant, a CHANGELOG heading for the current version) passes before it and
  fails in every CI cell after it. `make push` runs its tests after the bump, so `make bump-*`
  then `make push` is gated; a `git push` after the bump is not. In a script or by hand, run
  `make test` again on the bump commit and refuse to push when it fails or leaves the tree dirty
  (commit what it changed, then gate again). `make bump-*` renames the CHANGELOG's `[Unreleased]`
  heading and syncs `__init__conf__.py` and `plugin.json`, so of these pins only the SKILL.md
  floors can fail (the other pins fail after a hand or script bump): nothing in bmk edits a
  SKILL.md, so raise its `uvx` floors yourself, in the same release commit.
- `push` starts with a `deps` check (its first stage, `update_deps`, runs it) that FAILS when any
  dependency floor in `pyproject.toml` is behind the latest PyPI release (an exact pin excepted,
  see the next point), which can be minutes old. In the default JSON mode that is an
  `[update_deps] (exit code: 1)` block whose nested `[deps] (exit code: 1)` block holds only
  `(no output captured)`. Do not bisect your edits: the cause is a new
  upstream release. `BMK_OUTPUT_FORMAT=text` prints the report above that line; `bmk deps --update`
  (or a `make test`, whose first stage raises floors) fixes it. In a multi-repo sweep, one release
  of a shared dependency breaks every pending repo, so update them all before resuming. If you
  just released one of your own libraries that this project depends on, suspect the release
  cascade (next point) before a stale floor.
- **In a release cascade, wait until PyPI serves a library before pushing anything that depends
  on it.** The floor update raises a requirement on one of your OWN packages (exempt from the
  `[tool.uv]` cooldown, like every package when the project sets no cooldown) to its newest
  release as PyPI's JSON API lists it. A dependent pushed minutes after the library's publish can
  raise its floor to that version before the index serves it to uv, and the failure reads as a
  stale floor when the floor is in fact too fresh. Under `make push` the `deps` check fails first,
  with the same `[update_deps]` / nested `[deps]` / `(no output captured)` output as the
  stale-floor case above; the `bmk deps --update` (or `make test`) that fixes a stale floor then
  fails in its `[deps_update]` block
  (`<project>: uv lock --upgrade failed after the floor update`, or a failed re-sync). CI fails
  with uv's reason,
  `Because only <pkg><=<old> is available ... your requirements are unsatisfiable`. Before moving
  to the dependent, confirm both endpoints list the new version, since either can lag the other
  by minutes: `info.version` in `https://pypi.org/pypi/<pkg>/json`, and the files in
  `https://pypi.org/simple/<pkg>/`. If a run already failed this way, leave the raised floor
  alone, because it is correct: re-run once the version resolves, and release the dependent only
  after CI is green on that commit.
- **Tests that break right after a floor was raised are a dependency change, not your edit.**
  `make test`'s first stage can move a floor to a release the project never opted into. Before
  changing code, run `git diff pyproject.toml` to see which floor moved and from where, read that
  dependency's CHANGELOG entries between the old and the new floor, and adapt the caller to the
  documented change rather than patching the symptom. Example: a library that starts wrapping a
  `PermissionError` in its own error type breaks an `except PermissionError`; catch the new type
  and walk `__cause__` where the original error matters.
- **An exact pin is never moved.** The floor update reads every requirement list in
  `pyproject.toml` (`[project]` dependencies and optional extras, `[dependency-groups]`,
  `[build-system].requires`, `[tool.pdm.dev-dependencies]`) and raises `>=`, `>`, `~=` and
  wildcard (`==1.*`) requirements, a third-party one only to a release older than the project's
  `[tool.uv]` cooldown. An exact pin (`pkg==1.5.0`, `pkg===1.5.0`) is left as written and reported
  pinned (`[==]` in the `bmk deps` report), so it never fails the `deps` stage either. Use one for
  a release you hold on purpose, such as a test that compares the bytes one release produces.
- **Which bmk you are running:** `bmk --version` (run `$(uv tool dir --bin)/bmk --version` when
  `bmk` is not on your PATH). The Makefile's first line, `# BMK MAKEFILE X.Y.Z`, names the bmk
  that wrote the Makefile, not necessarily the one the next `make` runs, since every `make`
  upgrades bmk first.

### What version `bump` and `release` accept, and what they produce

`[project].version` may be any **canonical** PEP 440 version - `1.2.3`, `1.2.3a1`, `1.3.0b2`,
`1.2.3rc1`, `1.2.3.dev4`, `1.2.3.post1`, `1.0`, `1.2.3.4`, `1!2.0.0`. That is what hatchling builds
and PyPI accepts, so bmk does not narrow it to `X.Y.Z`.

`release` accepts every one of those - a pre-release is NOT refused for being one - and tags `v` +
the version string verbatim: `1.3.0b2` tags `v1.3.0b2`. Its only version check is the two shapes
below.

Two shapes are refused, each printing the fix:

| Written as                         | Refused because                                                                                                                                                                                |
|------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `v1.0.0`, `1.0.0-beta`, `1.2.3RC1` | Not canonical. `packaging` parses these but normalises them (`1.0.0`, `1.0.0b0`, `1.2.3rc1`), so the tag and the artifact hatchling uploads would disagree - and `v1.0.0` would tag `vv1.0.0`. |
| `1.2.3+local`                      | A local version. It would tag fine and then fail in CI: PyPI rejects a local version on upload.                                                                                                |

**A bump always lands on a plain three-part release, and FINALIZES a non-final version rather than
stepping past it** - so the release an rc was rehearsing stays reachable:

| current       | `bump-patch` | `bump-minor` | `bump-major` |
|---------------|--------------|--------------|--------------|
| `1.2.3`       | `1.2.4`      | `1.3.0`      | `2.0.0`      |
| `1.2.3rc1`    | `1.2.3`      | `1.3.0`      | `2.0.0`      |
| `1.3.0b2`     | `1.3.0`      | `1.3.0`      | `2.0.0`      |
| `1.2.3.dev4`  | `1.2.3`      | `1.3.0`      | `2.0.0`      |
| `1.2.3.post1` | `1.2.4`      | `1.3.0`      | `2.0.0`      |

A post release is FINAL, which is why `1.2.3.post1` increments. The epoch survives a bump; pre,
dev, post and local segments are dropped. bmk has no command that CREATES a pre-release - write one
into `pyproject.toml` yourself, then bump to finalize it.

**If the project ships a Claude Code skill**, two version rules apply and neither is optional.
An install re-fetches a skill only when `.claude-plugin/plugin.json` changes version, so a release
that edits `skills/` without moving that version ships the code and leaves every install on the old
skill - no error, nothing to notice, and the skill then documents behaviour the tool no longer has.

- `bump`, `push` and `release` raise `plugin.json` to the package version whenever it lags, and
  never lower it. The plugin version can legitimately be AHEAD, because a skill ships more often
  than the package it documents; writing the package version there unconditionally would move an
  install backward to a version it already had.
- So after `make bump-*`, do not hand-edit `plugin.json`: the bump already wrote it whenever it
  lagged. The one hand edit is the `release` refusal at the end of this list. The bump writes
  several files at once: `pyproject.toml`, `CHANGELOG.md`, `__init__conf__.py`, `plugin.json`
  when it lags, and a committed `uv.lock`, which it re-locks because the lock records the project's
  own version (left stale it fails `uv sync --locked`). Read `git status --porcelain`, check that
  the versions agree, and commit every one of those files with the bump. Where a repo's own test
  pins `plugin.json` to the `pyproject.toml` version, a plugin-only bump cannot pass it: a
  skill-only change ships there as a package patch bump.
- A **non-final** package version (`1.2.0rc1`) is NOT written into `plugin.json`. Ordering it is
  not the problem; that manifest is read by Claude Code's marketplace machinery and is only ever
  seen carrying a plain `X.Y.Z`. The final release that follows carries the skill.
- `release` refuses outright when `skills/` changed since the last tag and the plugin version did
  not move. That is the one case the sync cannot fix: no bump ran, or `plugin.json` was already
  ahead of the new package version, so there was nothing to raise. Bump `plugin.json` yourself,
  above its current version, and release again.

Run `bmk --help` or `bmk <command> --help` for the complete, current list (there are also `config`,
`config-deploy`, `config-generate-examples` (writes example TOML files with every option and its
default into `--destination`), `send-email`, `send-notification` (a plain-text notification
email), `run`, `info`, `logdemo`, ...). Most commands have more than one alias, and the table shows
one: `bump` is also `b` and `bmp`, `clean` also `cl` and `cln`, `push` also `p` and `psh`,
`codecov` also `coverage` and `cov`. From Python, `bmk.print_info()` prints the same metadata
block as `bmk info`.

## 4. Output format: JSON by default

`bmk test` / `bmk testintegration` default to **machine-readable JSON** and stay silent on success --
tool output is captured and shown **only when a stage fails**. To get the full verbose run:

- `make test-human` / any command with `--human`, **or**
- set `BMK_OUTPUT_FORMAT=text`.

The dependency check `deps` (run by `make push`'s first stage, `update_deps`) runs in-process
rather than as a tool and prints nothing in JSON mode, so its `[deps] (exit code: 1)` block, nested
inside `[update_deps] (exit code: 1)`, holds only `(no output captured)`;
`BMK_OUTPUT_FORMAT=text` shows its report. `deps_update` puts its failure lines into its captured
output, so its `[deps_update] (exit code: 1)` block names the failure in
JSON mode too: a failed re-sync shows the `[venv]` report with uv's reason, a `[tool.uv]` cooldown
uv refuses shows uv's refusal, and a failed lock upgrade is named by its step only
(`<project>: uv lock --upgrade failed after the floor update`), without uv's reason - run
`uv lock --upgrade` by hand in the project directory to see it (the floors bmk raised stay in
`pyproject.toml`, so it resolves the same manifest). `bmk deps update` /
`make dependencies-update` show that `[deps_update]` block directly; in `make test` the first stage
is `update_deps`, which runs the `deps_update` pipeline, so the block is
`[update_deps] (exit code: 1)` with the nested `[deps_update] (exit code: 1)` block inside it.

Precedence: `--human` (forces text) > `BMK_OUTPUT_FORMAT` > default (`json`). If a run "does nothing
visible", that is JSON mode succeeding -- add `--human` to watch it work.

**An outdated Makefile is handled by output mode, and an unanswered terminal hangs.** Before every
command except `install`, bmk compares the Makefile's `# BMK MAKEFILE <ver>` with itself. When the
versions differ, only `BMK_OUTPUT_FORMAT` decides (`--human` and `make test-human` do not count:
the check runs before the subcommand's options are read). A Makefile NEWER than the running bmk,
left by a skipped upgrade, is rewritten back to the older version the same way; there the remedy
is to let the next `make` upgrade bmk, not the `bmk install` the stderr line suggests:

- JSON mode (the default) replaces the Makefile without asking.
- Text mode with any stdin that is not a terminal (a pipe, `</dev/null`, a CI step, `yes y |`)
  keeps the OLD Makefile, prints `run 'bmk install' to update it` on stderr, and runs the command.
- Text mode with a terminal on stdin asks `Makefile is outdated (<old> -> <new>). Update? [y/N]`
  (the arrow prints as a Unicode character) and waits for an answer, with no timeout. A
  pseudo-terminal nobody answers (a detached tmux pane, pexpect, `ssh -tt`) is a terminal, so the
  gate blocks forever before its first stage. All that time it holds bmk's shared lock on the tool
  env (section 1), so every other repo's `make` skips its bmk upgrade with the
  `another bmk is using the shared tool environment` line until this one is answered or killed.

A hung gate looks like a slow one. When a gate shows no new output long past the suite's usual
runtime (and other repos keep skipping the bmk upgrade), read the pane's last line for the question
and look for a bmk process whose working directory is that repo and whose age is far beyond the
suite's runtime; answer or kill it rather than waiting longer. **Run unattended gates in JSON mode,
or in text mode with stdin that is not a terminal** (`BMK_OUTPUT_FORMAT=text make test </dev/null`),
and refresh an old Makefile with `bmk install`, which never asks.

## 5. Missing external tools: `bmk ensure`

Some pipeline stages call external tools (git, pwsh, shellcheck, shfmt, bashate, PSScriptAnalyzer).
If a run complains one is missing:

```bash
make ensure                 # install everything missing for this OS
bmk ensure --dry-run        # just report what would be installed
bmk ensure --strict         # non-zero exit if anything is still missing
```

**The `.sh` shell-lint gate's settings (know these before "fixing" a diff).** bmk runs
`shfmt -d -i 4 -bn -ci` and `bashate --max-line-length=<N> --ignore=<codes>`, taking `N` and the
codes from `[tool.bashate]` in `pyproject.toml` (`max-line-length`, `ignores`); with no such section
it warns and uses 120 and `E003`. Every flag matters: shfmt with the right indent but without
`-bn` (binary operators like `&&` and `|` may start a line) or `-ci` (indent switch cases) still
yields a rejected diff. And `bashate` itself reads NO config file, so run by hand without those
flags it falls back to its 79-char default and flags lines the gate accepts. Reformatting to your
local defaults instead of these values is the usual cause of "passes locally, fails the gate".

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

`make test-all` applies the same selection on every declared Python version, so it is the only
cross-version run your `local_only` tests ever get: CI excludes them. Run it before a release.
When `make testintegration` collects no test, pytest exits 5 ("no tests collected"): bmk prints
`[pytest_integration] (exit code: 5)` and exits 5, and make then prints `Error 5` and exits 2, its
code for any failed recipe. Key on the bmk line, not on make's exit code. If no test carries the
marker (no `mark.integration` in the tests), the lane is empty by construction: report it as an
empty lane, neither passed nor failed, and do not add a placeholder test. If integration tests exist
and none were collected, something is filtering them out, which is a real fault: run
`.venv/bin/python -m pytest --collect-only -m integration` to see what the lane collects. `push`, `ship` and `release` do not run this lane.

bmk runs pytest in **this project's own `.venv`** (section 1), which it syncs with the project's
`[dev]` extra, so `[dev]`-only test-import deps (fakes, test-support libraries, property-test
helpers) are present. That is the same venv pyright and pip-audit resolve, so the suite, the type
check and the audit all describe one environment.

**pytest runs in parallel once the project's pytest loads pytest-xdist and pytest-cov.** bmk runs the project's own
pytest configuration in its venv and directory and asks which plugins it LOADS, not which are
installed. When both `xdist` and `pytest_cov` load, the stage runs
`pytest -n <workers> --dist loadgroup --cov=<source>`; otherwise it runs serially. bmk never
installs xdist itself. The one-line hint names the package that is NOT INSTALLED (`pytest-xdist`,
else `pytest-cov`; shown in JSON mode only when the stage fails); a plugin that is installed but
not loaded (plugin autoload off, `-p no:xdist` in `addopts`) gives a serial run and no hint, and
with autoload off, `-p xdist -p pytest_cov` in `addopts` loads them again and the run is parallel.
Coverage, `fail_under` and `coverage.xml` come out the same either way. The parallel run passes
`--cov-fail-under=0`, so the floor is checked once, by the `coverage report` step that follows:
`fail_under` defaults to 80, `[tool.coverage.report] fail_under` overrides it, and in JSON mode a
floor failure shows only its exit line (the report table is printed in text mode, `--human`). A
`-n` (or `--dist`) the project already passes in `addopts` is left to it. `[tool.scripts.test] workers` takes `"auto"` (the default) or a
count, `1` meaning bmk adds no `-n`; `BMK_TEST_WORKERS` overrides it for one run, and a bad value
in either is refused with one line and exit 2. Tests that
share a database, a fixed port or a file must carry the same `@pytest.mark.xdist_group("<name>")`
so they run one at a time on one worker. Before adding pytest-xdist to an existing project, find
those tests (or set `workers = 1`) and run `-n auto` several times. A test that fails only in
parallel is order- or resource-dependent, not flaky: group it or fix it.

**`make test`'s `pytest` stage also uploads coverage to Codecov**, so a failed upload is reported
as `[pytest]` failing even when every test passed. The upload runs only when a `CODECOV_TOKEN` is
found (the environment first, else a `.env` in the project or any parent directory) and
`codecovcli` is on `PATH`; if either is missing the upload is skipped and the stage passes (text
mode prints a `[codecov] warning: ... skipping upload` line). bmk takes the Codecov slug
from the `origin` remote, so in a repo with no `origin` the uploader gets none and refuses
(observed: `ValueError: The provided slug is invalid`), and the stage exits 1 with
`[codecov] upload failed (exit <N>)`. Before debugging code, read the stage's last lines: a
`[codecov] upload failed` line after a passing test run means the code is fine. For a clean local
run, add an `origin` remote, or drop the token for local runs, from the `.env` and from an
exported `CODECOV_TOKEN` alike (ask first: the `.env` holds a secret).

## Proving a gate actually ENFORCES (two wrong readings of a green `make test`)

Two independent readings of a green `make test` are wrong, and both come from bmk's stage table
rather than from your code.

**1. `ruff --fix` rewrites the tree before any checker runs.** In the stage registry
`ruff_fix_apply` is order **30**, while `bandit`, `lint_imports`, `pip_audit`, `pyright`, `pytest`,
`ruff_format_check`, `ruff_lint`, `psscriptanalyzer` and `shellcheck` are ALL order **40**. So a probe you plant to prove a checker fires can be DELETED
before that checker ever sees it: a bare unused `import` is removed at stage 30 and the gate greens
having never examined it. To plant a probe that survives, BIND the imported name so `--fix` cannot
remove it, and keep the binding after the last import or `E402` fires instead.

**2. An undeclared tool does NOT mean its stage is skipped.** The registry lists every stage
unconditionally, and `context._prepend_tool_bin_to_path` deliberately puts bmk's OWN venv bin dir
first on the child `PATH` so bare-name stages resolve to bmk's pinned toolchain rather than to
whatever sits first on your `PATH`. `lint_imports_argv` returns a bare `["lint-imports"]`. So a
floor declared in your `pyproject.toml` never governs the gate, and a genuinely missing tool fails
LOUDLY with `FileNotFoundError` rather than silently skipping. Do not file a defect against a stage
on the theory that it was skipped.

The pinning differs per tool, which decides which environment a stage actually used: `pytest` runs
on `ctx.python_cmd`, `pyright` is pinned via `--pythonpath`, and `lint-imports` is pinned to
nothing.

**`pyright` checks every OS your CI runs on.** pyright type-checks one platform
per run, so a check on Linux passes code whose types break under Windows' stubs (`os.geteuid()`,
`signal.SIGHUP`). Unless one of the two project files below changes the runs, the stage runs
`pyright --pythonplatform` once per OS family listed in `[tool.ci].os`, the key CI builds its OS
matrix from (`ubuntu-*` -> Linux, `windows-*` -> Windows, `macos-*` -> Darwin), at the same time,
and fails if any run does. The runs are listed in a fixed order: each OS in the order
`[tool.ci].os` first names it (or the one pinned run), then the `pyrightconfig.<platform>.json`
arms. The stage takes the exit code of the first failing run in that order, not the first to
finish, and prints each run's output whole, in that order, headed by its command line. With `PYRIGHT_PYTHON_FORCE_VERSION` or
`PYRIGHT_PYTHON_USE_BUNDLED_PYRIGHT` set, pyright may install itself from npm into one unlocked
cache, so the first run goes alone and the others start together after it.
With no `[tool.ci].os` it checks the host only. So in a project that declares Windows, a
Windows-only type error turns `make test` red on Linux: fix the code (a `sys.platform` guard,
which pyright narrows), not the stage. Every `make test-all` cell makes the same runs.

Two project files change those runs:

- **A `pythonPlatform` pinned in the pyright config** (`[tool.pyright]` or `pyrightconfig.json`):
  the main config runs ONCE, under its pin, the way CI's bare `pyright` runs it, never once per OS
  with `--pythonplatform` forced over the pin.
- **A `pyrightconfig.<platform>.json` in the project root** (`linux`, `windows` or `darwin`, for an
  OS in `[tool.ci].os`): runs as one more arm, `pyright --project pyrightconfig.<platform>.json`,
  beside the main config. Use it for modules that only type-check on that OS. A file for an OS not
  in `[tool.ci].os` is ignored.

The two combine: with a pin, the gate makes the one pinned run plus one run per platform file, so
a pinned project type-checks another OS only through that OS's `pyrightconfig.<platform>.json`.

**Prove it rather than reasoning about it:** run the arm where the check must FAIL, and require the
gate to go red. A gate that has only ever passed has not been shown to gate. See
`bitranox:process-test-design`.

## Troubleshooting

| Symptom                                                                             | Cause / fix                                                                                                                                                                                                                                                        |
|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make test` prints almost nothing                                                   | JSON mode succeeding (output shown only on failure). Use `--human` to see it.                                                                                                                                                                                      |
| A stage fails: `<tool>` not found                                                   | Install it with `make ensure` (section 5).                                                                                                                                                                                                                         |
| `make: command not found` (Windows)                                                 | Install a `make`: non-admin box -> `winget install --id ezwinports.make -e --scope user` (run make from Git Bash so `SHELL := /bin/bash` resolves); `choco install make` needs an elevated shell. bmk itself needs no shell.                                       |
| `make release` runs green but no GitHub Release appears (Windows)                   | `make release` detects `gh` via `shutil.which` and SILENTLY skips the GitHub Release when `gh` is not on the INVOKING process's PATH (tag push + PyPI publish still succeed). Put gh's dir on PATH first, or run `gh release create v<version>` after.             |
| `bmk: command not found`                                                            | uv's tool bin dir is not on your PATH. You do not need it there - inside a project use `make <target>` (the Makefile calls the absolute path); to bootstrap a new one use `uvx bmk install`. To put it on PATH anyway: `uv tool update-shell`.                     |
| Tools resolve the wrong deps / import errors                                        | Re-run `make`: it re-syncs the PROJECT's venv (what the gates resolve) before every env-touching target. If it persists, check `BMK_NO_VENV_SYNC` (section 1); deleting `.venv` only forces a full re-resolve.                                                     |
| `make` keeps using an old bmk right after a release                                 | Usually another bmk holds the tool lock (the output says `another bmk is using the shared tool environment`), so the upgrade is skipped on every `make` until no bmk is running, a hung one included; else uv's index lags briefly. Not uv's cache (section 1).    |
| `make test` runs host-mutating `local_only` tests you want only on a throwaway host | Tag those tests `mutating` and set `[tool.scripts.test].exclude-markers = "mutating"` (section 6). `make test` running `local_only` is by design - do NOT exclude `local_only` to "match CI".                                                                      |
| `make test` fails on a `[dev]`-only import                                          | bmk runs pytest in this project's `.venv`, synced with the `[dev]` extra before every env-touching target. Re-run `make`; if it persists, check `BMK_NO_VENV_SYNC` (section 1).                                                                                    |
| `make release` refuses: version is not canonical / carries a local segment          | Not a read failure - the version WAS read. bmk accepts any canonical PEP 440 version but refuses a spelling `packaging` would normalise (`v1.0.0`, `1.0.0-beta`) or a local segment (`1.2.3+local`); the message names the canonical form to write. See section 3. |
| `make release` refuses: `Working tree not clean. Commit or stash changes first.`    | A tracked edit is pending. Never commit an unrelated one to get past it: set it aside, release, restore it (section 3).                                                                                                                                            |
| `make push` fails at `[deps] (exit code: 1)` with `(no output captured)`            | A dependency floor is behind a new PyPI release, not your edit. `bmk deps --update`, then push again (section 3).                                                                                                                                                  |
| `make test` fails at `[pytest]` though every test passed, in a repo with no remote  | The pytest stage also uploads coverage when a `CODECOV_TOKEN` and `codecovcli` are found; with no `origin` there is no slug and the upload fails. Look for `[codecov] upload failed` before debugging code (section 6).                                            |
| CI fails with `Because only <pkg><=<old> is available` after releasing the library  | The dependent's floor was raised to a release the index does not serve yet. The pin is correct: confirm PyPI lists the version, then re-run (section 3).                                                                                                           |
| Tests break right after `make test` raised a dependency floor                       | A dependency change, not your edit: `git diff pyproject.toml`, read that dependency's CHANGELOG, adapt the caller to the documented change (section 3).                                                                                                            |
| `ModuleNotFoundError` inside bmk's own dependencies                                 | bmk's shared env, not your code; the next `make` repairs it (section 1).                                                                                                                                                                                           |
| `make testintegration` fails: `[pytest_integration] (exit code: 5)`                 | pytest collected no test: an empty lane, or a filter hiding the tests (section 6).                                                                                                                                                                                 |
| Private GitHub deps fail to resolve                                                 | `git config --global url."https://<TOKEN>@github.com/<ORG>/".insteadOf "https://github.com/<ORG>/"` before install.                                                                                                                                                |

## Further reading

Self-contained above; for depth, read these (WebFetch the URL, or the local clone if you have it):

| Topic                            | URL                                                        |
|----------------------------------|------------------------------------------------------------|
| Overview + full command table    | https://github.com/bitranox/bmk/blob/master/README.md      |
| Every install method             | https://github.com/bitranox/bmk/blob/master/INSTALL.md     |
| Configuration reference          | https://github.com/bitranox/bmk/blob/master/CONFIG.md      |
| Development / architecture notes | https://github.com/bitranox/bmk/blob/master/DEVELOPMENT.md |
