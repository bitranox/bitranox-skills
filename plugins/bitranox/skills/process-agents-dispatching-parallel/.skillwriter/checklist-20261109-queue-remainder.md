# skill-writer checklist - process-agents-dispatching-parallel (2026-11-09, duplicate defects across batches)

Integration: a conflict can mean one defect queued twice under different targets, and what to keep.

Decisions: none - additive rule, no recorded decision is reversed (skill_decisions.py show process-agents-dispatching-parallel run first)

- [x] Step 0b `skill_decisions.py show process-agents-dispatching-parallel --kind rejected,removed` read before the first edit; nothing listed bears on this rule.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): the new rule's phrases are absent.
- [x] Every command or snippet the edit adds was executed. No command added.
- [x] GREEN, quote-back on haiku with the text pasted and no skill loaded: the question returned the governing sentence; a control question returned NONE.
- [x] Skill gaps from the probe decided: it reported only that the pasted excerpt lacks its surrounding document, which a reader of the whole file has.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: committed on a worktree branch and pushed with CI watched.
