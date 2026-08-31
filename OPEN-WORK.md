# Open work

The standing backlog: everything that outlives a single session. `handover.md` describes one
moment and is replaced wholesale every time; this file is not. Items leave it by being CLOSED,
never by being dropped.

One item per line, in this shape:

```
- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why it is still open | next: the concrete next action
```

- `(YYYY-MM-DD)` is when it was FIRST raised, and it never changes. Age is the point. A date
  nobody recorded is written as today's with a `?`, or as `(unknown)`; both parse, and an
  undated item sorts last within its rank. Never guess one.
- `[rank]` is priority, lowest number first, in TENS so an insertion is a new number rather than a
  renumbering of everything below it. `USER:` items outrank `FOUND:` items; a `USER:` item the
  user deferred sits below the live ones and still above every `FOUND:` one; within an origin the
  bigger `size` goes first. Blocked keeps its rank.
- `ORIGIN` is `USER:` or `FOUND:`. There are two. Blocked is a value for `open:`, not an origin.
- `size` is the count that says how big it is. It is the first field that gets dropped when this
  is retyped from memory, so it is not optional; `size: unknown` is honest, an invented count is
  not.
- Closing an item means `- [x]` plus `| closed: <reason>`. The line stays.

SessionStart prints the top ranks with their age. It does not consume them.

- [ ] (2026-08-27) [10] USER: "review all skills and scripts one by one, each in its own subagent and ask when smth is to change" | size: 20 hook reports read but never adjudicated, plus 88 of 135 targets never swept | open: no decision recorded since 2026-08-28 | next: adjudicate reports 28-47 in /media/srv-main-softdev/projects/public/KI/scriptwave-2026-08-28/reports - the hook sweep FINISHED at 47/47 with 194 findings while TRIAGE.md stops at 27 - then pick the next slice
- [ ] (2026-08-27) [20] USER: the reviewer half of that same audit directive | size: unknown, sizing it is the first step | open: deferred by the user on 2026-08-28 in favour of the cheaper buckets | next: count what the script wave already covered, then re-scope
- [ ] (2026-08-31) [30] USER: "make it sort right" - zero-pad the numbered backup to .bak.001 | size: one function, two tests | open: deferred by the user on 2026-08-31, "we will come back later to it" | next: change next_backup_path() in plugins/bitranox/skills/compuse-toolbox/scripts/anchor_edit.py, and decide what happens past 999
- [ ] (2026-08-31) [40] USER: "once its commitet, delete those baks" - reap a backup once git can restore the file | size: one verb or one guard | open: deferred by the user on 2026-08-31 with item 3, and the shape needs deciding first, separate verb or automatic on the next edit | next: put the two shapes to the user
- [x] (2026-08-31) [50] USER: track EXECUTION-USER-REVIEW.md, or keep it out of the public repo | size: 1 file, 3225 lines | closed: 2026-08-31, the user chose to remove the file. It was never tracked, so no internal hostname reached git history.
- [ ] (2026-08-28) [60] FOUND: 206 unframed memory bodies | size: 206 | open: sweep never started | next: sample 10 and decide whether framing them is worth the pass
- [ ] (2026-08-01) [70] FOUND: squash the memory store repo's history | size: 110 commits, past the ~50 threshold | open: blocked on a go from the user, the store has a private remote so squashing means force-pushing it | next: ask
- [ ] (2026-08-28) [80] FOUND: 57 statusrot candidates | size: 57 | open: flagged by a scan, never triaged | next: adjudicate a sample against their source facts before believing the count
- [ ] (2026-08-31) [90] FOUND: how a committed script names a compuse-toolbox jig's path | size: about 20 jigs | open: the installed plugin path is version-stamped and a glob plus tail -1 sorts lexicographically | next: decide a preamble rule or a vendoring step, with its own RED/GREEN; notes in plugins/bitranox/skills/compuse-toolbox/.skillwriter/checklist-20260831-anchor-edit.md
- [ ] (2026-08-30) [100] FOUND: 5 older queued contributions in contrib_queue | size: 5 | open: not drained | next: contrib_queue.py list, then check each against every shipped skill before writing it
- [ ] (2026-08-31) [110] FOUND: consolidate transcript_index against the shipped jsonl_grep and transcript_tail | size: 3 tools, 1 overlap | open: not started | next: diff what each answers before merging anything
- [ ] (2026-08-31) [120] FOUND: the tree-top fact on restoring from a copy should gain the automated form of its rule | size: 1 fact body | open: was waiting on a dream that has since finished | next: memory_engine.py add, upserting at the level that owns the pointer
- [ ] (2026-08-31) [130] FOUND: a standing memory rule still tells every session to write EXECUTION-USER-REVIEW.md, so the removed file comes back | size: 1 memory fact, feedback-log-autonomous-decisions-to-execution-user-review-md-on-auto-tasks | open: the file was removed on 2026-08-31 but the rule that creates it was not changed | next: decide whether to retire the rule or point it at a location outside the public repo, then update the fact
- [ ] (2026-08-31) [65] FOUND: contrib_context can blow the whole SessionStart essentials budget on its own | size: 11481 bytes measured at the queue's 100-entry cap, against a 3300 ceiling | open: pre-existing and unbounded, it formats every queued entry with no budget of its own; over the ceiling the harness persists the WHOLE essentials block and injects a ~2KB preview, so every other block goes with it | next: give it the same remaining-budget treatment the backlog block now has, and a compact fallback
- [ ] (2026-08-31) [135] FOUND: check whether the prose reconcile step actually holds | size: the next few handovers | open: the carry-forward rule is prose and nothing verifies it, which is the shape that caused the original drift; left as prose deliberately because the read side is now covered | next: after a few real handovers, diff OPEN-WORK.md against what each outgoing handover carried, and look for an item that lost its size or its line
- [x] (2026-08-21) [140] FOUND: backfill the 153 older CHANGELOG entries | size: 153 | closed: 2026-08-31, the user declared a completeness floor at 5.266.2 instead, and check_changelog_current_version now stops the class recurring. Not a backlog item; recorded so it is not rediscovered a third time.
