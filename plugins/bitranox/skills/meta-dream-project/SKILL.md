---
name: meta-dream-project
description: Consolidate the CURRENT project's memory like sleep - periodically, when memory has grown, or before context compaction would lose detail - and on "dream", "dream project", "/dream-project", "consolidate memory", "tidy memory", or when the SessionStart nudge says a consolidation is due. Runs AFTER per-turn capture (bitranox:meta-self-improve): dedups/merges/generalizes/re-wires/prunes this project's curated .claude-bx-selflearning store (de-doubling it against the native raw tier) and the session, promotes broadly-useful rules (kept concrete) to the right-altitude home - the global curated store at ~/.claude (.claude-bx-selflearning/) or, for a must-hold intermediate rule, CLAUDE.md - and batches skill-worthy generalizations into one self-PR. For the cross-project / global scan use bitranox:meta-dream-global. Honors an off/auto/propose mode.
---

# meta-dream-project

Memory consolidation for the CURRENT project, the way a brain reorganizes during sleep.
`bitranox:meta-self-improve` is the fast per-turn CAPTURE (note each learning as it happens).
**meta-dream-project is the periodic, batch CONSOLIDATION on top, scoped to this project:** take this
project's WHOLE memory store plus the session and dedup, merge, generalize, re-categorize, re-wire
(cross-link), prune detail, and refine concepts - so memory gets smaller and sharper, not bigger. It
extends `bitranox:meta-self-improve` (its lanes, the step-3b altitude logic, the upstream-PR loop, the
native-memory backend rules, `reconcile_memory_index.py`); follow that skill for the primitives, this
one for the batch pass. Do not duplicate its content.

This is the FREQUENT, cheap dream (one project). The EXPENSIVE cross-project work - reading across all
project stores, the global-dream scan, inbound gather, outbound cross-pollination - lives in the
separate `bitranox:meta-dream-global` skill; run that occasionally, not every time.

**The consolidation must SHRINK noise, never add it.** If a pass would grow the store, it is wrong.

## Mode (user can switch off the asking)

Read the mode first (or run `dream_state.py mode`). The mode (and the other knobs: privacy, promotion
eagerness, forgetting, nudges) live in one machine-local config `~/.claude/.bitranox-memory.json`
(`self_improve_signals.load_config()`); until that file exists the legacy `.bitranox-dream-off` /
`.bitranox-dream-auto` sentinels still apply (one-way migration). The values:

- **`propose`** (default): apply the safe private-memory consolidation, but ASK before editing a
  version-controlled CLAUDE.md and route skill changes to a self-PR for review. End the run by
  telling the user they can switch off the asking: `touch ~/.claude/.bitranox-dream-auto` for auto
  mode, or `touch ~/.claude/.bitranox-dream-off` to disable dreams.
- **`auto`** (`~/.claude/.bitranox-dream-auto`): the proposals are annoying, so do not ask - apply
  CLAUDE.md edits directly and ship skill changes (commit or self-PR) without per-change prompts.
- **`off`** (`~/.claude/.bitranox-dream-off`): no nudges; a manual dream consolidates PRIVATE MEMORY
  ONLY and skips all CLAUDE.md and skill proposals.

## When to run

- **Nudged when due:** the SessionStart hook surfaces "a memory consolidation is due" (threshold:
  memory changed since the last dream and the last dream is old). Run it then, or say "skip".
- **Around compaction:** the PreCompact hook salvages candidate learnings from the still-full
  transcript and PostCompact nudges you to capture/consolidate them - run a dream then so detail is
  not lost. (A hook cannot run the model, so it can only salvage + nudge; you do the dream.)
- **Manual:** "dream", "dream project", "/dream-project", "consolidate memory".

Check due-ness with `python3 <this-skill-dir>/dream_state.py due`; you do not need to dream if it
says `not-due` and nothing notable happened.

## Procedure

Create one todo per step.

1. **Capture first.** If the gate/audit flagged anything this session, run `bitranox:meta-self-improve`
   so the dream consolidates a COMPLETE store, not a half-captured one.
2. **Back up** BOTH tiers to a timestamped copy OUT of the project tree before any edit (so a backup
   is never re-discovered as live memory): `cp -r <proj>/.claude-bx-selflearning
   ~/.claude/self-improve-audit/backups/<key>-<ts>/curated` and `cp -r ~/.claude/projects/<proj>/memory
   ~/.claude/self-improve-audit/backups/<key>-<ts>/native`.
3. **Load** the curated store (`.claude-bx-selflearning/index.md` + `facts/`) AND the native raw tier
   (`~/.claude/projects/<proj>/memory/` MEMORY.md + topic files). Also skim the session (transcript
   tail / the `remember` buffer) for durable items not yet captured.
3b. **De-double the two tiers (curated + native).** A fact must live in exactly ONE tier. For each
   native entry, decide by provenance (a curated entry's `bx:src` set) and, failing that, a
   title/normalized-hook match: (a) if it is already in the curated store, DROP the native duplicate
   (keep the curated copy); (b) if it is native-only and worthwhile, PROMOTE it into the curated store
   via the engine (`memory_engine.py add ...`, merging its slug into `--source`); (c) if it is
   native-only but only some-value, LEAVE it in native (a legitimate raw tier). This keeps the union
   in context with no doubling. All curated writes go through the engine, never a hand-edit.
4. **Dedup / merge.** Fold near-duplicate or overlapping entries into one sharpened entry; update the
   index line; cross-link related entries with `[[name]]`. Edit-over-append (the core anti-bloat rule).
   Dedup runs TWICE: here on the as-loaded store, and AGAIN in step 8 - because promoting in step 5
   CREATES new overlap (a lifted general now duplicates what it came from, and may overlap siblings).
5. **Promote by SCOPE; NORMALIZE, don't duplicate.** Lift each learning to the narrowest always-present
   home whose scope it covers: per-project memory; broadly-useful -> the global curated store at
   `~/.claude` (`.claude-bx-selflearning/`, @imported by `~/.claude/CLAUDE.md`) KEPT CONCRETE (never
   water down a concrete-but-universal rule like fleet SSH access); a must-hold intermediate-subtree
   rule -> that level's `CLAUDE.md`. Promote by APPLICABILITY, not abstractness; abstract only when the
   specifics fit nowhere else.
   - **Reference + delta:** when a general and a specific overlap, keep the general ONCE at its altitude
     and have the lower entry `references [[general]]` + only its delta - they compose at load, never
     duplicated. **References point UPWARD only** (deleting a project must never dangle a higher entry).
     This holds ACROSS ALL CURATED altitudes, INCLUDING global (each has its own `index.md`). The
     global altitude is now a normal curated store: promotion into `~/.claude/.claude-bx-selflearning/`
     goes through the write engine exactly like any other altitude (an `index.md` hook + a lazy
     `facts/` body, de-doubled from the lower tier), NOT a loose whole-loaded `.md`. Do NOT write into
     or recreate the old `~/.claude/rules/bitranox/` loose layer - it was converted to this store.
   - **Point a rule at its skill; do not restate it.** During consolidation, check each rule fact for a
     bitranox SKILL that already covers its topic (input sanitization -> `bitranox:coding-input-sanitization`,
     resilience/self-healing -> `coding-resilience`, writing/reply tells -> `write-humanize-en`/`-de`,
     shell traps -> `compuse-bash`, remote PowerShell/SSH -> `compuse-ssh`). If one matches, keep the
     always-loaded hook as the trigger and make the body a CONCISE POINTER to that skill (`Detail:
     bitranox:<skill>`) instead of duplicating the skill's content. The dream does not delete such a
     rule (the always-on hook is its value), it just keeps the body from drifting into a skill copy.
   - **Promotion to the global layer is gated** (it loads in EVERY session): a USER-stated concrete rule
     promotes eagerly; a model-INFERRED generalization needs corroboration across >= 2 dreams first
     (`should_promote` / `note_promotion_candidate` in `self_improve_signals.py`; the `promotion` config
     knob). Those counters live OUT of the dreamed store, so gating never breaks convergence (step 11).
   - **Dedup the promotion against `CLAUDE.md`, not just memory.** Before lifting a rule to global, grep
     it against the project root + ancestor `CLAUDE.md` (and the global layer); during the conversion
     phase many rules still live in `CLAUDE.md`, so promoting one already there would DUPLICATE it. If
     it is already in a `CLAUDE.md`, do NOT duplicate - FLAG it (a possible declutter) and never edit
     `CLAUDE.md` without user confirmation.
   - The global rules layer is machine-local -> auto-apply; editing a version-controlled `CLAUDE.md` is
     propose-first (auto in `auto` mode), and only through the sanctioned bounded paths (step-3b /
     CLAUDE.md policy in `bitranox:meta-self-improve`).
6. **Re-categorize / re-wire.** Move entries to the right layer/altitude; add cross-links; drop stale
   or superseded ones.
7. **Prune.** Remove unimportant detail, leaked task-state, and obsolete entries (the backup makes
   this safe). Refine wording: state the fact and the why, nothing more.
8. **Re-dedup after promotion, then reconcile + check references.** FIRST, because promotion (step 5)
   created overlap, sweep the notes it touched - the promoted-from note AND any sibling that now
   overlaps a newly-promoted general - and normalize each to `references [[general]] + delta` (the
   general lives ONCE, upward-only). Do NOT skip this on the assumption step 4 already deduped: step 4
   ran before the promotions existed. (Net per-note bytes may be a wash; the win is one source of truth,
   not restating the general in every note.) THEN run `reconcile_memory_index.py <proj>/.claude-bx-selflearning`
   to backfill any `facts/` orphan, and `reconcile_memory_index.py --check <altitude-chain>` (the chain
   from `self_improve_signals.altitude_chain(proj)`, which is the curated dirs + global) to verify
   reference integrity and caps. Fix anything flagged: re-point a DOWNWARD ref upward, resolve an orphan,
   and route an over-cap `index.md`'s overflow by moving inline fact bodies OUT to `facts/` (shrinking
   the always-loaded index) - NEVER into the `@import` file (`CLAUDE.local.md`/`CLAUDE.md`, which holds
   only the one `@import` line), and a
   PINNED-budget overflow fails loud (re-examine what is pinned).
9. **Skill-fit -> batched change.** Collect generalizations that match or warrant a skill. Deliver
   them through `bitranox:meta-self-improve` -> "Propagating skill (or hook) improvements upstream":
   adjust an existing skill when it fits, propose a new one (via `bitranox:skill-writer`) when it does
   not. Batch them into ONE structured change - secret/PII scan, `plugin.json` bump, repo-gate green,
   structured title/body. In `propose`/default, route as a **self-PR** for review; in `auto`, commit
   or self-PR without asking; in `off`, skip skill changes entirely.
10. **Mark done + report, then nudge `/clear`.** Run `python3 <this-skill-dir>/dream_state.py done` to
    silence the nudge until a real fact changes again (it records the fact SIGNATURE, not just a
    timestamp). Then report: counts and one line each for merges / generalizations / prunes, any
    CLAUDE.md edits (applied or proposed), and the skill change (PR link or proposal). In `propose`
    mode, remind the user they can enable `auto` to stop the asking, or `off` to disable. **Finally,
    nudge the user to `/clear`** (or reload): memory files are re-read only at session start, so the
    consolidated store loads next session - and state plainly that NOT clearing loses nothing (this
    session already holds the pre-dream knowledge); clearing just refreshes to the tidied, de-doubled,
    newly-promoted form and frees context.

## Behavioral passes (demotion, forgetting, override, CLAUDE.md reconciliation)

Part of a full dream, all with **out-of-store counters** so a no-change dream stays a no-op (step 11):

- **Demotion (re-file over-promoted entries).** If a global/high entry turns out to apply to only one
  project, move it back down - but NEVER if lower entries still point UP at it
  (`reconcile_memory_index.has_inbound_refs`), and apply the SAME dwell/hysteresis as promotion
  (`note_promotion_candidate`) so a boundary entry cannot promote/demote on alternate dreams.
- **Removal = obsolete-pruning + manual (NO usage/age/size decay).** There is no automatic forgetting:
  usage cannot be measured (a note sits in context; reasoning is silent, so absence of a signal does NOT
  mean unused), and age and detail/size are not valid forget metrics. Detail belongs in the pulled body
  (representation), near-free, never a delete reason. The ONLY removals, all content-based + propose-first
  (the backup makes them safe): (1) dedup/merge duplicates; (2) **obsolete/superseded pruning** - read a
  note and archive it ONLY if its CONTENT is dead (references a deleted file/flag, a resolved/closed
  issue, superseded by a newer entry, leaked task-state), via `reconcile_memory_index.archive_entry`;
  (3) a manual "forget this". Never archive a still-valid but quiet note. (See `forgetting-is-usage-based-only`.)
- **Contradiction / override.** A hand-written `CLAUDE.md` is AUTHORITATIVE: if memory contradicts it,
  correct OUR memory, do not touch the rule. Memory-vs-memory: a project rule that CONTRADICTS a higher
  rule becomes a self-contained OVERRIDE (more-specific / lower wins at load), NOT a `[[reference]]`;
  flag a persistent contradiction for the user.
- **CLAUDE.md reconciliation (tiers ARE altitudes; reconcile to save context).** Every `CLAUDE.md` in
  this project's ancestor chain cascades into its context, so the chain + memory + global form ONE
  altitude lattice; apply the same reference+delta normalization to it, with "reduce total always-loaded
  context" as the decision rule. Back up a `CLAUDE.md` only BEFORE an actual edit. For a rule found in
  this project's chain:
  - **Already covered by a broader always-present home** (memory at the same scope, the global layer, or
    a BROADER ancestor `CLAUDE.md` that already cascades here) -> propose DELETING the lower duplicate.
    (This supersedes the old blanket "intermediate altitude = flag only": an intermediate copy IS safely
    deletable when a broader covering tier exists. Flag-only is the fallback ONLY when no broader covering
    home exists and there is no same-scope non-CLAUDE.md home.)
    - **ENHANCE-BEFORE-DELETE (unconditional precondition, so nothing is lost).** "Covered" is usually
      PARTIAL - the `CLAUDE.md` rule often carries a specific example, a why, or a nuance the memory hook
      lacks. Never delete on topic-overlap alone. First READ both, FOLD every unique detail/example from
      the `CLAUDE.md` rule INTO the surviving memory rule (via the engine), and VERIFY the survivor fully
      SUBSUMES it (nothing unique left). Only THEN propose the deletion.
    - **If the source `CLAUDE.md` is itself UNTRACKED:** deleting it into untracked memory loses no
      version control (there was none) but CONCENTRATES the rule in fragile untracked memory. So ensure
      the covering store is LOCALLY GIT-TRACKED FIRST (the Durability pass below), then fold + delete.
  - **Belongs higher** (recurs across the subtree) -> lift the general up to the broadest covering tier,
    leave only the DELTA below (`references [[general]]` + delta), or remove it if there is no delta.
  - **Genuinely only-here** -> leave it (it is the delta). **Contradiction** -> the hand-written
    `CLAUDE.md` is authoritative; correct OUR memory, never the rule.
  - Guard: never LIFT a narrow rule into a tier that loads where it is irrelevant (net context LOSS);
    never demote a must-always directive into a pulled/lazy body; never trim a TRACKED/shared lower copy
    into a broader home that is LESS durable/shared (e.g. an untracked dir) - that loses version-controlled
    knowledge. If the broader home is not itself a tracked, shareable repo, propose an `umbrella-<topic>`
    repo to host it first (ask private/public, default private; see `bitranox:meta-dream-global-deep`).
    Propose-first in `propose`, apply in `auto`; never touch `CLAUDE.md` without confirmation.
    (CLAUDE.md policy: `bitranox:meta-self-improve`.)
- **Filler-word classification (keeps memory recall precise) - PER PROJECT.** The per-prompt recall
  hook is model-free: it drops known filler and QUEUES any not-yet-classified keyword for THIS project
  (`self_improve_signals.load_pending_keywords(proj)`). Here, the slow pass: if the queue is non-empty,
  hand it to a **`sonnet`** subagent (per the tier doctrine) to classify each word as **filler**
  (generic / conversational - no topical signal, e.g. "again", "previous", "normal") or **topical**
  (a real technical term, e.g. "bindsnap", "stimer"). Apply, all keyed to the CURRENT project:
  `add_filler_words(filler, proj)` and `add_topical_words(topical, proj)`, then `clear_pending_keywords(proj)`.
  The learned lists are **per-project** (machine-local), NEVER the shipped global `filler_words.json`
  baseline - a classification is a project-specific judgment, so keeping it local stops one project's
  filler from suppressing another's recall (a word can be noise here, a real topic there; see the
  `recall-filler-per-project` memory). Only universal generic-English filler belongs in the baseline,
  via a PR. Be CONSERVATIVE - when unsure, classify as topical (a wrongly-blacklisted term would
  silently suppress useful recall; a missed filler only adds mild noise the rarity ranking already
  damps). Empty queue -> skip (no-op).
- **Model-hierarchy review (periodic, time-gated - keeps subagent tiering current).** When
  `self_improve_signals.model_review_due()` is true (no prior review or > ~30 days; model releases are
  infrequent), ask the `claude-code-guide` agent for the current Claude model lineup and compare it to
  the tier mapping in `bitranox:process-agents-subagent-driven-development` "Concrete tiers". If a NEW model/tier
  appeared or the capability/cost ordering shifted (e.g. a newer Sonnet now covers work currently on
  Opus -> downshift; a new fast tier fits fan-out better), PROPOSE a re-tier of that one mapping via the
  upstream self-PR loop (shared skill -> propose-first, version-bumped). Dispatches use the stable tier
  ALIASES (`opus`/`sonnet`/`haiku`), so version bumps need no edit - only a hierarchy SHIFT does. Then
  call `mark_model_reviewed()` so it does not re-fire until due. Not due -> skip (no-op).
- **Durability: keep each memory store LOCALLY git-tracked (auto, safe machine-local move).** A loose
  untracked store is lost to an accidental `rm`/reset with no recovery. So every dream, ensure each
  `.claude-bx-selflearning/` store it wrote is version-controlled by a LOCAL git repo, then commit the
  dream's changes. LOCAL-ONLY, never a remote. Pick the smallest repo that covers the store WITHOUT
  leaking private memory into a shared push:
  - **Global (`~/.claude`):** a repo AT `~/.claude` with an AIRTIGHT WHITELIST `.gitignore` that tracks
    ONLY `CLAUDE.md` + `.claude-bx-selflearning/` and ignores everything else (`/*` then `!/CLAUDE.md`
    `!/.claude-bx-selflearning/`, plus `.claude-bx-selflearning/state/` and `*.lock`). This captures the
    one-line `@import` `CLAUDE.md` AND the global store in one repo. NEVER blanket-`git add` `~/.claude`
    (it holds session transcripts, `plugins/` clones with their own `.git`, `security/`, caches). VERIFY
    the whitelist with `git add -A -n` before the first commit: nothing outside the two paths may appear.
  - **Private project (`track_private` on):** commit the store IN the project's own repo (the `track_private`
    knob un-gitignores `.claude-bx-selflearning/`).
  - **Public project / non-git / isolation wanted:** the store as its OWN isolated local repo
    (`git init` inside the store dir); the parent keeps gitignoring it, so private memory never enters a
    public push. Ephemeral `state/` and `*.lock` stay gitignored.
  This is a safe machine-local move -> auto-apply even in `propose` mode.
- **Bound history growth (squash, count-gated).** Memory stores accrue a commit per dream; over time the
  `.git` grows. When a store repo's commit count exceeds a threshold (e.g. `git rev-list --count HEAD` >
  ~50), SQUASH its history to a single fresh snapshot commit (`git checkout --orphan`, re-add, commit,
  replace the branch) so the repo stays small. Memory values the CURRENT state, not granular history, so
  a snapshot is enough. Safe for these LOCAL/personal repos (no shared history to break); if a private
  backup remote exists, the squash needs a force-push - fine for a PERSONAL backup, but NEVER squash/
  force-push a shared or published repo (see the marketplace append-only rule).
- **Off-machine backup reminder (periodic, time-gated).** Local git protects against `rm`/reset, NOT
  against disk failure. When `self_improve_signals.backup_reminder_due()` is true (no prior reminder or
  > ~30 days), REMIND the user they can push the local memory store repo(s) to a PRIVATE remote
  (GitHub/Gitea) so nothing is lost to hardware failure. Propose-first: the USER creates/approves the
  private remote and does the push; never auto-create a remote or push. Then call `mark_backup_reminded()`
  so it does not re-fire until due. Not due -> skip (no-op).

## Cross-project work lives in meta-dream-global

This skill is scoped to ONE project. The cross-tree passes - inbound gather, outbound
cross-pollination, and the global-dream scan that reads across ALL project stores - are the expensive,
occasional work and live in the separate `bitranox:meta-dream-global` skill. Do not do them here. If
this project's dream surfaces a learning that is clearly useful BEYOND this project, you may still
promote it UP to the global curated store at `~/.claude` in step 5 (gated); the broader
cross-project scan and sibling-tree gather are meta-dream-global's job.

## Boundaries

- **Private memory + the global `~/.claude/.claude-bx-selflearning/` store (machine-local):** back up, then
  apply (the whole point of a dream). Reversible via the backup.
- **CLAUDE.md (version-controlled):** propose-first in `propose`; apply in `auto` - only through the
  sanctioned bounded paths. Create it if the right-altitude file is missing.
- **Skills / hooks (shared, public):** never silently edit; route through the upstream-PR loop
  (self-PR in `propose`, commit-or-PR in `auto`, skipped in `off`).
- **Circle-breaker still applies:** if the same item has been consolidated twice and keeps coming
  back, stop re-writing it - escalate to a guard or hand it to the user.

## Common mistakes

- Growing the store. A dream must net-shrink noise; if it added entries, reclassify or merge.
- Dreaming without capturing first (consolidating a half-recorded session).
- Auto-editing CLAUDE.md or skills in `propose` mode (those are propose / self-PR).
- Forgetting `dream_state.py done`, so the nudge keeps firing.
- Duplicating the general and specific text instead of reference + delta.
- Deduping ONLY before promotion. Promotion creates the overlap, so the dedup/normalize sweep must run
  AGAIN as the last content step (step 8), or the just-promoted general sits duplicated below it.
- A DOWNWARD or cross-tree reference (a higher entry pointing at a lower one) - it dangles on deletion.
- Over-broadening: watering a concrete-but-universal rule into a vague principle, or globalizing a
  narrowly-applicable one (it then loads in every session for nothing).
