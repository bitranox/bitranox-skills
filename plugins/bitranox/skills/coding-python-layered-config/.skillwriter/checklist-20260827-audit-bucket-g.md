# skill-writer checklist - coding-python-layered-config (2026-08-27, audit bucket G)

Six flags presented as CLI-wide; not one of them is accepted by all six subcommands.

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
- [x] Measured against the installed `lib_layered_config` by running `--help` for EVERY
      subcommand and building the real availability matrix. Every rejection reproduced as a live
      `NoSuchOption`. `env-prefix` and `info` accept no options at all beyond `--help`.
- [x] The filed claim named three flags; the real defect covers all six, so a fix scoped to the
      filed claim would have left `--vendor`/`--app`/`--slug` still wrong for two subcommands.

## GREEN
- [x] Prose line replaced with a per-subcommand availability table plus the sentence that the two
      option-free subcommands exist.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Mirrored skill: the twin under `libs/lib_layered_config` carries the identical change and
      its own `plugin.json` is bumped.
