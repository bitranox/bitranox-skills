# skill-writer checklist - coding-resilience (memory rules folded in)

- [x] Change: Patterns, new bullet directly after 'Retry with backoff + jitter, always under a hard
      timeout' - coding-resilience/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: Linux
      probe CPython 3.14.4: threading.TIMEOUT_MAX -> 9223372036.0 (the ~9.2e9 s Linux figure);
      socketpair settimeout(3e9) accepted; float(10**400) -> OverflowError 'int too large to convert
      to float'; str(10**5000) -> ValueError 'Exceeds the limit (4300 digits) for integer string
      conversion'. Windows-only claims (TIMEOUT_MAX 4294967.0, bisected 2147483.647 s ceiling,
      OverflowError at use not at settimeout) could not be re-run here (skeptic: UNVERIFIED, Windows
      only); kept as observed behaviour with the version the body gives ('observed on CPython
      3.14'). No conflict with existing text: the retry bullet says only to time-bound every wait.
- [x] Dropped as stale or unverified: Dropped private names: the Windows dev VM host name, the mail
      library and its private constant name, the measurement date. Dropped the '3.11+' version
      qualifier on the str() limit (history-style wording; the 4300-digit limit stated as current
      behaviour). No table row added (bullet carries the full rule). Did not cite the slug.
- [x] GREEN gap fixed: one cap, 2147483 s, explained against the 2**31 - 1 ms limit (2147483.647 s);
      an isinstance check before float(); math.isfinite() after converting a string, since
      float("1e400") returns inf and float("nan") returns nan (probed).
- [x] Gaps declined: the lower bound and None (blocking) semantics of a timeout field (outside this
      rule).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (9 after the first review, 1 after the second).
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
