# skill-writer checklist - process-plan-brainstorming (2026-11-08, memory bound at design)

"Presenting the design" gains a bullet: the data-flow section decides memory for every input
whose size the caller controls (held per item, growth, peak), before the first data structure is
chosen. Iterate by default; spool read-once input to a disk file under a byte limit; a count limit
is no memory bound, so bound item size too; validate-then-act is a check pass plus an action pass;
accumulators keep the first N plus a total; hold a whole output only when it must be built in
memory as one piece, behind a byte limit. The same rule goes into process-plan-writing-plans as
Self-Review item 7 (its own checklist).

Decisions: d-20261108-1c917d46, d-20261108-6638c093

- [x] Step 0b: no ledger existed for this skill; nothing to reverse.
- [x] RED by text check, pre-edit text: `grep -ciE 'unbounded|bounded memory|peak memory|stream|memory'`
      printed 0. A behavioural RED was not used: the always-loaded memory index on the probe
      machine already carries the memory-bound rule, so a no-skill arm inherits the answer.
- [x] GREEN, edited bullet pasted, opus and haiku. Scenario: a CSV-to-label design parsed into a
      list, validated, then sent, "max_records=16000 keeps memory safe". Both tiers answered "not
      acceptable", rewrote it as two streaming passes with only counters held, kept max_records as
      a time limit, and quoted the bullet. 2 tiers, 2 cells.
- [x] Gaps closed after GREEN: validate-then-act case (now "a check pass that discards each
      result, then an action pass"), growing error lists (first N plus a total), the other factor
      of items x size (byte limit per item), read-once input (spool to a disk file; a tmpfs /tmp is
      memory), "must be whole" (built in memory as one piece; a streamable complete file does not
      qualify).
- [x] Re-runs on the final text: haiku scenario re-run (with an every-error report added) passed
      and applied first N, byte limits and two passes; opus quote-back (effort medium) found every
      clause and no contradiction with writing-plans item 7; a last haiku quote-back on the two
      touched clauses quoted both and found no contradiction. No new undecided gap.
- [x] Gaps declined: values for N, byte limits and "typed refusal" (a per-project choice,
      ledger entry d-20261108-0c4e895e in process-plan-writing-plans); a file changing between the
      two passes and a sink that forces the whole job (judgement for the design, not a memory
      rule); the "200-300 words per section" vs the probe's own word cap (an artifact of the probe
      prompt).
- [x] Added lines: none over 100 columns, no fence. ASCII only.
