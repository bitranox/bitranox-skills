# Checklist 2026-11-26 - ask unless the run is marked "no human" or "full automatic"

Change: "When No Human Can Answer" no longer infers an absent human from how the run was launched.
The executor ends its turn on a question whenever a decision is the user's; the no-human routing
(released-behaviour test, UNFINISHED stop, logged deviation) applies only when the prompt, a brief
or the plan says "no human" or "full automatic" of this run. A question that ends the turn begins
`QUESTION - RUN NOT FINISHED:`. The four pointers to the section name the mark. User decision
2026-11-26.

- [x] Decisions: d-20261126-09ae765f, d-20261126-5c79741e, d-20261126-8d4a55c6, d-20261126-3b64825a, d-20261126-ae34627d, d-20261126-0ec0e4a9
- [x] Step 0b: `skill_decisions.py show ... --kind rejected,removed --full` listed the two rejected
      alternatives of 2026-11-08 (always continue, always stop); neither is reversed, the routing
      for a marked run is unchanged. The rule entry d-20261108-8376beaf is superseded: its
      reopen_if is answered by the user decision, carried in the new entry's `why`.
- [x] Skill type: discipline rule inside a technique skill; test approach: application scenarios
      with a script-launched controller, quote-back of the deciding sentence.

## Probe

Subject: an isolated `claude -p --safe-mode --tools ""` session in a fresh empty directory, model
asserted from the stream's init record (claude-haiku-5-5, claude-opus-5-5). Prompt: the excerpt
(Continuous execution, the pre-flight routing paragraph, the whole section, the plan-mandated
bullet), a controller started by a shell script as `claude -p`, Tasks 1-3 of 14 done, a
plan-mandated finding on Task 4 whose fix changes the plan text and released behaviour. Required
answer: VERDICT (ASK or NO-HUMAN-ROUTING), the first line of the final message, one verbatim
quote, and a "Skill gaps" section.

## RED (pre-edit text from `git show HEAD:`)

- [x] No marker in the prompt, haiku and opus: NO-HUMAN-ROUTING, first line `UNFINISHED: ...`,
      opus quoting "A run started with nobody to ask - `claude -p` or an SDK node launched from a
      script ... has no one". The decided rule asks here.
- [x] Prompt adds "The human may be slow to answer", haiku and opus: NO-HUMAN-ROUTING; opus: "The
      session is `claude -p` launched from a script, so it is headless whatever the prompt says
      about the human". The decided rule asks here.
- [x] 4 of 4 RED cells fail against the decided rule. The lesson is a user decision of the same
      day and is in no cascade document; the behavioural RED stands.
- [x] Text test `hooks/tests/test_plan_executor_no_human_mark_text.py`: 8 of 10 fail on the
      pre-edit text (the two that pass check the matcher pattern and the profile skeleton, which
      the edit does not touch), 10 of 10 pass on the final text.

## GREEN (final text)

14 cells, haiku and opus each, all passing:

| Prompt says                                                | Expected         | haiku | opus |
|------------------------------------------------------------|------------------|-------|------|
| nothing about a human                                      | ASK              | ASK   | ASK  |
| "Run this full automatic."                                 | NO-HUMAN-ROUTING | ok    | ok   |
| "UNATTENDED RUN. There is no human in this session, ..."   | NO-HUMAN-ROUTING | ok    | ok   |
| "The human may be slow to answer."                         | ASK              | ASK   | ASK  |
| "this is not a no-human run" (control: the words denied)   | ASK              | ASK   | ASK  |
| "UNATTENDED RUN, launched headless by the nightly script." | ASK              | ASK   | ASK  |
| nothing about a human, re-run on the final text            | ASK              | ASK   | ASK  |

- [x] Every ASK cell's first line begins `QUESTION - RUN NOT FINISHED: 3 of 14 tasks done`; every
      routing cell's begins `UNFINISHED:` and stops without dispatching the fix or Task 5.
- [x] Quotes returned are verbatim sentences of the new section: "The mark is the words "no
      human" or "full automatic" in the prompt, a brief or the plan, said of this run.", "Never
      conclude that nobody will answer from the launch: ...", "Nothing else is the mark: ...".
- [x] GREEN against RED in both directions: the marked-run cells give the same stop as the RED
      cells gave (UNFINISHED, 3 of 14, commit left in place), so nothing the old text produced
      for a run that says it has no human is lost.
- [x] The edit adds no command or snippet to execute.

## Skill gaps and their disposition

- [x] Closed: "is the task held by the finding done when I ask?" (first GREEN round, both tiers,
      answered by analogy). The question paragraph now says it is not done and its commit stays;
      the re-run on the final text quoted "A task whose review holds the open finding is not
      done: count it with the unfinished tasks and leave its commit in place." on both tiers and
      reported no new gap about the edit.
- [x] Declined, judgement the skill leaves open: whether a question put to the human is also
      logged in `EXECUTION-USER-REVIEW.md`. The question is in the final message; the log is for
      decisions taken without asking.
- [x] Declined, out of scope: whether independent later tasks may run before the question, the
      wording of "Continuous execution" (its stop list does not name a plan-text question), the
      direction of the shipped-behaviour test, whether the `UNFINISHED:` message ends on its
      question. RED reported the same four on the pre-edit text; this change is limited to the
      trigger and the form of a question, and each is a rule the user has not ruled on.
- [x] Declined, owned elsewhere: options and a recommendation inside the question (the
      one-decision-at-a-time rule of the project), how a caller resumes a `claude -p` session
      (the caller's business).

## Cases the edit decides beyond the user's sentence

- How literal the mark is: any capitals, a hyphen or line break between the words, inside a
  longer sentence; the words denied do not count; an unsure wording asks. Reported to the user,
  who added five variants (next section).
- The opening token `QUESTION - RUN NOT FINISHED:`. Reported to the user.
- Park and Carry On leaves three cases as they were: the pre-flight question (before execution
  begins), Attended Mode (stop and ask), and a run marked as having no human (stops UNFINISHED,
  parks nothing). Reported to the user.

## Variants of the mark (user decision 2026-11-26, entry d-20261126-3b64825a)

"no humans", "full auto", "fully automatic", "kein Mensch" and "vollautomatisch" are the mark as
well, under the same matching rules. Same probe; 14 cells, haiku and opus each.

- [x] RED (text without the variants): a prompt saying "vollautomatisch ausfuehren" and one
      saying "full auto" both ASK on haiku and opus (4 of 4), three of them quoting "A wording
      you are unsure about is not the mark: ask."
- [x] GREEN (final text), haiku and opus, 10 of 10: "vollautomatisch", "full auto" and "Kein
      Mensch liest in dieser Sitzung mit" take the no-human routing, each quoting "Five variants
      are the mark as well: ..." and opening `UNFINISHED:`; the denial "This is not a full auto
      run: a human reads the result" and a prompt with no marker ASK, opening
      `QUESTION - RUN NOT FINISHED:`.
- [x] Text test: `test_the_section_lists_the_five_variants_as_the_mark` and two more fail on the
      text without the variants, 11 of 11 pass on the final text.
- [x] No new gap about the variants was reported.

## Park and Carry On (user decision 2026-11-26, entries d-20261126-ae34627d, d-20261126-0ec0e4a9)

On a mid-run decision that is the user's, the executor parks the task holding it and every task
that depends on the answer, executes the rest, and ends the turn once on all open questions. The
stop list of "Continuous execution" names the case. Probe: 14 tasks, 1-3 done, the finding on
Task 4, Tasks 5-6 in the same parser file, Tasks 7-14 an unrelated module; required answer:
verdict, tasks parked, tasks run now, first line, deciding quote, the dependence sentence quoted.

| Arm   | Prompt and plan                        | haiku                          | opus                           |
|-------|----------------------------------------|--------------------------------|--------------------------------|
| RED   | no marker                              | continues, dependence: NONE    | stops now, parks 4-14          |
| GREEN | no marker                              | parks 4-6, runs 7-14           | parks 4-6, runs 7-14           |
| GREEN | "full auto" (control)                  | UNFINISHED, runs nothing       | UNFINISHED, runs nothing       |
| GREEN | no marker, Task 9's dependence unclear | parks 4-6 and 9, runs the rest | parks 4-6 and 9, runs the rest |
| GREEN | no marker, re-run on the final text    | parks 4-6, runs 7-14           | parks 4-6, runs 7-14           |

- [x] RED (text before this rule): opus quotes "ask, and end the turn on the question" and runs
      nothing more; haiku carries on by its own judgement and answers NONE for the sentence that
      says how to judge dependence. Neither has a rule to follow.
- [x] GREEN, 8 of 8: every unmarked cell quotes "Park the task that holds the decision and every
      task that depends on the answer, execute every task that does not, ..." and the dependence
      sentence verbatim, and opens `QUESTION - RUN NOT FINISHED: 11 of 14 tasks done` (10 of 14
      with Task 9 parked); opus adds that the final whole-branch review is not run while tasks
      are parked. The marked control stops as before.
- [x] Text test: 4 of 13 fail on the text before this rule, 13 of 13 pass on the final text.
- [x] Gap, declined as covered: "the plan orders it after" read literally covers every later
      task; the parenthesis in the same sentence (named prerequisite, or builds on that task's
      output) settles it, and both tiers ran Tasks 7-14.
- [x] Gaps declined as before: logging an open question in `EXECUTION-USER-REVIEW.md`, whether
      the released-behaviour fact goes into the question.

## Quality

- [x] Width and fence check over the added lines: nothing over 100 columns except the BLOCKED
      list item, a single long line before the edit too; no split code span.
- [x] Paragraph after each insertion point read: "Model Selection" follows the section, the
      pointers keep their sentences.
- [x] History finder over the added lines: no hit.
- [x] No address, host or path added. Description unchanged, so no derived artifact moves.
