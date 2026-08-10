# checklist - the nudge fires at the end of a /goal run

Adds a "When it fires on its own" section: a met `/goal` objective, or a commit outside a goal,
once per session - and silence while a goal is still running.

## RED

- [x] No text RED for this edit, and that is a decision. The section documents WHEN the hook fires;
      the hook's behaviour is what needs proving, and it is proved by tests and by mutation below.
      A subagent scenario could only re-read the sentence back to me.
- [x] What this section CAN get wrong is describing a trigger the code does not implement, so that
      is what was checked: every condition the sentence names has a test, and the two states it
      distinguishes (running, met) are the two the reader is told about.

## GREEN

- [x] The record shape was verified against GROUND TRUTH, not the binary's promise: 14 real
      `met: true` records across 11 transcripts on disk. The binary said the field existed; only
      the transcripts show what is actually written, including that `sentinel` is present while a
      goal runs and absent on the met record.
- [x] Own writes EXCLUDED from that survey. The current session's transcript contains the token
      `goal_status` purely because the search for it was run here, and counting it would have been
      a detector matching its own output.
- [x] The LAST record wins, with a test for the ordinary case (false, false, true) and for the
      reverse (met, then running again), because the state is a running report rather than a
      one-shot event.
- [x] Mutation-verified: letting a RUNNING goal fall through to the commit check is killed by two
      tests, including the end-to-end "a goal still running is left alone".

## REFACTOR

- [x] The silence-while-running rule is the safety-critical half, not a nicety: Claude Code carries
      the string "Stop hook prevented continuation", so a blocking Stop hook during an unmet goal
      would cut short the loop the user started. The section says WHY, not just what.
- [x] A goal met without any commit still fires - the objective is the conclusion. Tested, because
      the commit-based rule that came first would have missed exactly that case.
- [x] The section states the hook does not replace asking: "Nothing stops you asking earlier; the
      hook exists for the times nobody remembers to."
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact. The goal conditions quoted from real transcripts were NOT
      copied in - they are other people's work descriptions.
