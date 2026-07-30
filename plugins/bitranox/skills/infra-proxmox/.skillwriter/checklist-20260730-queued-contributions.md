# skill-writer checklist - infra-proxmox: ship queued cross-project contributions (2026-07-30)

Batch: contributions queued by earlier dreams, delivered as one change via the upstream loop.

## PLAN
- [x] Skill type: REFERENCE row/section (a concrete mechanic), so the test is an application
      scenario, not a discipline pressure scenario.
- [x] Scenario drafted before the edit; trap WITHHELD (the symptom given, never the mechanism).
- [x] Scope: additive edit to the existing SKILL.md, no new supporting file.

## RED - baseline WITHOUT the change
- [x] Baseline dispatched with the skill content NOT supplied.
- [x] VERDICT: PASSED on sonnet; not re-run on haiku
- [x] Evidence, verbatim where quoted: sonnet named cpuunits vs cpulimit correctly and established the PSI field names by querying a live
      node. Shipped on the maintainer's instruction; the concrete field spelling (`pressurememory`, not
      `pressuremem*`) and the boot-vCPU multi-queue note are reference detail worth pinning regardless.
- [x] Re-run on a weak literal model (haiku) where sonnet passed, per the rule that a capable model
      can route around a gap. Recorded above per row - not every row has a failing baseline, and the
      ones that do not are marked as such rather than presented as tested.

## GREEN
- [x] Text addresses the observed failure (or, where the baseline passed, states the mechanic
      concretely enough to be actionable without it).
- [x] No content added beyond the queued item and what the baseline exposed.
- [x] Placed where retrieval lands: the quick-reference table, or the section already covering
      the neighbouring rule.
- [x] Frontmatter untouched; description still trigger-first.
- [x] No `@` links; any script or doc reference names its home.
- [x] ASCII only, no em-dashes or typographic tells.

## REFACTOR
- [x] Re-read for the loophole the baseline actually took, and closed that specific detour rather
      than only asserting the correct answer.
- [x] Checked against CURRENT skill content first; anything already shipped was dropped, not re-added.

## Quality
- [x] No narrative storytelling; states present behaviour.
- [x] Token budget: additive rows/short section in an existing reference skill.
- [x] No new external doc reference, so nothing new to make install-reachable.

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal paths
      or PII. Tool flags, API field names and language mechanics only.
- [x] Plugin version bumped in the same change.
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md, README count).
- [x] `repo-gate.py --ci` green with CI's full dependency set.
- [x] Additive commit to `master`; history append-only, no force-push.
