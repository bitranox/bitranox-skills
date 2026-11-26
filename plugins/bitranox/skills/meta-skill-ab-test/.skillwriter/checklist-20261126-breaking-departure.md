# meta-skill-ab-test: a breaking departure is judged on its merit

"Judging the arms" follows the user decision of 2026-11-26 for `coding-consistency`: a departure
that breaks a caller outside the arm's change is ruled on like any other, and its entry names
the callers it breaks where the judge knows them. It was PRESENT whatever its ground.

Decisions: d-20261126-875eef32

- [x] Step 0b: the ledger was read before the edit; no live entry pinned the old sentence.
      `skill_decisions.py check meta-skill-ab-test` reports 0 findings.
- [x] Not mirrored. No script changes.
- [x] RED (text check): the previous text reads "PRESENT whatever its ground"; the extended
      test in `hooks/tests/test_ab_test_judging_text.py` fails on it and passes on this text.
- [x] GREEN, quote-back on the final text, haiku and opus (opus at default effort), headless
      with no tools, 1 question on this section: both scored a breaking change that resolves
      a self-contradicting spec SOUND-DEPARTURE, with the callers named where known, and
      quoted the sentence. Both runs ended in a `Skill gaps` section.
- [x] DECLINED (judgement): wording for an entry where the judge knows no caller; "where the
      judge knows them" already leaves it out.
- [x] DECLINED (reported to the user): this section accepts a statement in the commit message
      or the hand-over for the flag, `coding-consistency` needs both.
- [x] Width and fence check over the added lines printed nothing; ASCII only.
