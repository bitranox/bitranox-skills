# skill-writer checklist - compuse-ssh (memory rules folded in)

- [x] Change: ## Quick reference table - new row directly after 'Remote Windows PowerShell' -
      compuse-ssh/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: No Windows host contacted
      (read-only, no system changes). Type-3 network logon lacking DPAPI master key, interactive
      desktop and per-user drive maps: standard Windows behaviour, as stated in the body (unverified
      here). 1312 = ERROR_NO_SUCH_LOGON_SESSION, consistent. `/it` runs only while the /ru user is
      logged on interactively: Microsoft schtasks /create documentation semantics (the skeptic's
      precondition). `>` in /tr not being a redirect: tree-top recorded observed behaviour (schtasks
      /tr runs the program directly with no shell), consistent with the body's 'redirect
      stdout/stderr to a file' only if done inside the wrapper, so the row says the script writes
      its own output file. compuse-ssh had no schtasks/DPAPI/1312 text before (grep).
- [x] Dropped as stale or unverified: Nothing dropped as stale. Replaced the body's 'redirect
      stdout/stderr to a file' (which would silently fail if put in /tr) with 'a .ps1/.cmd that
      writes its own output file'.
- [x] Change: ## Quick reference table - new row after the interactive-session row (second row after
      'Remote Windows PowerShell') - compuse-ssh/SKILL.md. RED on the pre-edit snapshot: partial.
      Verified: Procedural rule, no measured case in the body (UNVERIFIED as a measurement, carried
      as procedure only). PowerShell single-quoted strings do not process escapes, so '\\' + $server
      + '\' + $share yields \\server\share. Error 67 = ERROR_BAD_NET_NAME (network name not found),
      consistent with a collapsed leading \\. Existing skill already has the .ps1/-File rule (row
      'Remote Windows PowerShell') and the quoting-layers paragraph ('Each layer strips a level of
      quoting'); new row complements, does not contradict. The 1312 cross-reference ties it to the
      network-logon row added for the sibling fact.
- [x] Dropped as stale or unverified: None. 'VM config' kept generic ('that VM's own config'); no
      host names.
- [x] Gaps declined: the schtasks /create arguments the row elides (/tn, /tr, /sc) are not in the
      source either and were not measured here; schtasks /create /? documents them. The query for
      whether a user is logged on interactively is likewise left to the reader.
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
