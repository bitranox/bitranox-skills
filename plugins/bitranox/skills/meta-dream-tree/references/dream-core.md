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

## Script homes (the helper scripts ship inside their owning skill, NOT hooks/)

- `dream_state.py` (mode / due / done / session-review / session-reviewed / saw-promotable /
  should-promote / promoted) -> `<plugin>/skills/meta-dream-tree/dream_state.py`
- `reconcile_memory_index.py` (--check) -> `<plugin>/skills/meta-self-improve/reconcile_memory_index.py`

Launch either cross-platform through the same shim as the engine:
`bash <plugin>/hooks/run-python.sh <script> ...`, where `<plugin>` is the installed plugin dir
(`~/.claude/plugins/cache/bitranox-skills/bitranox/<version>`) or the source repo's
`plugins/bitranox`. Bare script names below refer to these two homes.

## Level enumeration - `find`, never a bare `grep -r` (and cross-check the count)

Enumerate the tree's levels with `find <anchor> -name CLAUDE.local.md` (or `grep --no-ignore-files`),
NEVER a bare `grep -r`. In a Claude Code bash session `grep` forwards to the `claude` search backend,
which honors `.gitignore` by default; `bmk` adds `CLAUDE.local.md` to a repo's `.gitignore`, so
`grep -rl BITRANOX-MEMORY-INDEX` silently returns a fraction of the levels (measured: 17 of 43 - every
project-level store missing) and the miss looks like success. A dream scoped by that grep scores
itself tree-wide while it only saw one chain. (`.claude-memory/facts/` is git-TRACKED, so a grep over
the bodies is sound - it is the CLAUDE.local.md pointer files that are gitignored.)

**Cross-check every enumeration or parse against a second method before acting on it.** A silent
under-count is the recurring failure of this whole procedure (one run hit three: a grep enumeration,
a slug regex that omitted the dot, a freshness checker comparing the wrong lists - each under-reported
and was acted on). Confirm a level list, a slug set, or a duplicate scan with an independent count
(e.g. `find | wc -l` vs the tool's own number) before you trust it.

**Verify every parallel WRITE fan-out from ground truth, not the agents' reports.** When you dispatch
one subagent per level to write descriptors (`set-scope`) or to apply moves, `set-scope` overwrites
UNCONDITIONALLY, so a subagent that writes the wrong `--proj` silently clobbers a sibling level and
still reports success on the correct path (observed: one agent wrote `apps/`'s descriptor into
`bitranox-systems/`, discarding what another agent had just written there). After ANY such fan-out,
re-run the freshness/enumeration check over ALL levels and diff each level's on-disk descriptor
against what its own agent RETURNED - keep each agent's returned text, because the pre-dream backup
holds only the stale version you were replacing, so it is your only restore source for a clobber.

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

**Read the session from DISK, not from what you remember.** Run
`dream_state.py session-review "<cwd>"` first. Your context is not the session: a compaction clears
the CONTEXT while the transcript FILE survives intact, so anything you "skim from memory" after a
compaction is the summary, and the detail is silently lost. `session-review` returns the material
from disk: the not-yet-reviewed transcript stretch, the SUBAGENT learnings buffered this session
(they are NOT in your transcript at all and die uncaptured), and the touched-path ROUTING EVIDENCE
(which repos this session edited that are not the cwd - route `--proj` by SUBJECT). It is
INCREMENTAL: a per-reviewer watermark means an already-consumed prefix is never re-read, so a second
dream in one session costs nothing and re-analyzes nothing. When the pass is done, run
`dream_state.py session-reviewed "<cwd>"` to advance the mark. If a compaction happened, the Stop
gate will not let the session stop until this nap has run.

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

**A DUPLICATE/MERGE finding is a CANDIDATE, not a verdict - VERIFY against ground truth before
merging.** A fan-out subagent (or a title/topic match) flags likely duplicates, but topic-match is
NOT redundancy: READ both bodies and check the refs first. These are NOT duplicates - do not merge:
a SUMMARY + DETAIL pair (one cites the other for the deep dive), two facts joined by a valid
cross-link, or a fact CITED across a subtree (its inbound-ref reach is evidence it belongs UP at the
common ancestor, not that it duplicates the citer). Only merge when both bodies teach the SAME lesson
and one adds nothing the other lacks. (Measured: a deep fan-out's 3 merge suggestions were all
complementary on inspection - evidence decides, not the agent's topic guess.)

## The placement routing prompt (verbatim - lives only here)

> Given this fact (title + hook + body) and the scope descriptors of every level on the chain:
> choose the NARROWEST level whose PLACE-HERE covers everywhere the fact applies; never a level
> where some children would find it noise (unless it is true for ALL); a fact naming one
> project's files belongs AT that project (move DOWN); route by WHERE THE HOOK MUST FIRE, not by
> what the fact is ABOUT - a fact about tool X whose trigger fires in every CONSUMER of X belongs
> where the consumers are (the common parent), not at X's own repo, or the hook never loads where
> the symptom appears; EVIDENCE, not wording, decides reach; tie or unsure -> keep + UNSURE.
> Return: `LEVEL | CONFIDENCE high/low | WHY`.

Low/UNSURE never moves. Pinned entries are EXEMPT from move/reword/archive without the user's
approval of that specific change - report them separately. Tree-top promotion additionally passes
the corroboration gate: a user-stated concrete rule promotes eagerly; a model-INFERRED generalization
needs >= 2 dream sightings. The gate is backed by a real dwell counter (out of the dreamed store, so
counting never bumps its mtime): record each sighting with `dream_state.py saw-promotable <slug>`,
ask `dream_state.py should-promote <slug>` (prints `promote`/`hold`), and after an actual promotion
run `dream_state.py promoted <slug>` to clear it. HOLD keeps the fact at the project level for the
next dream.

## Verification contract (every run ends with this)

Fail-loud engine calls throughout (strict env, require each command's success line, abort-and-show
on a miss; the command table is in `bitranox:meta-self-improve` -> references/memory-backend.md).
Post-run: re-derive the manifest and diff against the pre-run one;
`reconcile_memory_index.py --check <chain narrow->broad>` must end `TOTAL problems: 0`. For a
TREE-WIDE run (meta-dream-tree and the crosstree variants) ALSO run
`reconcile_memory_index.py --check-tree <anchor>` and require `TOTAL tree problems: 0` - the
chain-only `--check` structurally cannot see a slug DUPLICATED across sibling chains (slugs are
tree-unique), which `heal` also misses. Report counts (merges, placements with direction, prunes,
pinned untouched) and, for nap/project, run `dream_state.py done` when the run covered what the nudge
asked for.

## Tier note (inline deep judgments)

Placement/promotion judgment runs INLINE on the session model (it needs the whole loaded scope).
Below opus-class -> offer switch-model-or-continue per "The session model is fixed" in
`bitranox:process-agents-subagent-driven-development` (a /model switch keeps the conversation;
opus is the universally-available deep tier, fable sits above it but needs paid API credits, and
a fable session may equally switch DOWN afterward to save cost). Auto mode: continue + log.
