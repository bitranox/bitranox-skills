# skill-writer checklist - process-debug-systematic (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: Phase 3: Hypothesis and Testing, step 2 'Test Minimally' (new last bullet, after 'Run
      both arms from the SAME path'). Verified against ground truth: Placement: complements the
      existing 'One variable at a time' under Test Minimally (SKILL.md:166-169) without
      contradicting it. No repo-checkable claims (procedural rule); the parser case in the body is
      historical and was not carried over.
- [x] Claims the source contradicts were dropped or corrected, and machine-local figures and history
      were not carried over.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): partial for scenario 1.
      Behavioural RED replaced on purpose: each rule is in the always-loaded memory index of the
      authoring machine (inherited coverage), so the RED is a quote-back against the pre-edit file.
- [x] GREEN quote-back on haiku and opus against the edited files; every quote checked against the
      skill's files (a fragment check, then a grep of each inserted rule's lead sentence), all
      present.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Pass also run on the weakest tier: haiku arm beside opus for every scenario; tiers haiku and
      opus, one cell per scenario per tier.
- [x] Gaps closed or declined: declined - interactions of three or more ingredients (pairs are the
      stated next step; wider sets follow the same method).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
