# skill-writer checklist - meta-claude-hooks (memory rules folded in, pass 2)

- [x] Change: references/authoring.md - split a shell command by the TOOL that runs it, never the
      host OS (unknown tool: escape nothing; test matrix per shell tool; as_posix fixtures);
      probe a guard whose shipped copy is live (quoted heredoc, chr() metacharacters, event on
      stdin, a hook given no stdin fails open in an agent shell); a nested quantifier over
      alternatives backtracks exponentially on NON-matching input (measured, token walk fix).
- [x] Verified: hooks/shell_text.py:1016-1043 (split_for_tool), :1539 (strip_heredoc_bodies),
      shell-prefix-selfref-guard.py:185-196 and :221-223 (EOF on stdin returns 0); regex
      timings re-measured with CPython re (0.34 ms at 10 options to 1.7 s at 22).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of each skill (21 rows).
      The rules under test are recorded in this machine's memory store, so a behavioural arm
      would be contaminated; only a verbatim quote from the snapshot counts. RED: 2 NONE, 6
      PARTIAL, 13 quoted in full (among them the 8 rows already pointing at their skill).
- [x] GREEN quote-back on haiku and opus against the edited files: round 1 21/21 on both tiers;
      round 2 after the fixes, opus 21/21 and haiku 19/21 (its two NONE were search misses,
      the text is present at authoring.md:161 and dream-passes.md:129-137). Every quote was
      substring-checked against the files, misses resolved by grep.
- [x] Independent opus review of the full diff against the code and the fact bodies: fixed a false
      no-stdin claim, an overstated regex stall, the tablekit padding gap, the leak repair
      list, a subdirectory failure in the hash-object recipe, a narrowed search step, the bare
      listing names, the jev wording and exit code, and slug citations in code comments. A
      delta review of the fixes found the recipe's --cacheinfo still root-relative (fixed
      with a cd to the toplevel) and four wrap or wording problems (fixed).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), every
      fence closes, added prose wrapped to the surrounding file's width, no code span split.
- [x] Security scan: prose only; no secrets, hostnames, private paths, memory slugs or PII.
