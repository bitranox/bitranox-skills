# skill-writer checklist - infra-modulejail (new skill, 2026-08-10)

New guidance/reference skill: safely blocking every kernel module a host does not need,
without bricking a host you may not be able to reach.

## PLAN
- [x] Skill type: technique/reference (a safety-critical procedure) - test is an application
      scenario, not a discipline pressure scenario.
- [x] Scenario drafted before writing: harden a Proxmox host that then relocates to a site
      with no console and no out-of-band power, SSH-only afterward.
- [x] Scope: self-contained SKILL.md, no bundled script - matches every existing infra/net
      skill (none ship a script); the reference implementation stays in the operator's own
      deploy repos, one source of truth.

## RED - baseline WITHOUT the skill
- [x] Baseline dispatched with the skill NOT supplied, on two tiers (a capable model and a
      weak literal model).
- [x] VERDICT: the weak-literal baseline FAILED - it baked the block into the initramfs
      (early-boot brick risk before SSH on a console-less host), hand-picked a short blocklist
      instead of allowlisting and blocking the complement, skipped dependency-closure
      expansion, and had no invariant gate.
- [x] The capable-model baseline reasoned to most of the safe procedure but still chose the
      initramfs approach - recorded as a contaminated/strong baseline, not a clean pass.

## GREEN
- [x] Text addresses each failure: allowlist-then-block-complement; runtime-only, explicitly
      not the initramfs, with the reason; dependency-closure expansion; the invariant gate
      plus a known-negative control; the reboot-while-recoverable gate; the boot-critical
      hard-exempt tier.
- [x] Re-tested WITH the skill on the weak-literal tier that failed baseline: it now produces
      the safe procedure (runtime-only "not baked into initramfs for safety", closure, gate
      validated by planting a required module, reboot gate). Every baseline failure flipped.
- [x] Frontmatter trigger-first; description states triggers, does not summarize workflow.
- [x] No @ links; the one cross-reference names a skill.
- [x] ASCII only, no em-dashes or typographic tells.

## REFACTOR
- [x] GREEN gaps triaged. Genuine gap closed: the runtime file's immediate effect is now
      explicit (it blocks the next load at once; the reboot only proves the host still boots).
- [x] Gaps declined with reason: the closure resolver, the `install ... /bin/true` line, and
      the `modprobe -n -v` verification were reported "silent" only because the GREEN prompt
      carried an abridged copy; the shipped SKILL.md contains all three (confirmed by reading
      it back). `/bin/true` vs `/bin/false` is a stated reader choice, not a gap.
- [x] GREEN diffed against RED both directions; no valuable baseline result lost (the
      per-kernel regeneration note covers the kernel-change case the capable baseline raised).
- [x] Fixes verified by quote-back against the shipped text.

## Quality
- [x] Present tense; no session narrative or private provenance.
- [x] Every value is reserved-documentation or generic - no real host/IP/MAC/path. Verified.
- [x] Common-mistakes table and a differential-verification section.
- [x] Token budget: reference skill; body kept a lean procedure.
- [x] No new external doc reference to make install-reachable.

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal
      paths, or PII - tool names, module names, and file paths under /etc only.
- [x] Category prefix `infra-` is a registry key; name is descriptive.
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md) and README count
      bumped.
- [x] Plugin version bumped (MINOR) in the same change.
- [x] repo-gate.py --ci green with CI's dependency set.
- [x] Additive commit to master; history append-only, no force-push.
