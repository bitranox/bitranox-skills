---
name: meta-dream-global
description: The CROSS-PROJECT dream - consolidate memory ACROSS all your projects, the expensive pass that reads every project store. Use on "dream global", "/dream-global", "consolidate across projects", "global consolidation", or occasionally after several per-project dreams. Scans all project memory stores for recurring / broadly-useful knowledge and factors it up to the global ~/.claude/rules/bitranox/ layer (or the lowest common ancestor), pulls sibling-tree knowledge into projects (inbound gather), and cross-pollinates outward - all via lift-or-copy, never a cross-tree reference. For one project's routine tidy use bitranox:meta-dream-project. Honors an off/auto/propose mode.
---

# meta-dream-global

The cross-project dream. `bitranox:meta-dream-project` tidies ONE project's store and is the frequent,
cheap pass; **meta-dream-global is the occasional, EXPENSIVE pass that reads across ALL project stores**
to move knowledge between trees that the native cascade cannot reach. Native cascade only flows down one
ancestor chain + the global layer, so knowledge filed in a sibling tree is invisible elsewhere; this
skill bridges that. It builds on `bitranox:meta-self-improve` (altitude logic, the upstream-PR loop,
`reconcile_memory_index.py`) and delegates inbound gather to `bitranox:meta-collect-knowledge`; follow
those for the primitives. Do not duplicate per-project consolidation here - run meta-dream-project for
that first if a project's own store is messy.

**It must SHRINK noise, never add it**, and it moves knowledge ONLY by lift-or-copy - **NEVER a
cross-tree reference** (a sideways pointer dangles when the other tree is deleted).

## Mode

Same machine-local config as the project dream (`self_improve_signals.load_config()`; legacy
`.bitranox-dream-off` / `.bitranox-dream-auto` sentinels still apply until it exists):

- **`propose`** (default): apply the safe machine-local moves (the global `~/.claude/rules/bitranox/`
  layer and private project memory), but ASK before editing a version-controlled `CLAUDE.md` and route
  any skill change to a self-PR.
- **`auto`**: apply `CLAUDE.md` edits and ship skill changes without per-change prompts.
- **`off`**: skip this skill entirely (no cross-project consolidation, no nudges).

## When to run

- **Manual / occasional.** "dream global", "/dream-global", "consolidate across projects". There is no
  per-session nudge for this (it is heavy); run it deliberately - a good cadence is after several
  per-project dreams, or when you know two projects have learned related things.
- **Honor the `privacy` knob.** With `walled`, gather and promote ONLY within one privacy domain
  (e.g. do not lift a note from a private/client subtree into the loads-everywhere global layer); the
  default (open) does a light secret/PII scrub and otherwise propagates concrete operational knowledge
  freely.

## Procedure

Create one todo per step.

1. **Back up first.** Snapshot every store this run may touch (the global `~/.claude/rules/bitranox/`
   layer and any project memory dir you will write) to timestamped copies before any edit. The
   one-time whole-store backup is the safety net; this is the per-run one.
2. **Inbound gather (delegate).** For each project that should be enriched, run
   `bitranox:meta-collect-knowledge` (the grep -> inspect -> gather funnel): pull knowledge from OTHER
   trees relevant to that project and bring it in by **lifting broadly-useful hits to a common ancestor**
   or writing a **self-contained local copy** (marked so it is not re-promoted; scrubbed). Single source
   of truth - do not re-implement the funnel here.
3. **Global-dream scan (the cross-project read).** Scan ACROSS project memory stores for recurring or
   broadly-useful content and factor it up to the lowest covering altitude. **FAN OUT:** one **`sonnet`**
   subagent per project store (read it, return recurring / broadly-useful candidate entries), in
   parallel, to keep N stores out of the main context; reserve **`opus`** (the main agent) for the
   promotion-gate and the altitude / normalization decisions. (Tiers: "Concrete tiers" in
   `bitranox:process-agents-subagent-driven-development`.)
4. **Promotion gate (cross-project corroboration).** A promotion to the global layer loads into EVERY
   session, so it is high-blast. Here the gate may use the **cross-project corroboration** path - a
   model-inferred generalization promotes once it is seen in **>= 2 distinct projects** (vs the
   same-project >= 2-dreams dwell that meta-dream-project uses). A USER-stated concrete rule still
   promotes eagerly. Keep promoted rules CONCRETE (never water down a concrete-but-universal rule);
   abstract only when the specifics fit nowhere else. `should_promote` / `note_promotion_candidate` in
   `self_improve_signals.py`; counters live OUT of the dreamed store so a converged re-run is a no-op.
5. **Outbound cross-pollination.** When a learning is useful BEYOND its project, do not write into other
   projects - **promote it to the lowest common ancestor** (often the global layer) and let the native
   downward cascade deliver it; a project in a DIFFERENT subtree receives it via ITS inbound gather. A
   direct self-contained copy into one specific other project is the rare exception (marked so a later
   dream does not re-promote it; scrubbed; never a cross-tree ref).
6. **Re-dedup after promotion (the required final sweep), then reconcile.** Promotion is what CREATES
   the duplication: every rule lifted to a common ancestor or global now overlaps the note it came from
   AND any sibling note across the stores that holds the same lesson. So after promoting, sweep ALL
   affected stores and normalize each overlapping lower entry to `references [[general]]` + its delta -
   the general lives ONCE at its altitude, UPWARD-only. This is not optional and not covered by any
   earlier dedup: those ran before the promotions existed. (Per-note bytes may be a wash; the win is one
   source of truth instead of the general restated in every project.) Then run
   `reconcile_memory_index.py --check <altitude-chain>` over the affected chains to verify reference
   integrity (no orphans, no DOWNWARD or cross-tree refs, no over-cap).
7. **Skill-fit -> batched change.** A generalization that warrants a skill goes through
   `bitranox:meta-self-improve` -> "Propagating skill (or hook) improvements upstream" (self-PR in
   `propose`, commit-or-PR in `auto`, skipped in `off`).
8. **Report.** Counts: stores scanned, items gathered (lift vs local copy), promotions to global,
   cross-pollinations, normalizations, any CLAUDE.md edits (applied or proposed), and any skill change.

## Convergence

A second global dream on an already-converged set of stores must write nothing: corroboration / gather
counters live OUT of the dreamed stores; a content-hash stops re-copying an item already present up the
ancestor chain; gathered copies are marked exempt from re-promotion AND re-gather. If a run keeps
re-moving the same item, stop and treat it as a bug (the circle-breaker), do not loop.

## Boundaries

- **The global `~/.claude/rules/bitranox/` layer + private project memory (machine-local):** back up,
  then apply.
- **CLAUDE.md (version-controlled):** propose-first in `propose`, apply in `auto`, only through the
  sanctioned bounded paths (CLAUDE.md policy in `bitranox:meta-self-improve`).
- **Skills / hooks (shared, public):** never silently edit; route through the upstream-PR loop.
- **Never a cross-tree reference.** Bridge trees only by lift-to-common-ancestor or a self-contained
  copy. A sideways or downward pointer dangles when the lower / sibling tree is deleted.

## Common mistakes

- Running this every time instead of occasionally - it is the expensive pass; the routine tidy is
  `bitranox:meta-dream-project`.
- A cross-tree or downward reference instead of lift-or-copy.
- Promoting a model-inferred rule to global on first sight (it needs >= 2-project corroboration).
- Over-broadening: watering a concrete-but-universal rule into a vague principle, or globalizing a
  narrowly-applicable one (it then loads in every session for nothing).
- Ignoring the `privacy` knob and lifting a domain-private note into the loads-everywhere global layer.
