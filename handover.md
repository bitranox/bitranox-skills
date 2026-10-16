# Handover 2026-10-16: [23] phase 2 half done

## In flight

- [23] phase 2 (fold memory pointers into the skills that own them). Plan:
  `~/.claude/plans/curried-mapping-dolphin.md`. Phase 1 data: `.plan/fold-23/` in the MAIN
  checkout (gitignored): `rows.json` (all 1623 pointers, verdict, action, owner, reasons),
  `jobs/<skill>.json` (the 79 rules per owning skill), `edits-verify.json` (what each editor did
  and each verifier's PASS/FAIL with the gap). Review page for the user:
  https://claude.ai/artifact/9ogtPhxQyYnTeLVk8ZMrP2
- Done: the 17 tree-top REMOVE pointers are archived (bodies in `.claude-memory/.archive/`), after
  re-pointing the 12 facts that cited them. Tree top 367 -> 350. Manifest diff showed exactly
  those 17; `--check-tree` shows only the old rct-bose sideways ref.
- Half done, in worktree `../bitranox-skills-wt-fold-23` (branch `fold-23`), UNCOMMITTED, 19 paths
  (14 modified, 5 untracked: `hooks/bmk-gate-nudge.py`, its test, and three new `references/`
  dirs in compuse-toolbox, meta-context-watcher, process-test-design):
  - 46 rules landed, all in `references/` or side files, because skill-edit-guard refused every
    subagent edit to a SKILL.md. 22 skills need ONE pointer line in SKILL.md naming the new
    reference file, or the text is unreachable.
  - 32 rules were not added at all. The verifier gaps in `edits-verify.json` say exactly what
    each one lacks.
  - 11 contradictions to resolve (`edits-verify.json`, key `verify.contradictions`), e.g.
    compuse-toolbox `references/mutation-arms.md` vs SKILL.md:86 on bare `uv run`, and
    meta-dream-tree dream-passes "never pushes" vs the new squash step.
  - `hooks/bmk-gate-nudge.py` is finished: 25 tests green, a mutated dedup goes red, and a corpus
    replay showed 1161 firings over 154k commands, all genuine bmk gates, in 287 sessions.
    Registered in `hooks.json` and `tests/conftest.py`.
- The fold-23 branch sits at `5008fb75`; origin has moved past it (this handover commit).

## Committed, or not

- Pushed: `8575fb47` and `5008fb75` ([23] sizing and phase 1 result), and this handover commit.
- Memory store: the 17 archives, 12 re-pointed facts and the updated
  `feedback-index-hooks-are-trigger-first` fact are written but NOT committed to the store's own
  git; it also holds about 90 uncommitted changes from peer sessions. The next dream commits.
- The main checkout's old handover was copied to `handover.prev.md` (ignored).

## Decided, and why - do not reopen

- User, verbatim option labels: scope "Classify all, fold top first"; pinned "Keep pinned, fold
  the rest"; hooks "Shorten to about 250 chars" (for the 57 FOLD-KEEP-POINTER lines, after the
  skill holds the detail); bmk "Add it, then re-check reach"; ship "Archive REMOVE now, one
  release"; then "Hand over now". Full text in `EXECUTION-USER-REVIEW.md`.
- A pointer leaves only when the owning skill is LOADED whenever the rule fires (reach), not when
  a skill merely owns the topic: 24 of 89 tree-top fold candidates passed.
- Mirrored skills (devops-bmk, coding-python-pwshpy, coding-python-send-mail) and the provmm
  project skill provmm-benchmark are left out of this release: changing them means commits and
  pushes in their own repos, which the user has not approved in this conversation.

## Still open, untouched

- [12] waits for decide rows (earliest about 2026-10-18). Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a fan-out of subagents must edit SKILL.md files, do the SKILL.md edits in the main session (or fix the guard first): skill-edit-guard refuses them in subagents even after a Skill load, and editors silently fall back to unlinked references files.
- When a store_manifest backup is written, give --out a path OUTSIDE the knowledge tree: inside it, the copied CLAUDE.local.md files become decoy levels that mem_levels and ref_map resolve slugs to.
- When archiving a memory fact, run ref_map first and re-point every inbound [[ref]] to the skill that now holds the rule, or --check-tree reports dangling refs.
- When a cleanup drops `from __future__ import annotations` or raises a floor repo-wide, first exempt every script that runs under a PROJECT's interpreter (`LAUNCH_WITH = "project-python"`, perf-review's finders) and pin it with an `ast.parse(feature_version=...)` test.
- When you add two test files with the same basename in different skills, expect repo-gate's duplicate-basename check to refuse the PUSH: it reads tracked files, so every local run before the commit stays green.
- When you stage a memory fact body for `factedit apply --body-file`, pass a BARE body: a framed one passes through the engine unchanged and keeps its stale `description:`.
- When you loop `factedit apply --dry-run`, pass `--stage-dir`: each dry run leaves a `/tmp/factedit-*` dir behind.
- When you commit in a worktree of this repo, bump `plugin.json` before the first commit: repo-gate refuses even a WIP snapshot commit that touches `plugins/` without a bump.
- tooling: `anchor_edit.py reap` refuses a relative path; pass absolute ones.
- tooling: repo-gate blocked a commit touching only OPEN-WORK.md over mirror drift, because the worktree was one commit behind a mirror commit on origin (queued in contrib_queue).

## The exact next action

[12] is blocked on time, so the top live item is [23]. In `../bitranox-skills-wt-fold-23`: copy
the 14 modified files aside (not `git stash`, which the main checkout shares), restore them with
`git checkout -- <path>`, `git fetch && git rebase origin/master`, copy them back, then start the
meta-skill-writer receipt in the MAIN session and add the 22 SKILL.md pointer lines listed in
`.plan/fold-23/edits-verify.json`.

## Files that matter

- `../bitranox-skills-wt-fold-23/plugins/bitranox/hooks/bmk-gate-nudge.py` and
  `hooks/tests/test_bmk_gate_nudge.py`
- `.plan/fold-23/edits-verify.json`, `.plan/fold-23/rows.json`, `.plan/fold-23/jobs/`
- `OPEN-WORK.md` ([23])

## How to verify

- `cd ../bitranox-skills-wt-fold-23 && git status --porcelain | wc -l` prints 19.
- `grep -c '](mem:' /media/srv-main-softdev/CLAUDE.local.md` prints 350, unless peer sessions
  added facts since.
- In the fold-23 worktree, `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/test_bmk_gate_nudge.py -q`
  prints 25 passed.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
