---
name: meta-dream-nap
description: Use for a QUICK, cheap memory consolidation of only the current directory's chain - before or right after a context compaction (the PostCompact nudge points here), when the session accumulated learning signals worth folding in NOW, or on "nap", "dream nap", "/dream-nap", "quick tidy". Minutes, not tens of minutes; for the full periodic consolidation of the whole tree use bitranox:meta-dream-tree.
---

# meta-dream-nap

The NAP: a light, frequent consolidation of ONLY the cwd's altitude chain (project -> ancestors ->
anchor). It exists because the full dream is tree-wide and heavy; skipping consolidation at a
compaction loses detail, and silently cherry-picking the full dream's steps leaves a
half-consolidated store. A nap does the chain-internal basics fast and REPORTS what it deferred.

**REQUIRED BACKGROUND:** `bitranox:meta-dream-tree` -> `references/dream-core.md` - the shared
core (mode, capture-first, backup+manifest, dedup semantics, routing prompt, verification, tiers)
lives there and applies here unchanged; this file only carries the nap's SCOPE DELTA. The storage
spec is `bitranox:meta-self-improve` -> `references/memory-backend.md`.

## Scope (the delta)

The nap's scope is the cwd's ALTITUDE CHAIN ONLY: the project level, each ancestor level, and the
anchor. SIBLING projects, sibling departments, and other trees are OUT OF SCOPE - a nap never
reads or writes them (the acceptance harness asserts they stay byte-identical). Everything
cross-sibling belongs to `bitranox:meta-dream-tree`; everything cross-tree to
`bitranox:meta-dream-crosstree`.

## When to run

- Around a context compaction: the PreCompact hook salvaged candidate learnings; nap them into
  the store while the detail is still warm (the PostCompact nudge points here).
- The session accumulated several learning signals and a full dream is not worth its cost now.
- Manual: "nap", "dream nap", "/dream-nap", "quick tidy".
- NOT a replacement for the full dream: the SessionStart consolidation-due nudge still means
  `bitranox:meta-dream-tree`.

## Procedure (all semantics per dream-core.md)

1. **Capture first** (unconditional; the audit/salvage candidates plus this session's signals) -
   via `bitranox:meta-self-improve`, at the project level.
2. **Back up + manifest** the CHAIN's levels only (per the core).
3. **Dedup within the chain**: fold near-duplicates among the chain's entries (engine `add`,
   same slug). Do not chase sibling duplicates - out of scope, the full dream's job.
4. **Chain-internal placement only**: route entries whose EVIDENCE is already clear through the
   routing prompt (in the core), applying only moves whose from AND to levels are ON the chain
   (up or down). Low/UNSURE and anything involving a sibling stays put. Pinned entries untouched.
5. **Prune the obvious**: leaked task-state and dead-content entries AT the chain's levels
   (propose-first per the removal policy).
6. **Verify + report + state the leftovers**: the core's verification contract (manifest diff,
   reconcile `TOTAL problems: 0` over the chain), then report counts AND an explicit
   "deferred to the full dream" list (sibling dedup, tree-wide placement, descriptor synthesis,
   behavioral passes, unshipped skill/hook contributions (skill-fit) queued but not delivered, and
   the toolbox pass per dream-core.md - machine-global, outside the nap's chain-only budget). A nap is PARTIAL BY DESIGN and says so - never silently incomplete.
   Run `dream_state.py done` (home: `<plugin>/skills/meta-dream-tree/dream_state.py`, via
   `hooks/run-python.sh` - see dream-core.md "Script homes") ONLY if the nudge that triggered
   you asked for a nap; a consolidation-due nudge still needs the full dream.

## Deliverables (a completed nap has ALL of these)

- [ ] Capture ran (or a verified "nothing durable" line).
- [ ] Backup + manifest of the chain's levels recorded.
- [ ] Chain-internal dedup/placement/prune applied via the engine (fail-loud success lines).
- [ ] Sibling branches and other trees untouched (nothing outside the chain was read or written).
- [ ] Manifest diff clean; reconcile `TOTAL problems: 0` over the chain.
- [ ] The report ends with the explicit DEFERRED list for the next full dream.

## Rationalizations (these do not fly)

| Excuse                                                      | Reality                                                                                         |
|-------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| "While I'm here, that sibling duplicate is one quick merge" | Out of scope by design - the sibling snapshot assertion fails and the nap becomes a slow dream. |
| "No time even for a nap - skip consolidation"               | The nap exists precisely for this budget; capture + chain dedup is minutes.                     |
| "I'll just cherry-pick the full dream's steps"              | That is the silent-partial trap the nap replaces: run the nap, get the DEFERRED list stated.    |
| "The nap ran, so consolidation is done"                     | A nap is partial by design; the consolidation-due nudge still means the full dream.             |

## Common mistakes

- Touching a sibling project/department or another tree (scope violation; harness-asserted).
- Skipping the DEFERRED list (the next full dream needs to know what a nap left behind).
- Running `dream_state.py done` after a nap that was triggered by a consolidation-due nudge
  (silences the nudge without the tree-wide work having happened).
- Restating core semantics here instead of following dream-core.md (the contract test fails
  duplicated family literals).
