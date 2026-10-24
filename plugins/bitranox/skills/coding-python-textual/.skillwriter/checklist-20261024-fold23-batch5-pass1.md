# skill-writer checklist - coding-python-textual (memory rules folded in)

- [x] Change: ## Names that behave the opposite way from how they read - new paragraph under the
      table, plus two sentences appended to the overflow-x paragraph -
      coding-python-textual/SKILL.md. RED on the pre-edit snapshot: partial. Verified: All against
      an installed textual 8.2.8 venv: ActiveBinding._fields ==
      ('node','binding','enabled','tooltip'), Screen.active_bindings and DOMNode.refresh_bindings
      exist (python -c probe); active_bindings calls check_action on every read, skips `is False`,
      sets enabled=bool(state) so None -> enabled False (textual/screen.py def active_bindings);
      Footer reads screen.active_bindings (widgets/_footer.py:247) and redraws on
      bindings_updated_signal (_footer.py:330), published by Screen.refresh_bindings
      (screen.py:392-394); refresh triggered by focus (screen.py:378-379 _watch_focused), stack
      updates (screen.py:381-382), reactive bindings=True (reactive.py:152, 360-361); DataTable
      virtual_size = sum of column render widths + label column (widgets/_data_table.py:1507-1515);
      overflow-x auto -> show_horizontal = virtual_size.width > width (widget.py:2094-2095);
      scrollbar_size_horizontal default 1 (css/styles.py:429); show_horizontal_scrollbar is a
      Reactive (widget.py:381).
- [x] Dropped as stale or unverified: Skeptic/body claim 'check_action is only re-consulted after
      refresh_bindings()' is imprecise: active_bindings re-consults check_action on every read; only
      the Footer's redraw waits for a refresh, and refreshes also happen on focus change, screen
      stack updates and reactive(bindings=True). Text states the verified version. Dropped the
      private project name and the 'three of four cost a defect' history (skill already carries its
      own version of that line).
- [x] Review C fixed: the Footer redraw list is no longer "only" these four triggers; textual 8.2.8
      calls refresh_bindings on more paths, the advice to call refresh_bindings() after changing a
      plain attribute stands.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (6 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
