# Checkpoint 2026-11-08 (night run: OPEN-WORK [30], [40], then [25]; the user is asleep)

## In flight

- User order, verbatim: "do 30,40, then 25", then "no human, I go to bed". Questions for the user
  are recorded in the main checkout's `EXECUTION-USER-REVIEW.md`, never asked.
- Worktree `.claude/worktrees/night-backlog`, branch `worktree-night-backlog`, from origin/master
  10d4ea1b (10.22.1).
- [30] DONE as far as it goes: committed (`chore(backlog): [30] re-counted under 10.9.16, question
  pending; file [94]`), not pushed. The purge question waits for the user.
- [40] IN PROGRESS, uncommitted: memory-bound rule added to
  `plugins/bitranox/skills/process-plan-brainstorming/SKILL.md` ("Presenting the design" bullet)
  and `plugins/bitranox/skills/process-plan-writing-plans/SKILL.md` (Self-Review item 7). RED =
  text check (0 hits for memory in both, pre-edit); behavioural RED skipped because the memory
  index already teaches it. GREEN passed on opus and haiku for both skills; gaps closed
  (validate-then-act two-pass, cap accumulators, per-item byte limit, tracemalloc vs max RSS).
  Two re-probes on the final text are running (opus quote-back at effort medium, haiku
  brainstorming re-run) with a 120 s deadline shell.
- skill-writer receipt is armed (`skill_receipt.py end meta-skill-writer` after the [40] commit).

## Next action

Read the two re-probe hand-backs; then write the ledger entries (`skill_decisions.py add
--from-file`, anchors: brainstorming "state what is held per item, what grows with the count, and
the resulting peak", writing-plans "A step that collects every item before acting, or bounds
memory only with a count limit, is a defect"), one `.skillwriter/checklist-20261108-memory-bound.md`
in EACH of the two skill dirs, CHANGELOG + `bump_version.py --part minor` (origin is 10.22.1),
commit; then delete OPEN-WORK [40] in that commit (reason: shipped) and drop the three datamax-dpl
contrib_queue entries that carry the same change. Then [25].

## Decided, and why

- [40] owners: brainstorming + writing-plans, not coding-python-clean-architecture (the user said
  "at the design stage"; the planning skills serve every language). Logged in
  EXECUTION-USER-REVIEW.md.
- writing-plans item 7 is one long line like items 1-6 (file style), not wrapped.

## Coordination

- Peer session skills-history owns OPEN-WORK [95], [98], [99], [100] and will message before its
  push; message it before pushing too. From [25] leave entries targeting repo-gate or the
  skill-edit guard alone.

## Lessons for the next nap

- When a script must cut a numeric value from Python source by grep, remember adjacent string literals concatenate: "Save a " "checkpoint NOW" matches at runtime while grep for the phrase finds nothing.
- tooling: in a worktree-isolated session, a Bash call that runs python3 on a $VARIABLE path is refused; write literal paths.

## How to verify

- `git log --oneline origin/master..HEAD` lists the [30] commit (and later the [40] commit).
- `python3 plugins/bitranox/hooks/skill_decisions.py check`.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
