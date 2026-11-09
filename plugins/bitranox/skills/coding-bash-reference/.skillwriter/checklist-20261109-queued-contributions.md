# skill-writer checklist - coding-bash-reference (2026-11-09, queued contributions)

Entries: C1, C2. Process Substitution states when the substitution expands; a new pitfall covers find -name .* -prune from the start point.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show coding-bash-reference run first)

- [x] Step 0b `skill_decisions.py show coding-bash-reference --kind rejected,removed --full` read before the first edit; ledger empty.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (the loop STARTS, prunes the starting point).
- [x] Every command or snippet the edit adds was executed: find from '.' printed nothing rc 0, correct with -mindepth 1 and '.?*'; a process substitution reading an array saw count 0 inside the loop.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
