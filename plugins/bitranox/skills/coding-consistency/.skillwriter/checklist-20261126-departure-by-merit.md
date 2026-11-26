# skill-writer checklist - coding-consistency (2026-11-26, a departure is reviewed on its merit)

The review side of rule 4 changes on a user decision of 2026-11-26: a reviewer rules on a
changed fixed point by its merit against the spec text (the spec is unclear, incomplete or
contradictory there, or its version breaks something nameable, and the change resolves it
without a defect of its own). A sound one is `DEPARTED (sound)`, unrated, with a flag `stated`
or `silent`; a silent sound one is reported as a missing note for the author to add, not as a
rated defect; one that is not sound is `DISAGREE`, rated as usual. The author side keeps the
statement as the expected practice. This replaces the wording of
`checklist-20261126-rule-4-stated-departure.md`, where a silent departure was a defect and the
reviewer judged only the reason the author gave.

Decisions: d-20261126-2b186e09

- [x] Receipt fresh, skill-writer loaded in the editing agent. Step 0b: the ledger was read
      before the edit; the entry this change supersedes is d-20261126-1d9f8d21. The
      outside-caller entry d-20261126-65f209bd is unchanged and its anchor is still in the
      text. `skill_decisions.py check coding-consistency` reports 0 findings.
- [x] Not mirrored. Companions restate nothing of this (grep for DEPARTED, departure: no hit).
- [x] What changed in the text: the defect sentence of rule 4 (a change with no ground in the
      spec text is a defect, stated or not; a sound change left unstated comes back as a
      missing note); the verdict `DEPARTED (sound)` with its merit check and flag; the heading
      of review step 3; the paragraph after the finding bullets (a list of missing notes); the
      rating sentence; one row of the rationalization table; the execution summary (a fifth
      returned part). Rule 5 and the `ADDED` verdicts are unchanged.
- [x] RED (text check): the previous text reads "Judge the reason the statement gives, never
      one you could supply for it" and makes a changed fixed point without the statement
      `DISAGREE`. The rewritten text tests fail on that text and pass on this one.
- [x] GREEN, quote-back on the final text, haiku and opus (opus at default effort), headless
      with no tools, 5 questions on this skill: both tiers answered alike and quoted the
      governing sentence. Self-contradicting spec, supported side taken, nothing stated:
      `DEPARTED (sound)`, flag `silent`, no rating, listed for the owner and in the missing
      notes. Same with the stated reason "simpler": still `DEPARTED (sound)`, flag `stated`.
      A clear spec changed for taste with a careful four-part statement: `DISAGREE`. Author:
      still states it; unstated it comes back as a missing note. An unstated added minimum
      the reviewer finds sensible: `ADDED (silent)`, a defect.
- [x] CLOSED (opus): no flag was defined for a review that was given neither text; the flag
      is then `silent` and the row says the two texts were not seen, as for `ADDED`.
- [x] DECLINED (outside this decision, reported to the user): rule 5 still makes an unstated
      added condition a defect whatever its merit, while a changed fixed point is judged on
      merit. Rule 5 rests on its own user decision of the same day (d-20261125-8bd24c0f) and
      this change was scoped to rule 4.
- [x] DECLINED (reported to the user): the `stated` flag needs the commit message and the
      hand-over here, and one of the two in `meta-skill-ab-test`. The flag is never rated.
- [x] DECLINED (judgement): whether a statement whose reason is no ground still earns the
      flag `stated`. It names the departure, which is all the flag records.
- [x] DECLINED (judgement, as on the earlier checklist of this date): what "supports" means
      where the rest of the spec is only partly relevant, and how to rate when the question
      does not say what a user sees.
- [x] Width and fence check over the added lines: no prose line over 100 columns; no split
      code span in an added line; every fence closed; ASCII only; the rationalization table's
      rows are all one width.
- [x] Description unchanged (829 characters). Trigger map and catalogue regenerated and in
      sync.
- [x] Text tests in `hooks/tests/test_consistency_skill_family_text.py` pin the new rule: the
      author's defect sentence and missing note, the merit check, the absence of the old
      "never one you could supply" sentence, the flag, `DISAGREE` for an unsound change, the
      missing-notes list and the unrated row.
