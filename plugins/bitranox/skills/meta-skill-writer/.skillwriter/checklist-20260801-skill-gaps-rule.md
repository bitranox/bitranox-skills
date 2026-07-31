# skill-writer checklist - meta-skill-writer (2026-08-01, require a Skill gaps section)

Change: every RED and GREEN test dispatch must ask its subagent for a `Skill gaps` section, and
GREEN's list is REFACTOR input rather than a pass. Adds the dispatch snippet and the
evidence-not-verdict rule to GREEN, the gaps-are-input rule plus a loop-exit condition and
quote-back verification to REFACTOR, and three boxes to the REFACTOR checklist. Ships with plugin
5.121.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Test approach is application scenarios, per this skill's own
      "Testing All Skill Types" table.
- [x] RED attempt 1 was CONFOUNDED and is reported rather than counted. The scenario said an edit
      was made and then verified, which reads as a missing RED - a louder violation than the one
      under test. The subagent spent its answer on that ("You violated the Iron Law. You skipped
      the RED test entirely") and never reached the question of what a silent GREEN means. A
      scenario that contains a second, more obvious defect does not test the first.
- [x] RED attempt 2 was CONTAMINATED and is reported rather than counted. Rewritten so both arms
      were already done correctly, it produced the right answer for the wrong reason: the reply
      quoted `Check GREEN for what it LOST, not only for what it gained`, a sentence that appears
      nowhere in the excerpt it was given. It came from the memory index that loads for every agent
      in this tree. An in-tree subagent therefore CANNOT baseline an authoring rule this tree's
      memory already teaches - it measures the memory, not the skill.
- [x] RED attempt 3 ran in a CLEAN ROOM and failed as predicted: a `claude -p --model haiku` run in
      a temp dir with no CLAUDE.md or CLAUDE.local.md on its ancestor chain, so the only guidance
      was the pre-change excerpt. Verdict: "**Yes.** ... The edit is done", with the reasoning "No
      new rationalizations were discovered during GREEN, so the REFACTOR phase does not apply". It
      also required of its own GREEN subagent: "Statement of success ('no problems found' or
      equivalent) - proof it worked", treating a self-declared verdict as evidence. That is the
      defect, stated by the skill's own reader.
- [x] Weak, literal model (haiku) for every arm, per the rule that a capable model routes around a
      rigid procedure and masks the gap. Scenario withheld the trap: it never mentioned gaps,
      silence, or contradiction.
- [x] GREEN: the identical prompt and clean room against the edited excerpt reversed the verdict to
      "**No.** The procedure requires a 'Skill gaps' section from every test subagent (RED and
      GREEN). You did not require it from GREEN", quoting the new text back unprompted. Same model,
      same prompt, same environment - only the procedure text differs.
- [x] The rule applied to itself. The first GREEN was not asked for its gaps, which the new text
      makes a non-pass, so it was re-run with the required section. It reported two: how many gaps
      may survive before looping back ("procedure implies: zero new ones"), and whether REFACTOR
      re-tests the whole skill or only part.
- [x] Both gaps CLOSED, and the first was a real self-contradiction the edit itself introduced -
      its inference of "zero new ones" disagreed with the new checklist box allowing a gap to be
      declined with a reason. REFACTOR states the exit condition (an empty UNDECIDED list, never an
      empty list) and the re-test scope (only the questions the fix touched).
- [x] Refactor verified by quote-back: five contested questions, each answered with a direct quote
      of the governing sentence, no NONE. Q1 a silent GREEN, Q2 how many gaps may be open at ship,
      Q3 re-test scope, Q4 the form a verification answer takes, Q5 what a test reply must contain.
- [x] Scoped to the queued rule. The sibling rule about diffing GREEN against RED for findings LOST
      is deliberately not shipped here - it is a distinct claim needing its own RED, and folding it
      in would ship an untested rule alongside a tested one.
- [x] Token budget: hub skill, body remains an index; the addition is ~30 lines in the two phase
      sections it governs, not a new top-level section.
- [x] No session narrative or private provenance in the skill text. This artifact records the
      claim tested, how, and the outcome, with verbatim agent output only where it IS the evidence.
- [x] No addresses, MACs, hostnames or machine paths added.
