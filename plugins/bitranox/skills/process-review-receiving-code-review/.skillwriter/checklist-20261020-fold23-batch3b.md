# skill-writer checklist - process-review-receiving-code-review (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: Verify-before-implementing block: new paragraph after 'A prescribed fix is a
      hypothesis, even when the finding is right.', plus a one-line qualifier under 'IF suggestion
      seems wrong: Push back with technical reasoning'. Verified against ground truth: Example case
      -> hooks/self_improve_signals.py:2575-2579 (skeptic-confirmed): a pytest run closes only on a
      TIMED summary ('12 passed in 0.40s'); a bare count let a pyright run's per-line output
      through. Existing stance kept consistent: SKILL.md 'A prescribed fix is a hypothesis, even
      when the finding is right' and 'External feedback = suggestions to evaluate, not orders to
      follow' both still stand; the new text makes both readings hypotheses decided by data, which
      is the fact body's own resolution.
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
- [x] Gaps closed or declined: declined - what to do when no real data exists (out of scope for this
      rule).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
