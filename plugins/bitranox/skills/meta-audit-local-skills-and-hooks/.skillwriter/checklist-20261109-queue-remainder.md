# skill-writer checklist - meta-audit-local-skills-and-hooks (2026-11-09, personal half without a root)

Step 1 says to leave --root out for the personal half alone.

Decisions: none - additive rule, no recorded decision is reversed (skill_decisions.py show meta-audit-local-skills-and-hooks run first)

- [x] Step 0b `skill_decisions.py show meta-audit-local-skills-and-hooks --kind rejected,removed` read before the first edit; nothing listed bears on this rule.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): the new rule's phrases are absent.
- [x] Every command or snippet the edit adds was executed. `audit_local.py targets` with no --root exited 0 and selected the personal skills dir; the hooks dir is selected when it exists.
- [x] GREEN, quote-back on haiku with the text pasted and no skill loaded: the question returned the governing sentence; a control question returned NONE.
- [x] Skill gaps from the probe decided: it reported only that the pasted excerpt lacks its surrounding document, which a reader of the whole file has.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: committed on a worktree branch and pushed with CI watched.
