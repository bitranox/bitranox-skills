# skill-writer checklist - meta-dream-nap (2026-10-16, fold of always-loaded rules)

- [x] Change: "When to run", compaction bullet: added that a block naming an EARLIER session's
      transcript means that file holds unread material (the gate already drops a missing or fully
      consumed one), that a completed nap does not clear the flag (only `dream_state.py done` or
      the auto-drop does), and that the flag is never deleted by hand.
- [x] Change: "When to run": new bullet for a nap owed while plan mode is active - write "run the
      owed nap" as step 0 of the plan, naming the learnings, and run it right after ExitPlanMode.
- [x] Change: step 1 (Capture first): a nap deferred from an earlier session starts from the
      learnings the handover names and reads the last turns before the handover closely;
      deferral is cheaper, never better.
- [x] Ground truth for the flag text: `hooks/self_improve_signals.py` `mark_dream_done` calls
      `clear_nap_owed(proj)`, and `unsatisfiable_nap_owed` returns `NAP_OWED_TRANSCRIPT_GONE` for a
      missing path and `NAP_OWED_TRANSCRIPT_CONSUMED` when an earlier session's `dream` watermark
      reaches the file size; `hooks/self-improve-gate.py` clears the flag only in those two cases.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded the skill
- [x] RED (text check of the artifact): before this edit the skill had no text for the stale
      nap-owed flag, the deferred-nap weighting loss, or a nap owed under plan mode (verifier gaps:
      "never says to read the EARLIER session's named transcript ... never says a completed nap
      does not clear the flag"; "does not say to read the last turns before the handover closely";
      "The skill never mentions plan mode"). Behavioural RED replaced on purpose because the rules
      are in the always-loaded memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): stale nap-owed
      flag -> SKILL.md:46 "When the block names an EARLIER session's transcript, read that file"
      + SKILL.md:48-50 "A completed nap does NOT clear the flag; only `dream_state.py done` (step 6)
      or that auto-drop does ... Never delete the flag by hand."; deferred-nap weighting ->
      SKILL.md:67-70 "When the nap was DEFERRED from an earlier session that handed over ... read
      the last turns before the handover closely ... Deferral is cheaper, never better."; nap owed
      under plan mode -> SKILL.md:51-53 "Owed while plan mode is active ... Write 'run the owed
      nap' as step 0 of the plan, naming the specific learnings, and run it right after
      ExitPlanMode."; contradictions: none in job; unlinked md: none in job; step-4 scan of the
      SKILL.md diff: no non-ASCII, no hostnames/paths, no private provenance.
- [x] Gaps closed or declined: none open. Noted, not blocking: "the last turns" is not sized (how
      far back to read closely is left to judgment).
- [x] Description measured: unchanged (433 chars)
- [x] `test_dream_skill_contracts.py`, `test_post_compact_nudge.py` and `test_skill_roster.py` pass
      after the edit.
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
