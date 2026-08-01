# skill-writer checklist - process-ship-finishing-development-branch (2026-08-01, isolated-audit fix)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. These five skills reported after
four batches had already shipped, so their findings were triaged last. Ships with plugin 5.131.0.

- [x] WRONG, and it fails SILENTLY: Step 6 recomputed `GIT_DIR`/`GIT_COMMON`/`WORKTREE_PATH` from
      the current directory, but options 1 and 4 `cd` to the main root before calling it. A fresh
      probe there reports `GIT_DIR == GIT_COMMON`, so Step 6 concludes "no worktree to clean up"
      and returns success while the worktree is still on disk. Step 6 now REUSES the values Step 2
      captured, and refuses to run without them rather than guessing from the cwd.
- [x] UNEXECUTABLE: Step 2's three-row table keys the entire menu on named-branch versus detached
      HEAD, but its snippet computed only `GIT_DIR`/`GIT_COMMON` - which are identical in both
      cases. Step 2 now also captures `BRANCH` (empty on a detached HEAD, which is the actual
      discriminator) and `WORKTREE_PATH`, before anything cds away.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every claim re-measured against the real tool or file rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
