# skill-writer checklist - git-worktrees (2026-11-08, ignored work files and the ExitWorktree count)

Step 4 now names the ignored files that are work (a decision log, a handover, a backlog): diff
each non-build ignored file against the main checkout's copy, merge the worktree-only lines in,
copy in a file the main checkout lacks, compare a secret file with `cmp -s` only. A new paragraph
says ExitWorktree's "Discarded N commits" counts against the session's starting commit, not
origin, and how to judge a removal before and after it.

Decisions: d-20261108-f33703e1, d-20261108-bdfba564

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing (no ledger before this).
- [x] RED by text check, pre-edit text: "regenerable" covered every gitignored file with no
      exception; 0 hits for "ExitWorktree" and "Discarded".
- [x] Mechanism claims checked: CLI 2.1.319 binary - the refusal text says "commits that this
      session's starting commit lacks", the count is `rev-list --count <start>..HEAD`.
      `landed.py <sha>` ran: rc 0 on a landed sha, rc 2 on an all-zero sha.
- [x] GREEN, both passages pasted, opus and haiku: S1 ignored decision log + handover beside a
      teammate's "merged over" claim, S2 "Discarded 12 commits" with a lagging master, S3 control
      (only .venv and target/, must NOT diff). Both tiers passed all three, control included.
- [x] Gaps closed after GREEN: what build output is; what to do with the `<` lines (copy the main
      copy aside, merge, re-diff); a file with no main copy; a secret file (cmp -s, a differing
      one copied beside and left to its owner); the copied file must be ignored there too; the
      post-removal test uses a tip recorded before removal, never HEAD; exit 1 can still be a
      squash, so landed.py before calling it lost; the count covers commits only.
- [x] Re-run on the final text (opus+haiku with the backlog group, then haiku on the four
      changed sentences): every scenario answered with the quote; no new undecided gap.
- [x] Gaps declined: the exact beside-name (a judgement call per repo); which tool takes
      `--discard-uncommitted` (wtclean, Step 5, right below); whether ExitWorktree removes
      ignored files the same way as `git worktree remove` (not measured, and the advice is the
      same either way).
- [x] Width and fence check over the added lines printed nothing. ASCII only.
