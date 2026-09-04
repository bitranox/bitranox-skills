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

**The one carve-out is CAPTURE (step 1), and only at the level that OWNS the fact's pointer.**
Capture routes by SUBJECT, and `meta-self-improve`'s dedup rule requires an existing fact to be
upserted at its owning level - which is sometimes a sibling. Without the carve-out a nap that
learns something about a sibling-owned fact has only bad options: mint a duplicate at the cwd,
which that same rule forbids, or drop the signal. Neither is what "chain-only" is protecting. So
capture may write at a sibling; steps 2b through 6 may not, and nothing here licenses READING a
sibling's entries to consolidate them. Cross-tree stays closed even to capture - `move` cannot
cross trees, so a misfiled fact there is unrecoverable.

The acceptance harness's `SIBLINGS` assertion hashes sibling POINTER files, which cannot tell a
capture from a consolidation touch. It does not contradict the carve-out because its fixture plants
no sibling-owned capture, so the only thing that can move those hashes is a consolidation pass. Keep
it that way: if the fixture ever gains one, narrow the assertion to the consolidation steps rather
than deleting it.

## When to run

- Around a context compaction: the PreCompact hook salvaged candidate learnings; nap them into
  the store while the detail is still warm (the PostCompact nudge points here).
- The session accumulated several learning signals and a full dream is not worth its cost now.
- Manual: "nap", "dream nap", "/dream-nap", "quick tidy".
- NOT a replacement for the full dream: the SessionStart consolidation-due nudge still means
  `bitranox:meta-dream-tree`.

## Procedure (all semantics per dream-core.md)

1. **Capture first** (unconditional; the audit/salvage candidates plus this session's signals,
   plus every line under `## Lessons for the next nap` in the repo's `handover.md` - a work
   session records its lessons there and does NOT capture them itself, so this is where they
   enter the store) - via `bitranox:meta-self-improve`, at the level that OWNS each fact's
   pointer (see the Scope carve-out: this is the one step that may write a sibling, and only for
   that reason).
2. **Back up + manifest** the CHAIN's levels only (per the core).
2b. **Read the toolbox inventory** - `uv run ~/.claude/skills/toolbox/tools/toolbox.py list`, the
   READ half of the toolbox pass (per the core); skip only if that path does not exist. It runs
   HERE, before steps 3-5, because those are the passes whose scans a shipped tool has often
   already implemented and calibrated - check the names before hand-rolling any scan below.
   Deferring "the toolbox pass" defers the CONSOLIDATE half only, never this read.
3. **Dedup within the chain**: fold near-duplicates among the chain's entries (engine `add`,
   same slug). Do not chase sibling duplicates - out of scope, the full dream's job.
4. **Chain-internal placement only**: route entries whose EVIDENCE is already clear through the
   routing prompt (in the core), applying only moves whose from AND to levels are ON the chain
   (up or down). Low/UNSURE and anything involving a sibling stays put. A pinned fact re-levels
   like any other entry, pin intact; only its CONTENT is out of reach (per the core's Boundaries).
5. **Prune the obvious**: leaked task-state and dead-content entries AT the chain's levels
   (propose-first per the removal policy in `bitranox:meta-dream-tree` -> references/dream-passes.md).
6. **Verify + report + state the leftovers**: the core's verification contract (manifest diff,
   reconcile `TOTAL problems: 0` over the chain), then report counts AND an explicit
   "deferred to the full dream" list (sibling dedup, tree-wide placement, descriptor synthesis,
   behavioral passes, unshipped skill/hook contributions (skill-fit) queued but not delivered, and
   the toolbox CONSOLIDATE half per dream-core.md - machine-global, outside the nap's chain-only
   budget; its READ half already ran at step 2b). A nap is PARTIAL BY DESIGN and says so - never silently incomplete.
   Run `dream_state.py done` (home: `<plugin>/skills/meta-dream-tree/dream_state.py`, via
   `hooks/run-python.sh` - see dream-core.md "Script homes") ONLY if the nudge that triggered
   you asked for a nap; a consolidation-due nudge still needs the full dream.

## Deliverables (a completed nap has ALL of these)

- [ ] Capture ran (or a verified "nothing durable" line).
- [ ] Backup + manifest of the chain's levels recorded.
- [ ] Toolbox inventory read BEFORE the dedup/placement/prune passes (or the path confirmed absent).
- [ ] Chain-internal dedup/placement/prune applied via the engine (fail-loud success lines).
- [ ] Sibling branches and other trees untouched by steps 2b-6 (the capture carve-out is the only
      write allowed outside the chain, and only at a fact's owning level - name it in the report).
- [ ] Manifest diff clean; reconcile `TOTAL problems: 0` over the chain.
- [ ] The report ends with the explicit DEFERRED list for the next full dream.

## Rationalizations (these do not fly)

| Excuse                                                      | Reality                                                                                                        |
|-------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| "While I'm here, that sibling duplicate is one quick merge" | Out of scope by design - the sibling snapshot assertion fails and the nap becomes a slow dream.                |
| "No time even for a nap - skip consolidation"               | The nap exists precisely for this budget; capture + chain dedup is minutes.                                    |
| "I'll just cherry-pick the full dream's steps"              | That is the silent-partial trap the nap replaces: run the nap, get the DEFERRED list stated.                   |
| "The nap ran, so consolidation is done"                     | A nap is partial by design; the consolidation-due nudge still means the full dream.                            |
| "The toolbox pass is deferred, so skip the list"            | Deferred means the CONSOLIDATE half. The READ is step 2b and guards steps 3-5. One command.                    |
| "A quick regex is faster than finding the right tool"       | Measured twice: the hand-rolled scan missed state the tool persists, and its clean result read as reassurance. |

## Common mistakes

- Touching a sibling project/department or another tree (scope violation; harness-asserted).
- Skipping the DEFERRED list (the next full dream needs to know what a nap left behind).
- Running `dream_state.py done` after a nap that was triggered by a consolidation-due nudge
  (silences the nudge without the tree-wide work having happened).
- Restating core semantics here instead of following dream-core.md (the contract test fails
  duplicated family literals).
