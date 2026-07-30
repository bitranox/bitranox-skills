# skill-writer checklist - meta-dream-crosstree-deep: judge a CLAUDE.md trim by ancestor reachability (2026-07-30)

Family change: git tracking stops gating a CLAUDE.md trim; the test becomes whether a
covering rule sits at an ANCESTOR and is always-loaded. Applied + reported, not asked.

## PLAN
- [x] Skill type: DISCIPLINE/reference hybrid - a policy the dream must obey. Test approach
      is a decision scenario under the shipped guidance, not a retrieval question.
- [x] Scenario drafted before any edit.
- [x] Scope: pointer / policy edit in this file; the case model lives in dream-passes.md.
- [x] Task list created per phase.

## RED - baseline WITHOUT the change
- [x] Scenario dispatched to a sonnet subagent quoting the CURRENT guard text verbatim
      (dream-passes.md "never trim a TRACKED lower copy into a LESS durable broader home" plus the
      UNTRACKED-source clause). Trap withheld: the scenario never mentioned ancestry or loading.
- [x] Baseline FAILED, verbatim: for the git-tracked file it answered "LEAVE the line in place...
      It is git-tracked (durable). The covering home /work/CLAUDE.md is untracked... The stated
      guard forbids trimming a tracked lower copy into a less durable broader home." For the
      gitignored sibling it deleted the duplicate. Two identical rules, opposite outcomes, decided
      purely on git status - reproducing the 2026-07-30 incident exactly.
- [x] Control: a second scenario (no guard text) confirmed the model ALREADY lifts a rule shared by
      two siblings to their common ancestor and knows the cascade loads it - on sonnet AND on haiku.
      So the gap is not missing knowledge; the shipped text is what produces the wrong outcome.
- [x] Pattern identified: the guard tested DURABILITY (git) where it should test REACHABILITY
      (ancestry + load). Gitignore is irrelevant to loading, so the axis never affected the outcome
      it claimed to protect.

## GREEN - what changed here
- [x] Boundaries block reduced to a POINTER at dream-core.md + dream-passes.md, keeping only this
      skill's own delta: an ORG-CHART proposal is always proposed, never applied.
- [x] The inline "every CLAUDE.md edit is propose-first, never without confirmation" contradicted
      the new applied-and-reported policy; replaced with the reachability + backup + report rule.
- [x] Verified the org-chart / umbrella-repo guidance still reads correctly now that a trim is no
      longer blocked on a tracked home: the umbrella repo remains an offered option, not a gate.


## Quality
- [x] No narrative storytelling; states the rule as it now is.
- [x] Cross-references use skill names with no `@` links; the script/reference homes are named.
- [x] ASCII only, no em-dashes or typographic tells.
- [x] Token budget: net REDUCTION in this file (a restated block became a pointer).

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal paths
      or PII. The change is policy prose only.
- [x] Plugin version bumped in `plugins/bitranox/.claude-plugin/plugin.json` in the same change.
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md, README count).
- [x] `repo-gate.py --ci` green with CI's full dependency set.
- [x] Additive commit to `master`; history stays append-only, no force-push.
