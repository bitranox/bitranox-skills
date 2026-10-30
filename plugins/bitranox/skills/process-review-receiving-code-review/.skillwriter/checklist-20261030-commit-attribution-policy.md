# skill-writer checklist - process-review-receiving-code-review (2026-10-30, commit attribution policy)

- [x] Change: the "When YOU write a fix brief for someone else" sentence now adds, for an agent
      that may commit, the repo's commit-attribution policy, and a check of its commit messages
      against that policy before merging them, pointing at
      bitranox:process-agents-subagent-driven-development, File Handoffs. The rule is neutral: the
      skill names no policy of its own. The rest of the sentence is unchanged; the line after it
      was re-wrapped to the file's width, words unchanged.
- [x] Receipt held (`skill_receipt.py check meta-skill-writer`: fresh), skill loaded by the editing
      agent through the Skill tool.
- [x] Text check on the pre-edit file (`git show HEAD:`): `grep -ciE
      'attribution|co-authored|generated with'` printed 0.
- [x] RED (pre-edit excerpt of the fix-brief sentence; one combined probe over four skills, haiku,
      scenario: CONTRIBUTING requires `Tool-Assisted: yes` and forbids tool Co-Authored-By lines,
      every subagent's harness reminder adds `Co-Authored-By: Example Bot`): Q1 (what the brief
      says about the policy) NONE; Q2 (what is checked about commit messages before merge) NONE.
- [x] GREEN (post-edit excerpt plus the SDD File Handoffs bullets it points at, declared the text
      under test), haiku and opus (effort medium): Q1 both quoted "(for an agent that may commit,
      also the repo's commit-attribution policy, ...)"; Q2 both quoted "check its commit messages
      against that policy before you merge them" and applied the SDD forbid and require commands.
      Every quote checked against the pasted text.
- [x] GREEN vs RED both ways: RED produced only NONE; nothing is lost.
- [x] Gaps declined: the policy text itself lives in the SDD section the sentence points at (a
      pointer, as the change specified, not a copy); reword mechanics (owned by
      bitranox:compuse-git).
- [x] Tiers and cells: RED 1 (haiku) x 2 questions; GREEN 2 (haiku, opus) x 2 questions.
- [x] Added lines: no history-finder hit, no address or home path, ASCII only; description
      unchanged.
- [x] Tests: this skill ships no scripts; the hooks suite and the touched skills' tests ran green
      (counts in the report).
