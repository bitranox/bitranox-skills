# Review checklist 2026-10-31: claim a pending contribution before working it

Change: the skill-fit step (10) tells a dream to claim each pending queue entry with
`contrib_queue.py claim --match <text>` and to leave one that another session holds (exit 1). The
same sentence went into meta-dream-crosstree step 7; the full rule (expiry, release, ship/drop
ignoring a claim) lives in meta-self-improve `references/upstream-propagation.md`.

## Claims and their evidence

- [x] `claim` exits 1 on another holder's live claim and names it: `test_contrib_queue.py`
      `test_a_claim_held_by_another_session_refuses_a_second_claim`, and the "held exits 2" arm of
      a 10-arm mutation battery is killed by it.

## Probes (bitranox:baseline-probe, text only, haiku, 1 round each)

- [x] RED (step 10 before the edit): "NOT COVERED" to both "what do you do before working entry
      2" and "what if another session has it".
- [x] GREEN (step 10 after the edit): quoted "Claim each one before you work it
      (`contrib_queue.py claim --match <text>`; exit 1 means another session holds it - leave it)"
      for both questions.

## Gaps declined

- How a claim is held, released or expires when its session dies: answered in
  `upstream-propagation.md`, which step 10 already routes to; repeating it here would be a second
  copy to drift.
- Whether to revisit a held entry later in the same dream: a claim expires on its own, and the
  step already says to leave one queued only for user input or `off`; judgement left to the dream.
