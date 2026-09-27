# Handover - 2026-09-27 17:30, ranks 20, 95 and 12(a) shipped; two things wait on the user

## In flight

Nothing is part-done in this repo. 7.26.0 and 7.27.0 are released; the commit carrying this file
also carries the rank 12 update in `OPEN-WORK.md`.

Both user decisions from this session are now taken:

- **Decide mode: DONE on the user's word.** `classifier_skill_router = decide` is set here; it goes
  live once the installed plugin is 7.27.0 (`/plugin marketplace update bitranox-skills`, then
  `/reload-plugins`). Until then 7.26.0 reads it as off: keyword nudges as before, no router shadow rows.
- **igittigitt twin: PUSHED on the user's word** (`3924aea`, plugin 2.2.6); its CI was running at
  handover time - check it with ci_wait on that sha.

## Committed, or not

- Pushed, CI green: 7.26.0 `e73574f7` (rank 20 skills fixes + rank 95), `e7ff880e` (OPEN-WORK closes
  20 and 95), 7.27.0 `ccbb5d43` (skill router decide mode). CI on `ccbb5d43`: see "How to verify".
- Memory store (tree-top, not this repo): the fact
  `reference-claude-code-hooks-cannot-read-or-change-the-session-model` was rewritten through the
  engine at its owning level (this repo's `CLAUDE.local.md`); new title "Claude Code hooks can watch
  or veto a model switch, never choose one". Not committed to the store's git by this session.
- Queued in contrib_queue (target hook): `repo-gate.py --mirror-of` reads the main checkout's copy,
  not the worktree; the repo-gate PreToolUse hook judges the SESSION cwd, not the repo a command
  targets (confirmed: an OPEN-WORK-only commit blocked for mirror drift from the main checkout, then
  passed once the cwd was in the worktree).
- Main checkout: still ~200 commits behind origin/master with another session's `PLAN-JEV-SKILL.md`
  / `TODO-JEV.md` staged (OPEN-WORK rank 150). Left alone; all work here ran in worktrees.
- Worktrees left: `.claude/worktrees/rank20-int` and `.claude/worktrees/rank12-jev` (both fully
  pushed; remove with wtclean), plus `rank20-adj` from the previous session.

## Decided, and why - do not reopen

- Rank 12 order: rank 12 outranked rank 20 once its data block lifted (772 eligible rows); the user
  chose both in parallel.
- Router verdict: pre-registered outcome DECIDE-MODE (Jev 17 right / 2 wrong vs keywords 0 right / 70
  wrong picks, 87 prompts, five blind opus judges). The user chose "build decide mode" over re-testing
  the gate first.
- Decide mode scope: typed prompts only (the panel judged 0 notification turns); a Jev "no pick"
  injects nothing (no keyword fallback - the panel judged keyword picks noise); a stale cached pick
  falls back to keywords; one dedup identity (the Skill-tool name) across both paths.
- The PREREG was amended BEFORE any label: the relative-count rule alone chose decide mode on a
  synthetic all-wrong panel, so absolute floors were added (precision >= 0.6, USEFUL-ITEMS >= 5).
- Fixers never bump plugin.json; the integrator bumps once and commits blocked follow-ups on the
  integration branch (B2 and B5 follow-ups landed that way).

## Still open, untouched

`OPEN-WORK.md` is the list; read it first. Rank 12 carries the decide-mode result and its CURRENT
NEXT; new FOUND line rank 186 holds what the rank 20 fixers noticed and left.

## Lessons for the next nap

- When pre-registering a decision rule that compares two arms by relative counts, dry-run it on
  synthetic all-right / all-wrong / one-arm-right panels first: an arm that picks less wins every
  relative test, so the rule needs absolute floors.
- When a bitranox-skills fan-out forbids fixers to touch plugin.json, say in the brief that the
  version gate will block their plugins/ commits and that they leave the work uncommitted for the
  integrator.
- When running repo-gate.py --ci by hand, run it under CI's dependency set (uv run --with ...): under
  bare python3 whole modules importorskip away (~4.8k tests instead of ~10k) and it still says "all
  checks passed".
- When a subagent's report must be harvested, read the transcript's tool_use input: every hand-back
  in this session came through SubagentHandback or SendMessage, and B5's auditors reported to main
  because their spawner was between turns.
- When a backlog line names work by a relative label ("the reviewer half"), write what the thing IS
  in the line itself: the label outlived every record of its meaning.
- When a PreToolUse nudge names a shipped jig for a memory fact edit (factedit.py), use it instead of
  hand-rolling the frontmatter strip and re-add.
- When a subagent probes a public package index, tell it never to put the user's email in a
  User-Agent or contact field.
- When a Windows CI cell fails on tests that build Bash commands from tmp_path, check the command
  quotes the path before blaming the hook: bash strips unquoted backslashes.
- Windows Python 3.13: Path.resolve() does not raise on an embedded NUL; os.path.isabs("\\r") is
  False (drive-relative).
- tooling: the repo-gate PreToolUse hook judges the SESSION cwd; until fixed, cd into the target
  worktree in a separate command before committing or pushing from it.
- tooling: wtclean dry-run then --apply works; `git worktree add -b <b> origin/master` is the pattern
  while the main checkout is stale.

## The exact next action

Confirm the installed plugin is 7.27.0 and that decide rows appear in the shadow log
(`decide_path` field). Rank 12's step 2 waits on about a day of decide sessions; until then the
next workable item is the top live one in `OPEN-WORK.md`.

## Files that matter

- `.plan/jev-choicev1-2026-09-27/` (main checkout): PREREG.md, RESULTS.md, labels.json,
  verdicts-0..4.json, score.py, DECIDE-BRIEF.txt.
- `.plan/rank20-skills-2026-09-27/fix/` (main checkout): COMMON.txt, B5.report.txt, the four
  B5-audit-hooks-*.txt reports, LESSONS-FOR-HANDOVER.txt.
- `plugins/bitranox/hooks/skill-router.py`, `plugins/bitranox/hooks/classifier.py`,
  `plugins/bitranox/hooks/skill_roster.py`, `plugins/bitranox/hooks/tests/test_skill_router_decide.py`.

## How to verify this still stands

- `git fetch origin && git log --oneline -4 origin/master` shows this handover's commit on top of
  `ccbb5d43`.
- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha <this commit's full sha>` exits 0.
- `git status -sb` in that igittigitt checkout shows `ahead 1` until
  the user says push.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
