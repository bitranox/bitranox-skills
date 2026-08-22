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
- **`propose`** (default): apply safe private-memory consolidation; apply CLAUDE.md consolidation
  under the reachability invariant (see Boundaries) and REPORT every file touched; route skill
  changes to a self-PR. Mention the `dream_mode` knob (`bitranox:meta-memory-settings`) at the end.
- **`auto`**: no per-change prompts - CLAUDE.md edits as above, plus ship skill changes directly.
- **`off`**: no nudges; a manual run consolidates PRIVATE memory only.

## Boundaries (the whole family; skills point here, they do not restate it)

- **Private memory + the curated stores:** back up, then apply (reversible via the backup).
- **`CLAUDE.md`:** back up, then apply, then REPORT per file. A rule may be REMOVED only when the
  reachability invariant holds (`dream-passes.md` -> "CLAUDE.md reconciliation"): a covering rule at
  an ANCESTOR directory, delivered as always-loaded text. Otherwise rewrite in place and keep it.
  Git tracking is not a factor - it decides whether an edit needs a commit, never whether a rule
  reaches context.
- **Skills / hooks (shared, published):** never silently edit; route through the upstream-PR loop.
- **Pinned entries:** the engine REFUSES an ordinary `add` on a pinned slug (`PinnedEntry`);
  `amend-pinned` is the deliberate way through, human-only - the dream never calls it. Report a
  pinned fact whose content looks wrong; do not rewrite it. `move`/`relocate`/`rename` carry the
  pin through unchanged and never refuse on it, so re-leveling a pinned fact is ordinary placement
  work, no exception. `retitle` is the exception: it REFUSES a pinned fact and names
  `amend-pinned --title`, so a pinned fact's stale title is reported, never fixed in passing. Archiving is NOT gated by the engine (`reconcile_memory_index.py --archive`
  does not check `pin`) - treat it as un-archivable by the dream's own policy anyway: report it,
  never drop its pointer.
- **Structural moves** (relocating a directory, migrating a memory slug, creating a rung): always
  PROPOSED with consequences, never applied by the dream.

## Capture-first (unconditional on a manual run)

Enumerate this session's durable learnings and capture via `bitranox:meta-self-improve` BEFORE
consolidating. `not-due` never suppresses capture; an absent store is the trigger to CREATE one;
routing a learning only into a CLAUDE.md is NOT capture. Verify "nothing durable" - never assume.

**Read the session from DISK, not from what you remember.** Run
`dream_state.py session-review "<cwd>" > review.txt 2>&1` first and read the file - the
redirect is not optional, see the truncation note below. Your context is not the session: a compaction clears
the CONTEXT while the transcript FILE survives intact, so anything you "skim from memory" after a
compaction is the summary, and the detail is silently lost. `session-review` returns the material
from disk: the not-yet-reviewed transcript stretch, the SUBAGENT learnings buffered this session
(they are NOT in your transcript at all and die uncaptured), the touched-path ROUTING EVIDENCE
(which repos this session edited that are not the cwd - route `--proj` by SUBJECT), and the SKILLS
INVOKED tally (real data, not recall: if a miss shipped DESPITE a skill that ran, that is the
skill's coverage gap - flag it per `flag-a-skill-when-a-real-bug-slips-past-it`). It is
INCREMENTAL: a per-reviewer watermark means an already-consumed prefix is never re-read, so a second
dream in one session costs nothing and re-analyzes nothing. When the pass is done, run
`dream_state.py session-reviewed "<cwd>"` to advance the mark. If a compaction happened, the Stop
gate will not let the session stop until this nap has run.

**Redirect `session-review` to a file. Its output is truncated otherwise, and it does not say
so.** Run it as `dream_state.py session-review "<cwd>" > review.txt 2>&1` and read the file. The
harness only truncates what it RENDERS into the transcript, never what the process writes to a
file, so the redirect avoids the problem instead of repairing it afterwards. Measured: one run
reported 1,590,075 unreviewed bytes in its banner and left 1,590,965 bytes on disk - banner plus
content, the whole stretch, in one pass.

Rendered inline the same call is silently cut: the harness PERSISTS the result to its own file and
shows a short preview, and that file is a VIEW of the stretch, not the stretch. Measured twice -
a banner reporting 1,958,654 unreviewed bytes against a persisted 244,360, an eighth; and a
1,259,622-byte stretch against a 2KB preview. Nothing flags the gap, because what you get is
well-formed JSONL that parses cleanly.

So compare the byte count the banner CLAIMS against the size of the file you redirected into. With
the redirect that comparison is a cheap confirmation rather than a recovery step. If you did read
it inline and the numbers differ, read the source `.jsonl` yourself over that byte range (open it,
skip to the offset, extract the record types you need) before running `session-reviewed`. Advancing
the watermark is a one-way discard: it destroys the only pointer to what you skipped.

**The owed transcript is usually NOT this session's.** The obligation is recorded per PROJECT and
outlives the session that compacted, so it is routinely inherited by a later session that never
compacted at all. `session-review` therefore targets the transcript that ACTUALLY compacted while it
still has unreviewed bytes, and prints a `READING THE COMPACTED EARLIER SESSION` banner naming that
file; `session-reviewed` marks the same file. Read the banner before deciding whose learnings these
are, and do not clear the obligation any other way - discharging it without reading that file is how
a compacted session's stretch is lost while the run reports itself consolidated.

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

Low/UNSURE never moves. A pinned fact is placed by this SAME routing prompt, up or down, like any
other entry - `move` carries the pin through unchanged and never refuses on it. Only a pinned
fact's CONTENT is out of reach: the engine REFUSES an ordinary `add` on a pinned slug
(`PinnedEntry`); `amend-pinned` is the deliberate way through and is human-only - report a pinned
fact whose content looks wrong, never rewrite it or call `amend-pinned` on its behalf. Tree-top
promotion additionally passes
the corroboration gate: a user-stated concrete rule promotes eagerly; a model-INFERRED generalization
needs >= 2 DISTINCT PROJECTS. The gate is backed by a real dwell store (out of the dreamed store, so
counting never bumps its mtime) that counts distinct projects, not sightings - a dream re-reads
UNCHANGED fact bodies on every run, so counting sightings let one act of judgement corroborate itself.
Record each sighting with `dream_state.py saw-promotable <slug> <project the fact came from>` (the
project defaults to the cwd, which is wrong for a fan-out reading other projects' stores), ask
`dream_state.py should-promote <slug>` (prints `promote`/`hold`), and after an actual promotion run
`dream_state.py promoted <slug>` to clear every project's sighting at once. HOLD keeps the fact at
the project level until a SECOND project sights it.

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

## Toolbox pass (consolidate + contribute the local tools)

The per-turn loop (`bitranox:meta-self-improve` step 6) CREATES and ENHANCES the agent's local tools;
the dream is where they get CONSOLIDATED and CONTRIBUTED - the tool analogue of what a dream already
does for memory (dedup/merge, and skill-fit contribution). Each dream mode states its delta; the
mechanics live here once.

The toolbox is MACHINE-GLOBAL, not per-tree: a personal skill at `~/.claude/skills/toolbox/`. List
the live inventory with `uv run ~/.claude/skills/toolbox/tools/toolbox.py list` (name + one-line
purpose) - the same set regardless of which tree the dream runs in. If that path does not exist,
there is no toolbox yet: skip this pass.

**PROPOSE-ONLY.** The dream DETECTS and PROPOSES; it never edits tool code. A merge/enhance/removal is
a TDD code change and runs through `meta-self-improve`'s propose-first build (which owns the RED-test
+ fix + the tool's local git repo). The dream's job is to surface the candidate, honoring the mode
knob (propose: list; auto: queue via `contrib_queue`; off: skip).

- **CONSOLIDATE** (the `tree` delta): from the inventory, flag NEAR-DUPLICATE tools (two tools with
  overlapping purpose) -> propose merging into one parameterized tool; flag a STALE/superseded tool
  (its docstring/paths name something deleted, or a newer tool covers it) -> propose flagging. NO
  usage-based pruning - `forgetting-is-usage-based-only` applies to tools too; remove only on proven
  redundancy, never because a tool looks unused.
- **CONTRIBUTE** (the `crosstree`/`-deep` delta): judge which LOCAL tools are broadly useful to OTHER
  users -> propose contributing upstream via `contrib_queue` + the upstream loop (references/
  upstream-propagation.md), landing in a shared `meta-toolbox` skill or a relevant existing skill -
  the tool analogue of the skill-fit step. ALSO surface a chore that recurred across MANY sessions
  (visible to the cross-session view, missed by a single turn) -> propose a NEW tool. Default stays
  LOCAL; contribution is never automatic.
- **`nap` delta**: a cheap glance only; DEFER the full toolbox pass to the tree/crosstree dream (add
  "toolbox consolidation" to nap's reported deferred list) - it is machine-global work, outside nap's
  chain-only, minutes budget.
