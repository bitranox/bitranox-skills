# Handover - 2026-10-02 13:10, rank 16 Jev shadow plan: Task 1 of 10 shipped (7.35.0)

## In flight

- Executing the approved plan `/home/srvadmin/.claude/plans/write-a-plan-for-piped-starfish.md`
  (Jev shadow mode for 8 skill judgment sites, 5 FIT + 3 MAYBE, logging per-item data) with
  bitranox:process-agents-subagent-driven-development, in the worktree
  `.claude/worktrees/jev-shadow` (branch `worktree-jev-shadow`).
- Task 1 (settings knob `classifier_skills`, off/shadow) is committed, reviewed clean and pushed to
  origin/master as 346dd075 (7.35.0). CI was still running at handover time:
  `ci_wait.py --sha 346dd075d7e9bd5102a8fddba4f53c6e61d696f0`.
- Progress ledger: `.claude/worktrees/jev-shadow/.bitranox/sdd/progress.md`; task briefs for
  Tasks 1-3 sit beside it (`task-N-36114b73-brief.md`). Tasks 2-10 are open.

## Committed, or not

- This file and OPEN-WORK.md (ranks 16, 193) are committed together on top of 346dd075.
- The MAIN checkout has `TODO-JEV.md` staged (rank 150, the user's call) and `handover.md` carrying
  only a STALE marker on the 2026-10-01 handover: `git checkout -- handover.md` there before
  fast-forwarding. It also has a gitignored `EXECUTION-USER-REVIEW.md` entry for the
  `ai-llm-jev-judge` name.

## Decided, and why - do not reopen

- jev-judge is MIRRORED as `bitranox:ai-llm-jev-judge` (7.32.0), reversing the 2026-10-01
  "standalone" decision: bitranox skills must be able to rely on it being installed. Hooks keep
  `hooks/classifier.py`; skills call the `jev-judge` CLI.
- Every site starts in SHADOW, MAYBE sites included, so the data decides; decide mode is a later,
  pre-registered decision (plan Task 10).
- The mirror keeps the twin's H1 `# jev-judge`: the gate erases only a trailing `(<name>)`.
- Each push needs its own version bump: the commit gate diffs plugins/ against origin/master, so
  the plan's "one release at the end" became one bump per pushed batch.

## Decided against, and why

- No bitranox-side scripts inside `ai-llm-jev-judge/`: the mirror must stay byte-identical, so the
  shadow tool lives in `skills/meta-self-improve/jev_shadow.py` (plan Task 3).

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on Stop-gate decide rows and rank 99 on the user's
slash-command decision; rank 16 is this plan; rank 192 teaches the twin repo about the mirror;
rank 193 is a CLAUDE.md wording fix waiting on the user's go.

## Lessons for the next nap

- When a commit in this repo touches plugins/, bump plugin.json AND pyproject.toml first: the gate
  refuses version drift between them and refuses an unbumped plugins/ change, so an implementer
  told "do not bump" ends BLOCKED with everything staged.
- When the router's trigger map is regenerated for a new skill, replay it over the typed-prompt
  corpus before shipping: ai-llm-jev-judge matched 10 of 1,814 prompts, all on head words
  (`items`, `same`, `work`).
- When a mirrored skill is added, check `normalise_mirror` before renaming its H1: only a trailing
  `(<name>)` is a by-convention difference.
- tooling: a worktree-isolated session refuses `$(git ...)` inside another command; resolve the
  sha in its own call first.

## The exact next action

Rank 12 is the top-ranked item but waits on data (a day of Stop-gate decide rows), so the next
action is rank 16, which the user is actively waiting on: `EnterWorktree` with path
`.claude/worktrees/jev-shadow`, read `.bitranox/sdd/progress.md`, confirm 346dd075's CI is green,
then dispatch the Task 2 implementer (`guard_replay.py --firings`) from
`.bitranox/sdd/task-2-36114b73-brief.md`, re-arming the model gate first
(`skill_receipt.py start plan-execution`).

## Files that matter

- `plugins/bitranox/skills/meta-memory-settings/settings.py`, `plugins/bitranox/hooks/self_improve_signals.py` - the knob.
- `plugins/bitranox/skills/compuse-toolbox/scripts/guard_replay.py` - Task 2.
- `plugins/bitranox/skills/meta-self-improve/` - Task 3 home (`jev_shadow.py`, `jev_sites/`, `references/jev-shadow.md`).
- `plugins/bitranox/hooks/classifier.py` - `prepare_state`, `_plugin_version` to reuse.
- `plugins/bitranox/skills/ai-llm-jev-judge/SKILL.md` - the `jev-judge` floor (0.2.4) the shadow tool pins to.

## How to verify

- `git log --oneline -3 origin/master` shows 346dd075 (7.35.0) under this handover commit.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with
  ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/meta-memory-settings/tests/ -q`
  - green.
- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` - 0 of 11 pairs drifted.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
