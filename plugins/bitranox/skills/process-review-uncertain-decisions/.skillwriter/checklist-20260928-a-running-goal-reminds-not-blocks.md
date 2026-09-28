# checklist-20260928-a-running-goal-reminds-not-blocks

Change under test: "When it fires on its own" no longer says a running `/goal` counts as a
conclusion. A running goal gets one non-blocking reminder that claims nothing about its state; the
block is kept for a goal whose record says met, or an opened PR, and a met goal's block arrives at
the Stop after the one that ended it. The hook `decision-review-nudge.py` changes in the same
commit.

The measurement behind it: over every goal session in the transcript corpus, 16 decision-review
blocks fired in goal sessions. 3 landed on the Stop whose goal verdict was met. 13 fired on a Stop
with no verdict, 3 to 160 minutes into the goal and up to 583 minutes before it was met, and each
told the model "a /goal objective was met".

## PLAN

- [x] Skill type: reference. The section describes what a hook does, so the test is retrieval and
      application: given the text and a Stop, does the agent predict the hook's action and respond
      correctly.
- [x] Scope: one section of `SKILL.md`, plus the hook with its own RED tests.

## RED

- [x] Scenario: a goal set four minutes ago, five background implementers running, nothing
      committed, the turn ending to wait for them. Asked: block, remind or silent; is the message
      accurate; what to do.
- [x] Inherited coverage: `redcheck.py --corpus-cascade` reported STRONG on topic words (agents,
      background, completion, dispatched). Adjudicated a false positive: no fact body and no
      cascade file mentions the decision-review hook together with a goal (grep, zero hits), so the
      arm can fail honestly.
- [x] RED on haiku with the old section FAILS as predicted: "The hook blocks (stops) the session",
      quoting "a `/goal` in play". Its gaps: no definition of conclusion, no message content, no
      guidance on responding, turn-ending vs session-ending unclear.
- [x] Hook RED: `test_a_running_goal_is_not_a_conclusion`,
      `test_a_running_goal_is_reminded_without_blocking` and
      `test_a_goal_reminded_while_running_is_blocked_once_met` failed against the old hook (3
      failed, 73 passed).

## GREEN

- [x] Same scenario on haiku with the new section: "The hook reminds without blocking", quoting the
      RUNNING-goal sentence; the response is to ignore it because the turn ends to wait; at the goal's
      end the reminder comes first and the block at the next Stop, quoting the governing sentence.
- [x] Hook GREEN: 76 passed in `test_decision_review_nudge.py`.
- [x] Both arms asked for `Skill gaps`; lists recorded and worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (RED): no definition of a conclusion; turn-ending vs session-ending. CLOSED - the first
      sentence names the two conclusions, and the new paragraph says a turn that ends to wait
      looks the same as one that ends a goal, and what to do in each case.
- [x] GAP (GREEN): "the next Stop" - immediately, or later, and when. CLOSED - one clause says that
      after a goal has ended the next Stop usually comes only after the user's next message.
- [x] GAP (both): the block's message content and the expected response. DECLINED - the block
      invokes this skill by name, and its sections on surfacing and walking the points own that.
- [x] GAP (GREEN): "scrolled past" is a metaphor. DECLINED - unchanged sentence, not what this
      change tests.
- [x] GAP (GREEN): several goals in one session. DECLINED - the hook reads the last goal record,
      as before; nothing in this change touches it.
- [x] GREEN diffed against RED in both directions: RED's one correct judgement (the work is not
      concluding) is kept in GREEN; nothing RED produced is lost.
- [x] Quote-back on the closed "next Stop" gap: a haiku probe asked when the block arrives, answer
      required as a direct quote or NONE.

## Quality

- [x] Description unchanged.
- [x] No narrative, no scratch paths, no addresses; the measurement is stated as a result.
- [x] Cross-references unchanged.

## Deployment

- [x] Hook tests green with CI's dependency set; `repo-gate.py --pre-push` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry carries the numbers.
