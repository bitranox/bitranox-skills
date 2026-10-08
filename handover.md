# Handover - 2026-10-08 10:10, [11] shipped as 8.4.0; worktree and branch cleanup done

Working tree for this handover: `.claude/worktrees/handover-20261008` (branch `handover-20261008`),
created from origin/master only to commit this file and `OPEN-WORK.md`. Remove it after the push.

## In flight

- Nothing of this session is running. 8.4.0 (`1592043d`, OPEN-WORK [11]) is on origin.
- A PEER session is live in `.claude/worktrees/jev-shadow` (it pushed 8.4.1, `53c9f85a`, which
  fixes the Windows-only `test_recall_memory_decide.py::test_asks_every_shortlisted_note_at_once`
  failure that has reddened CI since 8.3.1). Its CI result decides whether master is green again.

## Committed, or not

- On origin: 8.4.0 and 8.4.1. Committed with this handover: `OPEN-WORK.md` gains [19].
- Not in git, only in the main checkout's gitignored `.plan/`:
  `.plan/worktree-archive-2026-10-08/` (34 archived worktree `.plan/` files plus
  `deleted-branches.txt`, name and sha of the 100 deleted branches).
- The main checkout itself is still far behind origin with someone's staged `TODO-JEV.md` ([150]).

## Decided, and why - do not reopen

- [11] GREEN was a quote-back retrieval run, not a fresh behavioural RED: the tree-top memory fact
  `feedback-a-parallel-write-agent-can-clobber-a-sibling-target-and-report-success` now names both
  jigs in the always-loaded index, so any new RED passes on inherited context (redcheck: STRONG on
  both scenarios). The RED recorded before that fact was written stands. Both `.skillwriter`
  checklists record this.
- compuse-toolbox's description was NOT given triggers for the two jigs: it is 1009 of 1024
  characters; they are reached through the toolbox-nudge rule, the Tools table and the
  dispatching-parallel Verification item.
- Cleanup removed only what was PROVEN contained: a worktree when no live process, no lock, every
  commit patch-equivalent on origin, and its uncommitted patch (if any) reverse-applies onto
  origin/master; a branch when `git cherry origin/master <b>` lists no `+`.
- The 8.4.0 CI failure was not investigated or fixed here: it predates 8.4.0 and the jev-shadow
  session owns it.

## Still open, untouched

- OPEN-WORK [12], [14], [16], [17], [18]: unchanged.
- OPEN-WORK [19]: the cleanup items that could not be proven safe.
- OPEN-WORK [245]: `agent-a26b133c84c5141bb` is still locked by the live jev-shadow session.

## Lessons for the next nap

- When deciding whether a worktree's uncommitted edits already landed, reverse-apply its
  `git diff --binary HEAD` onto a throwaway index read from origin/master
  (`GIT_INDEX_FILE=tmp git read-tree origin/master`, then `git apply --cached --check -R`): a diff
  against origin cannot answer once origin has moved past the worktree's base.
- When deciding whether a branch's work landed, `git cherry` matches rebased commits but not squash
  merges; `git merge-tree --write-tree origin/master <b>` returning origin's own tree proves
  containment, and a conflict proves nothing either way.
- When probing dirty worktrees, never `git add -N .`: it writes intent-to-add entries into THEIR
  index; read untracked files with `git ls-files -o --exclude-standard` instead.
- When CI goes red right after your push, check the PREVIOUS commit's run for the same failing
  test before investigating: 8.4.0's only failure had already failed 8.3.1's Windows cell.

## The exact next action

OPEN-WORK [12] step (5) is the top open item. The jev-shadow peer session is working Jev code
(8.4.1), so first run `ListAgents` and check whether it is still live and on [12]; if it is, leave
[12] to it and take [14] next. Otherwise count the recall_rerank shadow rows logged on plugin
>= 7.31.0 and put to the user whether that is "much more data" yet.

## Files that matter

- `OPEN-WORK.md` ([12], [19], [245])
- `.plan/worktree-archive-2026-10-08/deleted-branches.txt` in the main checkout (gitignored)

## How to verify

- `git log --oneline -3 origin/master` shows 8.4.1 and 8.4.0.
- `git worktree list` in the main checkout lists master, `jev-shadow`, the two locked agent
  worktrees, the four kept dirty ones, and this handover worktree until it is removed.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
