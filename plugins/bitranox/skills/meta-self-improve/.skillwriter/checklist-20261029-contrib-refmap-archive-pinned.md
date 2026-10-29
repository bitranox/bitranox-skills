# skill-writer checklist - meta-self-improve (ref_map prose and --moves, archive refusal, pinned apply)

- [x] Change (code, TDD in tests/test_ref_map_prose_and_moves.py and
      tests/test_reconcile_archive_inbound.py): `ref_map.py` reports plain-prose mentions as their
      own class and judges a JSONL plan with `--moves`; `reconcile_memory_index.py --archive` of
      the last pointer refuses (exit 1) while a fact links or names the slug or a level CLAUDE.md
      names it, `--force` overrides.
- [x] RED (text): `git show HEAD:<file> | grep -c` gave 0 for "allow-pinned", "--moves",
      "prose** list" in SKILL.md; HEAD SKILL.md said "`factedit.py apply` switches to it on its
      own for a pinned fact", now false.
- [x] GREEN (quote-back): SKILL.md "`factedit.py apply` refuses a pinned fact unless given
      `--allow-pinned`"; "A **prose** list names facts that mention the slug in plain text";
      "`ref_map.py --root <anchor> --moves <file> [--json]`. Exit 1 lists each conflict by kind";
      references/memory-backend.md archive row "the LAST pointer refuses, exit 1, ... `--force`
      archives anyway" (table reformatted with reformat_tables.py, one-line diff).
- [x] Conflict kinds and exit codes quoted from ref_map.judge_moves / _main_moves, not recalled.
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
