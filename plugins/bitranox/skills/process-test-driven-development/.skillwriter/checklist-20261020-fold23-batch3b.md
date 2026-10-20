# skill-writer checklist - process-test-driven-development (2026-10-20, fold23 batch 3, reach-partial rows)

- [x] Change: redcheck --corpus-cascade section, paragraph 'The two answers are not worth the same,
      and the tool says which one it gave you' (REPLACED the unqualified 'A hit is STRONG evidence:
      the lesson demonstrably sits in reachable context, and the report names the file it is in.').
      Verified against ground truth: Report prints shared terms under each hit ->
      scripts/redcheck.py:557-560 ('INHERITED COVERAGE ...', label + '(N shared terms, P%)', then ',
      '.join(hit.shared[:12])); JSON carries them -> redcheck.py:259 {"label","shared","score"}.
      Tool labels hits STRONG -> redcheck.py:99-100 INHERITED_STRONG_NOTE 'STRONG - the named
      document already contains this lesson'. Overlap is term-set intersection, not a reading ->
      redcheck.py:342-347 (shared = scenario_terms & terms; shared &= rare; len(shared) >=
      min_shared). The example words are not stop-words -> _STOP at redcheck.py:173 (none of
      going/walk/replacement listed per skeptic grep).
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
- [x] Gaps closed or declined: closed - the exit-1 table row now says the report names the document
      whose terms overlap it (re-tested by quote-back on haiku and opus, both quoted it); declined -
      a definition of the subject's own vocabulary (a judgement the paragraph leaves to the reader).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; values added are
      setting names, defaults, repo file paths or reserved examples.
