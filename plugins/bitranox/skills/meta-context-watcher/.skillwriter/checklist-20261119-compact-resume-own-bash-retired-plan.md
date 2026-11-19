# checklist - own Bash edits, topic names, retired checkpoints and plan mode in the resume

`hooks/compact-resume.py` now keeps a checkpoint the session's own records attribute when the
session's own later Bash call changes that path (a `sed -i` re-stamp after the clock nudge), accepts
`handover-<topic>.md` carrying the lessons heading, says so when the session retired its own
checkpoint before the compaction, and names the plan file when the session wrote it after the save
request. `stamp-clock-nudge.py` tells a checkpoint writer to read `date` and fix the stamp with the
Edit tool; the save request in `context-watcher.py` says the same and, in plan mode, says where the
checkpoint goes. The skill states each of these for the writer and the reader.

Decisions: d-20261119-8799febd, d-20261119-bbcf39ab, d-20261119-3d75510f, d-20261119-d9ad120d

## RED

- [x] Skill decisions read first: no rejected or removed entries; the live attribution rule
      d-20261116-8f504808 is superseded, its reopen condition answered in the new entry's why (an
      own Bash call is this session's record, so the peer protection holds).
- [x] Hook tests written first and run on the unfixed hooks: 12 failed in test_compact_resume.py,
      3 in test_stamp_clock_nudge.py, 3 in test_context_watcher.py.
- [x] Text probe on the pre-edit skill (opus and haiku, six questions): Q4 (retired), Q5 (plan mode
      save), Q6 (plan file resume) answered NONE on both tiers; Q1 (reading the clock) NONE on
      both; Q2 (topic name) both said not handed back; Q3 (Write then `sed`) both called it
      uncovered or contradictory ("The text contradicts itself here", haiku).

## GREEN

- [x] Hooks: 221 tests pass across the four hook test files; a 10-arm mutation battery on
      compact-resume.py all KILLED with a green baseline before and after.
- [x] Replay over the 47 real misses: all 25 own-Write-then-own-Bash cases now attributed, the 5
      topic-named ones handed back, 1 retired, 3 plan-file cases named (a fourth plan-mode
      session also wrote a topic-named checkpoint, which is handed back instead).
- [x] Text probe on the edited skill, opus and haiku, all six questions answered with a direct
      quote of the new text.

## REFACTOR

- [x] Closed (haiku): a plan-file checkpoint whose next action is already done met "do not mark
      it STALE" beside the general "mark it STALE and continue" - the text now says to continue
      from the summary's step and never mark the plan file STALE.
- [x] Closed (haiku, opus): steps 2, 3 and 5 in plan mode - step 3 does not apply, step 5's expiry
      line is left out, step 2's reconcile waits until plan mode ends.
- [x] Closed (opus): the stamp rule sat in the live-peer paragraph - it now reads "Wherever the
      checkpoint lives".
- [x] Closed (haiku): how to add the section without overwriting the plan - "with the Edit tool".
- [x] Closed (opus, haiku): where the plan file is when plan mode already ended - Read the path the
      block names (the resume text names it: `_PLAN` in hooks/compact-resume.py).
- [x] Re-probe of the touched questions on both tiers after the fixes: every answer quoted the
      final text; the remaining gaps are the declines below.
- [x] Declined (opus): stamp format or timezone - owned by the clock nudge, which judges local
      time or UTC by the stamp's own Z/UTC suffix (hooks/stamp-clock-nudge.py `_bad_stamps`).
- [x] Declined (opus): when a topic name should be used instead of `handover.md` - the procedure
      still prescribes `handover.md`; the resume only accepts the topic form a session improvised.
- [x] Declined (opus, haiku): what happens to the `## Checkpoint` section after plan mode ends and
      who triggers the carry-over - the plan-mode placement is an open question for the user,
      recorded with its reopen condition in d-20261119-d9ad120d; no policy is invented here.
- [x] Closed (haiku, final re-probe): the writer's paragraph said the harness attaches the plan
      file after the compaction without the "in plan mode" condition the reader's paragraph has -
      it now reads "after a compaction in plan mode".
- [x] Declined (haiku, final re-probe): a missing or unnamed plan path, a second `## Checkpoint`
      section from an earlier request, and which lessons section the nap reads - all part of the
      open plan-mode placement question (d-20261119-d9ad120d); the resume names the path whenever
      it reports a plan file.
- [x] Declined (opus): the "CLOCK CHECK" note is not named in the skill - the stamp rule answers it
      whatever triggers the correction.
- [x] Width and fence check over the added lines printed nothing; every anchor of the four new
      entries and the two carried ones is found exactly once.
