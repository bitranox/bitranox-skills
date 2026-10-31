# Review checklist 2026-10-31: a finished isolated agent's worktree stays locked

Change: one row in the situation table, before the `landed.py` row. A harness-locked
`isolation: "worktree"` checkout refuses `remove --force`. It is safe to unlock once its work is
landed (`landed.py`), and when the lock's pid is this session's claude or no longer running. A
live other session's lock is left alone.

## Claims and their evidence

- [x] The lock and its reason text: measured 2026-10-31 on two finished batch agents' worktrees in
      this repo; `git worktree remove --force` failed "cannot remove a locked working tree" with
      reason "claude agent agent-<id> (pid 1534711 ...)".
- [x] The pid check, executed: `ps -o pid,cmd -p $PPID` printed `1534711 claude ...` from this
      session's Bash tool. That is the same pid as the lock reason, so the Bash tool's parent is
      the session's claude.
- [x] unlock, then remove --force, then branch -D: run on both worktrees that day; each was
      removed and its branch deleted.
- [x] `landed.py` (the next row) answers whether a dirty worktree's or branch's work is on the
      base: the row's own text says "only exit 0 (landed) makes the discard safe".

## Probes (text only, haiku, passage pasted, quote-back required)

- [x] RED (the table without the row): Q1 "what do you do" and Q2 "what to check before
      unlocking" NOT COVERED.
- [x] GREEN: 4 of 4 by quote. Gaps that change what a reader does: no check named for
      "integrated", and no action for a dead pid. Both were closed (the `landed.py` pointer, and a
      stale-lock sentence) along with "ask that session" for a live one.
- [x] Final probe on the final text: see below.

## Gaps declined

- What `wtclean.py --apply` does: its own row and Step 5 cover it.
- Explaining why `$PPID` is the claude process: the measured check above shows it, and the row
  tells the reader to run `ps`, so it is not taken on trust.
- [x] Final probe on the final text: 4 of 4 by quote (the full sequence; `landed.py` exit 0
      before discarding; a dead pid is a stale lock, unlocked on the same conditions; another live
      session: leave it and ask).
- [x] Its one new gap that changes an action was pid reuse: a lock pid now running something
      unrelated is neither yours nor "another live session". Closed by rewording the last
      sentence to "Any other pid (another live session's claude, or a reused pid now running
      something else) is not yours". Recorded, with no further round: the change only narrows
      when you may act.
- [x] Declined from that probe: `landed.py`'s other exit codes, its relative path and Step 4.
      These are the next row's and Step 4's own text, which the passage did not include.
