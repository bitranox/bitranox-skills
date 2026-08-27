# skill-writer checklist - docs-generate-schematics (2026-08-27, audit bucket G)

The wrapper is not a thin single-shot wrapper, and the documented launch cannot work.

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
- [x] `generate_schematic.py` is a launcher: it re-executes the AI script with `sys.executable`
      and does not forward the default iteration count, so the child falls back to its own default
      of 2 and runs the full quality-review loop. The wrapper's own docstring already said so.
- [x] The documented `python3 scripts/generate_schematic.py` cannot run on a clean machine: the
      child hard-exits without `httpx2`. It is masked here only because `python3` resolves to an
      interpreter that happens to have it.

## GREEN
- [x] The comment now describes the real behaviour (same loop, iteration cap clamped to 2) and the
      command uses `uv run --with httpx2`; the stdlib-only note now explains that the child needs
      the dependency just as much.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Also fixed: the image-model reference comment linked a different model slug than the code
      calls. The COMMENT was corrected, not the model, since a comment is not evidence for
      changing which model a script invokes.
