# skill-writer checklist - infra-proxmox-bindsnap (2026-08-27, audit bucket G)

The frontmatter attributed the clone error to the snapshot path.

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
- [x] The body attributes `unable to clone mountpoint 'mpN' (type bind)` to the CLONE path at
      three sites and gives the snapshot row a different cause. The tool's own README and design
      doc agree: the snapshot path fails a `has_feature('snapshot')` gate, and the mountpoint
      string belongs solely to clone.

## GREEN
- [x] Clause rewritten so the snapshot and clone symptoms are named separately. Description
      measured: 512 characters, well under the 1024 cap.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Mirrored skill: the two descriptions were byte-identical, and the twin under
      `apps/pve-bindsnap` carries the identical change with its own `plugin.json` bumped.
