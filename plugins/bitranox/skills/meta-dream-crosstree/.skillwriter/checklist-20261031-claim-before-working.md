# Review checklist 2026-10-31: claim a pending contribution before working it

Change: the skill-fit step (7) tells a crosstree dream to claim each pending queue entry with
`contrib_queue.py claim --match <text>` and to leave one that another session holds (exit 1). The
same sentence went into meta-dream-tree step 10; the full rule (expiry, release, ship/drop ignoring
a claim) lives in meta-self-improve `references/upstream-propagation.md`.

## Claims and their evidence

- [x] `claim` exits 1 on another holder's live claim and names it: `test_contrib_queue.py`
      `test_a_claim_held_by_another_session_refuses_a_second_claim`, and the "held exits 2" arm of
      a 10-arm mutation battery is killed by it.

## Probes (bitranox:baseline-probe, text only, haiku, 1 round each)

- [x] RED: the identical pre-edit sentence set in meta-dream-tree step 10 answered "NOT COVERED"
      to both questions; this step's pre-edit text carries no claim step either.
- [x] GREEN (step 7 after the edit): quoted "Claim each one before you work it
      (`contrib_queue.py claim --match <text>`; exit 1 means another session holds it - leave it)"
      for "what do you do before working entry 2" and "what if another session has it".

## Gaps declined

- What to do with a held entry afterwards: a claim expires on its own and the step already says to
  leave one queued only for user input or `off`; the expiry rule is in `upstream-propagation.md`.
