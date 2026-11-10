# skill-writer checklist - meta-memory-settings (dream_mode row: the tree-top re-home)

Covers SKILL.md, the `dream_mode` row of the knobs table. docs/reference.md's `dream_mode` row
carries the same addition.

- [x] Change: the row now says what each mode does with a misplacement re-home to the tree top:
      propose proposes it with its cost (the bytes it adds to the top block) and does not apply it,
      auto applies it and prints its cost, a manual run under off proposes it as propose does. The
      text mirrors meta-dream-tree's references/dream-core.md Mode, the single source of the rule.
      docs/reference.md's row gets the same, and its stale propose and off wording ("asks before
      touching version-controlled files", "capture-only memory") is aligned with dream-core Mode
      and with this row, since both probe arms reported the two rows contradicting each other.
- [x] Step 0b: `show --kind rejected,removed --full` printed one removed entry
      (d-20261108-b2bb87de, context_mode, unrelated); no rule anchors exist for this skill.
- [x] Both tables re-run through docs-md-table-formatting's reformat_tables.py ("Unchanged": the
      existing padding absorbed the longer cells; every row of each table has one width).
- [x] RED (opus, HEAD rows pasted): from the settings row alone, propose / auto / off handling of
      a misplacement re-home to the tree top NONE, NONE, NONE; the same from docs/reference.md's
      row; gap "A user choosing a mode from either table can't learn that rule".
- [x] GREEN (opus and haiku, edited rows): propose "proposed with its cost ... and not applied",
      auto "apply that re-home, printing its cost", off "a manual run proposes that re-home with
      its cost" quoted from each row. Re-probe on the final docs/reference.md row (opus and haiku):
      propose applies CLAUDE.md consolidation, the re-home handled per mode as above.
- [x] Declined gap: neither row gives the cost formula (UTF-8 length of the pointer line plus the
      newline); a user choosing a mode needs the effect, and dream-core Mode, which every dream
      report points at, carries the formula.
- [x] Decisions: none - the row states the rule recorded in meta-dream-tree's ledger
      (d-20261110-442234ef); this skill makes no decision of its own.
