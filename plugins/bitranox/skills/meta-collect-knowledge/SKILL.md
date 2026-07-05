---
name: meta-collect-knowledge
description: Use to pull in knowledge from your OTHER projects or trees that is relevant to the current one - on "collect knowledge", "/collect-knowledge", when starting/seeding a fresh project, or when a learning reveals a topic this project now touches. Cascade only flows down one ancestor chain, so useful knowledge filed in a sibling project or another knowledge tree is otherwise invisible here; this gathers it in safely. Also runs as the inbound pass of bitranox:meta-dream-global.
---

# meta-collect-knowledge

Memory cascades DOWN one ancestor chain, so knowledge filed in a SIBLING project - or in a
completely different knowledge TREE (a machine can carry several independent tree tops) - never
reaches the current project on its own. This skill is the **inbound gather**: find knowledge
elsewhere that is relevant here and bring it in safely.

**REQUIRED BACKGROUND:** the storage spec (trees/anchors, slug store, engine fail-loud contract)
is `bitranox:meta-self-improve` -> `references/memory-backend.md`.

## When to run

- Manual: "collect knowledge", `/collect-knowledge`.
- New-project init: seed a fresh project from the existing tree so it starts informed.
- Opportunistic: a captured learning reveals a topic this project now touches - gather that topic.
- As `bitranox:meta-dream-global`'s inbound pass (the dream delegates here).

## Relevance needs a topic (descriptor-first)

The query is the project's scope descriptor (the `bitranox:self-learning` block in its
`CLAUDE.local.md`) or the topic of the triggering learning. At a brand-new project: first infer
the descriptor (README, dir name, package metadata, the parent's descriptor); if scope is still
unknown, defer - a blind gather pulls noise.

## Procedure (grep -> inspect -> import)

1. **Stage 1 - cheap grep (no model).** `python3 <this-skill-dir>/gather_scan.py --topic "<scope
   or topic>" --self "<cwd>"`. It greps other projects' curated slug-store bodies + native memory
   and prints candidates GROUPED BY KNOWLEDGE TREE (`TREE: <top>` headers; the native tier is
   labeled machine-local). With `cross_tree_search=false` (the knob defaults to true) the scan stays inside the CURRENT tree;
   pass `--cross-tree` for a deliberate cross-tree gather. Nothing matched -> stop (the whole
   gather cost one grep).
   - Optional MCP boost: with the `mcp_search` knob `auto` and a covering `basic-memory` index,
     the same command prints `MCP-CANDIDATES` (read-only search, never the store; the keyword
     grep is always the base).
2. **Stage 2 - inspect (model, context-isolated).** Dispatch a `sonnet` subagent to read the
   candidate files and return only what is genuinely useful to THIS project, privacy-scrubbed;
   discard near-misses. (Tier per `bitranox:process-agents-subagent-driven-development`.)
3. **Stage 3 - import by the tree rules:**
   - **Same tree, useful beyond this project** -> LIFT to the lowest common ancestor level
     (engine `move`/`add` at that level; honor the promotion corroboration gate; keep it
     concrete).
   - **Same tree, only relevant here** -> self-contained COPY into this project's memory (engine
     `add`), marked as gathered (`--source gathered:<origin-slug>`) so a later dream does not
     re-promote it as a fresh discovery.
   - **ANOTHER tree** -> ALWAYS a self-contained, labeled COPY (`--source
     gathered-cross-tree:<top>`); trees share no ancestor, so lifting is impossible and a
     cross-tree `[[reference]]` would dangle. Never link across trees.
4. **Privacy scrub on anything crossing a boundary.** Scrub secrets/PII before writing; never
   carry a credential across. Concrete operational detail (paths, hostnames) is the useful part -
   keep it.
5. **Debounce.** Record the (project, topic) as gathered (out-of-store) so the same topic is not
   re-grepped on every trigger.
6. **Verify + report.** `reconcile_memory_index.py --check <altitude chain>` must end
   `TOTAL problems: 0`. Report lifted vs copied, one line each; nothing relevant -> one line.

## Deliverables (a completed gather has ALL of these)

- [ ] A topic/descriptor stated BEFORE scanning (no blind gather).
- [ ] Stage-1 candidate list with per-tree `TREE:` labels (or a one-line "nothing matched").
- [ ] Every import via the engine, marked `gathered:`/`gathered-cross-tree:` in its provenance.
- [ ] Zero cross-tree or downward `[[references]]` introduced (reconcile 0 problems).
- [ ] The lifted-vs-copied report.

## Rationalizations (these do not fly)

| Excuse                                                        | Reality                                                                                              |
|---------------------------------------------------------------|------------------------------------------------------------------------------------------------------|
| "A reference to the other tree's fact is cheaper than a copy" | It is not loaded here and dangles when that tree moves or dies. Cross-tree is ALWAYS a copy.         |
| "Skip the TREE labels, the paths make it obvious"             | The labels are the boundary-crossing audit trail; the dream and the user read them.                  |
| "Seed everything, the project is new"                         | A blind gather imports noise the dream then has to prune. Descriptor first, topic-matched only.      |
| "cross_tree_search is false but this one fact is fine"        | The wall is the user's setting. Cross it only with the explicit --cross-tree act, as a labeled copy. |

## Common mistakes

- Gathering without a topic (blind, irrelevant pulls).
- A cross-tree reference instead of a labeled copy (dangles on deletion).
- Re-promoting a gathered copy on the next dream (the `gathered:` provenance mark prevents it).
- Importing an ancestor's knowledge the cascade already provides (the scan groups it under this
  tree's top - check before copying).
