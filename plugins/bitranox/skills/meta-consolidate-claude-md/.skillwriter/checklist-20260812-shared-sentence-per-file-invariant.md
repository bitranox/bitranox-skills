# skill-writer checklist - meta-consolidate-claude-md: shared-pointer-sentence row + per-file invariant (2026-08-12)

Family change: two additions to one skill. (1) a new variance-table row for the case where copies
share only a closing pointer sentence and the body is unique per copy - verdict LEAVE IT. (2) the
Lift section now states the reachability invariant is judged per FILE, not per GROUP, because a
group's members can straddle the covering ancestor's subtree.

## PLAN
- [x] Skill type: technique/discipline addition to an existing skill, not a new skill.
- [x] Scope: two edits inside SKILL.md - the variance table (section 1) and the "guards" list
      (section 4). No other section touched.
- [x] Re-verified before editing that neither case was already covered: claim_check.py against the
      shipped text, pattern absent, control present (file genuinely read), for both additions.
- [x] Scenario drafted before any edit; de-telegraphed (a fictional "Requesting code review"
      section across 9 CLAUDE.md files, not the real 27-file Make-targets case that motivated this).

## Origin: observed failure, not theory
- [x] Measured 2026-08-12 consolidating a real tree: the skill's own signal ("largest variant
      covers 60-75% means one dominant version") pointed at lifting a "Make targets specific to
      this repo" section appearing in 27 files across 8 variants. Reading a body showed all 27 were
      already the prescribed minimal delta plus one shared pointer line - correct as-is; lifting
      would have merged unrelated per-repo content under one heading.
- [x] Same pass: 2 of those 27 files sat outside the ancestor that carried the covering rule (a
      sibling directory, not a descendant), so a group-level trim would have deleted their guidance
      with nothing replacing it, because the covering rule never loads there.

## RED - baseline WITHOUT the change
- [x] Scenario dispatched to a sonnet subagent (bitranox:baseline-probe, foreground) quoting the
      PRE-EDIT section 1 table and section 4 "Two guards" verbatim, plus a 9-file scenario: 7 files
      under /repo/services/, 2 under the sibling /repo/tools/, all sharing one closing sentence over
      otherwise-unique bodies, measured at "71% largest variant."
- [x] Baseline did NOT fully reproduce the failure: it caught the sibling problem (using section 1's
      pre-existing "compute the common ancestor of ALL member paths" line) and named
      /repo/services/CLAUDE.md as wrong for tool-x/tool-y. This is the surrounding skill already
      generalizing, recorded honestly rather than manufacturing a harder scenario.
- [x] Baseline DID diverge from the new prescribed verdict on the first question: rather than LEAVE
      IT, it chose to lift the one shared sentence into a brand-new heading at /repo/CLAUDE.md and
      strip it from all 9 files - manufacturing a new ancestor section for a single boilerplate
      sentence. That is exactly the over-lift the new table row exists to block: a marginal, almost
      contentless shared fragment is not worth a new lifted heading.
- [x] Control: the same baseline correctly applied "every copy is unique -> leave it" to the bodies
      themselves, proving it can read variance correctly when the row already exists; the gap was
      specific to the ungoverned pointer-sentence case, not general misunderstanding.

## GREEN - what changed here
- [x] Same scenario, same subagent config, POST-EDIT text (new table row + "Three guards", first
      guard = per-file test). Response: "LEAVE IT" verbatim from the new row, no lift, all 9 files
      untouched. Quoted the new guard verbatim for the sibling question and named
      /repo/services/CLAUDE.md as invalid for tool-x/tool-y without being told the answer.
- [x] New variance-table row: "Copies share only a closing pointer sentence; the body is unique" ->
      LEAVE IT, with the reasoning (a coverage percentage can be the sentence's share of a short
      body, not real duplication).
- [x] Section 4 "Two guards" -> "Three guards": new first bullet states the invariant is tested per
      FILE, not per GROUP, and names the failure mode (a member outside the subtree loses guidance
      because the covering rule is only a SIBLING there).
- [x] No other section rewritten; the 60-75% signal paragraph and the other two guards are untouched
      except for the guard count number.

## Quality
- [x] No narrative storytelling in the shipped text; states the rule as it now is, no "we found"
      framing inside SKILL.md itself (the WHY lives in this checklist and the commit message).
- [x] Cross-references unchanged (still point at meta-dream-tree / dream-passes.md, no new links).
- [x] ASCII only, no em-dashes or typographic tells.
- [x] Table columns realigned by the docs-md-table-formatting hook/script to match file convention.

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal paths
      or PII. The change is policy prose plus a fictional scenario in this checklist only.
- [x] Plugin version bumped in plugins/bitranox/.claude-plugin/plugin.json (MINOR: new decision case
      plus a corrected invariant, backward-compatible).
- [x] Frontmatter (name/description) unchanged, so docs/skills.md needs no regeneration for this
      change; confirmed by diffing the frontmatter block before and after edit.
- [x] repo-gate.py --ci green with CI's full dependency set.
- [x] Additive commit to master; history stays append-only, no force-push.
