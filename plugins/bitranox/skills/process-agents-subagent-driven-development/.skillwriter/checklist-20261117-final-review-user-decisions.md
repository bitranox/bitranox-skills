# checklist - Final Whole-Branch Review: plan decisions against the user's recorded answers

The final whole-branch review gets `USER-DECISIONS.jsonl` (main checkout root) as an input and a
fourth instruction: check every decision the plan took against the user's recorded answers. A plan
decision that narrows a user decision or adds an exception the answer does not carry is a DEFECT
that quotes the plan's line and the user's answer. In a split review one reviewer runs the check;
the confirmation step says how such a defect is confirmed.

Decisions: d-20261117-cf579f8e

## RED

- [x] Skill decisions read first (`skill_decisions.py show`, also `--kind rejected,removed
      --full`): two rejected entries, both on headless plan-text findings, not touched here.
      Entry d-20261115-a7014084 checks a FIX's remedy against the user's requirements; this edit
      checks the PLAN's decisions in the final review, a different step.
- [x] Coverage check on the pre-edit section (`git show HEAD:` excerpt), quote-back probe, opus,
      five questions. Inputs: no `USER-DECISIONS.jsonl`. "Plan accepts an exception the user's
      answer did not have, code follows the plan": NONE, would report only if the answer were in
      the source design. "Where are the user's answers": NONE. "Which split reviewer checks":
      NONE. Control (a point no answer covers): not a defect.

## GREEN

- [x] The edit adds no command or snippet. The file location it names matches
      `scripts/task_brief.py` ("USER-DECISIONS.jsonl at the main checkout's root, where
      hooks/user-decision-log.py writes them").
- [x] Same five questions on the edited text, opus and haiku (2 tiers, 10 cells): both list the
      file among the inputs, quote the DEFECT sentence and what the finding cites, and give the
      check to one reviewer only. Control on both tiers: a point no recorded answer covers is not
      reported as a defect, so the rule does not over-trigger.
- [x] GREEN diffed against RED in both directions: every baseline input still listed; nothing
      lost.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided below.
- [x] Closed: "a point the answers never address" could be read as an exception the answer does
      not carry - the text now says such a decision is no DEFECT here.
- [x] Closed: "no such file" - the dispatch says so and the check is reported as not made.
- [x] Closed: "is not one" had an unclear referent (opus) - reworded to "is no DEFECT here".
- [x] Closed: "how is a defect with no failing input confirmed" (both tiers) - the confirmation
      step reads its two quotes in the files they come from.
- [x] Closed: a back-reference re-bound by the insertion ("so they approved it" after two new
      sentences) - rewritten to name its subject.
- [x] Declined: "severity of a decision defect" and "a Minor one skips confirmation" - the
      reviewer's judgement, as for every defect under instruction 2.
- [x] Declined: "which of the two reviewers" - the dispatcher's choice, as for PLAN CHANGES and
      the Minor triage in the same sentence.
- [x] Declined: "the review package", "the plan-mandated rule above", "see the bullet above" -
      covered outside the probed excerpt, in the same SKILL.md: the bullet "The final
      whole-branch review gets a package too: run ... review_package.py MERGE_BASE HEAD", the
      bullet "If the final whole-branch review returns findings, dispatch ONE fix subagent", and
      the plan-mandated rule ("Never dismiss a finding because the plan mandates it").
- [x] Declined: "`decisions.md` versus the decisions file" - instruction 2 already says
      "decisions file" for the input listed as `.bitranox/sdd/decisions.md`.
- [x] Declined: "plan at HEAD versus plan at MERGE_BASE" - reported by GREEN on text this edit
      did not change; two stated measures (judge the branch against the amended plan; list
      departures from the plan as it started), judgement the skill leaves as is.
- [x] Declined: "what covers means", "an answer that can be read either way", "what test a fix
      for a decision defect adds", "a finding the controller falsifies" - a fix that changes what
      the plan text requires goes to the human through the plan-mandated rule, which settles the
      first three case by case; the last is ordinary confirmation.
- [x] Re-probe of the touched questions after each fix round, opus (effort medium) and haiku:
      five questions after round one, two after the wording and confirmation fixes. Final run,
      both tiers quoted "A plan decision on a point no recorded answer covers is no DEFECT here."
      and "(a decision defect from instruction 4: read its two quotes in the files they come
      from)"; no new undecided gap.
- [x] Width, fence and non-ASCII check over the added lines printed nothing after each round; the
      paragraph after each insertion point read (the split-by-system paragraph after the new
      input, the confirmation paragraph after instruction 4); the split paragraph's list of
      single-reviewer parts now names instruction 4.
- [x] Cases the edit decides beyond the proposal, for the maintainer: an uncovered point is no
      defect under this check; an absent file means "check not made"; how the defect is
      confirmed.
