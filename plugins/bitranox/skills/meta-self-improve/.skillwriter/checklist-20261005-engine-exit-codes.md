# skill-writer checklist - meta-self-improve (2026-10-05, memory engine exit codes)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The changed lines state the memory engine's exit codes after the
      plugin-wide 0/1/2 unification, so the RED is a ground-truth check of the old text against the
      code, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft. The artifact checks are immune.
- [x] RED, ground truth: SKILL.md step 4 and the Deliverables box said an over-cap `add` exits 1,
      and `references/memory-backend.md` said a refusal exits 1 and that a missing `--hook`/`--scope`
      is `! refused: pass --X or --X-file`. The engine now exits 2 on every refusal and prints
      `! error:` on stderr for a usage or input-file error
      (`hooks/tests/test_memory_engine.py::test_cli_add_over_hard_cap_refusal_exit_two`,
      `hooks/tests/test_memory_engine_hook_scope_file.py`); `lint --tree` exits 1 on any finding and
      `heal` exits 2 when a level was unreadable (`test_memory_engine_unreadable_store.py`).
- [x] GREEN: a haiku probe given only the changed paragraphs answered seven questions (over-cap
      refusal, unreadable `--hook-file`, `lint --tree` exit 1, `heal` exit 2, which verb can exit 1,
      a refused `move`, an exit 2 with empty stdout) all correctly, each with a direct quote.
- [x] Skill gaps from GREEN decided: (a) "can `set-scope` exit 1" - DECLINED, "1 only from
      `lint --tree`" answers it; (b) codes of the other verbs - DECLINED, "2 whenever the action did
      not happen" covers every verb; (c) permission-denied vs not-found input file - DECLINED, both
      are "an input file it could not read".
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
