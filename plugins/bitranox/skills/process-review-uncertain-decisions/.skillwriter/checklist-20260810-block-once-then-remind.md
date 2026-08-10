# checklist - block once, then remind

The Stop hook stops the session on the FIRST conclusion and, on every conclusion after it, emits a
non-blocking reminder instead. Replaces the once-per-session-then-silent behaviour.

## RED

- [x] The gap is one this skill's own artifacts recorded rather than one invented for the edit: the
      previous version traded "sometimes-early" against "sometimes-never" and said so in writing.
      An early first ask meant a long goal got nothing at its end.
- [x] What made the old shape unavoidable was the belief that the only channel was a block, and a
      second block would nag. That premise is now checked rather than assumed - see GREEN.

## GREEN

- [x] The channel was verified against the CLI's own embedded hook documentation before being used:
      `{"hookSpecificOutput": {"hookEventName": ..., "additionalContext": ...}}`, with `decision`
      listed as valid for Stop. The Stop handler consumes `additionalContexts` and re-emits them
      tagged `hookName: "Stop"`, so the channel exists on this event and not only on PreToolUse,
      where the store's existing note had measured it.
- [x] Repeats are told apart by a SCORE, not a boolean. A commit never leaves the transcript, so a
      yes/no answer would re-fire on every later turn; the hook records the score it last acted on
      and speaks only when it rises. A goal scores 1 running and 2 met, so running-to-met registers
      as new even though no command ran.
- [x] Mutation-verified: making the repeat block as well is killed by two tests, one on the pure
      decision and one end to end asserting the emitted JSON has no `decision` key at all.
- [x] The end-to-end test asserts the SHAPE, not just the absence of a block: `hookEventName` is
      `Stop` and the reminder names the skill.

## REFACTOR

- [x] `decide(score, last_score)` carries the whole policy as one pure function with three named
      outcomes, so the block-versus-remind split is one readable line rather than a condition spread
      across `main`.
- [x] Repeated blocking was rejected for a second reason beyond nagging: the CLI ends a turn by
      override after a hook blocks N consecutive times. A remind-only repeat cannot reach that cap.
- [x] The renamed state helper (`record_score` for the old `mark_asked`) broke one existing test,
      which the run caught rather than a reader; the flag file now holds the score instead of a
      constant, and the session-keyed path is unchanged so the stale-flag property still holds.
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact.
