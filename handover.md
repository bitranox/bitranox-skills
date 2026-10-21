# Handover 2026-10-21 (2): [29] planned (review dispatches on opus at effort low), [23] hook cut not started

## In flight

- Nothing part-done. No subagent, workflow or worktree is running or left over.
- [23] (3b-hooks) was started and stopped at the reading stage: no hook was cut, no fact touched.
  The user switched to planning [29]. bitranox-skills 9.10.3 IS installed now
  (`~/.claude/plugins/cache/bitranox-skills/bitranox/9.10.3`), so the hook cut is unblocked.
- [29] has a full plan, NOT started: `docs/plans/2026-10-21-review-dispatch-effort-plan.md`
  (same text at `~/.claude/plans/plan-29-be-glittery-wave.md`). The user stopped at plan review
  with "save the plan and handover"; they have not approved it for execution.

## Committed, or not

- This commit: `OPEN-WORK.md` ([23] `next:` field corrected, [29] sized and pointed at the plan),
  the plan file, and this handover. Nothing else changed.
- Gitignored: `handover.prev.md` (the outgoing handover), the two user decisions below in
  `USER-DECISIONS.jsonl` (hook-written). They are NOT yet copied into `EXECUTION-USER-REVIEW.md`;
  plan Task 0 does that.

## Decided, and why - do not reopen

- [29] scope (user, 2026-10-21, "All judging review (Recommended)"): task/final/code review,
  skeptic and adversarial lenses, verify, adjudication, quote-back, audit reviewers, judge panels
  run on `opus` at `effort: low`. Implementers, fixers, scenario writers and RED/GREEN probe
  subjects keep their tiers; final synthesis keeps xhigh/max.
- [29] enforcement (user, 2026-10-21, "Warn-only nudge (Recommended)"): extend
  `plugins/bitranox/hooks/subagent-model-gate.py`, never block, replay-measure before shipping.
- `~/.claude/settings.json` (effortLevel xhigh, high for claude-opus-5-5) is NOT edited: the
  explicit per-dispatch field is the override.

## Decided against, and why

- Editing `~/.claude/agents/probe-effort-{low,max}.md` (sonnet) and `agents/baseline-probe.md`:
  probe scope, which the user excluded.

## Still open, untouched

- [23] hook cut for the 18 rows, then REACH-FAILS / SAFE / KEEP-SHORTENED / STAY rows: see `OPEN-WORK.md`.
- [29] execution: the plan above. [28], [335]: blocked on Jev shadow data. Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When an OPEN-WORK line carries several dated segments, the latest segment's "Next:" is current
  and the `next:` field can be stale: fix the field whenever you touch the item.
- When a rule depends on what an OMITTED subagent field inherits, read `~/.claude/settings.json`
  (effortLevel, modelSettings) first and probe the override before building on it.
- tooling: subagent-model-gate's message says effort "rides the agent type or a Workflow agent()
  call, not the dispatch", which is false (the Agent tool has `effort`, `claude -p` has
  `--effort`); [29] plan Task 5 fixes it.
- Carried from the previous handover (not yet napped):
  - When a handover's next action names counts, recount them from the cited data first: the last
    one said 9 better owners and 18 partial rows, `merged.json` held 5 and 19.
  - When a mirrored skill's text carries a package version floor, check every pin of that floor
    first (the twin's metadata test, `jev_shadow.py`): a skill-only change then needs a package
    release, and the marketplace push has to be ordered around PyPI.
  - tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp for
    a package no declared floor needs; declare the floor (a CVE pin) and let bmk write the pin.
  - When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command:
    the gate judges the index as it was before the command ran.

## The exact next action

[23] is the top-ranked open item: in `.plan/fold-23/batch3/fold18/`, quote-check the 18 rows'
GREEN quotes against `~/.claude/plugins/cache/bitranox-skills/bitranox/9.10.3/skills` (adapt
`.plan/fold-23/batch3/quotecheck_installed.py`: set INST to 9.10.3, read `fold-result.json` here),
then cut each hook to <= 250 chars ending "Detail: bitranox:<skill>." with factedit. If the user
picks [29] instead, start at plan Task 0 (worktree from origin/master), then Task 1 (the probe).

## Files that matter

- `docs/plans/2026-10-21-review-dispatch-effort-plan.md` - the [29] plan with the full inventory.
- `plugins/bitranox/skills/process-agents-subagent-driven-development/SKILL.md:135-164` - the effort table [29] rewrites.
- `plugins/bitranox/hooks/subagent-model-gate.py` - the hook [29] extends.
- `.plan/fold-23/batch3/fold18/` (gitignored) - [23] batch-3b data: g1-g5.json, fold-result.json, qcheck.py.

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- `grep -n '^- \[ \] (2026-10-2' OPEN-WORK.md` shows [29] with the plan path in `next:`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
