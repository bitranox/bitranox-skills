# skill-writer checklist - meta-memory-settings (2026-10-26, context_mode)

The knob table gains a `context_mode` row (`compact` default, `handover`), stating what each mode
does at the context limit, that compact mode needs `CLAUDE_CODE_AUTO_COMPACT_WINDOW` set to the
context limit in the `env` block of `~/.claude/settings.json`, what happens when it is unset, and
what the variable does in handover mode. The `context_handover_pct` and `context_handover_cap`
rows now call the threshold the context limit, and the cap row says the variable holds that limit,
which is the cap only when the cap is the smaller leg. `settings.py` validates the new enum.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference; the test is retrieval - which knob and value, and what the default
      needs, answered from the table.
- [x] RED by text check against the pre-change file (the knob did not exist, so no behavioural arm
      could pass on it): `git show HEAD:.../meta-memory-settings/SKILL.md | grep -c context_mode`
      prints 0; the edited file holds the row.
- [x] GREEN by quote-back on the edited file (opus at effort medium, plus haiku): both return the
      `context_mode` row for "offer me a handover and /clear like before", the default's
      `CLAUDE_CODE_AUTO_COMPACT_WINDOW` requirement, and the CLI's general refusal for a bad value.
- [x] Gaps, each decided:
      - the cap row said to keep the variable "equal to it", wrong whenever the percentage leg is
        smaller - CLOSED: "holds the context limit, which is this cap only when the cap is the
        smaller leg"; the same correction in `docs/reference.md`.
      - what happens when the variable is unset - CLOSED: "when it is unset or larger, the save
        request says so and the harness compacts only at its own, much later default".
      - what the variable does in handover mode - CLOSED: "In handover mode the variable only
        moves the harness's own compaction point."
      - a worked example of the limit, the harness's default compaction point, a value smaller than
        the limit, the exact refusal text - DECLINED: the min() rule is stated in the pct row and
        both tiers computed 140000 from it; the compaction point and the request text belong to
        `bitranox:meta-context-watcher`, which states them.
- [x] Re-probe on the final text (opus at effort medium, plus haiku; 5 questions): every answer a
      direct quote or a computation from quoted rows (both tiers: 140000 for a 200k window at 70%),
      no NONE, no disagreement between rows.
- [x] Tiers: GREEN opus + haiku, re-probe opus + haiku - 4 cells.
- [x] Description unchanged - no routing keyword moved. Tables canonical
      (`reformat_tables.py --check --strict`).
- [x] No address, MAC, hostname or machine path added; ASCII only; present tense.
