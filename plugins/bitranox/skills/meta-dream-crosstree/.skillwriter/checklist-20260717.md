# skill-writer checklist - meta-dream-crosstree (2026-07-17, explicit capture-first + contribution queue)

Change: (1) added an explicit step 0 "Capture first, reading the session from DISK" - crosstree cited
dream-core only for the MODE and dedup semantics, so the shared capture-first (and with it the
session-review from disk) was only IMPLICITLY inherited by the two most expensive dreams. (2) step 7
skill-fit now lists/queues/drains the durable pending-contribution queue.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: a user question ("which dream reads from disk? I hope all of them") prompted a check that
      found the gap: nap + tree cite capture-first explicitly; crosstree and -deep cite dream-core only
      for mode/dedup, so the most expensive dreams had the weakest wiring to the step that prevents
      losing a compacted session. Verified by grep, not assumed
- [x] GREEN: explicit step 0 citing dream-core's shared capture-first + the session-review commands;
      -deep inherits via its REQUIRED BACKGROUND, which now names capture-first explicitly
- [x] Scope reasoning recorded: session-review does NOT vary by mode (the session is one thing; capture
      routes by SUBJECT, not by dream scope); what varies is CONSOLIDATION scope. The watermark is
      deliberately SHARED across modes so whichever mode reviews first, the others do not re-pay
- [x] Single-sourced: the rule stays in dream-core; the skill cites it - contract test green
- [x] CSO description: unchanged (procedure edit only)
- [x] Security scan: prose + CLI references only
- [x] Docs describe current state: no legacy narrative
