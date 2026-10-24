# skill-writer checklist - coding-python-textual (memory rules folded in)

- [x] Change: New '### Generated key bindings share one namespace with `BINDINGS`' subsection under
      '## Names that behave the opposite way from how they read', after the overflow-x paragraph and
      before '### The vendored docs carry one local fix' - coding-python-textual/SKILL.md. RED on
      the pre-edit snapshot: NONE. Verified: textual 8.2.8 (installed in a project venv, METADATA
      Version 8.2.8): BindingsMap.key_to_bindings is dict[str, list[Binding]] with
      setdefault().append (binding.py:203-207); make_bindings splits comma keys
      (binding.py:122-150); DOMNode._merge_bindings assigns keys[key] = key_bindings per MRO class,
      so a subclass replaces the base's list (dom.py:671-695); App.BINDINGS holds ctrl+q
      priority=True and ctrl+c (app.py:454-464); COMMAND_PALETTE_BINDING = 'ctrl+p' (app.py:441).
      Probe: class with two f9 bindings -> key_to_bindings['f9'] == ['rescan','page_9']; subclass
      ctrl+q replaced base 'quit'. The test snippet was executed against textual 8.2.8 with a stub
      generator: 9 pages -> 'bound twice: ['f9']', 8 pages -> pass.
- [x] Dropped as stale or unverified: Dropped the lsdsk-specific 'f9 = rescan' instance (fixed
      since; rescan is now r,f10) and the review-history narrative. Did NOT claim which of two
      duplicate bindings wins at dispatch (priority mechanism unverified, per skeptic).
- [x] Review C fixed: the binding test walks MyApp.__mro__ (an intermediate base class's BINDINGS)
      and carries an overrides set; focused screens and widgets named. Re-run on textual 8.2.8 with
      an intermediate base holding "r,f9": nine pages report ['f9'], eight report [].
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
