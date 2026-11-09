# skill-writer checklist - coding-performance-review (2026-11-09, queued contributions)

Entries: C6, C17, C21. Repeated pure work covers mutable I/O, the method gains a differential run for rewrites (item 10) and user CPU on a loaded host.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show coding-performance-review run first)

- [x] Step 0b `skill_decisions.py show coding-performance-review --kind rejected,removed --full` read before the first edit; three rejected description entries and the rule entries read; none touched, description unchanged.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (differential run, user CPU, mutable I/O).
- [x] Every command or snippet the edit adds was executed: /usr/bin/time -f %U prints a user-CPU figure on the probe host; the differential and cache-key rules are method statements from a measured review, not re-run.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
