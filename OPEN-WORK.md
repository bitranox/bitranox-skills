# Open work

The standing backlog: everything that outlives a single session. `handover.md` describes one
moment and is replaced wholesale every time; this file is not. Items leave it by being CLOSED,
never by being dropped.

One item per line, in this shape:

```
- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why it is still open | next: the concrete next action
```

- `(YYYY-MM-DD)` is when it was FIRST raised, and it never changes. Age is the point. A date
  nobody recorded is written as today's with a `?`, never guessed.
- `[rank]` is priority, lowest number first. `USER:` items outrank `FOUND:` items; a `USER:` item
  the user deferred sits below the live ones and still above every `FOUND:` one; within an origin
  the bigger `size` goes first. Blocked keeps its rank.
- `ORIGIN` is `USER:` or `FOUND:`. There are two. Blocked is a value for `open:`, not an origin.
- `size` is the count that says how big it is. It is the first field that gets dropped when this
  is retyped from memory, so it is not optional; `size: unknown` is honest, an invented count is
  not.
- Closing an item means `- [x]` plus `| closed: <reason>`. The line stays.

SessionStart prints the top ranks with their age. It does not consume them.

- [ ] (2026-08-27) [1] USER: "review all skills and scripts one by one, each in its own subagent and ask when smth is to change" | size: 88 of 135 targets remain, 4 slices | open: no decision recorded since 2026-08-28 | next: pick a slice from the TRIAGE.md in /tmp/scriptwave-2026-08-28, and copy that dir into the repo first because /tmp does not survive a reboot
- [ ] (2026-08-27) [2] USER: the reviewer half of that same audit directive | size: unknown, sizing it is the first step | open: deferred by the user on 2026-08-28 in favour of the cheaper buckets | next: count what the script wave already covered, then re-scope
- [ ] (2026-08-31) [3] USER: "make it sort right" - zero-pad the numbered backup to .bak.001 | size: one function, two tests | open: deferred by the user on 2026-08-31, "we will come back later to it" | next: change next_backup_path() in plugins/bitranox/skills/compuse-toolbox/scripts/anchor_edit.py, and decide what happens past 999
- [ ] (2026-08-31) [4] USER: "once its commitet, delete those baks" - reap a backup once git can restore the file | size: one verb or one guard | open: deferred by the user on 2026-08-31 with item 3, and the shape needs deciding first, separate verb or automatic on the next edit | next: put the two shapes to the user
- [ ] (2026-08-31) [5] USER: track EXECUTION-USER-REVIEW.md, or keep it out of the public repo | size: 1 file, 216 KB, 3179 lines | open: it names about a dozen internal hosts and one private LAN address, and tracking it in a public marketplace repo publishes them permanently | next: the user decides; scrub or leave ignored
- [ ] (2026-08-28) [6] FOUND: 206 unframed memory bodies | size: 206 | open: sweep never started | next: sample 10 and decide whether framing them is worth the pass
- [ ] (2026-08-01) [7] FOUND: squash the memory store repo's history | size: 110 commits, past the ~50 threshold | open: blocked on a go from the user, the store has a private remote so squashing means force-pushing it | next: ask
- [ ] (2026-08-28) [8] FOUND: 57 statusrot candidates | size: 57 | open: flagged by a scan, never triaged | next: adjudicate a sample against their source facts before believing the count
- [ ] (2026-08-31) [9] FOUND: how a committed script names a compuse-toolbox jig's path | size: about 20 jigs | open: the installed plugin path is version-stamped and a glob plus tail -1 sorts lexicographically | next: decide a preamble rule or a vendoring step, with its own RED/GREEN; notes in plugins/bitranox/skills/compuse-toolbox/.skillwriter/checklist-20260831-anchor-edit.md
- [ ] (2026-08-30) [10] FOUND: 5 older queued contributions in contrib_queue | size: 5 | open: not drained | next: contrib_queue.py list, then check each against every shipped skill before writing it
- [ ] (2026-08-31) [11] FOUND: consolidate transcript_index against the shipped jsonl_grep and transcript_tail | size: 3 tools, 1 overlap | open: not started | next: diff what each answers before merging anything
- [ ] (2026-08-31) [12] FOUND: the tree-top fact on restoring from a copy should gain the automated form of its rule | size: 1 fact body | open: was waiting on a dream that has since finished | next: memory_engine.py add, upserting at the level that owns the pointer
- [x] (2026-08-21) [13] FOUND: backfill the 153 older CHANGELOG entries | size: 153 | closed: 2026-08-31, the user declared a completeness floor at 5.266.2 instead, and check_changelog_current_version now stops the class recurring. Not a backlog item; recorded so it is not rediscovered a third time.
