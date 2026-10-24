# skill-writer checklist - meta-context-watcher (memory rules folded in)

- [x] Change: Pickup flow, new paragraph directly after '**A background agent the handover names as
      running is LIVE.**' - meta-context-watcher/SKILL.md. RED on the pre-edit snapshot: partial.
      Verified: ListAgents lists 'other local Claude sessions on this machine': CONFIRMED from the
      ListAgents tool description in this harness. ~/.claude/sessions/<pid>.json exists with keys
      including pid, name, messagingSocketPath, sessionId: CONFIRMED by a read-only listing and key
      dump (values not printed); `claude --version` = 2.1.310. Not previously in the skill (only the
      background-agent LIVE paragraph): CONFIRMED by grep.
- [x] Dropped as stale or unverified: Dropped the memory-slug cross-reference in the body's Why
      line. Reworded 'no longer' (history-finder hit) to 'changes from ... to'.
- [x] Review B nit fixed: the registry lookup reads ~/.claude/sessions/*.json (or CLAUDE_CONFIG_DIR)
      as JSON on the top-level name, since a grep also hits formerNames; the one-liner returned the
      live pid for a running session and [] for an unknown name.
- [x] Delta review 2 blocker fixed: the closing fence now stands alone (markdown-it-py parse: the
      fence spans 3 lines).
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
