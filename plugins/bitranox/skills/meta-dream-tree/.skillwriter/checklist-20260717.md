# skill-writer checklist - meta-dream-tree (2026-07-17, drain the pending-contribution queue; session-review)

Change: (1) step 10 skill-fit now DRAINS the durable pending-contribution queue first (contributions
earlier sessions judged shippable but never shipped are part of this batch), QUEUES each new one as it
is found so it survives the session, and drains only what actually shipped. (2) dream-core capture-first
now mandates `dream_state.py session-review` - reading the session from DISK - because a dream that
skims only its own context loses everything a compaction cleared (the transcript file survives; the
context does not).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: (1) no state tracked a pending contribution -> intent died with the session (code-verified:
      no queue/marker anywhere). (2) the dream never opened a transcript; after a compaction the nap
      worked off the summary and the pre-compaction learnings were silently lost
- [x] GREEN: (1) contrib_queue.py list/add/drain wired into step 10, tested. (2) session-review proved
      e2e on a realistic growing transcript: a learning discussed BEFORE a compaction is recovered
      from disk afterwards, and the next review returns only the new bytes, not the prefix
- [x] Single-sourced: the session-review mandate lives in dream-core "Capture-first" (the shared core
      for ALL modes), not restated per skill - contract test green
- [x] CSO description: unchanged (procedure edit only)
- [x] Security scan: prose + CLI references; no secrets/PII/unsafe code
- [x] Docs describe current state: no legacy narrative
