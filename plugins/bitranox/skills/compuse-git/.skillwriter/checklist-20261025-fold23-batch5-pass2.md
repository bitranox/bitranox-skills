# skill-writer checklist - compuse-git (memory rules folded in)

- [x] Change: Quick reference table 'Line endings' row (pointer appended, column width preserved) +
      new section '## Line-ending churn after a Windows save' after '## Exec bit + fileMode' -
      compuse-git/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Scratch-repo probe (git
      2.53.0, core.autocrlf=false, pure-churn f.sh and a real one-line edit g.py, both re-saved
      CRLF): numstat '3 3 f.sh' and '2 2 g.py' (equal N/N for BOTH, so N/N is not proof); ls-files
      --eol 'i/lf w/crlf' for both (names the ending, not a content change); CR-stripped diff on
      f.sh EMPTY, on g.py printed only '< y / > Y'; 'git checkout -- f.sh' -> 'i/lf w/lf'. Committed
      CRLF h.sh shows 'i/crlf w/crlf'; after .gitattributes ('*.sh text eol=lf', '* text=auto') +
      'git add --renormalize .' status shows 'M h.sh' and index 'i/lf ... attr/text=auto eol=lf'.
      Clone with -c core.autocrlf=true: 'c/f.sh:0', 'c/h.sh:0', 'c/g.py:2' -> eol=lf files stay LF,
      a file matched only by '* text=auto' gets CRLF, which is why the clone check catches unpinned
      files. Table stays canonical: reformat_tables.py --check -> 'Unchanged: compuse-git/SKILL.md'.
      Row line length unchanged (cell width 1188, new content 371).
- [x] Dropped as stale or unverified: Nothing contradicted. Reconciled the body's blanket '*
      text=auto eol=lf' recommendation with the skill's existing per-type 'eol=lf' + '* text=auto'
      row: kept the row's pattern as the default, offered the catch-all only with the .bat/.cmd
      exception (and the eol=crlf lines for them). Dropped the body's repo-specific 'no .bat/.cmd
      here' remark.
- [x] GREEN gap fixed: churn already committed (i/crlf, pushed by someone else) is compared against
      the last commit before the churn, not HEAD, and fixed by the renormalize commit, not a
      checkout.
- [x] Gaps declined: rewriting shared-branch history to drop CRLF-only commits (a team decision, not
      a line-ending rule).
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
