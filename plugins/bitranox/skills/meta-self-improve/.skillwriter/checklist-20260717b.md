# skill-writer checklist - meta-self-improve (2026-07-17b, subagent learnings are capturable at all)

Change: a subagent's learning was structurally UNCAPTURABLE - there was no `SubagentStop` hook at all,
the capture nudge fires only on the MAIN session's Stop, nothing ever opened a subagent transcript, and
a named/background agent's report is not returned to main unless it SendMessages it. So a correction or
discovery a subagent made was lost unless the main agent happened to restate it. Now a `SubagentStop`
hook detects signals in the SUBAGENT's own transcript and buffers them; the Stop gate surfaces them
verbatim (and blocks EVEN WHEN the main turn is quiet, since no main-turn pattern can ever fire for a
finding that is not in the main transcript); step 3b tells the model those learnings are its to route
and write, and that they are surfaced once.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: user asked "I also dont know if learnings from subagents are working?" - a code
      investigation proved they are not: `grep -rn SubagentStop` = ZERO hits repo-wide; gate + audit
      each read only `event["transcript_path"]` (the main transcript); `<SUBAGENT-STOP>` even steers
      subagents away from the skill machinery. This session was the live example: the fan-out agents'
      findings reached memory only because I restated them by hand
- [x] GREEN: subagent-capture.py (SubagentStop) scans the subagent transcript + buffers; the gate
      surfaces + blocks on it even with a quiet main turn; drained once (consume-once, like the
      SessionStart audit) so it cannot re-nag. Tests: test_subagent_capture.py (6) +
      test_self_improve_gate.py (buffered-learning blocks / is named / no-noise-when-empty)
- [x] PROBE-CORRECTED before building (iron rule): the live probe proved `SubagentStop` DOES fire but
      its `transcript_path` is the MAIN session's - the subagent's own transcript is
      `agent_transcript_path`. The plan said to scan `transcript_path`; that would have read the wrong
      conversation. A regression test pins this (test_reads_the_AGENT_transcript_not_the_main_one).
      The probe also found `last_assistant_message` on the event - the subagent's final text for free
- [x] Fail-open: the hook never emits a decision and always exits 0 - a subagent finishing must never
      be blocked or wedged by capture machinery
- [x] Scripts/tests: `subagent-capture` registered in hooks/tests/conftest.py `_HOOK_MODULES`; run with
      the CI dep set
- [x] CSO description: unchanged (procedure edit only)
- [x] Security scan: snippets are capped transcript text kept machine-local under ~/.claude; no
      secrets/PII written anywhere shared; no unsafe code
- [x] Docs describe current state: no legacy narrative
