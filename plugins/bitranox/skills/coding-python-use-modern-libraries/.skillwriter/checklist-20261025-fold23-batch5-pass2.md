# skill-writer checklist - coding-python-use-modern-libraries (memory rules folded in)

- [x] Change: ## Notes (new bullet directly after the 'Logging and CLI framework' bullet) -
      coding-python-use-modern-libraries/SKILL.md. RED on the pre-edit snapshot: NONE. Verified:
      readable default True -> inspect.signature(click.Path.__init__) on click 8.5.0: 'writable:
      bool = False, readable: bool = True'. Check runs only on an existing target and uses os.access
      R_OK -> inspect.getsource(click.Path.convert): 'if not self.exists:' ... 'if self.readable and
      not os.access(rv, os.R_OK):' ... '{name} {filename!r} is not readable.'. Exit 2 + message and
      the fix -> scratch probe (CliRunner, existing target chmod 0o200, uid 1000): 'readable=True:
      exit=2 ... Error: Invalid value for '-o' / '--output': File ' is not readable.' /
      'readable=False: exit=0 output='wrote''. macOS /dev/stdout behaviour: NOT re-checkable here
      (Linux only); kept as observed behaviour ('observed in macOS CI'), undated. Root bypass and
      Windows chmod limitation: standard POSIX DAC / Python os.chmod docs (Windows sets only the
      read-only flag), not re-probed.
- [x] Dropped as stale or unverified: Private repo name, its test names, the exit-78 second-cause
      story and the dated measurement (leak_note). '/dev/fd/1' wording replaced by '/dev/stdout'
      (what the user types). Nothing CONTRADICTED by the skeptic.
- [x] Change: ## Notes, existing PEP 758 bullet (one parenthetical added, paragraph reflowed) -
      coding-python-use-modern-libraries/SKILL.md. RED on the pre-edit snapshot: partial. Verified:
      ALREADY claim checked claim by claim against the skill: valid on 3.14+ and catches both ->
      present; SyntaxError on <=3.13 under the Py2 grammar -> present; check
      requires-python/interpreter -> present; probe with python -c -> present; parens are style only
      -> present. Only missing part: the except* form. Probe on 3.14.8: 'except* KeyError,
      ValueError:' caught ValueError ('except* caught') and 'except KeyError, ValueError:' caught it
      ('except caught'); on 3.13 compile -> 'SyntaxError: multiple exception types must be
      parenthesized'.
- [x] Dropped as stale or unverified: Nothing; the body's anecdote (orjson handler in a specific
      project) is not carried.
- [x] Change: ## Notes, existing subprocess-exception bullet (one sentence appended) -
      coding-python-use-modern-libraries/SKILL.md. RED on the pre-edit snapshot: partial. Verified:
      ALREADY claim checked against the skill: never branch on exception type -> present; missing
      cwd FileNotFoundError on POSIX vs OSError [WinError 267] on Windows -> present; 127/126
      mapping diverges and POSIX stays green -> present; pre-check Path(cwd).exists()/.is_dir() and
      decide explicitly -> present; run the missing-path test on Windows -> present. Missing part:
      the skill offered exists() and is_dir() as interchangeable, but they classify a file-as-cwd
      differently. Probe on 3.14.8 Linux: subprocess.run(['true'], cwd='/nonexistent-dir-xyz') ->
      FileNotFoundError errno 2; cwd=<existing regular file> -> NotADirectoryError errno 20. The
      body records the same split (file cwd -> NotADirectoryError -> 126).
- [x] Dropped as stale or unverified: Repo file path, test name and commit sha from the body
      (leak_note); the cross-reference to another memory slug.
- [x] Review B fixed: the click.Path error text is Path '...' is not readable. (File '...' only with
      dir_okay=False), probed on click 8.5.0; the bullet is scoped to projects that use click,
      matching the note that the CLI framework is a project choice.
- [x] Gaps declined: dir_okay and allow_dash for -o - (not part of this rule); a Windows-side test
      (chmod cannot make a file write-only there, as stated); the missing-executable case in the
      subprocess bullet (a different condition from a missing cwd).
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
