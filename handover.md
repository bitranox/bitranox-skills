# Handover - 2026-10-08 10:35, recall decide shipped (8.3.0-8.4.1), [11] shipped (8.4.0), CI green

Two sessions handed over at the same moment; this file merges both. Session A worked in the
`jev-shadow` worktree (recall decide). Session B worked in `handover-20261008` ([11] and the
worktree/branch cleanup); its own text is in git as commit e0befd4f.

## In flight

- Nothing is running in either session. origin/master carries 8.4.1 (53c9f85a); CI green on every
  workflow, windows-latest included. 8.4.0 (1592043d) is session B's.

## Committed, or not

- On origin: 8.3.0 recall decide mode; 8.3.1 and 8.4.1 its test and TLS fixes; 8.4.0 [11].
  Committed with this handover: OPEN-WORK [19] (B) and [390] (A). Nothing else is uncommitted.
- Not in git, gitignored, with no other copy:
  - `jev-shadow` worktree `.plan/`: `openwork-batch-2026-10-04/`, `jev-stop-2026-10-06/`,
    `jev-recall-2026-10-06/` - OPEN-WORK [390].
  - main checkout `.plan/worktree-archive-2026-10-08/`: 34 archived worktree `.plan/` files plus
    `deleted-branches.txt` (name and sha of 100 deleted branches; `git branch <name> <sha>`
    restores one).
- The main checkout is still far behind origin with a staged `TODO-JEV.md` ([150]).
- This machine's config already has `classifier_recall_rerank = decide`; a running session needs
  `/reload-plugins` to pick up 8.4.1.

## Decided, and why - do not reopen

- recall_rerank goes to decide at 0.8 (user's choice: first 0.9, then "use 0.8"). Blind panel,
  pre-registered, 10 opus judges, 8/8 controls, 91% unanimous: keyword top 4 relevant 6%, Jev at
  0.8 44%, Jev at 0.9 74% (post-hoc, 46 notes). No pre-registered branch fired, so it was the
  user's call. Record: `.plan/jev-recall-2026-10-06/` in the jev-shadow worktree.
- Jev silent or every note under 0.8 injects NOTHING; the keyword ranking is not a fallback (6%).
  All shortlisted notes are asked at once; one TLS context per classifier.
- OPEN-WORK [10] deleted at the user's request after they rejected every fix option for recall
  pulling other projects' notes; decide mode now filters those notes instead.
- [11] GREEN was a quote-back retrieval run, not a fresh behavioural RED: the tree-top fact
  `feedback-a-parallel-write-agent-can-clobber-a-sibling-target-and-report-success` names both
  jigs, so a new RED passes on inherited context. compuse-toolbox's description got no trigger for
  the jigs (1009 of 1024 characters); they are reached through toolbox-nudge, the Tools table and
  the dispatching-parallel Verification item.
- Cleanup removed only what was PROVEN contained (no live process or lock, every commit
  patch-equivalent on origin, uncommitted patch reverse-applies onto origin/master; a branch when
  `git cherry origin/master <b>` lists no `+`).

## Decided against, and why

- Rewording prompts to dodge recall: it works (`./handover.md` or `what next?` extract no
  keywords) but is a workaround, not a fix.
- Asserting an exact request count in a deadline-bound test: it raced a slow windows-latest
  runner twice. The test asserts concurrency (> 8 in flight) instead.

## Still open, untouched

`OPEN-WORK.md` is the list. [12] step (6) waits about a week of decide rows (earliest
2026-10-13); [14] re-measure notification rows; [16] /tmp cleanup needs the user's
when/what/how; [17] identify the new Claude Code module feature; [18] deferred by the user;
[19] 4 dirty worktrees + 24 branches left to judge; [245] `agent-a26b133c84c5141bb` was locked;
[390] copy the jev-shadow `.plan/` records out.

## Lessons for the next nap

- When a test fake is a `ThreadingHTTPServer`, raise `request_queue_size` above its default 5:
  Windows aborts the surplus of simultaneous connections (WinError 10053) before any handler runs.
- When a test runs a client under a fixed deadline, assert a concurrency bound (max in flight),
  never how many requests arrived: a slow windows-latest runner started 9 of 12 in 1.5 s while a
  Windows dev box passed 5 of 5.
- When CI fails only on Windows, reproduce on the Windows dev box (git archive, scp, `pwsh -File`
  a .ps1 that loops the test) before changing code: it separated a timing race from a real defect.
- When a pre-registered panel lands in no branch, present the options as post-hoc and record the
  user's choice as theirs; do not adopt the best-looking post-hoc threshold yourself.
- When two sessions hand over at once, the later push meets a conflicting `handover.md`: merge
  both into one file rather than overwriting, and re-check the other's next action against your
  own work (B's pointed at [12] step 5, which A had finished).
- When deciding whether a worktree's uncommitted edits already landed, reverse-apply its
  `git diff --binary HEAD` onto a throwaway index read from origin/master
  (`GIT_INDEX_FILE=tmp git read-tree origin/master`, then `git apply --cached --check -R`).
- When deciding whether a branch's work landed, `git cherry` matches rebased commits but not
  squash merges; `git merge-tree --write-tree origin/master <b>` returning origin's own tree
  proves containment, and a conflict proves nothing either way.
- When probing dirty worktrees, never `git add -N .`: it writes intent-to-add entries into THEIR
  index; read untracked files with `git ls-files -o --exclude-standard`.
- When CI goes red right after your push, check the PREVIOUS commit's run for the same failing
  test before investigating.
- tooling: bump `pyproject.toml` together with `plugin.json` - repo-gate fails "version drift"
  after a 7-minute suite otherwise.
- tooling: in a worktree-isolated session, run pytest through a scratchpad wrapper script;
  `env -u VIRTUAL_ENV` inline is refused, and so is a python run with `$VAR` or `$(...)`
  arguments - pass literal paths.
- Carried from the 2026-10-06 handover (not yet confirmed napped): when a gate or filter is keyed
  on one field (prompt length), measure where the positives' evidence lives first; when a blind
  panel needs more items than one judge can read, split into halves with their own judges and
  controls and dry-run the scorer on all-true labels; when a shadow log grows during analysis,
  freeze the data with a timestamp cutoff in the pre-registration.

## The exact next action

[12] is blocked on time (step 6 needs about a week of decide rows), so start with [14]: count the
skill_router notification rows logged since plugin 7.30.9
(`~/.claude/self-improve-audit/classifier-shadow-*.jsonl`, rows carrying `notify_view`) and put
to the user whether that is enough to re-measure; if not, ask the user [16]'s when/what/how.

## Files that matter

- `plugins/bitranox/hooks/recall-memory.py` (`_decide_recall`, `_rerank_request`)
- `plugins/bitranox/hooks/classifier.py` (`ask_in_hook(workers=)`, `JevClassifier._tls_context`)
- `plugins/bitranox/hooks/tests/test_recall_memory_decide.py`, `tests/conftest.py` (`FakeJev`)
- `OPEN-WORK.md` ([12], [14], [19], [245], [390])

## How to verify

- `git log --oneline -3 origin/master` shows this handover commit on top of e0befd4f and 53c9f85a.
- `gh run list --commit 53c9f85a9c6e13100c9825fee65d5c5a178af108` shows ci and workflow success.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
