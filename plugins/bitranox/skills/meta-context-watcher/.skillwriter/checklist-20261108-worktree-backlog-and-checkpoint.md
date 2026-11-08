# skill-writer checklist - meta-context-watcher (2026-11-08, worktree backlog copy, uncommitted checkpoint)

A new paragraph after the backlog tools: in a linked worktree the tools write the worktree's own
OPEN-WORK.md; the result now names the file (`path`) and, in a linked worktree, the main
checkout's copy (`note`); bring the commit across or name the file before reporting. Step 4 now
says to copy an uncommitted checkpoint (handover.md, OPEN-WORK.md) aside before any step that
resets it, and put it back right after. Code: `open_work.main_checkout_of`, `mod_bridge._where`,
the backlog_add description in `hooks/mods/register.ts`; tests in `hooks/tests/test_mod_bridge.py`.

Decisions: d-20261108-79180a73, d-20261108-74812f67

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing for this skill.
- [x] RED: the two new bridge tests failed (KeyError 'path') before the code change and pass
      after; test_mod_bridge.py plus test_open_work.py: 120 passed. Text check, pre-edit: 0 hits
      for a worktree copy of the backlog or for protecting an uncommitted checkpoint.
- [x] GREEN, both passages pasted, opus and haiku: S1 worktree add with the tool's note, S2
      control (main checkout, no note: report directly), S3 a release step restoring the
      checkpoint. Both tiers passed, control included.
- [x] Gaps closed after GREEN: how to bring the commit across (a fast-forward, only on a clean
      tree that is yours to touch); an untracked backlog has no commit, so name the file;
      OPEN-WORK.md is protected too; put the copy back right after the step, success or not.
- [x] Re-run on the final text (haiku, the changed sentences, including a main checkout that is
      a peer's dirty tree and a failed restore): quoted the new clauses; no new undecided gap.
- [x] Gaps declined: a failed copy-back (the copy stays in the scratchpad, which is the point);
      whether a fetch may run in a peer's checkout (a fetch writes no working tree; out of scope).
- [x] Width and fence check over the added lines printed nothing. ASCII only.
