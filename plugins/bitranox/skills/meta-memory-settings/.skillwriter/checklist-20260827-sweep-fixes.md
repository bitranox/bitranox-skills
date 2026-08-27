# skill-writer checklist - meta-memory-settings (2026-08-27, sweep fixes)

Three factual corrections to the knobs table.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect class is a FACTUAL claim, so the RED is a
      ground-truth check against the code or the upstream document, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft, and the arm cannot fail honestly.
      The artifact check is immune to that.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] RED/GREEN for the promotion row: `note_promotion_candidate` returns the number of DISTINCT
      PROJECTS and is documented idempotent per project ("re-recording the same project adds no
      evidence"). The row said ">= 2 dreams", which no counter in the plugin implements. Row now
      states distinct projects AND that re-dreaming one project never corroborates.
- [x] RED/GREEN for coverage: comparing `DEFAULT_CONFIG` against the table found 3 of 12 knobs
      absent (`context_window`, `context_handover_pct`, `context_handover_cap`). Re-run after the
      edit reports none missing. `meta-context-watcher` sends readers here for `context_window`
      specifically, so the front-door claim was false for exactly the knob it is cited for.
- [x] RED/GREEN for `skill_placement`: `ENUM_CHOICES` lists three legal values; the row showed one.
      All three now listed, matching every other enum row.
