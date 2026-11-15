# Checkpoint 2026-11-15: releasing 11.6.0 (backlog [175] and [165])

## In flight

- Worktree `.claude/worktrees/fix-175-165`, branch `fix/backlog-175-165`, based on origin/master
  1cd91ed6. Committed: d84aa121 (bump 11.5.2 -> 11.6.0 with the full CHANGELOG), seven cherry-picked
  fixer commits (8554c39a topics; 07c3f870 + 75fa97fc memory_engine; 59c41112 store_manifest;
  76e46483 topic_placement; 9c5d7efd private-name scrub; 87574bbf session-start self-heal line),
  3a617431 meta-dream-tree lock-holder list (skill-writer RED/GREEN done, checklist committed).
- UNCOMMITTED in the worktree: `OPEN-WORK.md` ([175] and [165] closed, new [190] leftovers line,
  [130] private repo names neutralised) and this `handover.md`.
- The three fixer worktrees (`agent-ad81116b13ed4ef83`, `agent-a0f96d14b2f0c7589`,
  `agent-ade79ed26abc7a923`) are done and reported; their work is cherry-picked. Remove them and
  their `worktree-agent-*` branches after the push.

## Decided, and why

- Private directory name scrubbed forward in a plan and a test fixture, following 008cbd9a's
  precedent; history and dated checklists left alone. The bare `provmm` token is a question for
  the user, filed in [190].
- Minor bump (11.6.0): two additions (a bare frame key removes a stored unknown key; SessionStart
  names refused self-heal levels) besides the fixes.

## Next action

1. Commit `OPEN-WORK.md` and `handover.md` in the worktree (message: close [175] and [165], file
   [190]; reasons tagged measured).
2. Run the full gate once over the integrated tree (pre-push hook does it), then
   `git push origin HEAD:master` from the worktree and watch CI with
   `ci_wait.py --ref HEAD` (compuse-toolbox).
3. `skill_receipt.py end meta-skill-writer`; remove the four worktrees and branches; fast-forward
   the main checkout only if its tree is clean and ours to touch (it holds another session's
   uncommitted OPEN-WORK.md and handover.md - leave it).

## Lessons for the next nap

- When a PreToolUse gate refuses a commit for an unstaged new file, run `git add` as its own
  command first: the gate judges the whole command before the add runs.
- When an edit names which verbs a rule covers, read the probe's paraphrase for an implied
  generalisation ("a dry run of any of them"); it shows where the text over-claims.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
