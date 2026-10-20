# skill-writer checklist - ai-llm-jev-judge (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: ## Procedure, step 4 (Pilot) opening, and step 5 (reconciled the FLAT reading).
      Verified against ground truth: Pre-existing step 4 text ('If two rewrites still fail the
      pilot, Jev is the wrong tool here: say so and judge another way') and step 2 ('Put each piece
      of evidence in its own named field') kept intact; the new text is a pre-pilot check that adds
      a third reading of a flat result. Step 5's two readings (broken question / items alike)
      extended with the third in the same edit, so the two steps no longer disagree. The 'not for
      building Jev into an application' exclusion is unchanged (frontmatter untouched).
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
- [x] Gaps closed or declined: declined - whether a refusal gate in agent tooling is 'building Jev
      into an application' (the scope line predates this edit and is not changed here).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
