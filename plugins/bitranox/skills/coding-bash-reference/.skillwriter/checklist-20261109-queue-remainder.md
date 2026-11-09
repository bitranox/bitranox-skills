# skill-writer checklist - coding-bash-reference (2026-11-09, bash 3.2 heredoc trap)

A rule that a heredoc inside a command substitution needs balanced quotes for macOS bash 3.2, with a container check.

Decisions: none - additive rule, no recorded decision is reversed (skill_decisions.py show coding-bash-reference run first)

- [x] Step 0b `skill_decisions.py show coding-bash-reference --kind rejected,removed` read before the first edit; nothing listed bears on this rule.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): the new rule's phrases are absent.
- [x] Every command or snippet the edit adds was executed. `docker run --rm -v DIR:/s:ro bash:3.2 bash -n /s/script.sh` ran against a block with an apostrophe (exit 2, the quoted error) and without it (exit 0).
- [x] GREEN, quote-back on haiku with the text pasted and no skill loaded: the question returned the governing sentence; a control question returned NONE.
- [x] Skill gaps from the probe decided: it reported only that the pasted excerpt lacks its surrounding document, which a reader of the whole file has.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: committed on a worktree branch and pushed with CI watched.
