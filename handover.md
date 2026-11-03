# Handover 2026-11-03 (the [27] implementation plan is written; execution not started)

## In flight

- Nothing is part-done. The plan `docs/plans/2026-11-03-ab-test-skill.md` (16 tasks, M0-M2, later milestones after checkpoint 2) is complete and committed with the design amendments (24273510); the user has been offered the two execution options (subagent-driven on opus in this session, or attended) and has not answered yet.

## Committed, or not

- bitranox-skills: the plan, the design amendments, this file and the [27] backlog line are in the commit on top of 4019c1ca; pushed if `git log origin/master -1 --format=%s` names the plan.
- RESEARCH: all local, unpushed (public repo; reword run_arm.py's docstring before any push); branch abx-better-work-axis at 2838fe1.
- EXECUTION-USER-REVIEW.md (gitignored) holds the plan-writing decisions under "[27] implementation plan written on fable".

## Decided, and why

- Plan authored on fable; every implementer subagent and every arm/judge runs on opus, pinned and asserted (user directive 2026-11-02).
- Tasks are detailed only to checkpoint 2 (one real control arm): its duration and cost fix M5's deadline and cap, and whether the arm commits per task decides how M3 prices an advantage.

## Still open, untouched

OPEN-WORK.md: [27] (next: Task 1, the M0 probe), [25] (after [27] by the user), [40], [50] parked, [96].

## Next action

Task 1 of the plan (the M0 probe, about 0.20 USD) under whichever execution mode the user picks; if attended, a fresh session opens in a marketplace worktree per the plan's Global Constraints.

## How to verify

- `ls docs/plans/2026-11-03-ab-test-skill*.md` lists the design and the plan; `grep -c '^### Task' docs/plans/2026-11-03-ab-test-skill.md` prints 16.
- CI on the pushed commit: `uv run <plugin cache>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`.

## Lessons for the next nap

- When a user's directive pins the authoring tier (plans and skill text on fable), check the session's own model before starting the authoring and ask for the switch first: a design doc was written on opus and only caught at the plan stage.
- When writing a plan for a PUBLIC repo, scan it for tree paths and for the home-directory prefix inside any string literal before the commit: a gitignore pattern ending in that prefix (arms/*/home with a trailing slash) is refused by pushcheck like a real path.
