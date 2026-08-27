# skill-writer checklist - infra-swap-tuning (2026-08-27, audit bucket G)

A guard that compares bytes against megabytes and therefore always fires.

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
- [x] Read live: `/sys/block/zram0/disksize` is 8589934592 bytes = 8192 MiB, cross-checked against
      the 512-byte sector count. `zram-generator.conf(5)` defines `zram-size` in megabytes and the
      skill's own config comment says `# MB`. The two differ by a factor of 1048576, so the
      comparison is never equal and the guard does the unconditional swapoff/reset that the bullet
      three lines above it warns produces a node with no zram at all.

## GREEN
- [x] The bullet now converts before comparing, with a worked snippet that reads the wanted value
      from the config rather than hardcoding it, and notes that `zram-size` accepts expressions
      which must be resolved to a number first.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
