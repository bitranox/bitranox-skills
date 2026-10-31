# Open work

The standing backlog: everything that outlives a single session. `handover.md` describes one
moment and is replaced wholesale every time; this file is not. An item leaves it only when it is
SOLVED, and then its line is deleted; an unsolved item is never dropped.

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
- A solved item's line is DELETED, never kept as `- [x]` (user decision 2026-10-23). Delete it in
  the commit that records the solving work and put the reason in that commit message: git
  history keeps the old line.
- This file is published with the repo. Write a path repo-relative, under `~`, or with a
  placeholder (`/tmp/claude-<uid>/<project>/`), never as this machine's absolute path, and
  name a machine by its role ("the Windows dev VM"), never by its hostname.

SessionStart prints the top ranks with their age. It does not consume them.


- [ ] (2026-10-26) [30] USER: "if compact mode works fine we might purge the handover mode" | size: unknown until compact mode has run in real sessions | open: waits on compact mode (10.1.0, context_mode default compact) proving itself live | next: after several long sessions in compact mode, read their transcripts (save request near the save point, checkpoint written, compaction, resume block, work continued) and put the purge to the user
- [ ] (2026-10-02) [96] FOUND: pre-registered decide rule for the 10 Jev shadow skill sites (rank 16; written BEFORE any shadow data) - a site may be proposed for decide only when it has >= 100 paired items from >= 3 runs, agreement >= 90% outside the band, the band holds <= 25% of answers, no FLAT question, and a blind hand review of >= 20 disagreements shows Jev wrong no more often than the agent. A site failing at >= 100 paired items gets its question rewritten once (new `version`, replay over the logged states first) and is dropped if it fails again. Decide mode, when it comes, must keep logging every verdict | size: 10 sites, 0 with enough data yet | open: blocked on data - the shadow log `~/.claude/self-improve-audit/jev-skill-shadow-YYYY-MM.jsonl` fills only when skills run with `classifier_skills = shadow`; this rule must not be loosened after the data is seen | next: once a site passes 100 paired items, run `jev_shadow.py report` and check it against every clause above, recording the result here per site | 2026-10-05: 2026-10-04: dream-firing is the only site with data (31 records / 1 run / 29 paired, agreement outside band 95.7%, band 19.4%, flat=false, 1 logged disagreement); the other 9 sites have 0 records; no site meets >=100 paired / >=3 runs; rule unchanged. | 2026-10-09: report re-run, 41 records, last write 2026-10-06: dream-firing 29 paired / 1 run, data-arch-dict 10 paired; still no site at >=100 paired, rule unchanged. | 2026-10-23: report re-run (jev_shadow.py report, 181 records, log last written 2026-10-09; status: shadow on). dream-placement is the FIRST site past 100 paired: 140 paired, but all from ONE run (dbf7348b, 2026-10-09, one level); outside-band agreement 62.1% (29 paired, needs >= 90%), band 79.3% (needs <= 25%), not FLAT (Jev values 0.02-1.96); agent never answered 0 (2: 100, 1: 40). It fails two clauses and has 1 of the 3 runs. dream-firing 29 paired / 1 run and data-arch-dict 10 paired are unchanged; the 7 other sites have 0 records. Rule unchanged. User chose "Wait for 3 runs" 2026-10-23: the >= 3 runs floor also gates the rewrite-once branch, so no rewrite yet. Only meta-dream-tree step 5 feeds this site (40-item sample per tree dream, per its SKILL.md); the store runs since 10-09 were a crosstree-deep (10-19) and a nap (10-20), neither of which feeds it, so the stall is no tree dream, not a skipped step. next (supersedes the older one): after each meta-dream-tree run, re-run jev_shadow.py report; once dream-placement has >= 3 runs and still fails, apply the rewrite-once branch (v2, replayed over the logged states first) | 2026-10-29 data-arch-dict CLOSED, measured: 331 paired / 12 runs, band 44.1%, agreement outside band 60.0% -> rewrite-once branch: v2 pre-registered (.plan/jev-28/review-2026-10-29/PREREG-data-arch-dict-v2.md), replayed over 320 deduplicated states (replay_dad.py/json): v1 band 42.5% (apparatus comparable), v2 band 27.5% and agreement 77.2%, both FAIL -> dropped in 10.5.0. The agent label was false on every row (see [1040]). dream-placement 2 runs, dream-firing 2 runs, dream-prune 1 run: below the 3-run floor | next (supersedes): after each meta-dream-tree run, re-run jev_shadow.py report; apply the rewrite-once branch to a site once it has >= 3 runs and still fails
