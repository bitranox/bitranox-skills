# Checklist 2026-11-26 - the unattended note must carry the plan executor's mark

Change: one sentence in "Tell every arm that nobody answers, and see which arm asked anyway": an
arm that executes a plan under `bitranox:process-agents-subagent-driven-development` takes its
no-human routing only when the note holds the words "no human" or "full automatic" or one of the
variants that skill lists. The `unattended_note` mechanism is unchanged. User decision 2026-11-26.

- [x] Decisions: d-20261126-f248e9b0
- [x] Step 0b: `skill_decisions.py show meta-skill-ab-test --kind rejected,removed --full` lists
      one rejected entry (a hand-added sandbox bind), which this edit does not touch.
- [x] Skill type: reference sentence; test approach: coverage check against the skill file plus
      the behavioural probe of the plan-executor text the sentence points at.

## RED

- [x] The pre-edit text has no sentence tying the note's wording to the executor's routing:
      `test_the_ab_test_skill_says_the_note_must_carry_the_mark` fails on it.
- [x] Behavioural RED of the rule itself, on the pre-edit plan-executor text (isolated
      `claude -p --safe-mode --tools ""`, haiku and opus): a script-launched controller with no
      note took the no-human routing in 4 of 4 cells, so before this change the note's wording
      made no difference to that arm.

## GREEN

- [x] On the final plan-executor text, haiku and opus (4 cells): a prompt ending in "UNATTENDED
      RUN. There is no human in this session, and none will read or answer anything until it has
      ended." takes the no-human routing, opus quoting "the words count inside a longer sentence
      ("There is no human in this session", ...)"; a prompt ending in "UNATTENDED RUN, launched
      headless by the nightly script." asks, first line `QUESTION - RUN NOT FINISHED:`.
- [x] The example note in the profile skeleton ("No human reads this session. ...") matches the
      mark: `test_the_example_note_in_the_profile_skeleton_carries_the_mark` passes.
- [x] The edit adds no command or snippet to execute.

## Skill gaps and their disposition

- [x] None reported about this sentence. A note that says "unattended" without the two phrases
      leaves a plan-executor arm asking; the sentence says so.

## Quality

- [x] Added lines are under 100 columns; the bullet's following sentences keep their subject
      ("Each journal row and `result.json` carry ...").
- [x] History finder over the added lines: no hit. Description unchanged.
