# skill-writer checklist - net-firewall-pfsense (memory rules folded in)

- [x] Change: SKILL.md, traps - a pkg upgrade of a base component (unbound, openvpn) does not
      restart it: restart with a pfSsh.php playback script, confirm the start time with
      ps -axo lstart and resolve through the local resolver.
- [x] Dropped as unverified: comparing the on-disk version with the running daemon (no verified way
      to read the running version); an openvpn restart form (none verified).
- [x] Quote-check only (already covered, no text change): Snort Block Offenders adding a legitimate
      destination to snort2c - the RED quote-back found the rule in the current text.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts. Folded rows: NONE at RED.
- [x] GREEN quote-back on haiku and opus against the edited files, then again after the review fixes
      for every question they touched (7 questions, 14 cells): every answer quoted the new text,
      no NONE. Quotes were substring-checked against the files; misses traced to joined
      excerpts, list items run together and one punctuation mark after a reorder.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed
      (ssh-keygen -R target file, Windows os.kill, 'upgraded', lstart, href allowlist,
      dataclasses.replace, two ragged wraps, a caveat's placement) or declined above.
      Each GREEN Skill gaps list read.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), every fence
      closes, added prose wrapped at 100 columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are RFC 5737
      documentation ranges.
