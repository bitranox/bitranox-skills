---
name: meta-dream-crosstree
description: Use on "dream crosstree", "/dream-crosstree", "consolidate across projects", "global consolidation", occasionally after several per-project dreams, or when two projects or knowledge trees have learned related things that should be shared. This is the expensive cross-project/cross-tree pass reading every store; for one project's routine tidy use bitranox:meta-dream-tree. Honors an off/auto/propose mode. Formerly named meta-dream-global - answers to that name too.
---

# meta-dream-crosstree

The cross-project dream. `bitranox:meta-dream-tree` tidies ONE project's store, stays inside ONE
knowledge tree, and is the frequent, cheap pass; **meta-dream-crosstree is the occasional, EXPENSIVE
pass that reads across ALL project stores - and it is the ONLY dream whose territory spans
INDEPENDENT KNOWLEDGE TREES** (a machine can carry several tree tops; the project dream never
crosses them). Cascade only flows down one ancestor chain, so knowledge filed in a sibling project
or another tree is invisible elsewhere; this skill bridges that. Tree discovery runs over the
configured `discovery_roots` (`tree-top` / `ensure-all-trees` locate the tops). It builds on `bitranox:meta-self-improve` (altitude logic, the upstream-PR loop,
`reconcile_memory_index.py` - home: `<plugin>/skills/meta-self-improve/`, launch via
`hooks/run-python.sh`) and delegates inbound gather to `bitranox:meta-collect-knowledge`; follow
those for the primitives. Do not duplicate per-project consolidation here - run meta-dream-tree for
that first if a project's own store is messy.

**It must SHRINK noise, never add it**, and it moves knowledge ONLY by lift-or-copy - **NEVER a
cross-tree reference** (a sideways pointer dangles when the other tree is deleted).

## Mode

Read the mode per `bitranox:meta-dream-tree` -> references/dream-core.md (propose / auto /
off - the knob semantics live ONLY there); `off` skips this skill entirely.

## When to run

- **Manual / occasional.** "dream crosstree", "/dream-crosstree", "consolidate across projects". There is no
  per-session nudge for this (it is heavy); run it deliberately - a good cadence is after several
  per-project dreams, or when you know two projects have learned related things.
- **Honor the `privacy` knob.** With `walled`, gather and promote ONLY within one privacy domain
  (e.g. do not lift a note from a private/client subtree into a tree top that loads everywhere under it); the
  default (open) does a light secret/PII scrub and otherwise propagates concrete operational knowledge
  freely.

## Procedure

Create one todo per step.

0. **Capture first, reading the session from DISK** - the shared rule in
   `bitranox:meta-dream-tree` -> references/dream-core.md "Capture-first" applies here too (it is
   the shared core for EVERY consolidation skill, not just nap/tree). Run
   `dream_state.py session-review "<cwd>"` before consolidating: your context is not the session (a
   compaction clears the context, never the transcript file), and it also surfaces the SUBAGENT
   learnings and the touched-path routing evidence you would otherwise never see. Finish with
   `dream_state.py session-reviewed "<cwd>"`. It is incremental and the watermark is shared with the
   other dream modes, so if a nap already reviewed this session this costs nothing.
1. **Back up first.** Snapshot every store this run may touch - each affected tree's TOP store and, for any level you will write, the anchor's central
   `.claude-memory/` note bodies + that level's `CLAUDE.local.md` pointer block (+ native `memory/`) - to
   timestamped copies OUT of the project trees (`~/.claude/self-improve-audit/backups/`, so a backup is
   never re-discovered as live memory) before any edit. Curated writes go through the engine, not a
   hand-edit. The one-time whole-store backup is the safety net; this is the per-run one.
2. **Inbound gather (delegate).** For each project that should be enriched, run
   `bitranox:meta-collect-knowledge` (the grep -> inspect -> gather funnel): pull knowledge from OTHER
   trees relevant to that project and bring it in by **lifting broadly-useful hits to a common ancestor**
   or writing a **self-contained local copy** (marked so it is not re-promoted; scrubbed). Single source
   of truth - do not re-implement the funnel here.
3. **Cheap convergence pre-check, THEN ask before the deep scan.** The cross-project semantic read (the
   fan-out below) is the expensive part - dozens of subagents. Do NOT run it unconditionally. First the
   cheap, deterministic pass: which stores changed since the last global dream, `reconcile_memory_index.py
   --check` over the altitude chains (the LEVEL dirs; orphans / downward; index size is an advisory warning),
   `model_review_due()`, any pending
   filler queue. If nothing material changed since the last run, report convergence and STOP - a global
   dream that writes nothing is the correct outcome. Only if there is genuinely new cross-project material
   (or the user wants a fresh deep read), **ASK the user before launching the fan-out**. For an
   always-run deep semantic scan with no asking, that is its own skill: `bitranox:meta-dream-crosstree-deep`.
   - **Deep scan (on confirmation): FAN OUT** one **`sonnet`** subagent per project store (or per thematic
     batch for many stores), in parallel, each returning recurring / broadly-useful candidate entries.
     Instruct each subagent to flag a DUPLICATE/MERGE only from the BODIES (not a title/topic match),
     and treat every such finding as a CANDIDATE the main agent VERIFIES before merging (see "Dedup
     semantics" in references/dream-core.md: a summary+detail pair, a valid cross-link, or a
     cited-across-a-subtree fact is not a duplicate). Keep the promotion gate and altitude /
     normalization decisions INLINE on the main agent at
     opus-class OR ABOVE (opus is the universally-available deep tier; fable sits above it but
     needs paid API credits) - if the session is below opus-class, offer switch-model-or-continue
     per "The session model is fixed" in `bitranox:process-agents-subagent-driven-development`
     (a /model switch keeps the conversation; the main agent cannot self-switch). (Tiers:
     "Concrete tiers" in the same skill.)
4. **Promotion gate (corroboration + dedup against CLAUDE.md).** A promotion to a tree's TOP loads into every
   session UNDER THAT TREE, so it is high-blast. Gate by **cross-project corroboration** - a model-inferred
   generalization promotes once seen in **>= 2 distinct projects** (vs the same-project >= 2-dreams dwell
   meta-dream-tree uses); a USER-stated concrete rule promotes eagerly. **Before promoting, dedup the
   candidate against the existing global layer, the shipped skills, AND every `CLAUDE.md` in the tree**
   (project roots + ancestors + the workspace), not only the memory stores - during the conversion phase
   many rules still live in `CLAUDE.md`, and promoting one that is already there would DUPLICATE it.
   Classify each candidate: already-global/skill -> skip; already in a `CLAUDE.md` -> do NOT just
   duplicate-avoid, ROUTE it through the CLAUDE.md reconciliation model (delete the lower copy if a
   broader tier covers it / lift it up and leave only the delta / keep it if it is genuinely local),
   and across trees CONSOLIDATE the same rule duplicated in many sibling `CLAUDE.md` UP to their common
   ancestor - the highest-leverage context saving; new + corroborated + nowhere-else -> promote. (The
   case model + guards live in `bitranox:meta-dream-tree` "CLAUDE.md reconciliation"; every
   `CLAUDE.md` edit stays propose-first and never happens without user confirmation.) Keep promoted
   rules CONCRETE (never water a
   concrete-but-universal rule down); abstract only when specifics fit nowhere else. Gate the
   corroboration the same way as the tree dream: `dream_state.py saw-promotable <slug>` to record a
   sighting, `dream_state.py should-promote <slug>` (`promote`/`hold`), `dream_state.py promoted <slug>`
   to clear after an applied promotion (home: `<plugin>/skills/meta-dream-tree/`; the counters are the
   `self_improve_signals.py` dwell store, OUT of the dreamed store so a converged re-run is a no-op).
4b. **Misplacement audit (wrong-TREE facts).** ONLY the cross-tree modes can see this: a fact
   captured while cwd was another repo lands in the WRONG tree's store, and nothing in that tree's
   own integrity checks knows it is foreign (`meta-dream-tree` sees one tree and structurally
   cannot notice). Run `reconcile_memory_index.py --check-misplaced <anchor>` per tree (home:
   `<plugin>/skills/meta-self-improve/`): it reports facts whose body cites ONLY another tree's
   paths, plus the exact `relocate` command. A path mention is EVIDENCE, not proof - a fact may
   legitimately cite a neighbour - so JUDGE each candidate against its body before acting; expect
   to reject some. For a confirmed misfile use the engine's `relocate` verb (NOT a copy: a copy
   leaves the stale original, which is the bug). Propose-first in `propose`; apply in `auto`.

5. **Outbound cross-pollination.** When a learning is useful BEYOND its project, do not write into other
   projects - **promote it to the lowest common ancestor WITHIN ITS TREE** (often the tree's top) and let the native
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
   `reconcile_memory_index.py --check <altitude-chain>` (the LEVEL dirs) over the affected chains to verify reference
   integrity (no orphans, no DOWNWARD or cross-tree refs; index size is an advisory warning, not a
   failure), AND `reconcile_memory_index.py --check-tree <anchor>` per affected tree for
   `TOTAL tree problems: 0` - promotion to a common ancestor is exactly what can leave a slug pointed
   at from two levels, which the chain-only `--check` cannot see.
7. **Skill-fit -> batched change.** FIRST `contrib_queue.py list` (home:
   `<plugin>/skills/meta-self-improve/`) - contributions earlier sessions judged shippable but never
   shipped are part of THIS batch. QUEUE each new one as you find it (`contrib_queue.py add --what ...
   --target skill:<name> --why ...`) so it survives this session, then deliver via
   `bitranox:meta-self-improve` -> "Propagating skill (or hook) improvements upstream" (self-PR in
   `propose`, commit-or-PR in `auto`, skipped in `off`). `contrib_queue.py drain` ONLY for what
   actually shipped.
7b. **Toolbox pass (contribute; PROPOSE-ONLY).** Run the CONTRIBUTE delta per
   `bitranox:meta-dream-tree` -> references/dream-core.md "Toolbox pass": list the local toolbox
   (`uv run ~/.claude/skills/toolbox/tools/toolbox.py list`), judge which tools are broadly useful to
   OTHER users -> propose contributing upstream via `contrib_queue` + the upstream loop, and surface a
   chore that recurred across MANY sessions (the cross-session view a single turn misses) -> propose a
   NEW tool. Detect + propose ONLY; tools stay LOCAL by default; the build runs TDD through
   `bitranox:meta-self-improve`'s tool endpoint. Skip if the toolbox path does not exist.
8. **Report.** Counts: stores scanned, items gathered (lift vs local copy), promotions to global,
   cross-pollinations, normalizations, any CLAUDE.md edits (applied or proposed), any skill change,
   toolbox proposals (contribute / new tool), and the pending-contribution count still queued.

## Convergence

A second global dream on an already-converged set of stores must write nothing: corroboration / gather
counters live OUT of the dreamed stores; a content-hash stops re-copying an item already present up the
ancestor chain; gathered copies are marked exempt from re-promotion AND re-gather. If a run keeps
re-moving the same item, stop and treat it as a bug (the circle-breaker), do not loop.

## Boundaries

- **Tree-top curated stores + private project memory:** back up, then apply.
- **CLAUDE.md (version-controlled):** propose-first in `propose`, apply in `auto`, only through the
  sanctioned bounded paths (CLAUDE.md policy in `bitranox:meta-self-improve`).
- **Skills / hooks (shared, public):** never silently edit; route through the upstream-PR loop.
- **Never a cross-tree reference.** Bridge trees only by lift-to-common-ancestor or a self-contained
  copy. A sideways or downward pointer dangles when the lower / sibling tree is deleted.

## Common mistakes

- Running this every time instead of occasionally - it is the expensive pass; the routine tidy is
  `bitranox:meta-dream-tree`.
- A cross-tree or downward reference instead of lift-or-copy.
- Promoting a model-inferred rule to a tree top on first sight (it needs >= 2-project corroboration).
- Over-broadening: watering a concrete-but-universal rule into a vague principle, or globalizing a
  narrowly-applicable one (it then loads in every session for nothing).
- Ignoring the `privacy` knob and lifting a domain-private note into a tree top that loads everywhere under it.
