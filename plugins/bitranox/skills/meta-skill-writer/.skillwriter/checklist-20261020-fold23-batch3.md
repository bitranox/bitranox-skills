# skill-writer checklist - meta-skill-writer (2026-10-20, fold23 batch 3)

- [x] Change: Frontmatter block - the truncation boundary is named as the `skillListingMaxDescChars`
      setting (default 1536) instead of a measured 1060/2124 pair; a new bullet says a description
      under every cap can still be dropped WHOLE by the listing budget
      (`skillListingBudgetFraction`, default 0.01, never-used skills first); the "listing cannot be
      read off disk" bullet is replaced by reading the session's `skill_listing` transcript
      attachment. Ground truth: `hooks/skill-listing-budget.py:40-41` (MAX_DESC_CHARS = 1536),
      `:58` (HARNESS_DEFAULT_FRACTION = 0.01), `:4-9` (fallback and restore order);
      `hooks/skill_roster.py:8-12`, `:297` (`att.get('type') == 'skill_listing'`);
      `hooks/harness_checks.py:219` (DESCRIPTION_CAP = 1024).
- [x] Change: new section "Say Whose Verdict Is the Result" (a step with a second opinion names the
      agent's own verdict as the output; shadow vs advisory wording; test on haiku).
- [x] Change: RED section gains "The probe can also fetch the skill under test" (baseline-probe
      keeps the Skill tool; new skill -> uninstalled draft, edit -> coverage check on the pre-edit
      file; an off-limits line inverts a retrieval or GREEN arm; a GREEN arm with pasted text can
      load the installed old version, so check quotes against the pasted text).
- [x] Change: REFACTOR "Where the loop stops" - a gap NOT STATED in both RED and GREEN predates the
      edit, still goes on the list, and "not caused by this change" is not a decline reason.
- [x] Change (consistency): testing-skills-with-subagents.md "baseline contamination" now names
      three routes; Route 3 is the Skill-tool load, pointing at the SKILL.md paragraph.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first SKILL.md edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): description cap -
      partial (the 1024 cap and silent truncation were stated; no setting, no listing budget);
      installed-skill contamination - partial (contamination routes 1-2 only, nothing on the Skill
      tool or an off-limits line); shared NOT STATED - partial ("Where the loop stops" only);
      second-opinion verdict - NONE. Behavioural RED replaced on purpose: the four rules are in the
      always-loaded memory index of the authoring machine (inherited coverage), so the RED is a
      quote-back against the pre-edit file.
- [x] GREEN quote-back on haiku and opus, every quote substring-checked against the edited files
      (0 unmatched): description -> SKILL.md:218 "The cut is a setting, not the documented 1024."
      and :224 "A description under every cap can still be dropped WHOLE."; contamination ->
      :1151 "The probe can also fetch the skill under test."; shared gap -> :1253 "A gap RED and
      GREEN both report - a question answered NOT STATED in both arms - predates your edit.";
      second opinion -> :988 "### Say Whose Verdict Is the Result".
- [x] GREEN diffed against RED both ways: every RED partial quote is still present in GREEN's
      answers; nothing the baseline answered was lost.
- [x] Gaps closed or declined: closed - a GREEN arm can load the installed old version (sentence
      added to :1163-1165, re-tested by quote-back on haiku and opus, both quoted it); declined -
      "this repo's commit gate" is unnamed (pre-existing wording, the gate is repo-specific and
      named in CONTRIBUTING.md); "coverage check" reused outside routing tables (the RED section
      already defines the coverage check against the skill file); where a shadow verdict is
      recorded (skill-specific, left to the skill that adds the step).
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII; every value added is a
      setting name, a default or a repo file path
