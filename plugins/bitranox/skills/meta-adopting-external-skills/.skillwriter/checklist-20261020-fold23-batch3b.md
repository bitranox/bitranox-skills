# skill-writer checklist - meta-adopting-external-skills (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: Step 4 - Integrate and pass the gate (new paragraph after the attribution/house-style
      paragraph) + Common mistakes (new bullet). Verified against ground truth: Helper writes both
      -> adopt_skill.py:790 def add_credit_line (credit = f"> Adapted from {source_desc}
      ({lic_id})." at :800) and :818 def append_notice. Gate checks only sync ->
      hooks/repo-gate.py:560 `if not credited and not noticed: return []`, :563-569 report only
      credited-minus-noticed and noticed-minus-credited, so a skill with neither line is in neither
      set and passes. Renaming on adoption -> adopt_skill.py:586 normalize_name and :885-906
      validate_category refusing a name without an approved category prefix (so adopted names carry
      a category prefix; strip it before matching). Credit marker '> Adapted from' is the gate's own
      phrasing (repo-gate.py:569).
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
- [x] Gaps closed or declined: declined - the audit half also belongs where a catalogue review loads
      (meta-skill-audit): the fact keeps its always-loaded pointer for that moment, and the
      meta-skill-audit addition is queued as a contribution.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
