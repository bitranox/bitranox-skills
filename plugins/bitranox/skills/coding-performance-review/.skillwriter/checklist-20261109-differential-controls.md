# skill-writer checklist - coding-performance-review (2026-11-09, differential controls)

Step 10 gains two paragraphs (tabulate refusals per input kind, a control that really ran). New
step 11 re-measures a candidate on the adopted tree; the claim check becomes step 12.

Decisions: none - additive rules, no recorded decision is reversed (rejected entries are about the description, which is unchanged)

- [x] Step 0b `skill_decisions.py show coding-performance-review --kind rejected,removed --full` read before the first edit; three rejected description entries, none touched.
- [x] RED, text check against the pre-edit file and every skill's Markdown: no wording for refusals tabulated per exception type, a planted copy of the tree, an equivalent mutant, or re-measuring on the adopted tree.
- [x] Scope check against step 10: it asks for random valid AND malformed inputs, so a malformed kind refused 100 percent by the code's own error is correct. The rule is limited to a valid kind refused 100 percent or any kind refused only by a type the code does not raise for it.
- [x] Step numbers: a repo-wide grep found no reference to this skill's step 11; the renumbered claim check is cited nowhere else in shipped text.
- [x] GREEN: no subagent probe ran on this change; the evidence is the text check of the final file (each new rule phrase present once, ASCII only). Routing is unchanged since the description is unchanged.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, fence balance unchanged.
- [x] Deployment: committed with one version bump, pushed with CI watched.
