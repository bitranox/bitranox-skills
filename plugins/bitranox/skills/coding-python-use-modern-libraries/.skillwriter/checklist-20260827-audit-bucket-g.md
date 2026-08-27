# skill-writer checklist - coding-python-use-modern-libraries (2026-08-27, audit bucket G)

A kwarg that does not exist on the library the skill recommends.

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
- [x] Executed against installed httpx2: `Client(proxies=...)` and `AsyncClient(proxies=...)` both
      raise `TypeError`. The code sample six lines above already used the correct `proxy=`, so the
      file contradicted itself. `mounts=` verified accepted as the per-scheme replacement.

## GREEN
- [x] Prose now names `proxy=` and `mounts=`, states that `proxies=` does not exist, and quotes the
      exact TypeError a reader following the old text would hit.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
