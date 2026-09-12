# skill-writer checklist - compuse-ssh (2026-09-11, hook citations name the full registration)

The "Hook / script" section cited `block-pgrep-self-match` and `warn-inline-powershell` as
"PreToolUse on Bash". hooks.json registers both on Bash|PowerShell, and both read the command of
either tool: warn-inline-powershell fires under tool_name=PowerShell end to end, and
block-pgrep-self-match passes the tool name to its command splitting.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a FACTUAL claim about two hooks' registration, so the
      test is a check of the skill text against hooks.json, not a pressure scenario.
- [x] Scope: two citations corrected. No procedure, trigger or frontmatter change.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording and cannot fail honestly, and the claim is mechanically
      checkable against the file that decides it.
- [x] `hooks/tests/test_hook_docstring_registrations.py` fails on the old text for both citations,
      e.g. "skills/compuse-ssh/SKILL.md cites warn-inline-powershell as PreToolUse on Bash;
      hooks.json also registers ['PowerShell']".
- [x] Direction: prose NARROWER than the registration invites a maintainer to "fix" the
      registration back out, which for warn-inline-powershell would drop the very tool it is about.

## GREEN
- [x] Both citations read "PreToolUse on Bash and PowerShell"; the same test passes, and its
      vacuity check pins that this skill's warn-inline-powershell citation is still found.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
