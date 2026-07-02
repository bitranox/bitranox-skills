---
name: meta-collect-knowledge
description: Use to pull in knowledge from your OTHER projects that is relevant to the current one - on "collect knowledge", "/collect-knowledge", when starting/seeding a fresh project, or when a learning reveals a topic this project now touches. Native cascade only flows down one ancestor chain + global, so useful knowledge filed in a sibling tree is otherwise invisible here; this gathers it in safely. Also runs as the inbound pass of bitranox:meta-dream-global.
---

# meta-collect-knowledge

Native memory cascades DOWN one ancestor chain plus the global layer, so knowledge filed in a SIBLING
or unrelated tree never reaches the current project on its own. This skill is the **inbound cross-tree
gather**: find knowledge elsewhere that is relevant here, and bring it in safely. It extends
`bitranox:meta-self-improve` (altitudes, the `~/.claude/.claude-bx-selflearning/` global layer, normalization)
- follow that for the primitives.

## When to run
- **Manual:** "collect knowledge", `/collect-knowledge`.
- **New-project init:** seed a fresh project from the existing knowledge tree so it starts informed.
- **Opportunistic (a learning reveals a topic):** when self-improve captures something, the topic is a
  relevance signal - gather that topic from other trees.
- **As `bitranox:meta-dream-global`'s inbound pass** (the dream delegates here - single source of truth).

## Relevance needs a topic (descriptor-first)
Gather only makes sense once you know what the project is about. The query is the project's **scope
descriptor** (the `<!-- bitranox:self-learning -->` block at the top of its
`.claude-bx-selflearning/index.md`), or the topic of the
learning that triggered this. At a brand-new project: first infer the descriptor (README, dir name,
package metadata, the parent tree's descriptor, the first request); if scope is still unknown, defer.

## Procedure (grep -> inspect -> gather)

1. **Stage 1 - cheap grep (no model).** Run `python3 <this-skill-dir>/gather_scan.py --topic "<scope
   or learning topic>" --self "<cwd>"`. It derives keywords and greps OTHER projects' curated stores
   (`.claude-bx-selflearning/`) + native memory + the global rules layer (the current project is
   excluded), printing candidate files. Nothing matched -> stop; the whole gather cost one grep.
   - **Optional MCP boost:** when the `mcp_search` knob is `auto` and a `basic-memory` project's index
     COVERS this tree, the same command also prints `MCP-CANDIDATES` (semantic/full-text hits from
     `basic-memory tool search-notes`, read-only). Treat those as extra Stage-2 inputs. Absent or
     misconfigured MCP -> nothing printed; the keyword grep is always the base (self-healing). The MCP
     is only a search index over the local files - never the store; a memory MCP's file-writing SYNC
     is the user's opt-in setup, wired only via the `update-config` skill.
2. **Stage 2 - inspect (model).** Dispatch a **`sonnet`** subagent (bounded relevance/extraction work -
   keeps candidate bodies out of the main context): read the candidate files, return only what is
   genuinely useful to THIS project, privacy-scrubbed; discard near-misses. (Tier: "Concrete tiers" in
   `bitranox:process-agents-subagent-driven-development`.)
3. **Bring it in by ONE of two SAFE moves - never a cross-tree reference** (it is not loaded here and
   would dangle if that tree is deleted):
   - **Lift to the lowest common ancestor** (often the global `~/.claude/.claude-bx-selflearning/` layer) when
     the knowledge is broadly useful -> native cascade then delivers it here AND to the other tree.
     This is a promotion: honor the quality/dwell gate and keep it concrete (see meta-self-improve 3b).
   - **Self-contained local copy** into this project's memory when it is only relevant here. Copy the
     content (not a link), and MARK it as gathered so a later dream does not re-promote it.
4. **Privacy scrub on anything crossing a boundary.** Before writing a gathered/promoted entry, scrub
   for secrets/PII (reuse the repo-gate patterns); never carry a credential across. Concrete operational
   detail (paths, hostnames, subnets) is fine - that is the useful part.
5. **Debounce.** Record the `(project, topic)` as gathered (out-of-store) so the same topic is not
   re-grepped every trigger.
6. **Reconcile + report.** Run `reconcile_memory_index.py` on the project memory, then
   `--check <altitude-chain>` (no orphans / downward refs). Report what was lifted vs copied, one line
   each. Nothing relevant -> say so in one line.

## Boundaries
- Never create a cross-tree or downward `[[reference]]` - lift to a common ancestor or copy.
- Never gather a secret; scrub before any cross-boundary write.
- Do not re-gather what an ancestor already provides (global is scanned only to detect that).
- Honor the privacy knob (config `privacy`): with `walled`, gather only within the same domain.

## Common mistakes
- Gathering without a topic (blind, irrelevant pulls).
- A cross-tree reference instead of lift-or-copy (dangles on deletion).
- Re-promoting a gathered copy on the next dream (mark it; it is a copy, not a fresh discovery).
