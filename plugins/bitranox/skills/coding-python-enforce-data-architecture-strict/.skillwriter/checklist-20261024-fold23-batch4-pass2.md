# skill-writer checklist - coding-python-enforce-data-architecture-strict (memory rules folded in)

- [x] Change: New '### Converting a `str` parameter to an Enum changes its contract: scope it with
      its tests' before '### Anti-Patterns to Eliminate'; new Rationalizations row after the
      StrEnum-shim row; reconciled sentence in Workflow STEP B -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot:
      partial. Verified: Probe with python3 on a `class P(str, Enum): MAJOR='major'`: 'major' ==
      P.MAJOR True, 'major' is P.MAJOR False, {P.MAJOR:1}.get('major') == 1, 'major' in {P.MAJOR}
      True, `match 'major': case P.MAJOR` matches, P('bogus') raises ValueError. Core Principle 7
      'No Compatibility Shims' exists (SKILL.md line 26). Rationalizations row fits existing column
      widths; reformat_tables.py --check --strict rc=0.
- [x] Dropped as stale or unverified: Dropped the repo-specific example names (_bump_version.py,
      BumpPart, test file names) and the irrelevant 'See bitranox:devops-bmk' cross-reference;
      generalised to the scenario's release()/ReleasePart. Reconciled the existing STEP B line
      'every existing string-literal call site ... stays green', which contradicted the
      identity-dispatch case, by qualifying it with `==` (not `is`). Reworded 'no longer checks'
      (history-finder hit).
- [x] Review C fixed: the STEP B sentence names raw-string call sites that stay green wherever the
      code compares by value (==, match, dict/set lookup) rather than by identity.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
