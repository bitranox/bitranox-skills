---
name: process-review-uncertain-decisions
description: Use after finishing a piece of work - a feature, a fix, a refactor, a plan step, a release - and before moving on, to surface the choices made along the way that are not settled. Also use on "what are you unsure about", "which decisions are shaky", "review your own decisions", or when a Stop nudge asks for a decision review.
---

# Surface the decisions you are not confident about

Work produces two kinds of decision: the ones where the answer was clear, and the ones where
you picked something and moved on because the work had to continue. Only the second kind is
worth anybody's attention, and it is the kind that never gets raised, because at the moment you
made it you had already decided.

## The question

Ask it exactly like this. It has been measured to work unchanged on a weak model as well as a
strong one, so do not elaborate it:

```text
While working on this, which important decisions / choices did you make, that you are not
confident about?

Think about this deeply, reason about all the important decisions made, and think whether these
decisions have any other great alternatives that we have not considered.

DO NOT list out the choices / decisions where we already have the best possible solution.

Only list out the decisions you are really unsure about.

answer in short, in plain english. be very concise.
```

## What makes an answer good

**The suppression is the point, not the list.** Every other review skill here pushes toward MORE
findings - severity ladders, completeness sweeps, "over-report rather than under-report". This one
pushes the other way. A reply that includes the decisions you got right has failed, however true
each line is, because the reader now has to sort the shaky ones out again.

Look for the kinds that leave no trace in a diff, because those are the ones no review catches:

- a default that changes behaviour for people who upgrade;
- a version tier, a scope cut, a "we can add that later";
- something dismissed as noise (a flaky test, an odd exit code) without being understood;
- a fix that replaces a mechanism rather than extending it, where the old one had other callers.

Name the alternative you did not take, and what would settle it. If nothing is genuinely
unsettled, say that in one line - a short honest answer is the correct output, not a failure to
find anything.

## When it fires on its own

A Stop hook watches for work concluding: a `/goal` in play, or - with no goal - a commit, a push,
or an opened PR. A goal counts whether or not it has reported met yet, because the verdict is
written while the Stop hooks are already running, so at the moment the hook looks the record still
says not-met and waiting for it costs a whole turn a finished session may never take.

It stops the session ONCE, on the first conclusion, because an ask that can be scrolled past is one
that gets scrolled past. Every conclusion after that only reminds, without blocking. That split is
what makes the early-versus-late question stop mattering: an early first ask no longer means
silence for the rest of the session, and a second block would be nagging anyway. Nothing stops you
asking earlier; the hook exists for the times nobody remembers to.

## Where the answer goes

Interactive session: say it, in the conversation, and stop. It is for the person reading.

Running unattended: append it to a git-ignored `EXECUTION-USER-REVIEW.md` at the repo root, newest
first, so the decisions you made without being able to ask are reviewable afterwards. Keep the
decisions the USER made in a separate section from the ones you made yourself - the log exists for
the second kind.

## Not the same as its neighbours

- `bitranox:process-review-verification-before-completion` asks "is my claim true", answered with
  evidence. This asks "was that the right call", answered with judgment. Both can be needed.
- `bitranox:meta-self-improve` captures durable lessons into memory for later reuse. This surfaces
  open questions for a person, now, and writes no memory.
