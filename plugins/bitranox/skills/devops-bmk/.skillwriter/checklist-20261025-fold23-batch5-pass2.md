# skill-writer checklist - devops-bmk (memory rules folded in)

- [x] Change: push/release gotchas list - new bullet directly after the 'On an already-committed
      tree, the push commit's subject...' bullet (which names MSG= as the safe channel) -
      devops-bmk/SKILL.md. RED on the pre-edit snapshot: partial. Verified: bmk 3.27.0 Makefile
      src/bmk/makefile/Makefile:12 'make push MSG="fix(cli): x" # push with ANY message:
      punctuation, newlines, $ - all safe'; :98-99 'export BMK_COMMIT_MESSAGE := $(value MSG)';
      :112-113 $(error ARGS contains a newline ...); :402,408 recipes '$(BMK) commit "$(ARGS)"' /
      '$(BMK) push "$(ARGS)"' (quoted, comment :391-397 'LOAD-BEARING'); :423 '$(BMK) ship $(ARGS)'
      unquoted; :294-295 trailing words appended to ARGS. Precedence args > MSG ->
      git_ops.resolve_message docstring 'args -> BMK_COMMIT_MESSAGE -> prompt (tty) -> chores'.
      Scratch Makefile probe (SHELL=/bin/bash): quoted recipe -> '[fix(deps): bump httpx floor; drop
      legacy pin]', "['chore(release): 1.1.2']" (literal quotes), '[cost is OME and X]' ($ eaten,
      backtick executed), 'say "hi" there' -> '[say hi there]'; unquoted recipe -> 'syntax error
      near unexpected token (' (exit 2), 'bump floor; removed pin' -> prints then 'removed: command
      not found' Error 127. Push-still-commits-truncated-subject on ';' -> fact body's measurement
      (unquoted recipe era), kept as behaviour of an unquoted recipe.
- [x] Dropped as stale or unverified: Hint's remedy 'inner-single-quote the value: make push
      ARGS="'fix(deps): ...'"' DROPPED (contradicted: with the current quoted recipe the quotes land
      in the subject). Skeptic's amended text 'a ; runs the rest as a command ... ( is a syntax
      error' for push is STALE for the current Makefile (push/commit recipes quote ARGS, so ( and ;
      survive); reworded to apply only where the recipe is unquoted (ship always, or a repo's own
      older-style push recipe, found by grep). Body's remedy 'git commit -F <file> plus git push'
      superseded by MSG=. Body's unrelated bmk gotchas (pip-audit .venv, Makefile/floor churn) not
      carried - covered elsewhere in devops-bmk. Private repo names, commit sha and German bash
      error text dropped.
- [x] GREEN gap fixed: the MSG bullet separates the quoted recipe (push, commit) from the unquoted
      one (ship, and any older Makefile), with one remedy; verified against
      src/bmk/makefile/Makefile (lines 402-425 and the MSG block). A Makefile without the MSG block
      (no BMK_COMMIT_MESSAGE) ignores MSG, so the bullet tells the reader to refresh it with uvx bmk
      install first.
- [x] Measured against the fact body: bmk wraps ARGS in double quotes in the push and commit
      recipes, so the body's ";" and "(" breakage applies only to the unquoted case.
- [x] Gaps declined: how a refreshed Makefile is committed (bmk churn rides along with git add -A,
      stated in section 3); the timestamped push subject and amending a pushed subject (outside this
      rule); env prefix versus make variable for MSG (make imports the environment, so ifdef MSG
      sees both).
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
