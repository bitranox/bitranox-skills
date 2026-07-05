# Architecture

This chapter answers: how the memory is stored on disk, which component owns each job, and what
runs at every hook event. It is the technical companion to [concepts.md](concepts.md); the
authoritative specs live next to the code and are linked from each section.

## The store

Knowledge is organized in **knowledge trees**. A tree is any directory subtree whose top carries a
`CLAUDE.md`; the topmost such ancestor is the tree's **anchor**. A machine can hold several
independent trees, discovered by walking the configured `discovery_roots`.

Each fact has two parts:

- **A pointer line**, always loaded, inside an engine-managed fenced block in the
  `CLAUDE.local.md` of the level (altitude) the fact applies to:

  ```markdown
  - [Title](mem:<slug>) - trigger-first hook <!-- bx:src=<provenance> bx:pin -->
  ```

  The block also carries the level's **scope descriptor** (what belongs at this level versus
  above/below - the routing key for consolidation), the retrieval recipe that tells Claude how to
  fetch bodies mid-task, and an `## Iron rules` section for pinned entries.

- **A body**, stored exactly once at `<anchor>/.claude-memory/facts/<slug>.md`: frontmatter
  (name, one-line description, type) plus the fact text with explicit **Why** and **How to
  apply** lines. Slugs are unique per tree; `[[slug]]` links connect related facts, pointing
  upward only, never across trees.

Because pointer lines cascade with the `CLAUDE.md`/`CLAUDE.local.md` chain, a session in any
project always has its own line of altitudes loaded: project, each ancestor, anchor.

Full spec: [`plugins/bitranox/skills/meta-self-improve/references/memory-backend.md`](../plugins/bitranox/skills/meta-self-improve/references/memory-backend.md).

## The engine: the single write path

Every mutation of the store goes through
[`plugins/bitranox/hooks/memory_engine.py`](../plugins/bitranox/hooks/memory_engine.py) - skills
call it, humans call it, nothing writes store files directly (a guard enforces this, see below).
It is fail-loud: every subcommand ends in an explicit success line or a non-zero exit.

| Subcommand                | Job                                                                    |
|---------------------------|------------------------------------------------------------------------|
| `add`                     | Upsert one fact (pointer + central body); same slug updates in place   |
| `move`                    | Re-level one fact: relocate its pointer line within the tree           |
| `heal`                    | Self-heal missing or malformed pointer blocks across the chain         |
| `set-scope`               | Upsert a level's scope descriptor                                      |
| `ensure-memory-structure` | Scaffold missing `CLAUDE.md`/`CLAUDE.local.md`/blocks up to the anchor |
| `tree-top`                | Print the tree top, store path, and bootstrap flag for a directory     |
| `ensure-all-trees`        | Discover every tree under the roots and scaffold each (dry-run first)  |

`reconcile_memory_index.py --check` is the consistency audit (dangling pointers, orphan bodies,
cross-tree links); every consolidation must end it with `TOTAL problems: 0`.

## Three delivery paths

1. **Always-on**: the pointer blocks load with the `CLAUDE.local.md` cascade - titles and hooks
   are simply present in context.
2. **On-demand**: the block's retrieval recipe has Claude `Read` a fact's body mid-task when its
   hook becomes relevant.
3. **Per-prompt recall**: a keyword scan over other projects' stores surfaces matching notes
   under the prompt - deterministic, deduplicated per session, tunable by the
   `cross_tree_search` and `mcp_search` knobs.

## The hook pipeline

All hooks launch through [`run-python.sh`](../plugins/bitranox/hooks/run-python.sh) (interpreter
probing, UTF-8 forcing, Git-Bash-only on Windows); every failure path exits 0 so a broken hook
never wedges a turn.

| Event              | Script                                                                                                                                     | Job                                                                            |
|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `SessionStart`     | `session-start.py`                                                                                                                         | Heal/scaffold the tree, inject retrieval rule, surface nudges + the miss audit |
| `SessionStart`     | `session-banner.py`                                                                                                                        | Inject the skills-first standing instruction (meta-using-bitranox-skills)      |
| `UserPromptSubmit` | `recall-memory.py`                                                                                                                         | Per-prompt recall (path 3 above)                                               |
| `UserPromptSubmit` | `skill-router.py`                                                                                                                          | Nudge up to 2 skills whose triggers match the prompt, once per session         |
| `PreToolUse` Bash  | `repo-gate.py`                                                                                                                             | This repo's shipping rules (version bump, skill artifacts, CSO lint, taxonomy) |
| `PreToolUse` Bash  | `block-pgrep-self-match.py`, `git-footgun-guard.py`, `git-commit-branch-guard.py`, `commit-tell-sweep.py`, `block-sed-structured-files.py` | Guards against classic shell/git footguns and non-ASCII tells in commits       |
| `PreToolUse` Task  | `subagent-model-gate.py`                                                                                                                   | Warn on unpinned subagent model; DENY while a plan execution is armed          |
| `PreToolUse` Edit  | `skill-edit-guard.py`                                                                                                                      | Block casual `SKILL.md` edits (skill authoring needs the skill-writer receipt) |
| `PreToolUse` Edit  | `store-edit-guard.py`                                                                                                                      | Block direct writes to pointer blocks and `.claude-memory/` (engine-only)      |
| `PostToolUse`      | `validate-structured-files.py`, `tell-sweep.py`, `reformat-md-tables.py`                                                                   | Validate JSON/YAML/TOML/XML edits, sweep non-ASCII tells, realign md tables    |
| `Stop`             | `self-improve-gate.py`                                                                                                                     | Detect learning signals in the turn; nudge the capture skill                   |
| `SessionEnd`       | `self-improve-audit.py`                                                                                                                    | Broad-recall scan for signals the gate missed; surfaced once next session      |
| `PreCompact`       | `self-improve-audit.py`                                                                                                                    | Salvage learning candidates before compaction discards the detail              |
| `PostCompact`      | `post-compact-nudge.py`                                                                                                                    | Point at `/dream-nap` to fold the salvaged candidates in                       |

The gate and the audit share their signal patterns
([`self_improve_signals.py`](../plugins/bitranox/hooks/self_improve_signals.py)), so precision
tuning and the broad net never drift apart. That module also owns the config
(`~/.claude/.bitranox-memory.json`) read by every hook and skill.

## The skill layer

- **Trigger-first descriptions**: every skill's frontmatter description states WHEN it fires;
  the repo gate lints this on change.
- **The router map** ([`skill_triggers.json`](../plugins/bitranox/hooks/skill_triggers.json)) and
  **the catalog** ([skills.md](skills.md)) are both GENERATED from those descriptions
  (`build_skill_triggers.py`, `build_skill_docs.py`); pytest sync tests fail when either goes
  stale, so neither can rot.
- **The dream family** shares one core -
  [`meta-dream-tree/references/dream-core.md`](../plugins/bitranox/skills/meta-dream-tree/references/dream-core.md)
  (mode knob, capture-first, backup + manifest, dedup semantics, the routing prompt,
  verification) - while each skill carries only its scope: nap = the cwd's chain, tree = one
  whole tree, crosstree = across trees. A contract test asserts the scope markers and that the
  shared semantics exist exactly once; a parity-matrix acceptance harness (fixture builder +
  asserter with per-scope profiles) verifies each dream's behavior on a synthetic tree, including
  that a nap leaves sibling branches byte-identical.

## Trust boundaries

The memory is machine-local. `CLAUDE.local.md` and `.claude-memory/` are gitignored by default
(the `track_private` knob can opt a PRIVATE repo in); promotion and gathering scrub secrets and
PII at every boundary crossing; cross-tree sharing is always an explicit, labeled copy - trees
never link into each other.
