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
    - [Title](mem:<slug>) - hook <!-- bx:pin -->

    ## Memory index
    - [Title](mem:<slug>) - hook
    <!-- BITRANOX-MEMORY-INDEX:END -->

- **The slug IS the identity** and the body-file key. Every body lives centrally at
  `<anchor>/.claude-memory/facts/<slug>.md` - flat, slug-named, human-readable, greppable. Slugs are
  TREE-unique: the body file is the registry, and the engine refuses a colliding `add` with a
  suggested suffix. Tree-uniqueness is VERIFIED tree-wide by `reconcile_memory_index.py --check-tree`
  (a slug pointed at from two levels is a violation `heal` and the chain-only `--check` both miss),
  with one exception: a fact placed by topic (below) has a line at every level its topics place
  it at, and `--check-tree` judges those lines by the render instead.
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
  CLI prints `! refused:` and exits 2, no body file and no pointer line are written, and on an
  update the existing entry keeps its old hook. Nothing needs cleaning up - rewrite the hook, move
  the surplus detail into the body, and re-run `add`; do not delete detail to fit. The hook must
  stay self-sufficient: keep the load-bearing names, paths, flags, and numbers in it, even if that
  pushes it past the soft cap.
- **The body is FRAMED as a native memory entry**: the frontmatter block below, ahead of the prose
  (probe-verified ~5x application lift over bare prose - the model discounts bodies that do not
  look like genuine memory entries). The engine writes that frame automatically. The `title:` line
  carries the pointer's title as data: an engine write that rewrites a body (`add`, `amend-pinned`,
  `retitle`, factedit's `apply`) keeps the two equal by setting it from the pointer, so a stale
  `title:` in a body handed back is overwritten, never copied to the pointer, and
  `heal --backfill-titles` fills it into bodies written before it existed. A `topics:` line
  (`topics: [python, uv]`, written after `title:`) lists the topics the fact is bound to, at most
  12 and each from the tree's closed list; `topics: []` means it was tagged and is bound to none,
  and no line means it was never tagged. An `add`, `amend-pinned` or factedit `apply` that
  updates the fact keeps what is stored (the line, a line that does not parse, or no line),
  whatever the body handed in says, and an `add` that creates a fact refuses a body whose
  frontmatter carries a `topics:` line (`TopicsOnCreate`, printed as "! refused: '<slug>' has no
  body file yet and the body given carries a frontmatter topics: line; ...", nothing is written):
  add it without the line, then run `set-topics`. So `set-topics` is the only verb that sets a
  fact's topics. Besides its `--clear`, one other verb removes the line: a cross-tree `relocate`,
  whose copy leaves it behind (see `relocate` below). Only the leading frontmatter is read, so a
  `topics:` line in the prose is never touched. A body's `topics:` line or a descriptor's
  `TOPICS:` line does not parse when it holds a tag that is no valid topic name or more than 12
  tags. A line with no tag parses, and so does one holding a valid name that is missing from the
  tree's list: the list is checked when a topic verb writes, not when a stored line is read. The
  `**Why:**` and `**How to apply:**` labels are the authoring template, not the measured frame:
  write them, but a body that carries its reasoning in prose without them is not discounted by
  anything measured.

      ---
      name: <slug>
      description: <the hook>
      title: <the pointer's title>
      metadata:
        type: feedback | project | reference | user
      ---

      <the fact, 1-3 short paragraphs>

      **Why:** <the reasoning / the failure that taught it>

      **How to apply:** <the concrete procedure or check>

- **Write the hook AND the body in English, whatever the conversation's language**, so the store
  stays uniform. When you rewrite or touch a fact whose body is in another language, translate it;
  do not mass-translate the store unprompted.
- **No STATUS in a hook, body or slug** - shipped/deployed/TODO, issue or task IDs, branch names,
  "fixed in X.Y". An always-loaded pointer never updates, so it rots while still reading like a
  durable lesson, and a slug outlives every body edit. State the mechanism or decision and point
  at the owner that does update (TODO.md, git, a doc's status section). Reword or narrow a stale
  one, never delete it; `statusrot.py` and `versionrot.py` in `bitranox:meta-dream-tree` scan for
  them.
- **Resolve a fact's LEVEL from its pointer, never from its body's path.** Every body sits at
  `<anchor>/.claude-memory/facts/` whatever level owns it, so the body path reads "tree top" for
  every fact. Before an amend, any claim about a fact's altitude, or a backlog note calling it out
  of reach, find the level whose `CLAUDE.local.md` carries `mem:<slug>` (with `find`, since those
  files are usually gitignored) and pass that to `--proj`/`--level`. A tool reporting
  `no pointer for <slug> at any level` means the level is wrong, not the fact.
- Related facts link with `[[slug]]` references - UPWARD ONLY along ONE ancestor chain (a project
  entry may cite a tree-top rule; a higher entry never cites a lower one, or deleting the project
  would dangle it). Citing a SIBLING project's slug is as invalid as citing a child: the cascade
  only flows DOWN one ancestor chain, so a sideways ref never loads where the citing entry does and
  dangles. `--check` catches a sideways ref only when its chain happens to include the citing level;
  `--check-tree` catches it TREE-WIDE (a ref whose target is not on the citing fact's ancestor-or-self
  path, even though the target resolves somewhere in the tree). When in doubt, demote the link to plain
  prose - or, if the target is genuinely shared, lift it to a common ancestor so the ref becomes upward.
- **Before writing a ref, ask where its TARGET lives, not only whether it exists.** At write time
  `add` warns only about a ref whose target exists nowhere; a ref whose target exists but sits off
  the citing fact's ancestor chain passes silently, and only `--check-tree` reports it
  (`sideways/downward ref ... target exists but not on this level's ancestor chain`). At the tree top almost
  everything is below you, so prefer prose naming the lower fact's subject over a link to it.
- **Every double-bracket token in PROSE is a live ref**, including an illustrative example and a
  TOML array-of-tables header, and `--check-tree` then reports an orphan ref to a fact named after
  the bracketed word. Only an inline code span or a fenced block is masked, so quote such syntax in
  code ticks or write it as plain words.

A level's scope descriptor may carry one line `TOPICS: python, uv`: the topics this directory
has, at most 12 and each from the tree's list. To record that a fact is read only where a topic
is, bind the fact with `set-topics` and give each such directory the topic with
`set-level-topics`. `set-level-topics` refuses the tree top. The top's line is set with
`set-top-topics`, which refuses every other level and is run only on the user's decision, never
by a nap or dream on its own, because the top's block is read by every session of the tree.
Both refuse a level that has no descriptor yet. Both name a level by its path, never following
a symlink: a level reached through a symlinked directory is keyed by its own path below the tree
top and reads like any other level, and a path that is not below the tree top is refused. Each
checks the topic file (list present, level keyable) before it writes the descriptor, so a refusal
there writes neither file; an OS error writing the topic file after the descriptor was written
is `! error` (exit 2), and `topics-stale` then reports the level stale until the verb is run
again.

Every write of a descriptor passes one `TOPICS:` gate: `set-scope`, `add --scope` /
`--scope-file`, and the setup of a level that moves a legacy `CLAUDE.md` scope block into the
pointer block. The legacy block, while it is there, is the level's current descriptor, read
without being moved. The gate keeps the stored line when the new text has none and accepts the
same line. It refuses, before anything is written, a text that carries a different `TOPICS:`
line or adds one to a level that has none (an empty `TOPICS:` line counts), printing "! refused:
a descriptor's TOPICS line changes only through set-level-topics (set-top-topics at the tree
top); leave the line out of the new text"; a new line that does not parse is refused as an
invalid topic. It refuses every text while the stored line does not parse: replace a pointer
block's line with `set-level-topics` (`set-top-topics` at the top) first. A legacy block whose
line does not parse refuses `set-scope`, `add` and every other verb that would set that level
up, exit 2 and nothing written, printing "! refused: the legacy scope block in <path>/CLAUDE.md
has a TOPICS line that does not parse (<reason>); fix or remove that line there by hand, then run
this again"; `set-level-topics` reads only the pointer block, so it cannot replace that line
either. The three commands that set up a whole chain are the exception to that exit 2:
`ensure-memory-structure`, `heal` and `ensure-all-trees --apply` leave such a level and its
`CLAUDE.md` as they are, set up the rest of the chain, and name it with one line per level:
"    ! refused level, left untouched: the legacy scope block in <path>/CLAUDE.md has a TOPICS line
that does not parse (<reason>); fix or remove that line there by hand, then run this again
[<level>]". The line does not change their exit code (0 when nothing else went wrong).
`set-scope` holds the level's lock for its whole read, check and write.

The tree's closed topic list, with a one-line meaning per topic, is
`<anchor>/.claude-memory/topics.json`, written by `topics-set-list`: 1 to 64 topics, each name
lower case letters, digits and dashes (at most 32 characters, starting with a letter or digit),
each meaning one line of at most 200 characters. A tree without that file has no topics:
`set-topics`, `set-level-topics` and `set-top-topics` refuse there, `topics-show` exits 1 and
`topics-stale` prints `fresh`. With a list, `topics-stale` reports a level as stale when it has
no descriptor, no `TOPICS:` line, a `TOPICS:` line that does not parse, or a descriptor whose
other lines differ from the text its topics were set on.

**A fact placed by topic.** A fact is placed by topic when its body is bound to at least one
topic (a non-empty `topics:` line), holds the `title:` and `description:` its line is built from,
has a line at some level, and no line of it is pinned or a legacy `uuid:` line at any level
(either one keeps the whole fact where its lines are, so the tree and chain renders,
`--check-tree`, `mem_levels.py`, `ref_map.py` and `topic_tagging.py` all treat it as unplaced, and
an un-bind leaves its lines as they are). Its lines then belong to
`render-topics`: one line at each level that has one of its topics while no level above it does,
and one line at the tree top when no level has any of them, each built from the body's `title:`
and `description:`. Every other line (pinned, legacy, unbound, `topics: []`) is never added,
dropped or rewritten by the render. A bound body that lacks `title:` or `description:` keeps its
lines where they are, and the render lists it: `~ N tagged fact(s) have a body without title: or
description: and stay where they are: <slugs>`.

`render-topics --proj D --scope tree|chain [--dry-run] [--json]` places them:

- `--scope tree` renders every level of D's tree, adding every missing line before it removes
  any, so an interruption leaves a line twice, never a fact with no line. Nor does its remove pass
  drop a line whose fact has no line, read back from disk, at any level its topics place it at
  (its body changed during the render without the placement lock, for example by hand): that line
  is kept, counted as `kept` in the `--json` row of its level, and named in `~ warning: kept N
  line(s) placed elsewhere, ... Run render-topics --scope tree again to place them`.
- `--scope chain` renders only the levels from D up to the tree top and writes no file off that
  chain: it adds no line below a level of the chain that already holds it, drops such a lower
  copy, and leaves a line placed at some other level for a tree render to sweep. Run the tree
  scope after topics change; the chain scope is the repair `--check` names for a repeated line.
- It prints one `  <level>: +N added, N refreshed, -N removed` line per level it changed, then
  `render-topics (<scope>): N managed fact(s); changed N level(s)` (`would change` with
  `--dry-run`); `--json` prints one object with the same counts instead. A tree with no topic
  list prints `no topic list in this tree: nothing is placed by topic`, exit 0.
- `--dry-run` writes nothing and takes no lock, so it runs on a read-only tree, beside a lock
  another session holds and under `BITRANOX_MEMORY_WRITES=off`; without `--dry-run` that switch
  refuses it, exit 2. A real run holds the tree's placement lock (below) from its walk over the
  levels to its last drop.
- Before the first write it refuses, exit 2 and `! refused:`, the dry run too: a level whose
  `TOPICS:` line does not parse ("set-level-topics replaces it"), a tree top with no pointer block
  ("ensure-memory-structure writes one"), and a level whose block it would leave past the block
  cap and larger than it is now.

**The block cap.** One level's pointer block may hold at most 1048576 bytes (1 MiB) of lines,
each line counting its line break. Every writer of a block follows one rule against it: a write
is refused only when the block would END past the cap AND be larger than it is now. So a write
that leaves an over-full block no larger than it is goes through (a render adding nothing there,
a refresh to a line no longer than before, a drop), and one over-full level never stops the
renders and writes that do not make it fuller. What a render counts is the lines that stay at
the level (pinned, legacy and unplaced lines, plus, in a chain render, lines placed at another
level that it does not drop) and every line the render places there; a line the run drops never
counts. A render that would end past the cap and grow the block refuses before its first write (a block that grows while it runs can still
stop it at that level, before any line is dropped) and names the one route that can free
the bytes: a tree render when the lines placed elsewhere are what push it over; a `move` of the
kept lines to another level of the altitude chain when they are the larger part; a
`set-topics --proj <level> --batch <file>` rebinding the facts that need not be read there when
the placed lines are; both, with the amount of each, when neither part alone is enough.
`--check-tree` reports the same condition as `! the placement by topic could not be checked:
<why>`. `move` and `relocate` hold the level they move lines to to the same cap: "! refused:
moving these lines to <level> would leave its block at N bytes, M bytes over the 1048576 bytes
one level's block may hold ...", naming how many of the lines fit there, smallest first, and to
move the rest to another level of the altitude chain that has room. When none fits, it says
"None of the lines fits there: move them to another level of the altitude chain that has room,
with <route>, or first free room at <level> by moving lines out of it with <route>". Exit 2,
nothing written. `add` and `amend-pinned` (every level a placed fact's line is rewritten at,
all checked before any is written), `retitle` and `rename` (every level holding a line of the
fact) follow the same rule: "! refused: <verb> would leave the block at <level> at N bytes, M
bytes over the 1048576 bytes one level's block may hold and K bytes larger than it is now ...",
naming how many bytes shorter the hook or title must make the line (characters shorter for a
`rename`'s slug), with the command to run again - a line no longer than the one there now
always goes through - or, for a new fact, another level of the altitude chain to add it at;
and, second, how many bytes to free at that level by moving lines out of it. Exit 2, nothing
written.

**The placement lock.** A level's lock covers that one file, and a render, a `set-topics` and a
write to a placed fact each read and write several levels and a body, so each of them also holds
ONE lock for the whole tree, `<anchor>/.claude-memory/placement.lock`, across all of its reads and
writes: `render-topics` (a real run, either scope), `set-topics` (from its row checks to its last
body write, a collapse's line writes included, `--batch` too), `add` of a fact whose body is
bound to a topic (`factedit.py apply` writes through `add`, so it holds it too), and `rename`,
`retitle` and `reconcile_memory_index.py --archive` of any fact in a tree that has a topic list
(they read and write level after level, so a fact bound, placed and un-bound by peers between
two of their steps could get a line put back). So no render runs between a collapse's line writes
and its un-bind, and no `set-topics` between a render's add and remove passes. An `add` of a fact
bound to no topic, any verb in a tree without a topic list, dry runs and checks take none. It is taken
before any level lock and never while one is held, so the two kinds cannot deadlock. A verb waits
up to 30 s for it, then exits 2 with `! error: <verb> waited 30 s for the placement lock of the
tree <anchor> (<lock file>): another render-topics, set-topics, or write to a fact placed by topic
holds it. Run <verb> again once that one finishes; a lock left by a holder that crashed is
reclaimed once it is 120 s old`. Reclaiming is the level locks' rule (the lock file's mtime), and
a holder keeps its lock fresh while it works: a render refreshes the lock file's mtime at each
level it walks in each pass and `set-topics` at each row, whenever it is more than 30 s old. So
only a holder that crashed or stopped walking has its lock reclaimed.

What the other verbs do with a fact placed by topic:

- `set-topics` binding a fact (`--topics`, or a batch row carrying topics) refuses the whole
  call, the dry run too, while no line can be rendered from its body yet, and names the repair
  to run before tagging it: no `title:` - `hooks/memory_engine.py heal --proj <anchor>
  --backfill-titles` (or `skills/meta-dream-tree/factedit.py apply --slug S --level L --title T`);
  no `description:` - `factedit.py apply --slug S --level L --body-file F` (or
  `add --proj L --slug S --title T --hook-file F --body-file F`); a line that differs from what the
  body renders - `factedit.py apply --slug S --level L --hook-file F` (or
  `add --proj L --slug S --title T --hook-file F`); a legacy `uuid:` pointer -
  `hooks/migrate_to_slug_store.py --root <anchor> --apply`.
- Un-binding (`--clear`, `--universal`, a batch row `null` or `[]`) leaves a fact that had lines
  at several levels one line, at the tree top, and says so: `~ note: N un-bound fact(s) had a line
  at several levels; each now has one line, at the tree top: <slugs>` (`each would keep one line`
  with `--dry-run`). When those lines would take the top's block past the cap, the call is refused
  before any write, the dry run too ("un-binding these facts leaves one line of each at the tree
  top ..."), naming the route: a tree render, a move of lines out of the top, a rebind, or fewer
  facts un-bound per call.
- `add` from a level that holds no line of it is refused (exit 2, `! refused:`), naming the
  levels it is read at; from a level that holds one it updates the body and every line.
  `add --pin` of a fact placed by topic is refused, exit 2: un-bind it first
  (`set-topics --proj <anchor> --slug S --clear`).
- `move` and `relocate` refuse it (exit 2, `! refused:`, nothing written): where it is read
  follows its topics and the levels'. To place it by hand, un-bind it first; its lines collapse
  to one at the tree top, where a move or relocate takes it.
- `rename` and `retitle` change every line of it; `retitle` prints `also retitled at: <levels>`.
- `reconcile_memory_index.py --archive S D` drops every line of it: the other levels' lines
  first, then it moves the body and drops D's line (a failed write of D's block moves the body
  back), so the archive is always its last pointer and the inbound check always applies. It
  prints `archived S (pointer dropped at D and at the N other level(s) its topics place it at:
  <levels>)`. A failure after some lines were dropped exits 2: the message
  names the dropped lines and the ones left, the body is not archived, and it names both repairs -
  re-run the same `--archive`, or put the dropped lines back with `render-topics --scope tree`.

`set-topics --batch F` reads its whole JSONL file, one line at a time, before it changes any
fact, and stops at the first problem: each of these is `! error` on stderr, exit 2, naming the
line, and no fact is changed - a line longer than 4096 bytes (its line break counted), a file
holding more than 5000 rows, a slug named twice ("slug '<s>' is named twice (first on line M)"),
a line that is not UTF-8 ("is not UTF-8 (byte at offset K) - re-save it as UTF-8"), and a line
that is no `{"slug": ..., "topics": ...}` object, too-deep nesting included. A leading BOM is
accepted. A `--topics` value that is no topic list, on `set-topics`, `set-level-topics` or
`set-top-topics`, is a usage error: `! error: --topics '<value>': <reason>` on stderr, exit 2. A
pinned fact may lose its line (`--clear`, or a batch row `null`, which leaves the rest of the body
byte for byte as it was) but is never tagged: "<slug> is pinned; a pinned fact stays where it is
(only --clear may change it)". `set-topics --dry-run` writes nothing, so it also runs under
`BITRANOX_MEMORY_WRITES=off` (exit 0, `would set topics on ...`); without `--dry-run` that switch
refuses it, exit 2.

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

**Capture with `add`, never with a hand-written body plus `--rehome`.** `reconcile_memory_index.py
--rehome` is a REPAIR verb that re-attaches a body which lost its pointer; it runs none of `add`'s
validation (hook hard cap, type vocabulary, slug), so a hand-written `facts/<slug>.md` attached that
way can put an over-cap hook straight into the always-loaded index while `--check-tree` still
reports `TOTAL tree problems: 0` (reference integrity is a different question from entry validity).
If a body was already hand-written, re-run `add --slug <slug>` over it so the validation executes.

**A stranded body does not fail `--check-tree`.** A body no level points at (its level dir was
deleted or re-cloned, or its pointer line was lost) prints as
`~ dangling body (no pointer at any level): <slug>` plus a `TOTAL dangling bodies: N` line marked
advisory, and neither counts toward `TOTAL tree problems`, so a run ending
`TOTAL tree problems: 0` can still carry stranded bodies: read the dangling lines, not only the
total. With any level or store dir unreadable the danglers are not assessed at all (that run exits
2). `--check-misplaced` cannot see a stranded body either: it judges a fact only by the absolute
paths in its body. Re-attach with `--rehome` (default target the tree top; `--rehome-to LEVEL`
keeps a subtree's danglers in that subtree), or re-run `add --slug <slug> --proj <owning level>`,
which adopts a dangling body there when no other level on that chain still points at it.

| Command                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Success line to REQUIRE                                                                                                                                                              |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `add --proj D --title T --hook H\|--hook-file F --body-file F [--type feedback\|project\|reference\|user] [--pin] [--scope TEXT] [--slug S]` [--skill NAME]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | the printed slug                                                                                                                                                                     |
| `amend-pinned --proj D --slug S [--title T] [--hook H\|--hook-file F] [--body-file F] [--type feedback\|project\|reference\|user]` (the deliberate way through - an ordinary `add` REFUSES a pinned slug, and so does `retitle`; human use only, no autonomous pass invokes this verb)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | the printed slug                                                                                                                                                                     |
| `heal --proj D`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `healed N file(s) across M level(s)`                                                                                                                                                 |
| `heal --proj D --backfill-titles` (every level of D's tree, a one-off: copies each pointer's title into a body that has no `title:`; never rewrites one that has; plain `heal` never opens a body. A skipped body prints a `~ ... left as it is: <slug>` or `! missing central body (not fabricated): <slug>` line; an unreadable body or level exits 2)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | `back-filled N title(s); M body(ies) already had one`                                                                                                                                |
| `set-scope --proj D --scope TEXT\|--scope-file F`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | `scope updated:` / `scope unchanged:`                                                                                                                                                |
| `topics-show --proj D [--json]` (D is any dir of the tree)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | `tagger: T`, then one `<topic> - <meaning>` line per topic (one JSON object with `--json`); `no topic list in this tree` and exit 1 when it has none                                 |
| `topics-set-list --proj D --from-file F` (F is JSON: `{"tagger": "jev"\|"opus", "topics": {"<tag>": "<meaning>"}}`; replaces the whole list; refuses an empty list, more than 64 topics, and a list that drops a topic a fact or a level's `TOPICS:` line still uses - names are compared trimmed, and a level whose `TOPICS:` line or a fact whose `topics:` line does not parse is skipped)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `topic list updated: N topic(s), tagger T` / `topic list unchanged: ...`                                                                                                             |
| `set-topics --proj D --slug S --topics a,b\|--universal\|--clear [--dry-run]` or `set-topics --proj D --batch F.jsonl [--dry-run]` (`--universal` writes `topics: []`, `--clear` removes the line; a batch line is `{"slug": ..., "topics": [...]}`, `[]` for bound to none, `null` to remove the line, at most 5000 rows. Every row is checked before any is written: an invalid slug, a slug no level points at, a pinned fact, a topic outside the list or a body without frontmatter refuses the whole call, and so does binding a fact no line can be rendered from yet (no `title:` or `description:`, a line that differs from its body, a legacy `uuid:` pointer) and an un-bind whose collapse to one line at the tree top would pass the block cap, each naming its repair (see "A fact placed by topic"); the batch file's own limits and the pinned and dry-run rules are in the paragraph after the topic list) | `set topics on N fact(s); M unchanged` (`would set topics on ...` with `--dry-run`)                                                                                                  |
| `set-level-topics --proj LEVEL --topics a,b` (`--topics ''` writes the line with no topic: tagged, and the directory has none; refused at the tree top, for a topic outside the list, and for a level with no descriptor; a `--topics` value that is no topic list is a usage error)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `topics updated: <LEVEL>` / `topics unchanged: <LEVEL>`                                                                                                                              |
| `set-top-topics --proj ANCHOR --topics a,b` (the tree top's line; run on the user's decision only, never by a nap or dream on its own; refused at any other level; a `--topics` value that is no topic list is a usage error)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `topics updated: <ANCHOR>` / `topics unchanged: <ANCHOR>`                                                                                                                            |
| `topics-stale --proj LEVEL`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `fresh` (exit 0) or `stale: <why>` (exit 1)                                                                                                                                          |
| `render-topics --proj D --scope tree\|chain [--dry-run] [--json]` (places the lines of every fact placed by topic; `tree` renders every level, `chain` the levels from D up; `--dry-run` writes nothing and takes no lock; refused, exit 2, by a `TOPICS:` line that does not parse, a top with no pointer block and a level past the block cap; see "A fact placed by topic")                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `render-topics (<scope>): N managed fact(s); changed N level(s)` (`would change` with `--dry-run`); `no topic list in this tree: nothing is placed by topic` (exit 0) without a list |
| `move --from-level A --to-level B --slug S [--slug S2 ...] [--force]` (several slugs move as ONE set; see below; refuses a fact placed by topic, and a move that would take the target's block past the block cap)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | `moved <slug>: A -> B (up\|down)`                                                                                                                                                    |
| `relocate --from-level A --to-level B --slug S [--force]` (refuses a fact placed by topic, and a target block the lines would take past the block cap)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | `relocated <slug>: A -> B (...)`                                                                                                                                                     |
| `rename --level D --slug S --to-slug S2` (fix a WRONG NAME: `move`/`relocate` change a fact's level, never its name; this repoints every inbound `[[ref]]` so nothing is orphaned; a fact placed by topic is renamed at every level holding a line of it)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `renamed <slug> -> <slug2> at D`                                                                                                                                                     |
| `retitle --level D --slug S --to-title T` (fix a STALE TITLE - the pointer's link text - leaving slug, hook and prose untouched; the body's `title:` line follows the new title; refuses a pinned fact, which goes through `amend-pinned --title`; a fact placed by topic is retitled at every level holding a line of it, printed as `also retitled at: <levels>`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `retitled <slug> -> '<title>' at D`                                                                                                                                                  |
| `lint --tree D`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `TOTAL over-cap hooks: N \| ...`                                                                                                                                                     |
| `tree-top --proj D [--json]`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | the printed top/store lines                                                                                                                                                          |
| `ensure-all-trees [--roots ...] [--apply]`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | the `DRY-RUN:`/`APPLIED:` report                                                                                                                                                     |
| `skills/meta-self-improve/reconcile_memory_index.py --check <chain narrow->broad>` (a SEPARATE script, NOT an engine verb - it lives in this skill's dir, same `run-python.sh` launch; also reports `! repeated line: <slug> at <level> is also held by <upper> above it`, a fact placed by topic held twice on the chain, which `render-topics --proj <level> --scope chain` drops)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `TOTAL problems: 0`                                                                                                                                                                  |
| `skills/meta-self-improve/reconcile_memory_index.py --check-tree D` (TREE-WIDE: cross-sibling duplicate pointers, orphans, sideways/downward refs, dangling that `--check`/`heal` miss; a fact placed by topic is judged by the render instead of as a duplicate: `! render drift: <level> -> N line(s) missing, N differing from the body, N placed elsewhere (<slugs>)`, repaired by `render-topics --proj <anchor> --scope tree`, and `! the placement by topic could not be checked: <why>` when the render would refuse; both count as tree problems)                                                                                                                                                                                                                                                                                                                                                                   | `TOTAL tree problems: 0`                                                                                                                                                             |
| `skills/meta-self-improve/reconcile_memory_index.py --archive S D [--force]` (forget a fact: drop its pointer at D + move its body to `.archive/`; the LAST pointer refuses, exit 1, while a fact links or names S or a level's CLAUDE.md names it - `--force` archives anyway; a fact placed by topic loses every line, the archive always being its last pointer, and the output names the other levels)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | `archived <slug> ...`                                                                                                                                                                |
The `--check-tree` success line counts problems only: a run that prints it can still carry
advisory `~ dangling body` lines, which the paragraph above the table says how to read.

**Fail-loud contract:** run engine calls with `BITRANOX_RUN_PYTHON_STRICT=1`, require the command's
success line in the output, and ABORT-AND-SHOW on any miss (a refused move prints `! refused:` and
exits 2; a colliding add prints `! refused:` with a suggested slug). Never continue past a silent or
malformed engine result.

**Engine exit codes:** 0 done. 1 only from the three verbs that are a check, when their answer is
no: `lint --tree` when it reports anything, `topics-show` when the tree has no topic list,
`topics-stale` when the level is stale. 2 whenever the action did not happen, and the printed
line says which kind: `! refused: <why>` on stdout when the engine declined the whole write
(collision, hook over the hard cap, empty body on a new fact, pinned target, unknown or invalid
slug, excluded altitude, a refused move/relocate/rename/retitle, a refused topic write, a new
fact whose body brings a `topics:` line, a descriptor text from `set-scope` or `add --scope`
that brings or changes a `TOPICS:` line, a legacy `CLAUDE.md` scope block whose `TOPICS:` line
does not parse; nothing is written), or `! error: <why>` on stderr when it could not run (a
usage error, a `--topics` value that is no topic list included, an input file it could not read
or decode, a `set-topics --batch` file over its limits, a store it could not read, a
`topics.json` that `topics-show` or `topics-stale` cannot use, a level lock or the placement
lock held past its timeout, a failed write). Among the topic verbs one failed write leaves a change behind: the
topic file write that `set-level-topics` or `set-top-topics` makes after writing the descriptor
(see the descriptor paragraph above). `heal` exits 2 when it left a level it could not read
untouched. A refusal is fixed by changing the input (rewrite the hook, pick the suggested slug,
use `amend-pinned`); an error by fixing the file, path or permissions it names.

**Pass a hook or a scope descriptor as a FILE, never through a shell substitution.** A hook runs to
500 chars and a scope descriptor is multi-line, so the tempting form is `--hook "$(cat f)"` - but
that is a command substitution the SHELL evaluates, and the plugin's own `shell-prefix-selfref-guard`
denies it (it cannot tell a benign `cat` from prose that executes). The denial also discards the
WHOLE pending command, so a heredoc writing that file in the same call dies with it and the next
call fails on a missing input, pointing at the wrong cause. Use `--hook-file` / `--scope-file`
instead (the file wins if both forms are given, matching `--body-file`); either verb stops with
`! error: pass --X or --X-file` (exit 2) when neither is present. `set-scope` checks both a missing
flag and its `TOPICS:` refusals BEFORE it scaffolds the level, so either rejection on a directory
that is not a level yet leaves nothing behind.

`add` semantics: upserts by slug (title-derived unless `--slug` targets an existing identity),
leaves an unpinned entry unpinned, keeps the existing body when `--body` is empty, frames a bare
body, enforces tree-unique slugs, refuses a pinned target (`PinnedEntry` - `amend-pinned` is the
deliberate way through). A slug names the body FILE, so `add`, `amend-pinned`, `rename --to-slug`
and `relocate` refuse one that is not a plain filename (lowercase letters, digits, hyphens and
dots, starting and ending with a letter or digit) before anything is written. On an update,
`--type` with no body re-types the stored body in place; an unknown `--type` is refused.
`--scope` / `--scope-file` is the descriptor written for a level that has none (no pointer-block
descriptor and no legacy `CLAUDE.md` scope block); on a level that has one it is ignored,
unchecked. It passes the `TOPICS:` gate above: a `TOPICS:` line in it, an empty one included, is
refused (exit 2), and nothing is written - no body, no pointer, no `CLAUDE.local.md`, and
`CLAUDE.md` untouched.
`--skill NAME` (`bitranox:compuse-git`) records the skill a fact is tied to as `metadata: skill:`
in the body's frontmatter, for a fact written beside a fix queued against that skill; like
`--type` it is kept on an update that omits it, and given with no body it tags the stored body. A
name that is not `name` or `plugin:name` in lower case is refused (`InvalidSkill`). A hook or
title that spans several lines (a wrapped `--hook-file`) is joined onto one pointer line, since a
line break would split it. `--proj .` means the cwd; HOME, the temp dir and the filesystem root are
refused, a symlink to one of them included. `add`, `set-scope`, `move` and `relocate` also refuse
a level whose path crosses a directory every walk over the tree's levels prunes, exit 2 and
nothing written ("! refused: <path> is no memory level: its path crosses '<name>', a directory
every walk over the tree's levels prunes ..."): the names in `uuid_store.NON_LEVEL_DIRNAMES`
(`.git`, `node_modules`, `venv`, `site-packages`, `build`, `dist`, `target`, the tool caches and
the rest of the vendored dirs), a name starting `.venv`, `venv-` or `venv_`, and any directory
whose name starts with the store dir's name (`.claude-memory`).
It is one rule, `uuid_store.is_non_level_dirname`, so a level the
engine accepts is a level every walk finds; `venvnotes` or `vendor` stay ordinary names.
`move` relocates only a pointer LINE (the body never moves); if the
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
`move` (the body already sits at the right anchor). It refuses when the target tree already holds
a DIFFERENT body under that slug, whichever level points at it or none (slugs are tree-unique and
the body file is the registry, so landing on one would destroy a different fact); an IDENTICAL body
there is an interrupted relocate, and re-running the same command completes it. It also refuses
when the fact leaving the tree would dangle any inbound `[[ref]]` left behind (`--force` warns
instead). The cross-tree copy drops the body's frontmatter `topics:` line, because topics are
tagged against one tree's list, and prints "~ note: dropped the topics: line of <slug> - topics
are tagged against one tree's list; tag it in the target tree with set-topics". A same-tree move
leaves the body untouched, and a `topics:` line in the prose is never touched.

**`move` is CHAIN-ONLY, and it guards only INBOUND refs - promoting a fact strands its OWN outbound
refs.** It walks the altitude chain, so it accepts ancestor <-> descendant only and REFUSES a
SIBLING move (`sibling levels - a move follows the altitude chain`) as well as a cross-tree one.
Do not retry the refused sideways command: a fact that belongs under a sibling subtree is re-homed
in TWO moves through the common ancestor (up, then down), and the second leg strands any outbound
ref whose target sits on the old chain only, so run `--check-tree` afterwards and require
`TOTAL tree problems: 0`. And its ref guard is one-directional: it refuses a DOWN-move
that would dangle refs pointing AT the fact, but never checks the refs the fact itself MAKES. So
lifting a fact to a common ancestor silently strands every `[[ref]]` it makes to facts left below
(measured: a crosstree promotion round took a tree from 2 to 14 `--check-tree` problems). Before
promoting, read the body's `[[refs]]`: lift the genuinely-shared targets too, or demote the
irreducibly-local ones to plain prose. Chasing it by lifting targets alone cascades - each lifted
target drags its own refs up with it.

`heal` runs every session (skip-fast when healthy), is
CHAIN-scoped and normalizes drifted grammar only; a pointer whose body is missing is REPORTED, never
fabricated - it does NOT detect cross-sibling duplicate pointers, which is `--check-tree`'s job.
A level `heal` cannot read is reported and left untouched, and the run then exits 2.
`heal` re-renders each level's pointer block from the parsed pointer LINES alone and never opens a
fact body, so it is safe to run while other sessions hold uncommitted body edits in the shared
store: those edits cannot reach the always-loaded index through it. The converse bites: editing a
body's `description:` never updates its pointer hook, heal or no heal, so a body-only correction
stays invisible to every later session. Change what a fact broadcasts through the engine at the
level that owns its pointer (`add --proj <owning level> --slug <stored slug>` with the new hook,
or `skills/meta-dream-tree/factedit.py apply --hook-file`). The only place a body's `description:`
becomes a hook is `add` adopting a DANGLING body (one whose pointer was lost). What heal does drop:
a pointer line whose slug is not a plain filename is removed by the normalisation and reported
under `invalid_pointers` - read that list rather than assuming the block came back unchanged.
`lint --tree` is the read-only voice/style sweep (over-hard-cap hooks, trigger-less hooks, bodies
without the Why/How labels - a style advisory, not a backlog to clear). It exits 1 when it reports
anything and 0 on a clean tree; the 1 is the answer of a check, not a failure to act on.

## Keeping it lean

One fact per entry. Dedup BEFORE writing: grep the pointer blocks + `facts/` bodies + native tier;
sharpening an existing fact is the SAME `add` (same slug) - not a new entry. The pointer block is
always-loaded context: hooks short, detail in the body. Block size is advisory
(`reconcile_memory_index.py --check` warns, never fails); growth is the dream's cue to dedup, merge,
and re-level with `move`.
