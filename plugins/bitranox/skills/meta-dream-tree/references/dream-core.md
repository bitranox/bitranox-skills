# Dream core (single source for ALL consolidation skills)

The pieces every consolidation skill shares - `bitranox:meta-dream-nap` (the cwd's chain),
`bitranox:meta-dream-tree` (one tree), `bitranox:meta-dream-crosstree`/`-deep` (across trees) -
live HERE exactly once. A dream skill's own SKILL.md carries only its SCOPE DELTA and unique
steps; if you are about to restate something below in one of them, stop and reference this file
instead (the contract test fails duplicated family literals).

## The scope ladder (each skill states exactly one rung)

| Skill                       | Scope                                                            |
|-----------------------------|------------------------------------------------------------------|
| meta-dream-nap              | the cwd's ALTITUDE CHAIN only (project -> ancestors -> anchor)   |
| meta-dream-tree             | ONE knowledge tree, TREE-WIDE (every level under the anchor)     |
| meta-dream-crosstree(+deep) | ACROSS trees (discovery over discovery_roots; lift-or-copy only) |

## Mode (the user can switch off the asking)

Read the mode first (`dream_state.py mode`; knobs in `~/.claude/.bitranox-memory.json` via
`self_improve_signals.load_config()`):
- **`propose`** (default): apply safe private-memory consolidation; ASK before editing a
  version-controlled CLAUDE.md; route skill changes to a self-PR. Mention the `dream_mode`
  knob (`bitranox:meta-memory-settings`) at the end.
- **`auto`**: no per-change prompts - apply CLAUDE.md edits and ship skill changes directly.
- **`off`**: no nudges; a manual run consolidates PRIVATE memory only.

## Capture-first (unconditional on a manual run)

Enumerate this session's durable learnings and capture via `bitranox:meta-self-improve` BEFORE
consolidating. `not-due` never suppresses capture; an absent store is the trigger to CREATE one;
routing a learning only into a CLAUDE.md is NOT capture. Verify "nothing durable" - never assume.

## Backup + manifest (before any edit)

Copy every store the run may touch (the anchor's `.claude-memory/` + each in-scope level's
`CLAUDE.local.md`, + the native tier when read) to
`~/.claude/self-improve-audit/backups/<key>-<ts>/` (OUT of the trees, so a backup is never
re-discovered as live memory), and record the ORDER-INDEPENDENT manifest: the set of
(level, slug, title, pin) tuples for the in-scope levels. The post-run check re-derives it; only
`level` may change (placement), everything else only via an explicit merge/prune/reword decision.
Commit the store's git repo (durability) so the pre-run state is one `git diff` away.

## Dedup semantics

Fold near-duplicates into ONE sharpened entry (engine `add`, same slug); the surviving entry
merges provenance; cross-link related entries with `[[slug]]` (UPWARD only). Dedup compares
across the WHOLE scope of the running skill, and runs AGAIN after any placement (placement
creates new overlap).

## The placement routing prompt (verbatim - lives only here)

> Given this fact (title + hook + body) and the scope descriptors of every level on the chain:
> choose the NARROWEST level whose PLACE-HERE covers everywhere the fact applies; never a level
> where some children would find it noise (unless it is true for ALL); a fact naming one
> project's files belongs AT that project (move DOWN); EVIDENCE, not wording, decides reach;
> tie or unsure -> keep + UNSURE. Return: `LEVEL | CONFIDENCE high/low | WHY`.

Low/UNSURE never moves. Pinned entries are EXEMPT from move/reword/archive without the user's
approval of that specific change - report them separately. Tree-top promotion additionally passes
the corroboration gate (user-stated: eager; model-inferred: >= 2 dreams via `should_promote`).

## Verification contract (every run ends with this)

Fail-loud engine calls throughout (strict env, require each command's success line, abort-and-show
on a miss; the command table is in `bitranox:meta-self-improve` -> references/memory-backend.md).
Post-run: re-derive the manifest and diff against the pre-run one;
`reconcile_memory_index.py --check <chain narrow->broad>` must end `TOTAL problems: 0`; report
counts (merges, placements with direction, prunes, pinned untouched) and, for nap/project, run
`dream_state.py done` when the run covered what the nudge asked for.

## Tier note (inline deep judgments)

Placement/promotion judgment runs INLINE on the session model (it needs the whole loaded scope).
Below opus-class -> offer switch-model-or-continue per "The session model is fixed" in
`bitranox:process-agents-subagent-driven-development` (a /model switch keeps the conversation;
opus is the universally-available deep tier, fable sits above it but needs paid API credits, and
a fable session may equally switch DOWN afterward to save cost). Auto mode: continue + log.
