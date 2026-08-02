# skill-writer checklist - meta-dream-crosstree-deep (git tracking never gates a trim)

Change: remove the rule that made an untracked rung a reason to skip a lift, and demote the
umbrella repo from precondition to optional distribution choice. Correction of a contradiction
between two shipped files, not a new feature.

## PLAN
- [x] Skill type identified: procedure (a dream mode), rigid - its rules gate real edits.
- [x] Scope decided: one bullet in `meta-dream-crosstree-deep/SKILL.md` step 4. No change to the
      reachability invariant itself, which was already correct and is now the single authority.
- [x] Checked whether the defect appears anywhere else before editing: grepped the whole shipped
      skills tree for `umbrella repo`, `untracked rung`, `tracked, shareable`, `do NOT trim`. Four
      hits, all in the one bullet. Not a fleet-wide pattern.

## The defect
- [x] Two shipped files contradicted each other on the same decision:
      - `meta-dream-tree/references/dream-passes.md`: "Git tracking is NOT a condition here...
        Judge only by the reachability invariant" and "Git plays no part in this decision: not
        tracked-vs-ignored, not the remote, not who could clone it."
      - `meta-dream-crosstree-deep/SKILL.md`: "do NOT create a bare untracked rung and do NOT trim
        ... Until that shared home exists, keep the rung additive (no trim)."
- [x] Consequence observed live, not hypothesised: during the 2026-08-02 deep dream I lifted 9
      shared sections to `rotek/apps/CLAUDE.md`, found that target is in no git repo, followed the
      crosstree-deep bullet, and stopped a completed and correct consolidation to raise an umbrella
      repo question. The user's ruling: the dev machine is backed up as a machine, so repo
      membership is not a criterion. The rule was wrong, and it had already cost a stall.
- [x] Root cause, not symptom: the bullet reasoned about DURABILITY (who can clone this) inside a
      pass whose only question is REACHABILITY (does this text load where the rule must fire).
      Durability is the Durability pass's job, which `dream-passes.md` already says.

## GREEN
- [x] The bullet now states the inverse rule explicitly ("git tracking NEVER gates the trim") rather
      than merely deleting the old one, so a reader who half-remembers the old rule is corrected
      instead of finding silence.
- [x] Gives the REASON a reader can re-derive: the cascade loads a file by PATH, not by repo
      membership.
- [x] Points at the single authority (`dream-passes.md` reachability invariant) instead of restating
      it, per the no-duplicated-family-literals rule this skill family enforces.
- [x] Umbrella repo kept, reframed: proposed on its own merits when the user wants the rung's
      history reviewable or shared, never as a precondition. The private-or-public ask moves with it.
- [x] No other rule in the file changed; step 4's structural-proposal boundary is untouched.
- [x] ASCII only, no typographic tells.

## Verification
- [x] Grepped the shipped skills for the gating language afterwards: zero hits.
- [x] Confirmed the surviving text and `dream-passes.md` now agree rather than merely differ.
- [x] Full suite green under CI's dependency set; `repo-gate.py --ci` green.

## Deliverables
- [x] SKILL.md bullet rewritten; `plugin.json` bumped so installs see it.
- [x] Memory fact captured for the class of defect (a rule that gates one axis on another).
