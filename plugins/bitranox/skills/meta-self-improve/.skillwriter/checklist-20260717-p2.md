# skill-writer checklist - meta-self-improve (2026-07-17, P2: the audit's three sources)

Change: the miss-audit section described a prose-only scan. It now names the three sources the
audit actually reads - prose, TOOL blocks (tool_use commands + tool_result output), and the skill
tally - and states the skill-gap correlation: a miss that shipped DESPITE a skill that ran is that
skill's coverage gap, not merely a fact to remember.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: verified in code, not assumed - self-improve-audit.py's `_text()` extracted only
      `b["text"]`, so tool_use/tool_result blocks were never scanned at all; and nothing recorded
      which skills ran, leaving flag-a-skill-when-a-real-bug-slips-past-it with no data but recall.
      Failing tests written first (tool-only learning not found; report names no skills).
- [x] GREEN: TOOL_SIGNAL_PATTERN + tool_matches() + skills_invoked() in self_improve_signals.py;
      audit scans a synthetic "tool" role and reports the tally; 141 hook tests + 14 dream_state
      tests green
- [x] Precision, not just recall: tightened `wait[, ]`, which fired on ordinary narration and made
      6 of 13 candidates noise in a real session - an audit is only acted on if it stays scannable
- [x] Docs match the code: the three sources are what the hook does, verified by test
- [x] Security scan: prose + stdlib only, no secrets, hostnames, or private paths
- [x] CSO description: unchanged (body edit only)
