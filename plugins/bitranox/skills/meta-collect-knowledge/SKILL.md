---
name: meta-collect-knowledge
description: Use to pull in knowledge from your OTHER projects or trees that is relevant to the current one - on "collect knowledge", "/collect-knowledge", when starting/seeding a fresh project, or when a learning reveals a topic this project now touches. Cascade only flows down one ancestor chain, so useful knowledge filed in a sibling project or another knowledge tree is otherwise invisible here; this gathers it in safely. Also runs as the inbound pass of bitranox:meta-dream-crosstree.
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
- As `bitranox:meta-dream-crosstree`'s inbound pass (the dream delegates here).

## Relevance needs a topic (descriptor-first)

The query is the project's scope descriptor (the `bitranox:self-learning` block in its
`CLAUDE.local.md`) or the topic of the triggering learning. At a brand-new project: first infer
the descriptor (README, dir name, package metadata, the parent's descriptor); if scope is still
unknown, defer - a blind gather pulls noise.

## Procedure (grep -> inspect -> import)

1. **Stage 1 - cheap grep (no model).** `python3 <this-skill-dir>/gather_scan.py --topic "<scope
   or topic>" --self "<cwd>"`. It greps other projects' curated slug-store bodies + native memory
   and prints candidates GROUPED BY KNOWLEDGE TREE (`TREE: <top>` headers; the native tier is
   labeled `native-tier (machine-local)` - that whole string is the label, so grep for it, not for
`machine-local` alone). With `cross_tree_search=false` (the knob defaults to true) the scan stays inside the CURRENT tree;
   pass `--cross-tree` for a deliberate cross-tree gather. Nothing matched (`CANDIDATES: 0 in ...`,
   exit 0) -> stop (the whole gather cost one grep). `CANDIDATES: 0 (not scanned: <reason>)` exits 2:
   no scan ran, so fix the reason (a topic with no usable keyword, or no tree anchor while
   `cross_tree_search=false`) rather than reading it as "nothing to gather".
   A note it cannot read or decode is skipped and named on stderr, never fatal.
   - Optional MCP boost: with the `mcp_search` knob `auto` and a covering `basic-memory` index,
     the same command prints `MCP-CANDIDATES` (read-only search, never the store; the keyword
     grep is always the base).
2. **Stage 2 - inspect (model, context-isolated).** Dispatch a `sonnet` subagent to read the
   candidate files and return only what is genuinely useful to THIS project, privacy-scrubbed;
   discard near-misses. (Tier per `bitranox:process-agents-subagent-driven-development`.)
   - **Jev shadow on that keep/discard** (only when `jev_shadow.py status` exits 0; home
     `<plugin>/skills/meta-self-improve/`, launch via `hooks/run-python.sh`; procedure in its
     `references/jev-shadow.md`; create a fresh `D=$(mktemp -d)` outside any repo first, since other
     projects' note texts land there unredacted): the dispatch asks the subagent for three things.
     (1) Its reply as above: the useful knowledge, privacy-scrubbed - what stage 3 imports. (2)
     `$D/items.jsonl`, written by the SUBAGENT itself at that path you give it, one line per
     candidate, `{"id": "<candidate path>", "state": {"project": "<the scope descriptor or topic>",
     "candidate": "<the note's full text as read, not a summary>"}}` (the tool redacts secrets and
     caps it before sending), so full texts never pass through your context. (3) Keep or discard for
     EVERY candidate. The subagent's keep/discard is the verdict: you, the main agent, write it to
     `$D/verdicts.jsonl` FIRST (`{"id": "<candidate path>", "verdict": {"useful_here": true}}` for
     keep, `false` for discard; none left out, since every candidate is judged), then `jev_shadow.py
     run --site collect-relevance --items "$D/items.jsonl" --verdicts "$D/verdicts.jsonl"`, then
     `rm -rf "$D"`. `run` prints counts only. Import what the subagent kept, whatever `run` printed or
     exited with; `report` waits until the gather is finished.
3. **Stage 3 - import by the tree rules:**
   - **Same tree, useful beyond this project** -> LIFT to the lowest common ancestor level
     (engine `move`/`add` at that level; honor the promotion corroboration gate; keep it
     concrete).
   - **Same tree, only relevant here** -> self-contained COPY into this project's memory (engine
     `add`).
   - **ANOTHER tree** -> ALWAYS a self-contained, labeled COPY; trees share no ancestor, so
     lifting is impossible and a cross-tree `[[reference]]` would dangle. Never link across
     trees.
4. **Privacy scrub on anything crossing a boundary.** Scrub secrets/PII before writing; never
   carry a credential across. Concrete operational detail (paths, hostnames) is the useful part -
   keep it.
5. **Debounce.** Record the (project, topic) as gathered so the same topic is not re-grepped on
   every trigger: `gather_scan.py --topic "<topic>" --mark`. Ask before spending a scan with
   `--seen` (exit 0 already gathered, 1 not, 2 error), which answers from the record and walks
   nothing. `--mark` exits 2 when it could not write the record.
   Neither GATES a scan - a scan you ask for still runs, whatever the record says, so `--seen`
   is advice to the caller rather than a lock. The record lives OUT of the curated store on
   purpose: written into it, it would be a fact, and the next dream would tidy, promote or
   dedup a bookkeeping row.
6. **Verify + report.** `reconcile_memory_index.py --check <altitude chain>` (home:
   `<plugin>/skills/meta-self-improve/reconcile_memory_index.py`, launch via
   `hooks/run-python.sh`) must end
   `TOTAL problems: 0`. Report lifted vs copied, one line each; nothing relevant -> one line.

## Deliverables (a completed gather has ALL of these)

- [ ] A topic/descriptor stated BEFORE scanning (no blind gather).
- [ ] Stage-1 candidate list with per-tree `TREE:` labels (or a one-line "nothing matched").
- [ ] Every import via the engine.
- [ ] Privacy scrub applied to everything copied across a boundary (no credential carried across).
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
- Re-promoting a gathered copy on the next dream. The debounce is `gather_scan.py`'s own
  `gathered-topics.tsv`, kept OUT of the store so a dream does not tidy it away. A provenance
  mark never prevented this: nothing read it, and provenance was removed in 5.300.0.
- Importing an ancestor's knowledge the cascade already provides (the scan groups it under this
  tree's top - check before copying).
