# meta-skill-ab-test: SOUND-DEPARTURE is decided on the departure's merit

"Judging the arms" changes on a user decision of 2026-11-26: the judge rules on the departure
itself (the spec is unclear, incomplete or contradictory there, or its version breaks something
nameable, and the change resolves it without a defect of its own). Whether the arm stated it is
a flag, `stated` or `silent`, reported beside the SOUND-DEPARTURE list and never counted. The
arm's commit messages and hand-over stay an input. This replaces the wording of
`checklist-20261126-sound-departure.md`, where a departure had to be stated and the judge ruled
only on the reason the arm gave.

Decisions: d-20261126-26b6c008

- [x] Step 0b: the ledger was read before the edit; the entry this change supersedes is
      d-20261126-71734d87. `skill_decisions.py check meta-skill-ab-test` reports 0 findings.
- [x] Not mirrored. No script changes.
- [x] RED (text check): the previous text asks "Is it stated" as a condition and says the
      judge rules "never on one the judge could supply for it". The new text tests in
      `hooks/tests/test_ab_test_judging_text.py` fail on that text and pass on this one.
- [x] GREEN, quote-back on the final text, haiku and opus (opus at default effort), headless
      with no tools, 4 questions on this section: both tiers answered alike and quoted the
      governing sentence. A silent departure on a self-contradicting point: SOUND-DEPARTURE,
      flag `silent`. Judged without any statements: still SOUND-DEPARTURE. A clear spec number
      changed for a carefully stated reason of taste: PRESENT. The flag changes no tally.
      Every dispatch ended in a `Skill gaps` section.
- [x] CLOSED (opus): no flag was defined for judges given no statements; the flag is then
      `silent` and the report says the statements were not seen.
- [x] DECLINED (owned by `coding-consistency`, reported to the user): that skill still makes
      an unstated added condition a defect, while this section scores an added condition on
      its merit like any other departure.
- [x] DECLINED (owned by the run's own briefs): a list of missing notes for the arm's author,
      and a severity scale for PRESENT items.
- [x] DECLINED (judgement): whether the judge may find an ambiguity the arm did not mention;
      the text says the judge rules on the merit whether or not the arm gave a reason.
- [x] Width and fence check over the added lines printed nothing; ASCII only; the finder for
      version-history wording has no hit in the added lines.
