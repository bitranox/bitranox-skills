# skill-writer checklist - meta-self-improve (2026-10-20, fold23 batch 3)

- [x] Change: references/upstream-propagation.md - new paragraph "Before writing a queued
      documentation contribution, check it is not already shipped elsewhere" (search every shipped
      skill and the local layer, read the matching lines, try every spelling, drop with
      `--reason "already in <skill>/<file>"`, and when the owning sibling is not loaded where the
      reader needs it add a one-line pointer in the skill that is, never a second copy).
- [x] Change: references/memory-backend.md - `heal` re-renders pointer blocks from the pointer
      LINES and never opens a body; a body's `description:` never updates its hook; change a hook
      through the engine at the owning level or `factedit.py apply --hook-file`; heal drops a
      pointer whose slug is not a plain filename and reports it under `invalid_pointers`. Ground
      truth: `hooks/memory_engine.py:236-241` (`_warn_dropped_invalid_pointers`), `:1125`
      (`'invalid_pointers'` in the heal result); `skills/meta-dream-tree/factedit.py:44-45`
      (`apply ... --hook-file`).
- [x] Receipt held; SKILL.md itself is unchanged (references only), checklist kept as the record.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): already-shipped check -
      NONE; heal round-trip - partial (heal is chain-scoped and reports missing bodies; nothing on
      hooks vs bodies). Behavioural RED replaced on purpose: the rules are in the always-loaded
      memory index of the authoring machine.
- [x] GREEN quote-back on haiku and opus, quotes substring-checked: upstream-propagation.md:48
      "Before writing a queued documentation contribution, check it is not already shipped
      elsewhere." and memory-backend.md:272 "`heal` re-renders each level's pointer block from the
      parsed pointer LINES alone and never opens a fact body".
- [x] GREEN diffed against RED both ways: the RED partial quote is still present; nothing lost.
- [x] Gaps closed or declined: closed - a sibling that carries the rule but is not loaded where it
      is needed (one-line pointer, re-tested by quote-back on haiku and opus, both quoted it);
      declined - concrete prose search terms per rule (rule-specific by nature).
- [x] Description measured: unchanged
- [x] Security scan: prose only; `~/.claude/skills/` and `~/.claude/commands/` are generic Claude
      Code paths, no private specifics
