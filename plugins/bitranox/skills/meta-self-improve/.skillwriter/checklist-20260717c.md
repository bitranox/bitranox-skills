# skill-writer checklist - meta-self-improve (2026-07-17c, the intent-to-ship becomes durable state)

Change: propagating a learning to a shipped skill/hook was PURE PROSE with no state. Nothing recorded
that a learning had been judged shippable, so if the session ended before the self-PR was authored the
INTENT evaporated (the private fact survived; "this should become a skill change" did not). The only
deterministic checkpoint (repo-gate's version bump) sits at the DESTINATION, downstream of every drop
point. Now: a durable per-project queue (contrib_queue.py add/list/drain), SessionStart surfaces it
every session WITHOUT consuming it, and step 3b + upstream-propagation.md say to QUEUE THE INTENT the
moment it is judged shippable - before doing the work.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: user reported "propagating to contribution also not really [working]"; a code
      investigation confirmed there is no queue/marker/state anywhere - the whole path is prose the
      model may skip, with 7 enumerated silent-drop points
- [x] GREEN: contrib_queue.py (add/list/drain) + self_improve_signals queue helpers; session-start
      surfaces N pending contributions. Tests: test_contrib_queue.py (6),
      test_self_improve_signals.py::contribution* (5), test_session_start.py::pending_contributions*
- [x] The key design distinction is TESTED, not just stated: unlike the miss-audit (consume-once), a
      pending contribution SURVIVES being surfaced - it stands until it actually ships and is drained
      (test_pending_contributions_are_surfaced_and_NOT_consumed,
      test_contribution_queue_survives_reading_unlike_the_audit)
- [x] Dedup on (what, target): re-noticing the same gap is not a second TODO
- [x] Scripts/tests: contrib_queue.py has sibling tests; run with the CI dep set
- [x] CSO description: unchanged (procedure/reference edit only)
- [x] Security scan: queue text is machine-local under ~/.claude; no secrets/PII; the scrub step in
      upstream-propagation.md still governs what may leave the machine
- [x] Docs describe current state: no legacy narrative
