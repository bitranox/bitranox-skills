# skill-writer checklist - compuse-git: ship queued cross-project contributions (2026-07-30)

Batch: contributions queued by earlier dreams, delivered as one change via the upstream loop.

## PLAN
- [x] Skill type: REFERENCE row/section (a concrete mechanic), so the test is an application
      scenario, not a discipline pressure scenario.
- [x] Scenario drafted before the edit; trap WITHHELD (the symptom given, never the mechanism).
- [x] Scope: additive edit to the existing SKILL.md, no new supporting file.

## RED - baseline WITHOUT the change
- [x] Baseline dispatched with the skill content NOT supplied.
- [x] VERDICT: FAILED on haiku for the cwd/ref half; PASSED both tiers for rerere
- [x] Evidence, verbatim where quoted: asked to compare `release` to `origin/release` across 18 repos in a shell with a persisting cwd,
      haiku wrote `for repo in ...; do cd "$repo" && git diff release...origin/release` - the `cd`
      hazard itself, a three-dot range that does not compare tips, and `2>/dev/null` masking a missing
      branch rather than detecting it. The rerere row PASSED on both tiers (both refused to trust a
      green build); it ships as reference detail, not on a failing baseline.
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
