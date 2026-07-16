# The memory backend (canonical storage spec)

The single source of truth for HOW durable memory is stored, delivered, and written. Other skills
(dream-project, dream-global, collect-knowledge, skill-writer) cross-reference this file instead of
restating it.

## Knowledge trees and anchors

A machine can carry SEVERAL independent knowledge TREES (a marketing company and a bakery share
nothing). Each tree has one TOP - the anchor: the topmost ancestor directory that carries a
`CLAUDE.md` AND the co-located central store `.claude-memory/` (bootstrap: the topmost `CLAUDE.md`
alone, until the first write creates the store there). Every level between a project and its anchor
is an ALTITUDE. Capture and the project dream stay WITHIN the current tree; cross-tree movement is
only ever an explicit copy (collect-knowledge import, dream-global). Say "the tree's top", not "the
global layer" - there can be several tops on one machine.

Engine helpers: `tree-top --proj DIR [--json]` prints a dir's top/store/bootstrap flag;
`ensure-all-trees [--roots ...] [--apply]` discovers every tree under the configured
`discovery_roots` and scaffolds each member chain (dry-run by default; a storeless top ABOVE
store-bearing trees is reported `ambiguous`, never auto-merged).

## Store format

Each altitude's `CLAUDE.local.md` carries ONE managed, fenced pointer block:

    <!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->
    <!-- bitranox:self-learning -->
    <scope descriptor: what this level is about - the dream's routing key>
    <!-- /bitranox:self-learning -->

    # Memory index
    (retrieval recipe line - teaches walking UP to the anchor and Reading facts/<slug>.md)

    ## Iron rules
    - [Title](mem:<slug>) - hook <!-- bx:src=<sources> bx:pin -->

    ## Memory index
    - [Title](mem:<slug>) - hook <!-- bx:src=<sources> -->
    <!-- BITRANOX-MEMORY-INDEX:END -->

- **The slug IS the identity** and the body-file key. Every body lives centrally at
  `<anchor>/.claude-memory/facts/<slug>.md` - flat, slug-named, human-readable, greppable. Slugs are
  TREE-unique: the body file is the registry, and the engine refuses a colliding `add` with a
  suggested suffix. Tree-uniqueness is VERIFIED tree-wide by `reconcile_memory_index.py --check-tree`
  (a slug pointed at from two levels is a violation `heal` and the chain-only `--check` both miss).
  The slug CHARSET is `[a-z0-9._-]` - it may contain a dot (e.g.
  `reference-pwshpy-tier-b-hosting-reuse-installed-ps7.6-assemblies`), so any tool parsing a
  `mem:<slug>` link MUST accept the dot; the engine's one pointer regex (`uuid_store._PTR_RX`,
  `mem:[^)]+`) already does - reuse it, never a hand-rolled `[a-z0-9-]+` that silently skips a
  dotted slug and mistakes its body for an orphan.
- **Pinned entries (`bx:pin`) are the iron rules**: rendered first under `## Iron rules`, exempt
  from archive/move/reword in the dream unless the user approves that specific change.
- **The hook is TRIGGER-FIRST** (probe-verified: a hook that leads with its situation drove an
  unprompted mid-task body read in 100% of runs; a trigger-less hook never fires):
  `When <situation>, <directive>.` - directive second person, 1-3 complete sentences. Soft cap 350
  chars (`add` warns past it - advisory only, never a reason to trim; the missing-trigger warning is
  the one that matters). The HARD cap is 500 chars (`cap_hook` word-boundary-truncates past it). The
  hook must stay self-sufficient: keep the load-bearing names, paths, flags, and numbers in it, even
  if that pushes it past the soft cap (but under the 500 hard cap).
- **The body is FRAMED as a native memory entry** (probe-verified ~5x application lift over bare
  prose - the model discounts bodies that do not look like genuine memory entries). The engine
  frames automatically; write the prose with the reasoning sections:

      ---
      name: <slug>
      description: <the hook>
      metadata:
        type: feedback | project | reference | user
      ---

      <the fact, 1-3 short paragraphs>

      **Why:** <the reasoning / the failure that taught it>

      **How to apply:** <the concrete procedure or check>

- Related facts link with `[[slug]]` references - UPWARD ONLY along ONE ancestor chain (a project
  entry may cite a tree-top rule; a higher entry never cites a lower one, or deleting the project
  would dangle it). Citing a SIBLING project's slug is as invalid as citing a child: the cascade
  only flows DOWN one ancestor chain, so a sideways ref never loads where the citing entry does and
  dangles. `--check` catches a sideways ref only when its chain happens to include the citing level;
  `--check-tree` catches it TREE-WIDE (a ref whose target is not on the citing fact's ancestor-or-self
  path, even though the target resolves somewhere in the tree). When in doubt, demote the link to plain
  prose - or, if the target is genuinely shared, lift it to a common ancestor so the ref becomes upward.

## Two tiers and the capture flow

- **Curated tier** (this store): deduplicated, engine-written learnings. **Hooks never write
  memory.** The flow is: the gated Stop hook NUDGES -> the MODEL runs `bitranox:meta-self-improve`
  -> engine `add` -> the fact lands directly in the store at the PROJECT level of the current tree.
  There is no MEMORY.md intermediate, and capture never reaches up to an ancestor - placement to the
  right altitude is the DREAM's job (engine `move`), never capture's.
- **Native raw tier**: Claude Code's own Auto memory (`~/.claude/projects/<proj>/memory/`),
  per-machine, uncurated. Keep it ON; the dream de-doubles the tiers and lifts worthwhile raw
  entries into the curated store (dream step 3b).
- The SessionEnd audit file buffers only MISSED-signal candidates for next-session review - it is a
  review queue, not a memory tier.
- The `remember` plugin / `.remember/` is session task-continuity only - never durable learnings.

## Three delivery paths (how a fact reaches context)

1. **Cascade text** - ancestor `CLAUDE.local.md` blocks load as plain text every session (and reach
   Task subagents). The pointer lines (title + trigger-first hook) are therefore always in context.
2. **Per-prompt recall hook** - keyword scan over OTHER projects' stores + CLAUDE.md files,
   injecting top matches. Machine-global by default; the `cross_tree_search` config knob (false =
   current tree only) walls it for independent trees.
3. **The retrieval standing rule + in-block recipe** - teach reading a body ON DEMAND mid-task:
   walk UP to the first ancestor containing `.claude-memory/`, Read `facts/<slug>.md`. This is what
   makes bodies reachable DURING reasoning; read a body only when its hook is relevant, never bulk.

The SEARCH mechanism is swappable: a memory MCP (`basic-memory`) may sharpen cross-project recall as
an OPTIONAL, read-only full-text+graph index OVER these files - never the store, never a write path;
absent MCP, the keyword scan is the fallback. Wire one only via the `update-config` skill.

## The engine (the ONLY write path) and its fail-loud contract

All writes go through `hooks/memory_engine.py`, launched cross-platform via `hooks/run-python.sh`.
Never hand-edit a pointer block or a body - a PreToolUse guard denies it (bypass only via a
`BITRANOX_MEMORY_ENGINE=1` session for deliberate hand-repair).

| Command                                                                                                                                                                                 | Success line to REQUIRE               |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| `add --proj D --title T --hook H --body-file F [--type feedback\|project\|reference\|user] [--source S] [--pin] [--scope TEXT] [--slug S]`                                              | the printed slug                      |
| `heal --proj D`                                                                                                                                                                         | `healed N file(s) across M level(s)`  |
| `set-scope --proj D --scope TEXT`                                                                                                                                                       | `scope updated:` / `scope unchanged:` |
| `move --from-level A --to-level B --slug S [--force]`                                                                                                                                   | `moved <slug>: A -> B (up\|down)`     |
| `lint --tree D`                                                                                                                                                                         | `TOTAL over-cap hooks: N \| ...`      |
| `tree-top --proj D [--json]`                                                                                                                                                            | the printed top/store lines           |
| `ensure-all-trees [--roots ...] [--apply]`                                                                                                                                              | the `DRY-RUN:`/`APPLIED:` report      |
| `skills/meta-self-improve/reconcile_memory_index.py --check <chain narrow->broad>` (a SEPARATE script, NOT an engine verb - it lives in this skill's dir, same `run-python.sh` launch)  | `TOTAL problems: 0`                   |
| `skills/meta-self-improve/reconcile_memory_index.py --check-tree D` (TREE-WIDE: cross-sibling duplicate pointers, orphans, sideways/downward refs, dangling that `--check`/`heal` miss) | `TOTAL tree problems: 0`              |
| `skills/meta-self-improve/reconcile_memory_index.py --archive S D` (forget a fact: drop its pointer at D + move its body to `.archive/`)                                                | `archived <slug> ...`                 |

**Fail-loud contract:** run engine calls with `BITRANOX_RUN_PYTHON_STRICT=1`, require the command's
success line in the output, and ABORT-AND-SHOW on any miss (a refused move prints `! refused:` and
exits 1; a colliding add prints `! refused:` with a suggested slug). Never continue past a silent or
malformed engine result.

`add` semantics: upserts by slug (title-derived unless `--slug` targets an existing identity),
merges provenance (`bx:src`) and pin, keeps the existing body when `--body` is empty, frames a bare
body, enforces tree-unique slugs. `move` relocates only a pointer LINE (the body never moves); if the
target ALREADY points at the slug with a different hook it REFUSES (a duplicate, not a relocation -
picking by direction would silently discard the richer hook), and `--force` dedups by keeping the
LONGER hook and dropping the other. `heal` runs every session (skip-fast when healthy), is
CHAIN-scoped and normalizes drifted grammar only; a pointer whose body is missing is REPORTED, never
fabricated - it does NOT detect cross-sibling duplicate pointers, which is `--check-tree`'s job.
`lint --tree` is the read-only voice/frame backlog sweep (over-hard-cap hooks, trigger-less hooks,
unframed bodies).

## Keeping it lean

One fact per entry. Dedup BEFORE writing: grep the pointer blocks + `facts/` bodies + native tier;
sharpening an existing fact is the SAME `add` (same slug) - not a new entry. The pointer block is
always-loaded context: hooks short, detail in the body. Block size is advisory
(`reconcile_memory_index.py --check` warns, never fails); growth is the dream's cue to dedup, merge,
and re-level with `move`.
