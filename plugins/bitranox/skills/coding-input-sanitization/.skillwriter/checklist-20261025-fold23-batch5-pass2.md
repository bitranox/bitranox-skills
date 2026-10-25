# skill-writer checklist - coding-input-sanitization (memory rules folded in)

- [x] Change: Common mistakes (new last bullet) + Quick checklist (new line after the charset line)
      - coding-input-sanitization/SKILL.md. RED on the pre-edit snapshot: NONE. Verified: python3 -I
      probe on CPython 3.14.4: re.compile(r"(\d{4})-(\d{2})-(\d{2})$").match("2026-10-08\n") ->
      True; .fullmatch(same) -> False; re.fullmatch(r"\d", chr(0x0662)) -> True and int(chr(0x0662))
      == 2; with re.ASCII -> False; [0-9] -> False; "chr(0xB2)".isdigit() True, .isdecimal() False;
      int("chr(0xB2)") -> ValueError 'invalid literal for int() with base 10'; int("9"*5000) ->
      ValueError 'Exceeds the limit (4300 digits) ... use sys.set_int_max_str_digits()';
      chr(0x0662).isdecimal() True. httpx probe (uv run --with httpx): httpx.Response(200,
      headers=[("content-length","chr(0xB2)")]) -> UnicodeEncodeError 'ascii' codec can't encode;
      bytes header [(b'x-test', b'\xb2')] builds fine. Edited file checked: no non-ASCII bytes,
      backslash escapes (\n, \d, \xb2) landed literally, new lines <=100 cols.
      ThreadPoolExecutor.map escape kept only as a generic mechanism (an escaping exception from map
      ends the pass), not re-measured.
- [x] Dropped as stale or unverified: Nothing stale (skeptic CONFIRMED all claims). Dropped as
      private/narrative: the a repo script and a private consumer names, measurement dates, speaker
      XML / preset id / utcTime specifics. Replaced the literal superscript character with chr(0xB2)
      to keep the skill ASCII-only, and the session date in the example with 2024-01-31. Did not
      cite the slug.
- [x] Gaps declined: calendar validity of a parsed date (a different rule from the one folded); the
      exact digit bound N for a numeric field (sized to the field, as stated).
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
