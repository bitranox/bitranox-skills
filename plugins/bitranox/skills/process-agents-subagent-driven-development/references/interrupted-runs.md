# Interrupted runs

Supporting reference for `SKILL.md`, section "Interrupted Runs". The normal loop assumes every
dispatched agent ends with a report. Four things end a run, or part of it, without one; each
leaves state behind that a fresh dispatch would trample.

## Plan mode switched on while writers run

When the user switches the session into plan mode while background WRITE agents (implementers,
fixers) are running, each one is blocked at its next write. It stops BLOCKED with half-done,
UNCOMMITTED work in its checkout and its gate not run. A fresh dispatch after the plan is
approved rebuilds the context from nothing and can clobber, or commit, the half-done edits.

1. List every running writer in the progress ledger: agent id, task, checkout path, and the last
   step it reported.
2. Leave their checkouts untouched: no commit, no reset, no stash, no fresh agent working there.
3. Make "resume the blocked writers" Phase 0 of the new plan.
4. After approval, resume each by SendMessage. It keeps its context and its own notes or steps
   file, and continues from the write it was blocked at. Re-dispatch only an agent that cannot be
   resumed, and then brief the fresh agent with that checkout's `git status` and `git diff` as the
   state to finish, never as a clean start.

This is a different case from dispatching while plan mode is still on (see "Plan mode must have
ended before the first dispatch" in SKILL.md): there the agent returns a plan instead of code; here
it has already written code.

## A dispatch stopped on the usage limit

Parallel agents share the session's API limit, so when it is hit (HTTP 429, a weekly or session
limit) every running agent can stop at once, mid-task. A stopped agent's state is saved: SendMessage
resumes it once requests are accepted again, and switching to an account with headroom lifts the
stop at once.

- Prefer resuming over a fresh dispatch. The resumed agent keeps its context and skips what it
  already did; a fresh one redoes it and races the uncommitted diff the stopped one left.
- When the reset is days away and the work cannot wait, finish the item from its checkout instead
  (commits since the recorded base, `git status`, `git diff`), test-first, and run its full gate.
- No tier substitution: a stopped `opus` reviewer is resumed or re-dispatched on `opus`. No
  cheaper tier stands in for it, and `haiku` may not judge (see "Concrete tiers" in SKILL.md).
- A review YOU do inline while the reviewer is stopped is a deviation, never the gate. Log it in
  `EXECUTION-USER-REVIEW.md` and keep the task open: it counts as complete only after the resumed
  or freshly dispatched `opus` review has run and come back clean.
- Keep each stopped agent unticked in the ledger (stopped, not finished) until its work is
  resumed, taken over, or dropped by decision.

## An agent holding a borrowed or shared resource

A subagent may hold something that is not the session's own: another session's VM, a throwaway
host with an agreed window, a snapshot it took, a lock, a port. If it dies, nobody releases it,
and the failure notice can arrive while the session is idle, so the resource stays held until
someone looks.

- Before dispatch, write the exact cleanup recipe into the progress ledger: what the agent will
  take, the command that releases each item, and the deadline agreed with the owner.
- Treat ANY non-success notification from that agent (an API error, a usage limit, a crash, a
  hang past its backstop) as "take over the cleanup now": check the resource's state at once and
  release it per the recipe. Do not wait for a resume that may be hours away.
- The controller owns the cleanup, never the agent alone: an agent that cannot run any more
  cannot clean up after itself.

## A session that resumes a plan

The model gate's `plan-execution` receipt is keyed to the SESSION id. A session that picks a plan
up after a handover, a `/clear` or a restart runs without it, so a dispatch with no `model` is no
longer denied, until it arms the gate again:

    bash "$CLAUDE_PLUGIN_ROOT/hooks/run-python.sh" "$CLAUDE_PLUGIN_ROOT/hooks/skill_receipt.py" start plan-execution

Run it before the resumed session's first dispatch; `skill_receipt.py check plan-execution`
(exit 0 fresh, 1 stale or missing) shows whether this session holds one. A receipt also expires 8
hours after its latest `start`, so a longer run re-runs `start`. Then read the ledger and
`git log` before dispatching anything (see "Durable Progress" in SKILL.md).
