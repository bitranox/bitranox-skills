# meta-skill-ab-test: a stated departure whose reason holds is no defect

"Judging the arms" changes on a user decision of 2026-11-26: the scoring takes well-reasoned
changes into account, because a spec can be unclear, incomplete or contradictory. A departure
the arm stated in a commit message or its hand-over, whose stated reason holds against the spec
text, is scored SOUND-DEPARTURE, counts as no defect and is listed apart per arm. A silent
departure, or one whose reason does not hold, is scored PRESENT as before. Every judge,
verifier and hunter receives the spec and the arm's statements beside the diff.

Decisions: d-20261126-71734d87

- [x] Step 0b: `skill_decisions.py show meta-skill-ab-test --kind rejected,removed --full` run
      before the first edit; the one rejected entry (a hand-added read-only bind) is not
      touched. The anchors of `judge-is-the-verdict` and `shared-checklist-two-judges` stay in
      the text; `skill_decisions.py check` reports no finding.
- [x] Not mirrored. No script changes: the statements are read from `git log` of the arm's
      branch and from `stream.jsonl`, which the run already keeps.
- [x] RED (text check of the pre-edit file): the section at HEAD hands judges "the diff and
      the spec only" and "diffs only", and has no hit for "departure", "statement" or
      "hand-over", so a stated, well-reasoned departure was scored like a silent one.
- [x] GREEN and quote-back, haiku and opus (opus at default effort), headless with no tools,
      the final section pasted in, 2 rounds, 4 and 4 questions on this section: both tiers
      quoted the governing sentence for each (stated and sound: SOUND-DEPARTURE, no defect;
      what the judge receives and what is removed; silent: PRESENT; statement against diff:
      the diff; one commit message is enough; a statement naming another value than the diff
      does not state the departure; a real contradiction with the reason "simpler": PRESENT).
      Every dispatch ended in a `Skill gaps` section.
- [x] CLOSED (opus, round 1): steps 3 and 4 gave their judges no spec, so they could not rule
      on a reason; both steps now list the spec.
- [x] CLOSED (opus, round 1): where the statement must stand, and how many parts it needs,
      were unstated; the first question now says one of the two places is enough and what the
      statement names.
- [x] CLOSED (opus, round 1): a statement that misdescribes the diff, and a judge supplying a
      better reason than the arm gave, were undecided; both are now stated.
- [x] CLOSED (haiku, round 1): "rated like any other defect" pointed at a scale this skill
      does not define; the sentence now reads "scored PRESENT and counted like any other
      defect".
- [x] DECLINED (deliberate difference): `coding-consistency` asks an author for the statement
      in the commit message AND the hand-over, this section accepts one of the two. An arm is
      judged whichever skills it loaded, and the ledger entry says so.
- [x] DECLINED (owned by the run's own briefs): a severity scale for PRESENT items, and a
      mapping of this section's values onto the verdicts of `coding-consistency`.
- [x] DECLINED (judgement): how a judge treats two contradicting lines where the rest of the
      spec favours neither side; the ruling is quoted in the list for the spec's owner.
- [x] Width and fence check over the added lines printed nothing; ASCII only; the finder for
      version-history wording has no hit in the added lines.
