# skill-writer checklist - meta-dream-tree (2026-09-25, script behaviour sync)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every changed line in `SKILL.md` and
      `references/dream-core.md` states what `statusrot.py`, `store_manifest.py`, `dedup_scan.py`
      or `dream_state.py` now does, so the RED is a ground-truth check of the old text against the
      code, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft. The artifact checks are immune.
- [x] RED, ground truth: the old text said nothing a reader could act on for five behaviours the
      scripts now have, each pinned by a test in `tests/`: `statusrot clear` refuses an unparseable
      baseline (`test_statusrot.py`); every tool anchors at the engine's store, not the nearest one
      (`test_tree_support.py`, `test_store_manifest.py`); an unreadable level or fact is exit 2
      with the path named (`test_dedup_scan.py`, `test_store_manifest.py`); `store_manifest --out`
      inside the store is refused; `session-review` shows a stretch over 2 MB in parts and the
      write verbs exit 2 when their write did not land (`test_dream_state.py`).
- [x] Import path: the five scripts import their sibling `tree_support` with their own dir put on
      `sys.path` first. `test_a_script_loaded_by_path_from_elsewhere_finds_tree_support` loads each
      one by path in an isolated interpreter from a foreign cwd: 5 of 5 failed with
      `No module named 'tree_support'` against the scripts without the path line, 5 of 5 pass with it.
- [x] GREEN: a haiku probe given only the new text answered seven retrieval questions (unparseable
      baseline, which store is backed up, INCOMPLETE meaning, `--out` inside the store, TRUNCATED
      loop, a success line from a write verb, frontmatter scoring) all correctly. It answered in
      paraphrase rather than quoting; each answer maps to exactly one sentence of the new text.
- [x] Skill gaps from GREEN: none reported.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added; ASCII only.
- [x] Present tense, no session narrative, no private provenance.
