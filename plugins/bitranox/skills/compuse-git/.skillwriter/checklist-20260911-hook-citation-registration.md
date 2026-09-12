# skill-writer checklist - compuse-git (2026-09-11, hook citation names the full registration)

The "Hooks" section cited `repo-gate` as "PreToolUse on Bash". hooks.json registers it on
Bash|PowerShell, and its command check receives the tool name, so it gates a commit issued from
either tool.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a FACTUAL claim about a hook's registration, so the test
      is a check of the skill text against hooks.json, not a pressure scenario.
- [x] Scope: one citation corrected. No procedure, trigger or frontmatter change.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording and cannot fail honestly, and the claim is mechanically
      checkable against the file that decides it.
- [x] `hooks/tests/test_hook_docstring_registrations.py` fails on the old text: "skills/compuse-git/SKILL.md
      cites repo-gate as PreToolUse on Bash; hooks.json also registers ['PowerShell']".
- [x] Direction: a citation NARROWER than the registration is the one that invites a maintainer to
      narrow the registration back to match it, so that is the direction the test forbids.

## GREEN
- [x] The citation reads "PreToolUse on Bash and PowerShell"; the same test passes, and its vacuity
      check still finds skill citations to compare.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
