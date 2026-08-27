# skill-writer checklist - compuse-toolbox (2026-08-27, audit bucket G)

The Tools table told readers to launch `gate` the one way this file forbids.

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
- [x] The table's Invocation cell said `uv run scripts/gate.py`, contradicting the prose 46 lines
      below it, which records a measured false RED: `uv run` puts an ephemeral interpreter on the
      environment child gates inherit, and a gate shelling out to `python3 -m pytest` then died
      with `No module named pytest`. The script's PEP 723 block declares no dependencies, so
      `uv run` buys nothing; `python3 scripts/gate.py --help` runs clean.
- [x] Three sites carried it, not the one filed: the table and two lines of the script's own
      `Run:` block.

## GREEN
- [x] All three now say `python3`, the script's block carries the reason inline, and the blanket
      "run it with `uv run`" sentence names `gate` as the exception.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Also corrected in the same file: the redcheck row's exit-code note, which claimed exit 3 for
      an empty corpus without saying it fires only for `--corpus-cascade`.
