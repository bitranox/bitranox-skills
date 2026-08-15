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
- **Pinned entries (`bx:pin`) are the iron rules**: rendered first under `## Iron rules`. The pin is
  a WRITE-PERMISSION gate, not just render-ordering advice: an ordinary `add` targeting an
  already-pinned slug is REFUSED by the engine before any write (`PinnedEntry`, raised in
  `add_or_update_entry`) - `amend-pinned` is the deliberate way through, a separate verb rather than
  a `--force` flag on `add` so an autonomous pass copying an example `add` invocation can never
  reach it by accident. The movers (`move`, `relocate`, `rename`) are unaffected by this gate: they
  carry `pin` through untouched and never refuse on it, so re-leveling a pinned fact needs no
  exception.
- **The hook is TRIGGER-FIRST** (probe-verified: a hook that leads with its situation drove an
  unprompted mid-task body read in 100% of runs; a trigger-less hook never fires):
  `When <situation>, <directive>.` - directive second person, 1-3 complete sentences. Soft cap 350
  chars (`add` warns past it - advisory only, never a reason to trim; the missing-trigger warning is
  the one that matters). The HARD cap is 500 chars and `add` REFUSES a longer hook rather than
  truncating it, because every pointer line is always-loaded context and a silently cut one still
  reads like a complete instruction. The refusal is checked BEFORE the lock, so it is atomic: the
  CLI prints `! refused:` and exits 1, no body file and no pointer line are written, and on an
  update the existing entry keeps its old hook. Nothing needs cleaning up - rewrite the hook, move
  the surplus detail into the body, and re-run `add`; do not delete detail to fit. The hook must
  stay self-sufficient: keep the load-bearing names, paths, flags, and numbers in it, even if that
  pushes it past the soft cap.
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
  -> engine `add` -> the fact lands directly in the store at the PROJECT level of its SUBJECT - the
  cwd unless the turn's routing evidence (the `touched-paths` recorder, surfaced by the Stop gate)
  shows the learning is about another repo you edited; route `--proj` there instead. There is no
  MEMORY.md intermediate, and capture never reaches up to an ancestor - the ALTITUDE is the DREAM's
  job (engine `move`), never capture's. Getting the SUBJECT right matters most cross-tree: `move`
  refuses to cross trees (it relocates a pointer, and the body is anchored per tree), so a
  cross-tree misfile needs the heavier `relocate` verb - which copies the body into the target
  tree and archives the source. Cheaper to route right at capture than to re-home later.
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

| Command                                                                                                                                                                                  | Success line to REQUIRE               |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| `add --proj D --title T --hook H --body-file F [--type feedback\|project\|reference\|user] [--source S] [--pin] [--scope TEXT] [--slug S]`                                               | the printed slug                      |
| `amend-pinned --proj D --slug S [--hook H] [--body-file F]` (the deliberate way through - an ordinary `add` REFUSES a pinned slug; human use only, no autonomous pass invokes this verb) | the printed slug                      |
| `heal --proj D`                                                                                                                                                                          | `healed N file(s) across M level(s)`  |
| `set-scope --proj D --scope TEXT`                                                                                                                                                        | `scope updated:` / `scope unchanged:` |
| `move --from-level A --to-level B --slug S [--slug S2 ...] [--force]` (several slugs move as ONE set; see below)                                                                         | `moved <slug>: A -> B (up\|down)`     |
| `relocate --from-level A --to-level B --slug S [--force]`                                                                                                                                | `relocated <slug>: A -> B (...)`      |
| `rename --level D --slug S --to-slug S2` (fix a WRONG NAME: `move`/`relocate` change a fact's level, never its name; this repoints every inbound `[[ref]]` so nothing is orphaned)       | `renamed <slug> -> <slug2> at D`      |
| `lint --tree D`                                                                                                                                                                          | `TOTAL over-cap hooks: N \| ...`      |
| `tree-top --proj D [--json]`                                                                                                                                                             | the printed top/store lines           |
| `ensure-all-trees [--roots ...] [--apply]`                                                                                                                                               | the `DRY-RUN:`/`APPLIED:` report      |
| `skills/meta-self-improve/reconcile_memory_index.py --check <chain narrow->broad>` (a SEPARATE script, NOT an engine verb - it lives in this skill's dir, same `run-python.sh` launch)   | `TOTAL problems: 0`                   |
| `skills/meta-self-improve/reconcile_memory_index.py --check-tree D` (TREE-WIDE: cross-sibling duplicate pointers, orphans, sideways/downward refs, dangling that `--check`/`heal` miss)  | `TOTAL tree problems: 0`              |
| `skills/meta-self-improve/reconcile_memory_index.py --archive S D` (forget a fact: drop its pointer at D + move its body to `.archive/`)                                                 | `archived <slug> ...`                 |

**Fail-loud contract:** run engine calls with `BITRANOX_RUN_PYTHON_STRICT=1`, require the command's
success line in the output, and ABORT-AND-SHOW on any miss (a refused move prints `! refused:` and
exits 1; a colliding add prints `! refused:` with a suggested slug). Never continue past a silent or
malformed engine result.

`add` semantics: upserts by slug (title-derived unless `--slug` targets an existing identity),
merges provenance (`bx:src`) and pin, keeps the existing body when `--body` is empty, frames a bare
body, enforces tree-unique slugs, refuses a pinned target (`PinnedEntry` - `amend-pinned` is the
deliberate way through). `move` relocates only a pointer LINE (the body never moves); if the
target ALREADY points at the slug with a different hook it REFUSES (a duplicate, not a relocation -
picking by direction would silently discard the richer hook), and `--force` dedups by keeping the
LONGER hook and dropping the other.

**`move` takes a SET of slugs that travels together.** Repeat `--slug` (or name several after one
`--slug`) and the members move as one unit; the down-move ref guard then judges each member by where
the WHOLE set lands, so a member citing another member is not dangling. That is the only way to
demote a MUTUALLY-CITING pair or cluster without `--force`: each one's inbound ref is the other, so
single-slug moves refuse in BOTH orders, and forcing it strands the very ref the guard protects.
Reach for it whenever a down-move refuses with a citer that itself belongs at the target - the usual
shape when shrinking an oversized always-loaded block, because an internally cross-linked cluster is
what accumulates there. A citer OUTSIDE the set still refuses (the guard is set-aware, not weakened),
and the exemption follows the pointer AT the from-level, so a stray duplicate pointer for a moving
slug left higher up still counts. The set is ATOMIC ON REFUSAL: presence, legacy state, refs and
duplicate-pointer conflicts are decided for every member before anything is written, so a refusal
leaves every pointer where it was. The write phase is per-slug add-then-remove, so an interruption
leaves a visible duplicate pointer, never a lost fact - re-run the SAME command to complete it.

`relocate` is the CROSS-TREE move `move` cannot do: it copies
the central body into the TARGET tree's store, points at it there, drops the source pointer and
ARCHIVES the source body - one live copy, old one recoverable. Same-tree it just delegates to
`move` (the body already sits at the right anchor). It refuses a divergent slug in the target tree
(slugs are tree-unique, so landing on one would destroy a different fact) and refuses when the
fact leaving the tree would dangle any inbound `[[ref]]` left behind (`--force` warns instead).

**`move` is CHAIN-ONLY, and it guards only INBOUND refs - promoting a fact strands its OWN outbound
refs.** It walks the altitude chain, so it accepts ancestor <-> descendant only and REFUSES a
SIBLING move (`sibling levels - a move follows the altitude chain`) as well as a cross-tree one; a
fact that belongs under a sibling subtree cannot be relocated there at all, which is a placement
finding to report, not a move to retry. And its ref guard is one-directional: it refuses a DOWN-move
that would dangle refs pointing AT the fact, but never checks the refs the fact itself MAKES. So
lifting a fact to a common ancestor silently strands every `[[ref]]` it makes to facts left below
(measured: a crosstree promotion round took a tree from 2 to 14 `--check-tree` problems). Before
promoting, read the body's `[[refs]]`: lift the genuinely-shared targets too, or demote the
irreducibly-local ones to plain prose. Chasing it by lifting targets alone cascades - each lifted
target drags its own refs up with it.

`heal` runs every session (skip-fast when healthy), is
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
