# skill-writer checklist - meta-dream-tree (2026-08-01, hook hard cap refuses)

Change: one sentence in the step-6 maintenance sweep. `lint --tree` still reports hooks over the
500-char hard cap, but the cap is now enforced by refusal at the write path, so an over-cap hook
that the sweep finds arrived by hand-edit or from a legacy store and needs a rewrite rather than a
shrug. Ships with plugin 5.120.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] RED shared with the meta-self-improve arm: the pre-change text told a haiku subagent that the
      engine word-boundary-truncates past 500, which made an over-cap hook read as an ordinary
      stored state rather than an anomaly worth chasing. A dream that believes truncation is normal
      has no reason to treat a lint hit as damage.
- [x] The sweep's own wording no longer contradicts the engine. The line previously read "hooks
      over the 500-char HARD cap that `cap_hook` would truncate"; `cap_hook` no longer exists, so
      the sentence named a function the reader cannot find and predicted behaviour the engine no
      longer has.
- [x] The 350-soft-cap guidance below it is unchanged and still says NOT to rewrite a hook merely
      for exceeding 350 - the soft cap stays advisory. Only the hard-cap clause changed, so the two
      rules do not now contradict each other.
- [x] Verified against the shipped code: `lint_tree` still reports `over_cap` entries, so the sweep
      it describes still exists and still finds them; only the reason one can exist has changed.
- [x] No session narrative, no private provenance, no machine values added.
