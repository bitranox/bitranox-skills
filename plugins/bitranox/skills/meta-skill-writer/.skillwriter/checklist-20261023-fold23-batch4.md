# skill-writer checklist - meta-skill-writer (fold of memory rules into the skill)

- [x] Change: 'Write the skill and its artifacts in the present tense, not as a story' (new
      paragraph after the <Good> example), plus a Quality Checks checklist line after the 'No
      session narrative' line. Verified against ground truth: Conflict with vendored doc:
      anthropic-best-practices.md:566-584 recommends an 'Old patterns' <details> section -> new text
      states it overrides that (vendored file left unedited, per the skill's own 'Vendored upstream
      documentation keeps its own examples' rule, SKILL.md ~605). Pinned-skill exception exists ->
      SKILL.md:505-509 ('ONLY when the skill is pinned to one library version'). Finder grep tested:
      matches all four body examples ('From btx_lib_mail 2.0.0', 'Before 3.0.0', 'Available from
      1.8.0', 'before 1.8.0'), skips 'Baseline is uv 0.10.2' and 'x>=0.3.2' (printf | grep -niE).
- [x] Change: REFACTOR: Close Loopholes - new paragraph right after '**Where the loop stops:**' (the
      gap-triage step), before 'A probe stops at the first gap it trips on'. Verified against ground
      truth: Existing half: testing-skills-with-subagents.md:372-376 ('A gap declined as "covered
      elsewhere" needs a grep of the elsewhere ... quote the line you found in the review artifact')
      - new text is consistent (requires file, line and quoted wording) and adds the missing
      converse. Placement: SKILL.md 'Where the loop stops' (~line 1287) lists decline reasons and is
      where gaps are triaged; Skill gaps requirement at SKILL.md:1225. Skeptic's exception (excerpt
      met alone: reference loaded on demand, description, injected section) included so real gaps in
      standalone-read files are not declined. No contradiction with existing lines.
- [x] Added after review: the history finder names Starting with / As of / New in / as before, both
      passes share one pattern, the joined-text pass joins whitespace runs and labels hits with the
      file name safely; the decline-reason list names covered-elsewhere.
- [x] Claims the source contradicts were dropped or corrected; machine-local figures, private names
      and incident history were not carried over.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against the pre-edit snapshot (partial for scenario 1;
      partial for scenario 2). Only a verbatim quote from the snapshot counts, so context inherited
      from this machine cannot satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files, in four rounds: after the edit,
      after the first review's fixes, after the delta review's fixes, and a final round on the
      questions the last fixes touched. Every scenario was answered with a quote from the new text
      on both tiers in every round; no NONE.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text;
      nothing the baseline answered was lost.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or recorded below.
- [x] Gaps closed or declined: closed - the missing history openers, one shared finder pattern, a
      joined pass that survives indented wraps and odd file names, rewrite-versus-review wording,
      the covered-elsewhere decline reason (re-tested by quote-back on haiku and opus); declined -
      how to locate a mirrored twin (repo-specific machinery, routed to the repo's CONTRIBUTING per
      this skill's universal-versus-marketplace section), a bare X.Y.Z alternative (matches every
      floor and example; the review step judges candidates), non-Markdown files (scripts and data
      carry no history prose), line numbers in the joined pass (the file label plus the excerpt
      locate it), phrasings such as 'onwards' (the review catches them; add one to the pattern when
      it recurs).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, repo file paths or reserved examples.
