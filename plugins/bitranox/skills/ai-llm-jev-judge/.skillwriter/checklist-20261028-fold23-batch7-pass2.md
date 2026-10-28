# skill-writer checklist - ai-llm-jev-judge (memory rules folded in, pass 2)

- [x] Change: SKILL.md, Commands - run sends and bills every non-blank line of --items; an extra
      top-level key refuses the whole run (exit 2) before anything is sent; annotations put
      inside state are sent; keep them in a separate file and filter items before run.
- [x] Verified: btx-skill-jev-judge items.py:19-50 (blank lines skipped, extra='forbid' on id and
      state), commands/judge.py:5 (InputError is exit 2) and :233 (load_items runs before
      iter_judged), judge.py:234 (--pilot slice). Mirrored to the twin, released there as
      0.3.6; the five uvx floors and JEV_JUDGE_FLOOR move to 0.3.6 once PyPI serves it.
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
