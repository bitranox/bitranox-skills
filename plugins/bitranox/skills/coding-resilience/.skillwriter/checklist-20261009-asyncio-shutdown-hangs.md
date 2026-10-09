# skill-writer checklist - coding-resilience (2026-10-09, asyncio shutdown hangs)

New section "Python asyncio: two shutdowns that hang instead of failing": a cancel of a task that
awaits another task is delivered through the awaited child (so `except CancelledError` around
`await child` swallows the parent's own cancel), and `Server.wait_closed()` waits for every client
transport from 3.12.0 (so an orphan connection hangs the teardown); both with a verified pattern.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Home chosen by trigger: the description already carries "hang", "timeout" and "network
      connection", the words a reader whose `stop()` never returns arrives with. No other skill
      covers asyncio cancellation or server teardown (searched every SKILL.md and reference file
      for wait_closed, close_clients, CancelledError, cancelling, asyncio).
- [x] Description unchanged - no routing keyword moved, trigger map needs no rebuild.
- [x] Every claim measured before writing, on CPython 3.11.15, 3.12.0, 3.12.1, 3.12.13, 3.13.13
      and 3.14.4: the swallowing supervisor is still running 1 s after `cancel()` (3.12, 3.14);
      the `asyncio.wait({child})` and `cancelling()` patterns both end on a supervisor cancel AND
      still restart on a child-only cancel; `wait_closed()` with an idle orphan hangs on 3.12.0
      through 3.14 and returns at once on 3.11; `close_clients`/`abort_clients` exist from 3.13;
      a graceful close (`writer.close()`, `close_clients()`) still hangs `wait_closed()` when the
      peer stopped reading with data buffered, and an abort returns.
- [x] The server snippet as written in the file executed verbatim (timeouts shortened) on 3.12,
      3.13 and 3.14 against an idle client (returns at once) and a stalled reader (returns after
      the first timeout, via the abort branch).
- [x] RED (inert baseline-probe, sonnet and haiku, a PR-review scenario with both defects and no
      hint): both arms found both hangs - the capable baseline does not fail on recognition. Both
      GUESSED the 3.12 patch where `wait_closed()` changed, and neither named the stalled-reader
      case. redcheck --corpus-cascade flagged inherited coverage; adjudicated: the matching fact
      bodies have their pointers at sibling levels, not on this chain, and the CLAUDE.local.md
      hits are function words. The edit's value is the pinned versions and the verified patterns.
- [x] GREEN (sonnet and haiku, given the edited file): both found both hangs and quoted the new
      text for each; both adopted the `asyncio.wait` supervisor and client closing.
- [x] Skill gaps requested from every arm; GREEN gaps worked: timeout budget (closed: sum under
      the stop timeout), handler tracking shape (closed), which cancel pattern to prefer (closed,
      with the reason), `current_task()` None guard (closed), "bound every teardown wait" vs the
      unbounded supervisor wait (closed: "every wait in the stop path"), graceful close against a
      stalled reader (closed after measuring it). Declined: restart backoff and signal wiring
      (owned by the retry bullets and by the app), `readline()` limit (not a shutdown hang).
- [x] GREEN diffed against RED both ways: RED arms also noted SIGTERM wiring and handler
      try/finally; the handler point survives in GREEN, SIGTERM wiring is outside this section.
- [x] Fixes verified by quote-back (direct quote or NONE).
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
