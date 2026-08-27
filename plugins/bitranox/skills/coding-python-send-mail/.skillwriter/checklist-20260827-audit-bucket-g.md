# skill-writer checklist - coding-python-send-mail (2026-08-27, audit bucket G)

Two claims about the installed library that do not hold.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] The dangerous-extension default is OS-SELECTED (`_default_blocked_extensions` branches on
      `sys.platform`). The POSIX and Windows sets share 4 of 58 entries. The real validator was
      executed with the resolved defaults, no SMTP contact: on Linux `.exe`, `.bat`, `.ps1`,
      `.dll`, `.msi`, `.scr` and `.vbs` are all ACCEPTED. The sentence's two examples sat one in
      each disjoint half, so on any single platform one of them was false.
- [x] `cli.py` declares no `envvar=` at all; the 15 variables are resolved by hand and cover 15 of
      19 `send` options. `--subject` and `--body` are REQUIRED and have none. Reproduced: setting
      them via environment gives `Error: Missing option '--subject'`, rc 2. A control arm proved
      the mechanism works for `--host`/`--recipient`/`--sender` (the run reached SMTP and failed
      on a refused connection), so the check could answer either way.

## GREEN
- [x] Both passages rewritten to state the OS selection and the content-option gap, and to give
      the union expression that blocks both families on every platform.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Mirrored skill: the twin under `libs/btx_lib_mail` carries the identical change and its own
      `plugin.json` is bumped.
