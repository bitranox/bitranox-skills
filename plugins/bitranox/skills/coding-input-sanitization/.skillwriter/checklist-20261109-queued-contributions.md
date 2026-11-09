# skill-writer checklist - coding-input-sanitization (2026-11-09, queued contributions)

Entries: C3, C4, C5. Sink table gains a device command stream row, IN gains the ASCII shortcut and strict CSV, Common mistakes gains redact before cutting.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show coding-input-sanitization run first)

- [x] Step 0b `skill_decisions.py show coding-input-sanitization --kind rejected,removed --full` read before the first edit; ledger empty.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (value.isascii(), strict=True, Device command stream, WHOLE text).
- [x] Every command or snippet the edit adds was executed: csv.reader without strict merged rows rc 0, strict raised csv.Error; the shortcut matched the walk on all 128 ASCII chars; a window cut past BEGIN left key material a delimiter pattern missed.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
