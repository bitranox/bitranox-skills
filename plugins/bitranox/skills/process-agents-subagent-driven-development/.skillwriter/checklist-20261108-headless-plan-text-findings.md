# Checklist 2026-11-08 - headless plan-text findings

Change: new section "When No Human Can Answer", plus pointers to it from the Pre-Flight Plan
Review, the review loop's plan-mandated bullet and BLOCKED step 4. In a headless run, a finding
whose fix changes what the plan text requires is routed by whether the fix changes behaviour a
release already ships: stop UNFINISHED if it does or you cannot tell, otherwise apply the fix as
its own revertible commit, log it and continue. User decision 2026-11-08.

- [x] Decisions: d-20261108-8376beaf, d-20261108-a8c9d2e4, d-20261108-697fb84b
- [x] Step 0b: `skill_decisions.py show ... --kind rejected,removed --full` printed nothing.
- [x] Skill type: discipline rule inside a technique skill; test approach: application scenarios
      with a headless controller, two branches plus a human-present control.

## RED (pre-edit text, opus, text-only probe agent, excerpt pasted)

- [x] Released case: the probe kept the plan text, continued through Tasks 5-14 and ended with
      "Plan docs/plans/parser.md: Tasks 1-14 implemented and committed. One decision is waiting
      for you" - a message that reads as completion, past a finding the decided rule stops on.
      Its own skill gap: "it does not say what to do when no human can answer during the run".
- [x] Unreleased case: the probe kept the plan reading, did not apply the fix, continued and
      ended "Run finished: Tasks 1-14 are done and committed. One decision is yours" - the
      decided rule applies the fix as its own commit instead.
- [x] `redcheck --corpus-cascade` named five documents by term overlap (controller, reviewer,
      final, questions, raise); none states the released/unreleased split, and both RED probes
      failed against it, so the behavioural RED stands.

## GREEN (final text)

Cells: released x opus (twice: before and after the gap fix), released x haiku, unreleased x opus,
unreleased x haiku, human-present control x haiku - 6 cells, all passing.

- [x] Released, opus and haiku: stop with "UNFINISHED: 3 of 14 tasks done", Task 4 not done with
      its commit left in place, Task 5 not dispatched; each choice quoted from the new section.
- [x] Unreleased, opus and haiku: fix as a separate commit, logged with a reopen-if line,
      continue to Task 5, final message names the deviation and `git revert <fix-sha>`.
- [x] Control (human present, haiku): asks the user, quoting the review-loop line, and says
      "When No Human Can Answer" does not apply - the new rule does not over-trigger.

## Skill gaps and their disposition

- [x] Closed: "does the task held by the finding count as done?" (first released GREEN) - the
      stop branch now says it is not done and its plan-conforming commit stays; the re-run on the
      final text quoted that sentence back.
- [x] Declined, covered elsewhere: whether a task whose fix went in counts as done - the process
      flowchart (SKILL.md line 119) sends every fix through a re-review until approved; the fixer's
      model is in "Model Selection".
- [x] Declined, user decision: the stop blocks independent later tasks too; the reason is recorded
      in the ledger entry, and continuing past it was a rejected option.
- [x] Declined, owned elsewhere: options and a recommendation in the question (the tree-wide
      ask-one-decision rule), the format of an EXECUTION-USER-REVIEW.md entry (the skill names
      what goes in it at each use; no format is fixed anywhere in it).
- [x] Declined, not controllable: an exit code signalling failure - the controller cannot set the
      CLI's exit code, so the final message is the signal, which the rule fixes.
- [x] Declined, outside the change: the four control-arm gaps about the human-present path
      (mid-plan batching, the plan-mandated label, logging a deferred question), unchanged by this
      edit; and the two other asks in the skill (two tasks sharing an id, a meaning nobody chose),
      which the user decision did not cover, so the text stays silent on them.

## Mechanical checks

- [x] Width and fence check over the added lines: only BLOCKED step 4 is over 100 columns, a
      list whose items are single long lines throughout; no fence left open.
- [x] The paragraph after the new section is the "## Model Selection" heading; the paragraphs
      after the three pointers read unchanged.
- [x] No version-history wording, no private paths or hosts added.
