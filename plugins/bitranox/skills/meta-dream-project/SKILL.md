---
name: meta-dream-project
description: Use when the SessionStart nudge says a memory consolidation is due, when the store has grown or feels noisy/duplicated, before context compaction would lose detail, or on "dream", "dream project", "/dream-project", "consolidate memory", "tidy memory". Use AFTER per-turn capture (bitranox:meta-self-improve); for the cross-project / cross-tree scan use bitranox:meta-dream-global instead. Honors an off/auto/propose mode.
---

# meta-dream-project

Memory consolidation for the CURRENT project's knowledge tree, the way a brain reorganizes during
sleep. `bitranox:meta-self-improve` is the fast per-turn CAPTURE; this is the periodic batch
CONSOLIDATION: dedup, merge, re-level (PLACEMENT), normalize, prune - so memory gets smaller and
sharper, not bigger. **If a pass would grow the store, it is wrong.**

**REQUIRED BACKGROUND:** the storage spec (trees/anchors, store grammar, trigger-first hooks,
framed bodies, engine commands + fail-loud contract) is `bitranox:meta-self-improve` ->
`references/memory-backend.md` - Read it BEFORE the first engine call. This skill stays WITHIN the
current tree; cross-tree work is `bitranox:meta-dream-global`.

## Reference files

| Topic                                                                                                                                                                                                         | File                       |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| The behavioral pass catalog - removal policy, contradiction/override, CLAUDE.md reconciliation, skill/hook pointing, filler words, model review, skill-gap, gate-coverage, durability/squash, backup reminder | references/dream-passes.md |
| Acceptance harness - planted-fixture test that proves a dream run works                                                                                                                                       | tests/README-acceptance.md |

Use the Read tool to load a referenced file when running its passes.

## Mode (the user can switch off the asking)

Read the mode first (`dream_state.py mode`; knobs live in `~/.claude/.bitranox-memory.json` via
`self_improve_signals.load_config()`):
- **`propose`** (default): apply the safe private-memory consolidation; ASK before editing a
  version-controlled CLAUDE.md; route skill changes to a self-PR. End by mentioning
  `~/.claude/.bitranox-dream-auto` (auto) / `~/.claude/.bitranox-dream-off` (off).
- **`auto`**: no per-change prompts - apply CLAUDE.md edits and ship skill changes directly.
- **`off`**: no nudges; a manual dream consolidates PRIVATE memory only.

## When to run

Nudged when due (SessionStart), around compaction (PreCompact salvages, you dream), or manual
("dream", "/dream-project"). Check `dream_state.py due`. **A MANUAL dream ALWAYS captures -
`not-due` never suppresses capture.** An absent store is the trigger to CREATE one (the first
engine `add` bootstraps it), never a reason to skip; routing a learning only into a CLAUDE.md is
NOT capture. Verify "nothing durable" - never assume it.

## Procedure

Create one todo per step. Every engine call follows the fail-loud contract (strict env, require
the success line, abort-and-show on a miss).

0a. **Deterministic scaffold (a script, no model).** `memory_engine.py heal --proj "<cwd>"` (via
    `run-python.sh`): creates every missing marker `CLAUDE.md` + `CLAUDE.local.md` pointer block
    from the project up to the anchor, plus the central store; normalizes drifted grammar.
    Require `healed N file(s) across M level(s)`.

0b. **Scope-descriptor synthesis (freshness-gated, parallel sonnet subagents).** The per-level
    descriptors are the PLACEMENT ROUTING KEY, so every level needs a meaningful one. LEVELS MEANS
    THE WHOLE TREE: every pointer-block-bearing dir under the anchor - SIBLING projects and
    departments included - not just the cwd's ancestor chain (walk the tree or list the
    CLAUDE.local.md files under the anchor). Only synthesize levels whose descriptor is EMPTY,
    INCOMPLETE (missing template keys), or whose CHILDREN list is stale vs the actual
    subdirectories. Dispatch one `sonnet` subagent per stale
    level, in parallel (bottom-up in two waves when a leaf and its parent are both stale, so the
    parent can read fresh child descriptors). An upper level's subagent reads each child dir's
    README/CLAUDE.md/docs headings + child descriptors; the project level's subagent reads the
    project's OWN docs. Write via `set-scope` (require its success line). Fixed template, <= 120
    words per level, ASCII, uppercase keys:

        WHAT: <1-2 sentences: what this level IS>
        STACK: <languages, frameworks, tools, key resources>
        CHILDREN:
        - <dir>/: <one clause>
        PLACE-HERE: <knowledge true for THIS WHOLE subtree but NOT above>
        PLACE-ELSEWHERE: <push child-specific down; push broader-than-subtree up>

1. **Capture first (unconditional on a manual dream).** Enumerate this session's durable learnings
   and capture via `bitranox:meta-self-improve` BEFORE consolidating, so the dream works on a
   complete store.

2. **Back up + manifest.** Copy the anchor's `.claude-memory/` AND each level's `CLAUDE.local.md`
   to `~/.claude/self-improve-audit/backups/<key>-<ts>/curated` (+ the native tier to `/native`),
   and record an ORDER-INDEPENDENT manifest: the set of (level, slug, title, pin) tuples. The
   post-dream check (step 8) re-derives it; placement legitimately changes `level`, nothing else
   changes without an explicit merge/prune decision. Commit the store's git repo (Durability pass)
   so the pre-dream state is one `git diff` away.

3. **Load both tiers TREE-WIDE** - every level's pointer block under the anchor (the cwd's chain
   AND every sibling project/department; the central bodies are one store) plus the native raw
   tier - and skim the session for uncaptured items. A dream that only reads the cwd's chain
   misses exactly where duplicates and misplaced facts live: the siblings.

3b. **De-double the tiers.** A fact lives in exactly ONE tier. Per native entry: already curated
   (by `bx:src` provenance or title/hook match) -> drop the native duplicate; native-only and
   worthwhile -> PROMOTE via engine `add` (merge its slug into `--source`); some-value -> leave in
   native. There is NO "native-only backend" mode - an absent pointer block is the trigger to
   create one, not evidence of one. The only reasons a worthwhile fact stays native: some-value,
   or the SECRETS carve-out (curated stores are git-tracked; the native tier is not - never stage
   credentials into a repo).

4. **Dedup / merge ACROSS THE TREE.** Fold near-duplicates into one sharpened entry (engine
   `add`, same slug) - comparing across ALL levels, especially SIBLING projects (the classic
   duplicate is the same lesson captured independently in two sibling projects; it merges at
   their common parent). Cross-link related entries with `[[slug]]`. Dedup runs TWICE - here,
   and again in step 8, because placement creates new overlap.

5. **PLACEMENT (re-level every unpinned entry; up AND down).** Route each unpinned fact through
   the routing prompt against the descriptor ladder (leaf -> anchor):

   > Given this fact (title + hook + body) and the scope descriptors of every level on the chain:
   > choose the NARROWEST level whose PLACE-HERE covers everywhere the fact applies; never a level
   > where some children would find it noise (unless it is true for ALL); a fact naming one
   > project's files belongs AT that project (move DOWN); EVIDENCE, not wording, decides reach;
   > tie or unsure -> keep + UNSURE. Return: `LEVEL | CONFIDENCE high/low | WHY`.

   Batch the high-confidence moves into ONE propose-diff (auto mode: apply); apply each via engine
   `move --from-level A --to-level B --slug s` and require its success line (`! refused:` aborts
   that move - a down-move with inbound refs needs the refs re-pointed first, or stays). Low/UNSURE
   never moves. Tree-top promotion additionally passes the corroboration gate (user-stated: eager;
   model-inferred: >= 2 dreams via `should_promote`). After moving, normalize reference+delta
   UPWARD-ONLY: the general lives once at its altitude, lower entries cite `[[general]]` + delta.
   Pinned entries are EXEMPT from move/reword/archive unless the user approves that specific
   change - report them separately.

6. **Voice + firing check (maintenance).** The engine lints new hooks at add-time; here, sweep for
   residue: any hook failing the trigger-first lint (`hook_missing_trigger`), over the 350 soft
   cap, or whose trigger does not actually name the situations its body applies to (the FIRING
   check - would this line catch your attention at the right moment?). Queue offenders to a sonnet
   rewrite (trigger-first, facts preserved, slug-stable via `add --slug`), propose-diff, apply.
   Bodies missing the frame or the **Why:**/**How to apply:** sections get the same treatment.

7. **Prune (content-based only, tree-wide).** Archive obsolete/superseded/task-state entries at
   EVERY level of the tree (siblings included) per the removal policy in
   references/dream-passes.md (propose-first; the backup makes it safe). Never
   usage/age/size-based.

8. **Re-dedup, then verify.** Sweep the entries placement touched (a lifted general now overlaps
   its origin and siblings) and normalize. Then: re-derive the manifest and diff against step 2
   (only `level` may differ, plus explicitly-decided merges/prunes/rewords); run
   `reconcile_memory_index.py --check <altitude chain, narrow->broad>` and require
   `TOTAL problems: 0`; fix integrity failures via the engine (re-point a downward ref, resolve an
   orphan). Size warnings are advisory.

9. **Behavioral passes.** Run the catalog in references/dream-passes.md (each pass on its own
   trigger): CLAUDE.md reconciliation (chain-gated - runs EVERY dream, rule-by-rule, both
   directions), contradiction/override, skill/hook pointing, filler words, model review,
   skill-gap review, gate-coverage audit, durability/git + squash, backup reminder.

10. **Skill-fit -> batched change.** Collect generalizations that match or warrant a shipped
    skill; deliver via the upstream loop (`bitranox:meta-self-improve` ->
    references/upstream-propagation.md) as ONE structured change. `propose` -> self-PR; `auto` ->
    commit or self-PR; `off` -> skip.

11. **Done + report + /clear nudge.** `dream_state.py done` (records the fact signature). Report
    counts + one line each: merges, placements (with direction), voice rewrites, prunes, CLAUDE.md
    edits (applied/proposed), skill changes, pinned entries left untouched. Nudge `/clear` (the
    consolidated store loads next session; not clearing loses nothing).

## The tree, not "the global layer"

This dream is scoped to the CURRENT tree (cwd's anchor). A machine can carry several independent
trees; another tree is NEVER read or written here - `ensure-all-trees`/`tree-top` locate tops, and
cross-tree movement is only ever collect-knowledge's labeled copy or dream-global's job. Say "the
tree's top", not "the global layer".

## Acceptance harness (prove the dream works)

`tests/fixture_builder.py` plants a deterministic two-tree fixture (dup pair, mis-placed high/low
facts, an obsolete entry, task-state, a trigger-less hook, a pinned decoy, an empty descriptor, an
untouched control tree); `tests/fixture_asserter.py` checks a post-dream run: HARD assertions
(control tree byte-identical, pinned entry untouched, slugs stable under voice rewrites, reconcile
0 problems, backups exist) and JUDGMENT assertions (dup merged at the parent, high fact moved
down, low fact moved up exactly one level, obsolete proposed for archive, task-state pruned,
descriptor synthesized). Run it after any substantive change to this skill (procedure in
tests/README-acceptance.md); the bar is all-hard + >= 5/6 judgment on two consecutive runs.

## Boundaries

- Private memory + the tree-top store: back up, then apply (reversible via backup).
- Version-controlled CLAUDE.md: propose-first in `propose`; only through the sanctioned paths.
- Skills/hooks (shared): never silently edit; the upstream loop only.
- Pinned entries: exempt from archive/move/reword without explicit user approval.
- Circle-breaker: consolidated twice and it keeps coming back -> escalate to a guard or the user.

## Deliverables (a completed dream has ALL of these)

- [ ] heal success line ("healed N file(s) across M level(s)").
- [ ] Scope descriptors fresh: every chain level carries the template keys (or was verified fresh).
- [ ] Capture ran BEFORE consolidation (or a verified "nothing durable" statement).
- [ ] Backup taken + the (level, slug, title, pin) manifest recorded pre-dream.
- [ ] Placement report: applied moves (with direction), kept UNSUREs, pinned entries untouched.
- [ ] Voice/firing residue swept (or "0 offenders" verified via the lint).
- [ ] Post-dream manifest diff clean (only `level` changed, plus explicitly-decided merges/prunes).
- [ ] `reconcile ... --check` printed `TOTAL problems: 0`.
- [ ] Each behavioral pass reported against ITS OWN trigger (ran / no-op with the verified reason).
- [ ] `dream_state.py done` ran; report + `/clear` nudge delivered.

An ended run missing any box is not done - finish it or say plainly what was skipped and why.

## Rationalizations (pressure-tested; these do not fly)

| Excuse                                                         | Reality                                                                                                                          |
|----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| "not-due / no store exists -> nothing to consolidate"          | not-due never suppresses capture; an absent store is the TRIGGER to create one. Two learnings uncaptured = work exists.          |
| "Only N entries changed -> grep their keywords over CLAUDE.md" | The named prohibited shortcut. Reconciliation is rule-by-rule, BOTH directions, every dream - pre-existing overlap is the point. |
| "auto mode + 'stop asking' covers the pinned entry"            | The pinned exemption requires approval of THAT specific change; auto only silences CLAUDE.md/skill prompts.                      |
| "I'm 90% sure, despite CONFIDENCE low"                         | The router's confidence gates the move, not your certainty. Evidence beats wording; UNSURE stays put.                            |
| "Writing it into CLAUDE.md is faster than the engine"          | Routing into CLAUDE.md is not capture; the store is the system of record.                                                        |
| "The store is empty/unchanged, so the passes no-op"            | Only counter-gated passes no-op on emptiness; chain-gated passes (reconciliation, dedup, placement) run EVERY dream.             |
| "No time for the full pass - I'll note it for next dream"      | Say it out loud in the report as INCOMPLETE and flagged; never silently downgrade a pass and call the dream done.                |

## Common mistakes

- Growing the store (a dream must net-shrink noise).
- Dreaming without capturing first.
- Consolidating only the cwd's ancestor CHAIN. The dream covers the WHOLE tree - sibling
  projects and departments are where the dups, misplacements, and stale task-state live (a
  chain-only run leaves them untouched and scores as a half-dream).
- Placement by wording instead of EVIDENCE, or moving a low-confidence fact.
- Moving a pinned entry, or moving DOWN past inbound `[[refs]]` (the engine refuses; re-point
  first).
- Deduping only BEFORE placement (placement creates the overlap; step 8 exists for that).
- Reading a no-op off the wrong signal: chain-gated passes (CLAUDE.md reconciliation, dedup,
  placement) run EVERY dream; only counter-gated passes no-op on emptiness.
- Running CLAUDE.md reconciliation as a keyword-grep of only the newly-written entries (misses all
  pre-existing duplication; the pass is rule-by-rule over the entire chain, both directions).
- A downward or cross-tree `[[reference]]` (dangles on deletion; cross-tree is always a copy).
- Forgetting `dream_state.py done`, so the nudge keeps firing.
