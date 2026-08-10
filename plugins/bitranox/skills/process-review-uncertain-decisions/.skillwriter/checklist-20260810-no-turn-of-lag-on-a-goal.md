# checklist - the goal ask must not lag a turn behind

Corrects the "When it fires on its own" section: a `/goal` counts whether or not it has reported
met, because the met verdict is written after the Stop hooks have already read the transcript.

## RED

- [x] RED is a REAL RECORDED FAILURE, not a constructed one. The hook shipped, the plugin was
      reloaded, a one-turn goal ran and was achieved - and the hook did not fire. Ground truth: its
      session-keyed flag file did not exist.
- [x] Cause established from timestamps, not inference: the goal was set at 19:58:49 with
      `met: false`, and `met: true` was written at 19:59:07. The Stop hook read the transcript
      between the two, so it saw a running goal and stayed silent by its own rule.
- [x] Confirmed against the CLI: the goal's own `goal_status` is yielded from inside Stop-hook
      processing, so no earlier read can see the verdict. Searched for an on-disk goal state a hook
      could read instead - `~/.claude` outside the transcripts, with a control proving the search
      finds the token where it does exist - and there is none.

## GREEN

- [x] The premise behind the old suppression was WRONG and is corrected in the text rather than
      quietly dropped: "Stop hook prevented continuation" comes from a hook setting
      `preventContinuation`, a different field this hook never sets. `{"decision": "block"}` feeds
      a reason back and the turn continues.
- [x] Measured, not argued: the self-improve gate blocked during an ACTIVE goal earlier in the same
      session and the goal still completed. A block mid-goal is safe.
- [x] Verified by REPLAY of the exact failing input - the real transcript truncated at the last
      `met: false` record, the state that produced the silence. Old code silent, new code fires.
      A differential on the true input, with both arms run from their own flag namespace so the
      first arm's flag could not suppress the second.
- [x] The replay's first run tested the INSTALLED copy by mistake and reported "still silent". That
      is the stale-copy trap, and the replay is what exposed it; the arms are labelled by path now
      so the version under test is never ambiguous.

## REFACTOR

- [x] The trade is stated in the skill rather than hidden: firing on an active goal means a long
      goal is asked early instead of at its end. With one ask per session the real choice is
      sometimes-early against sometimes-never, and never is the worse failure.
- [x] Two tests inverted deliberately, with names that carry the reason
      (`..._also_counts_so_the_ask_is_never_missed`, `..._without_waiting_a_turn`) so a later reader
      does not restore the old behaviour thinking it was a regression.
- [x] No session narrative, no scratch paths, no machine-derived addresses or hostnames in the
      skill text or in this artifact.
