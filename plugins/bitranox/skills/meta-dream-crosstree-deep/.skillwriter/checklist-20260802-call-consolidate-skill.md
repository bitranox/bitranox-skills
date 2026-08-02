# skill-writer checklist - meta-dream-crosstree-deep (call the consolidation skill)

Change: step 3's CLAUDE.md reconciliation gains a call site for the new
`bitranox:meta-consolidate-claude-md`, for the case where a section was copy-pasted across many
repos and has since drifted. Second edit to this file today; the first was the git-tracking fix
(checklist-20260802-git-never-gates-a-trim.md).

## PLAN
- [x] Skill type: procedure (a dream mode), rigid.
- [x] Scope: one added paragraph at the existing consolidation sentence in step 3. No other rule in
      the file changed; the promotion gate, the org-chart step and the boundaries are untouched.
- [x] Placed at the existing call point rather than as a new step, because step 3 already owned
      "CONSOLIDATE a rule duplicated across many sibling CLAUDE.md UP to their common ancestor" -
      it stated the goal and gave no procedure, which is exactly the gap.

## The gap it closes
- [x] Observed, not theorised: running that sentence for real over a 92-file tree needed a method it
      does not supply. Without one the obvious reading is "find identical text, move it up", which
      silently assumes the copies are correct. They were not: a `menu` make target documented in 5
      variants and defined in 0 Makefiles, 4 files asserting two implemented commands "will fail",
      a systemprompt file deleted in June still referenced in 3 repos.
- [x] So the call site does not merely name the skill, it states WHY: drift means most copies are
      now wrong, and deduplicating by picking the most-copied variant installs a stale claim at an
      ancestor where it binds every repo below.

## GREEN
- [x] Cites the skill by name and says to FOLLOW it; does not restate its procedure, per the
      family's no-duplicated-literals rule (the contract test fails duplicated family literals).
- [x] Ends with "Do not re-derive that procedure here", which is the instruction that keeps the
      restatement from growing back at the next edit.
- [x] Names the four phases (measure, verify, converge, lift) so a reader knows what they are
      invoking without loading it, but no phase is explained here.
- [x] No change to the surrounding classification rules; the sentence it attaches to still reads
      correctly on its own for the non-drifted case.
- [x] ASCII only, no typographic tells.

## Verification
- [x] `repo-gate.py --ci` green, full suite 1582 passed / 7 skipped.
- [x] The gate itself caught the first attempt at this commit: it blocked because this SKILL.md had
      changed without a checklist in the same change. That is the rule working, and this file is
      the response to it rather than a formality.

## Deliverables
- [x] The call-site paragraph in step 3; this checklist; `plugin.json` bumped with the new skill.
