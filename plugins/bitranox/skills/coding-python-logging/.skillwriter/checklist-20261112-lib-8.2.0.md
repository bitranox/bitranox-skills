# skill-writer checklist - coding-python-logging (2026-11-12, lib_log_rich 8.2.0)

Edit: `SKILL.md` row "Graylog enabled, nothing arrives" and `sinks-and-deployment.md`, Graylog
section ("Level gate", "Delivery", the unreachable-server bullet, a new "Gap report" bullet, "What
the app sees"). lib_log_rich 8.2.0 backs off from an unreachable Graylog (5 s doubling to 300 s),
reports skipped events to Graylog as a WARNING with `_skipped_events`, logs an adapter `OSError` as
one line without a traceback and exports `GraylogUnavailableError` from `lib_log_rich.adapters`.
Twin of `libs/lib_log_rich/skills/python-logging`, identical apart from the conventional
divergences. Frontmatter unchanged.

## PLAN
- [x] Skill type: reference. Test: RED as a retrieval probe on the pre-edit text (the installed copy
      is the old text), GREEN as the same probe on the edited text, opus and haiku.

## RED
- [x] Each claim checked against the code and tests first: `tests/adapters/test_graylog_adapter.py`
      (tried once then skipped, doubling, 300 s cap, skipped-events notice with level 4 and
      `_skipped_events`, reset on recovery, UDP, TLS close, a real refused port),
      `tests/application/test_fan_out_dispatch.py` (an `OSError` logs one line without `exc_info`, a
      `ValueError` keeps it), and probes against the real runtime: a refused port printed one line and
      shut down in 1.00 s (the old code: a traceback per event and `RuntimeError` after 5.00 s); a
      packet-dropping endpoint printed one `(timed out)` line and shut down in 1.01 s. The 7-attempt
      schedule was computed from the window rule; an unconnected UDP `sendto` to a dead port was run
      and does not raise.
- [x] RED probe (opus) on the pre-edit text, 600 events over a 10 minute outage: answered two connect
      attempts per event, a traceback per event, no loss visible in Graylog, exception type NOT
      STATED - the old behaviour, as expected.

## GREEN
- [x] Same probe on the edited text, opus and haiku: 7 attempts, one stderr line per window without
      a traceback, the `_skipped_events` WARNING, `GraylogUnavailableError` from
      `lib_log_rich.adapters`, all by quote.
- [x] Gaps the GREEN probes raised, folded in after a check against the code: worst case about 2 s
      for a send that times out on an open connection plus the reconnect; attempts happen only when
      an event arrives; later lines name the new window; the notice rides on the next event that
      passes `graylog_level` and is sent whatever the gate says (and the "Level gate" bullet now names
      that exception); the count is held in memory and lost when the process exits first; shutdown
      drains for up to `queue_stop_timeout`; not importable from `lib_log_rich` (checked: `hasattr`
      False).
- [x] Re-check (haiku) on the revised text with a short-CLI scenario: 3 attempts in 30 s, second
      line "10 s", the WARNING never reaches Graylog from that run, exact import line - all correct;
      its one contradiction (level gate vs notice) is fixed by the "Level gate" sentence above.
- [x] Non-ASCII: none added. No added line over 105 characters. Frontmatter untouched.
- [x] `repo-gate.py --mirror-of <lib_log_rich worktree>` reports `in sync`.
- [x] No address, hostname or private path added (the examples use `<host>:<port>`).
- [x] Decisions: none - the edit records measured library behaviour of 8.2.0; no wording or scope
      choice in it is a judgement a later edit could reverse.
