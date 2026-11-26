# skill-writer checklist - coding-consistency (2026-11-26, an added condition is reviewed on its merit)

Rule 5 follows rule 4 on a user decision of 2026-11-26: a reviewer rules on a condition the spec
does not carry by its merit, stated or not. A sound one is `ADDED (sound)`, unrated, with a flag
`stated` or `silent`, listed for the owner's decision; a silent sound one is also a missing note
for the author; any other is `ADDED (unsound)`, a rated defect even when stated. The verdicts
`ADDED (stated)` and `ADDED (silent)` are gone. This replaces the review side of
`checklist-20261126-rule-5-stated-departure.md`.

Decisions: d-20261126-6f8ccd40

- [x] Receipt fresh, skill-writer loaded in the editing agent. Step 0b: the ledger was read
      before the edit; the entry this change supersedes is d-20261125-8bd24c0f, whose first
      anchor stays in the text. `skill_decisions.py check coding-consistency` reports 0
      findings.
- [x] Not mirrored. The two language companions name no `ADDED` verdict (grep: no hit).
- [x] What changed in the text: rule 5 (what the why must name; no ground is a defect, stated
      or not; a sound unstated one comes back as a missing note; no reason means leave it out
      and ask); the `ADDED` verdict with its merit test; the heading and two bullets of review
      step 3; the paragraph after them; the rating sentence; two rationalization rows; the
      execution summary. The outside-caller limit is unchanged.
- [x] RED (text check): the previous text reads "An `ADDED (silent)` row is a defect." and
      lets a stated condition pass with no check of its reason. The rewritten text tests fail
      on that text (3 failed) and pass on this one.
- [x] GREEN, quote-back on the final text, haiku and opus (opus at default effort), headless
      with no tools, 7 questions: both tiers answered alike and quoted the governing sentence.
      An unstated minimum sample that prevents a meaningless figure: `ADDED (sound)`, flag
      `silent`, no rating, listed for the owner and in the missing notes. A carefully stated
      wait with the reason "usual practice": `ADDED (unsound)`, a rated defect. The same
      minimum stated: `ADDED (sound)`, `stated`. A sensible idea with a value that hides most
      output: `ADDED (unsound)`. Author: still states it, the why names what goes wrong or the
      gap. Neither text given: flag `silent`, the row says so. No finding for `AGREE`,
      `ADDED (sound)`, `DEPARTED (sound)`. Both runs ended in a `Skill gaps` section.
- [x] DECLINED (judgement): how much held-back output is too much between clear cases, and
      whether a late alert rates medium or high; the tiers rated one such case medium and
      high. The rating scale is not part of this decision.
- [x] DECLINED (reported to the user): `stated` needs the commit message and the hand-over;
      a statement in only one of them gives `silent`. Unchanged from the earlier checklist.
- [x] DECLINED (judgement): how hard a reviewer must look for an input before ruling an
      addition unsound, and what a non-interactive review does after asking for the texts
      (the text gives the result: flag `silent`, the row says they were not seen).
- [x] Width and fence check over the added lines: no prose line over 100 columns; every fence
      closed; ASCII only; the rationalization table's rows are all one width.
- [x] Description unchanged. Trigger map and catalogue regenerated and in sync.
- [x] Text tests in `hooks/tests/test_consistency_skill_family_text.py` pin the new rule 5 and
      the `ADDED (sound)` / `ADDED (unsound)` review text, and the absence of the old verdicts.
