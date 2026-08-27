# skill-writer checklist - process-test-design (2026-08-27, audit bucket G)

A table cell naming a tool that does not do what the column is about.

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
- [x] The column is "Order / shuffle". nextest documents no shuffle, seed or random-order option,
      and its own configuration docs state the default order is sorted by binary name then test
      name. What it provides is process isolation, a different property.
- [x] Measured locally on cargo 1.95.0: `cargo test -- --shuffle` exists but is nightly-only, and
      on nightly it genuinely reorders. `RUST_TEST_SHUFFLE=1` is silently ignored on both
      channels, which makes it a false-comfort alternative worth naming.
- [x] The other four cells in the column were checked and are correct.

## GREEN
- [x] The cell now gives the nightly-only invocation, states that nextest does not shuffle and what
      it does instead, and names the ignored environment variable.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
