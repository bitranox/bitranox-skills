# checklist - late applier handoffs after the store commit

One queued contribution: the dream-core verification contract now says an applier can keep
writing after it reports, so before calling the store committed, check `git status --porcelain`
on every slug named in a handoff received since the commit and make a follow-up commit, and it
points at the nap's rule (d) for verbatim quotes.

Decisions: d-20261120-9665e075

## RED

- [x] Skill decisions read first: two rejected entries (ref_map after a dropped move, re-deriving
      a batch after a scratch review), unrelated.
- [x] Text check of the pre-edit references/dream-core.md: "handoff received" 0 hits; the
      contract's commit rules covered peers' rows, not this run's own late writers.

## GREEN

- [x] Quote-back probe (opus, haiku): C1 answered with the new paragraph's lines.

## REFACTOR

- [x] Declined (opus, haiku): an end condition and a stop step for appliers - the rule is keyed
      on handoffs received, which is what the coordinator can observe; stopping a runaway is
      covered by the stop-runaway-subagent rule.
- [x] Declined (opus): a staging rule - the paragraph above already requires path-scoped staging.
- [x] Width, fence and ASCII checks on the added lines clean.
