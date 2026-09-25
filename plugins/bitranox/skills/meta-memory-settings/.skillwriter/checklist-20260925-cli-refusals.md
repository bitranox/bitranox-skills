# skill-writer checklist - meta-memory-settings (2026-09-25, CLI refusals and exit codes)

The "Use the CLI" section gains four bullets stating what `settings.py` refuses and what its exit
codes mean: integer knob bounds and rooted `discovery_roots` entries, exact argument counts per
verb, a config that is not a JSON object (refused with exit 2, left untouched), and exit 1 for a
failed write. The knob table and the description are unchanged.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario of five questions: is
      `set context_handover_pct 0` stored, what does `set` do to a config with a trailing comma,
      what exit 1 means, whether a relative `discovery_roots` entry is accepted, and what
      `reset --dry-run` does.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the section pasted and Skill invocation forbidden, so neither arm could answer from
      the installed copy.
- [x] RED (pre-change section): NONE on all five questions.
- [x] GREEN (new section): all five answered with a direct quote - refused with exit 2, refused
      with exit 2 and left untouched, "the write failed ... nothing was saved", not accepted,
      refused with exit 2.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed all five as silent. GREEN listed
      three, each declined: the order of the checks (no reader action depends on it - every
      refusal is exit 2 and writes nothing); which keys exist and whether `dream_mode` is one (the
      probe was given an excerpt; the full SKILL.md carries the complete knob table and the
      unknown-key refusal). Nothing RED produced is missing from GREEN.
- [x] The statement matches the code: `settings.INT_BOUNDS` and `_INT_SPECIAL` (bounds),
      `settings._coerce_list` (rooted `discovery_roots`), `settings._ARGC` (argument counts),
      `settings._config_problem` (non-object config refused by every verb before any write),
      `settings._save_and_print` (exit 1 on a failed `save_config(..., strict=True)`); each is
      pinned by a test in `tests/test_settings.py`.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
