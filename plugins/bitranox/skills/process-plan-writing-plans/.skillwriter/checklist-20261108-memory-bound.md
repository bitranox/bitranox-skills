# skill-writer checklist - process-plan-writing-plans (2026-11-08, memory bound in Self-Review)

Self-Review gains item 7, "Memory bound": for every caller-sized input the plan states what the
code holds per item, what grows with the count, and the peak, and the task building that path
prescribes a peak-memory test at two sizes (child maximum RSS where a driver or native code
allocates; spool bytes per item where a spool exists). Collect-then-act or a count-only bound is a
defect: iterate, a byte limit per item, accumulators to the first N plus a total. The one
exception is an output that must be built in memory as one piece, held behind a byte limit with a
typed refusal. If the design never answered the question, the item sends the reader to
process-plan-brainstorming's data-flow rule.

Decisions: d-20261108-2528498e, d-20261108-0c4e895e

- [x] Step 0b: no ledger existed for this skill; nothing to reverse.
- [x] RED by text check, pre-edit text: `grep -ciE 'unbounded|bounded memory|peak memory|stream|memory'`
      printed 0. A behavioural RED was not used: the probe machine's always-loaded memory index
      already carries the rule.
- [x] GREEN, item 7 pasted, opus and haiku. Scenario: Task 3 reads a caller's JSONL file of
      blob-carrying rows into a list, validates, aborts on a bad row, inserts; Step 4 tests 10
      rows. Both tiers answered "fails item 7", rewrote it as a check pass plus an action pass in
      one transaction with a two-size peak test, and quoted the item. 2 tiers, 2 cells.
- [x] Gaps closed after GREEN: which measurement (tracemalloc sees only Python objects; child max
      RSS for native allocations), growing error lists (first N plus a total), the per-item byte
      limit and caches (aligned with the brainstorming bullet), the whole-output exception (an
      output built in memory as one piece; a streamable complete file does not qualify).
- [x] Re-runs on the final text: opus quote-back (effort medium) quoted the exception, the byte
      limit and the two-size test and found no contradiction with the brainstorming bullet; haiku
      re-run on a variant (every error collected, psycopg driver, a 50000-row cap) failed the task
      and listed all eleven required changes with a quote each. No new undecided gap.
- [x] Gaps declined: numbers for N, the byte limit, the two sizes and the "not scaling" tolerance
      (ledger d-20261108-0c4e895e); server-side transaction or journal growth (not process memory,
      a database design question); how to measure child RSS in a given language (left to the
      plan; the item names what to measure).
- [x] Item 7 is one long line like items 1-6 of the Self-Review list (file style), not wrapped.
      No fence touched. ASCII only.
