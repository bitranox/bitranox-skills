# skill-writer checklist - process-test-design (memory rules folded in)

- [x] Change: SKILL.md, 'Deterministic and order-independent' - a test that sends a fatal signal to
      its own process installs a raising handler first (POSIX-only, Windows skip); a fixture
      serving from a listening socket calls shutdown() before close(), and a RED with skips is
      not a RED (-rs, 0 skipped). references/silent-test-defeaters.md - a dataclass double that
      redefines a field as a property fails at construction: dataclasses.replace for a fixed
      value, a __getattr__ proxy only for a computed one; read the failing line of every RED.
- [x] Verified: socket close() vs accept() and the rebind EADDRINUSE run on Linux; the dataclass
      property AttributeError run on Python 3.12-3.14; os.kill on Windows is TerminateProcess
      per the Python os.kill documentation.
- [x] Declined gaps: whether to keep a busy-port skip (test-design judgement, the rule is 0 skipped
      in RED); behaviour on other OSes beyond the Windows skip (not measured); the
      AttributeError wording on older Pythons (the failure, not the message, is the rule).
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
