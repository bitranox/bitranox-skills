# skill-writer checklist - files-edit-toml (2026-11-09, queued contributions)

Entries: C27. SKILL.md and the array table name rebuilding an array as comment loss.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show files-edit-toml run first)

- [x] Step 0b `skill_decisions.py show files-edit-toml --kind rejected,removed --full` read before the first edit; ledger empty.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (Rebuilding an array).
- [x] Every command or snippet the edit adds was executed: tomlkit 0.15.2: rebuilding with tomlkit.array() and assigning a list both dropped every comment, del in place kept them.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
