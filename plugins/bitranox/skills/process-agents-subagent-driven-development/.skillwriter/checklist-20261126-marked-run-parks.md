# Checklist 2026-11-26 - a marked run parks and carries on before it stops UNFINISHED

Change: in a run marked "no human" or "full automatic", a finding whose fix changes behaviour a
release already ships (or where that cannot be told) does not stop the run at once. The executor
dispatches no fix for it, parks the task holding it and every task that depends on it by the
dependence test of "Park and Carry On", logs the finding in `EXECUTION-USER-REVIEW.md` at once,
executes every independent task with its reviews, and then stops once with `UNFINISHED:`, the
tasks done (N of M), each parked task with its reason and every open finding with its question.
The "Park and Carry On" paragraph and the failure-modes review's sentence on a stopped run say
the same. User decision 2026-11-26.

- [x] Decisions: d-20261126-95be0a75, d-20261126-87801865, d-20261126-b566f8e7, d-20261126-97a2c791
- [x] Step 0b: `skill_decisions.py show ... --kind rejected,removed --full` was read. The two
      rejected routings of 2026-11-08 (always continue, always stop) are not adopted: the
      released-behaviour test still decides, and a marked run still ends UNFINISHED on such a
      finding. The rule entries d-20261126-3b64825a and d-20261126-ae34627d are superseded; their
      reopen conditions are answered by the user decision, carried in the new entries' `why`.
- [x] Skill type: discipline rule inside a technique skill; test approach: an application
      scenario with quote-back.

## Probe

Subject: an isolated `claude -p --safe-mode --tools ""` session in a fresh empty directory, the
whole SKILL.md pasted between markers, model asserted from the stream's init record
(claude-haiku-5-5, claude-opus-5-5). Scenario: a 14-task plan in a run whose prompt says "This is
a full automatic run"; Tasks 1 to 3 complete; the review of Task 4 holds a plan-mandated finding
whose fix changes behaviour the last release ships; Tasks 5 and 6 build on Task 4; Tasks 7 to 14
are independent. Questions: what happens with the finding and Tasks 4 to 6, whether Tasks 7 to 14
are executed, when the run stops and how its final message begins, whether the two whole-branch
reviews run, a direct quote per answer, and a "Skill gaps" section.

## RED (text before this change)

- [x] haiku: Tasks 7 to 14 "no", "I stop the run rather than executing them", quoting "In a run
      so marked a question is never answered and nothing is parked".
- [x] opus: "No. I dispatch no further implementer."
- [x] 2 of 2 cells stop at once. The rule is a user decision of the same day; a failing RED
      cannot be a contaminated pass.
- [x] Text tests in `hooks/tests/test_plan_executor_no_human_mark_text.py` and
      `test_plan_executor_failure_modes_review_text.py`: 8 fail on the text before this change,
      all pass on the final text.

## GREEN (final text)

- [x] haiku and opus, 2 of 2: no fix for the finding; Tasks 4, 5 and 6 parked; the finding
      logged at once; Tasks 7 to 14 executed with their reviews; one stop with `UNFINISHED:`,
      11 of 14 tasks done, the three parked tasks with their reasons and the open finding; no
      final whole-branch review and no failure-modes review in this run. Quotes: "Dispatch no
      fix, and do not stop yet: park and carry on, by the rule above." and "Then stop the run
      UNFINISHED, once: begin the final message with `UNFINISHED:`".
- [x] The text adds no command.

## REFACTOR

- [x] Closed: whether another finding of the same review that needs no decision is fixed (it
      gets its fix round as usual).
- [x] Declined, out of scope of this change (they hold for a stop on a question in the same
      way): whether the model gate is disarmed when a run stops with tasks parked, the ledger
      line of a parked task, and the "an order to stop dispatching" sentence under "Agents
      already running are a bet on the plan" beside "Park and Carry On".
- [x] Declined, covered elsewhere in the skill: how tasks are counted ("A parked task is not
      done", "When No Human Can Answer"); "No run drops it" beside a parked run ("A run that has
      parked a task ... has not reached this step", "Failure-Modes Review").
- [x] GREEN against RED in both directions: the RED cells' logging of the finding, the
      plan-conforming commit left in place and the `UNFINISHED:` opening are all in the GREEN
      cells; nothing was lost.
- [x] Width and fence check over the added lines: no prose line over 100 columns, no odd
      backtick count. The paragraphs after each insertion point were read.
- [x] Description unchanged.
- [x] Cases the edit decides beyond the user's option, each in the `argued` ledger entry
      d-20261126-97a2c791: a run that parked a task ends without the two whole-branch reviews; a
      released-behaviour finding from one of those reviews stops the run after the fixes that
      need no decision.
