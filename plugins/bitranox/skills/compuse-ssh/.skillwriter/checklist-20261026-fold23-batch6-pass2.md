# skill-writer checklist - compuse-ssh (memory rules folded in)

- [x] Rule: The agent should not trust the Windows receiver's size, which stays at 0 (or at the
      old size when overwriting) until the write handle closes. It should measure progress at the
      sender by sampling /proc/<scp-pid>/io rchar twice over an interval, finding the pid with
      pgrep -x scp and confirming the file via /proc/<pid>/fd. For integrity it should run a tool
      that parses the file (Get-WindowsImage -ImagePath for a .wim), never rely on a byte-count
      match.
      Where: SKILL.md, ## Quick reference table, new row directly after 'Slow/large remote download (GB
      image, model, tarball)' (cells padded to the existing 80/774 column widths)
- [x] Rule: The agent should note that ConnectTimeout bounds only the connect and banner, so a
      stalled session can hang forever. It should add subprocess timeout= and catch TimeoutExpired
      as a failed read (e.g. rc 124), add -o ServerAliveInterval=5 -o ServerAliveCountMax=2, and
      give the sweep a whole-run deadline below the unit's TimeoutStartSec. Without that, a hang
      gets the unit killed with a false failure alert and leaves the other targets unread.
      Where: SKILL.md, ## Quick reference table: new row after 'Long remote reload/restart over SSH';
      that row and 'Slow/large remote download' corrected (cells padded to the existing 80/774
      widths)
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 2 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 4 closed in the text, 8 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
