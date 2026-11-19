# STALE - read 2026-11-19 13:04 CET, work continued (11.13.1 to 11.13.3 released since)

## In flight

- Release 11.13.0 from branch `fix/sweep-1119` (worktree `.claude/worktrees/sweep-1119`): all
  fixer work for [25], [100], [150], [180], [190], [195], [200], [210] plus the second-round
  typed engine reports, doc rows and the quadratic-regex fixes. Being pushed to master in the
  commit after this handover; check with `git log origin/master` and `ci_wait.py --ref HEAD`
  (compuse-toolbox) from that worktree.
- A peer session ("dream", cwd projects/public/libs/lib_layered_config) holds an UNPUSHED
  bitranox-skills commit on `dream/crosstree-deep-20261119` (bump 11.12.1). It repeats the
  process-test-design fake rules this release ships; it was told to drop that hunk when it
  rebases. Do not touch that branch.

## Decided, and why

In EXECUTION-USER-REVIEW.md (main checkout root, gitignored), section "2026-11-19 03:37 CET
overnight sweep": the private project-family name is scrubbed from every shipped file;
mutation_arm refuses an unwritable journal dir; a plan-mode checkpoint goes into the plan file;
[195] G4 FU-b closed without a cache; a bare `type:` keeps the stored kind; the named-teammate
probe entry stays closed (covered by process-agents-dispatching-parallel "Waited-for probes").

## Still open

See OPEN-WORK.md: [25] residue, [100] re-measure after a week on 11.13.0, [150] 11 items with
#1 a user question, [195] 4 items plus follow-ups, new [215] (finder misses two shapes) and
[220] (`<key>-<ts>` undefined).

## Next action

After CI is green: ship the four remaining queue entries of b76cc15ac35f308a with
`contrib_queue.py ship --match`, run `skill_receipt.py end meta-skill-writer`, remove the
fixer worktrees by exact path, and fold the mutation_arm change into the tree-top memory fact
feedback-a-worker-reports-finished-never-quiet-measure-the-tree-before-you-gate-it.

## Lessons for the next nap

- When a brief lets a background agent dispatch its own probes, copy the "Waited-for probes"
  line of process-agents-dispatching-parallel into it, or the probes' reports land in main.
- When a measurement agent finds a regression in the item it measures, dispatch the fixer in
  the same sweep: ask the measurement brief for the recommended fix with code lines.
- When fixers run in parallel on one file, confine each to named functions; the cherry-picks
  then merge clean.
- Before a release push to this repo, list the other sessions' unpushed branches on it
  (`git branch -a`, contrib_queue shipped notes): a peer can ship the same queued entry.
