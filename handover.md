# Handover - 2026-10-16 12:00, 9.0.0 shipped ([25]), [22] memory cleanup applied; next is [23]

## In flight

- Nothing part-done. 9.0.0 (`37d324c2`) is pushed and released (v9.0.0): CI run 38879808240
  green on all five jobs (gate, ubuntu 3.14, ubuntu 3.15, windows 3.15, macos 3.15).

## Committed, or not

- bitranox-skills: everything pushed up to `37d324c2`; this handover and the `OPEN-WORK.md`
  edits ([22] closed, new [590]) are committed and pushed together with this file.
- Memory store (`/media/srv-main-softdev/.claude-memory`, its own git): the [22] pass is commit
  `f402bea`, made by pathspec. 62 OTHER uncommitted store entries belong to other sessions
  (new facts, edits) and were deliberately left out; the next dream commits them.
- Both worktrees (`recall-threshold-09`, `py314-floor`) and their branches are removed.

## Decided, and why - do not reopen

- [25] user, verbatim: "raise it - we only do 3.14/3.15 - also clean up old code and raise to
  3.14 compatibility". Hook floor: user chose "Shim requires 3.14": `run-python.sh` picks the
  first interpreter >= 3.14 (python3, python, python3.15, python3.14, py -3.15, py -3.14, py -3)
  and otherwise skips with `needs Python 3.14 or newer, found only ...`. Shipped as a MAJOR (9.0.0)
  because users on 3.11-3.13 lose the hooks.
- Kept at a 3.10 floor ON PURPOSE (they run in the user's PROJECT interpreter, not the plugin's):
  the 12 mirrored skills, `coding-python-performance-review`'s scripts, and `mutation_arm` with
  `anchor_edit` + `_cli_envelope`. Tests `test_project_python_closure_floor.py` (compuse-toolbox)
  and `test_perf_scripts_floor.py` (performance-review) pin it.
- Not removed: printf-style formatting (ruff UP031, 1569 hits) - style, not version.
- [22] user chose "Apply all, no renames": the 5 slugs whose names now contradict their bodies
  (run-python-sh-exits-0, repo-gate-mirrors-compares-only-skill-md,
  factedit-apply-drops-metadata-type, btx-lib-mail-1-5-0, btx-lib-mail-2-0-0) stay as they are.
- `dream_state.py done` was NOT run: this was the dream's step-7 version pass only, not a full
  tree dream, so the dream-due nudge stays on.

## Still open, untouched

- [12] waits for decide rows (earliest about 2026-10-18). Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a cleanup drops `from __future__ import annotations` or raises a floor repo-wide, first exempt every script that runs under a PROJECT's interpreter (`LAUNCH_WITH = "project-python"`, perf-review's finders) and pin it with an `ast.parse(feature_version=...)` test.
- When you add two test files with the same basename in different skills, expect repo-gate's duplicate-basename check to refuse the PUSH: it reads tracked files, so every local run before the commit stays green.
- When you stage a memory fact body for `factedit apply --body-file`, pass a BARE body: a framed one passes through the engine unchanged and keeps its stale `description:`.
- When you loop `factedit apply --dry-run`, pass `--stage-dir`: each dry run leaves a `/tmp/factedit-*` dir behind.
- When you commit in a worktree of this repo, bump `plugin.json` before the first commit: repo-gate refuses even a WIP snapshot commit that touches `plugins/` without a bump.
- tooling: `anchor_edit.py reap` refuses a relative path; pass absolute ones.

## The exact next action

[12] is blocked on time, so the top live item is [23]: size it - classify each of the 367 tree-top
pointer lines in `/media/srv-main-softdev/CLAUDE.local.md` by the shipped skill whose domain owns
it (or none), then propose per skill which lines move in and which stay.

## Files that matter

- `OPEN-WORK.md` ([23], [24], [590])
- `plugins/bitranox/hooks/run-python.sh`, `plugins/bitranox/hooks/tests/test_run_python_sh.py`
- `.github/workflows/ci.yml`, `pyproject.toml`, `CHANGELOG.md` ([9.0.0])
- `plugins/bitranox/skills/meta-dream-tree/versionrot.py`, `factedit.py`

## How to verify

- `gh run list --repo bitranox/bitranox-skills --commit 37d324c2c97d24a13a38f60746a9c5cd3e9a9573`
  shows `ci` success.
- `python3 plugins/bitranox/skills/meta-dream-tree/versionrot.py scan --tree /media/srv-main-softdev`
  lists 60 facts, every one a KEEP or a kept measurement line.
- `bash plugins/bitranox/hooks/run-python.sh plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py --check-tree /media/srv-main-softdev`
  prints `TOTAL tree problems: 2` - the two pre-existing sideways refs in [590].

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
