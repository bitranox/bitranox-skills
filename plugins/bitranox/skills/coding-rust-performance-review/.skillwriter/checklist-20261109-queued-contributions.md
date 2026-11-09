# skill-writer checklist - coding-rust-performance-review (2026-11-09, queued contributions)

Entries: C26. The checklist table gains the AtomicU64 row for one shared counter.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show coding-rust-performance-review run first)

- [x] Step 0b `skill_decisions.py show coding-rust-performance-review --kind rejected,removed --full` read before the first edit; rejected description entries read, untouched.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (AtomicU64).
- [x] Every command or snippet the edit adds was executed: no command added; the row is a text review judgement.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
