# skill-writer checklist - compuse-bash (2026-09-11, hook citation names the full registration)

The "Hook" section cited `block-pgrep-self-match` as "PreToolUse on Bash". hooks.json registers it
on Bash|PowerShell, and it passes the tool name to its command splitting, so it reads a command
from either tool.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a FACTUAL claim about a hook's registration, so the test
      is a check of the skill text against hooks.json, not a pressure scenario.
- [x] Scope: one citation corrected. No procedure, trigger or frontmatter change.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording and cannot fail honestly, and the claim is mechanically
      checkable against the file that decides it.
- [x] `hooks/tests/test_hook_docstring_registrations.py` fails on the old text: "skills/compuse-bash/SKILL.md
      cites block-pgrep-self-match as PreToolUse on Bash; hooks.json also registers ['PowerShell']".

## GREEN
- [x] The citation reads "PreToolUse on Bash and PowerShell"; the same test passes.
- [x] The five realigned rows of the patterns table are the markdown formatter's output: every
      cell's content is identical before and after, checked cell by cell with a control that must
      report a changed cell as different.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
