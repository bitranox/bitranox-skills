---
name: meta-dream-global-deep
description: The DEEP cross-project dream - always runs the full semantic fan-out scan across ALL project memory stores AND their CLAUDE.md, with no convergence shortcut and no asking. Use on "deep global dream", "/dream-global-deep", "deep cross-project scan", or when you want the exhaustive cross-project read regardless of whether anything obviously changed. For the normal, cheaper global dream that convergence-checks first and asks before the expensive scan, use meta-dream-global.
---

# meta-dream-global-deep

The exhaustive variant of `bitranox:meta-dream-global`. Same goal, same safety model, same outputs -
the ONE difference is that the **deep cross-project semantic scan is mandatory here, not opt-in**:
this skill always reads every store (and every CLAUDE.md), even if the cheap convergence pre-check
says nothing changed. Use it when you want the thorough read; use `bitranox:meta-dream-global` for the
routine, convergence-gated pass that asks before going deep.

**REQUIRED BACKGROUND:** Follow `bitranox:meta-dream-global` for the full procedure (backup, inbound
gather, promotion gate, outbound cross-pollination, re-dedup + reconcile, skill-fit, report) and
`bitranox:meta-self-improve` for the altitude/normalization primitives. This skill only overrides how
the scan in step 3 is run; do not duplicate the rest.

## What changes vs meta-dream-global

1. **Back up first** (per-run snapshot of the global layer + any store you will write) - unchanged.
2. **Always run the semantic fan-out - no convergence shortcut, no asking.** FAN OUT one **`sonnet`**
   subagent per project store, OR (for many stores) one per thematic batch, in parallel. Each reads its
   stores and returns ONLY cross-project-generalizable candidates (general dev/tooling/test/security/
   workflow practice), pre-filtered against the existing global rules and shipped skills. Reserve
   **`opus`** (the main agent) for the promotion gate and altitude/normalization decisions. (Tiers:
   "Concrete tiers" in `bitranox:process-agents-subagent-driven-development`.)
3. **Promotion gate + CLAUDE.md reconciliation.** Before promoting any candidate to the global layer,
   dedup it against the existing global layer, the shipped skills, AND every `CLAUDE.md` in the tree
   (project roots + ancestors + the workspace), not just the memory stores. During the conversion phase
   many rules still live in `CLAUDE.md`; promoting one already there would DUPLICATE it. Classify:
   already-global/skill -> skip; already in a `CLAUDE.md` -> ROUTE through the reconciliation model
   (delete the lower copy if a broader tier covers it / lift it up + leave the delta / keep if local),
   and CONSOLIDATE a rule duplicated across many sibling `CLAUDE.md` UP to their common ancestor (the
   biggest cross-tree context saving); new + corroborated (>= 2 distinct projects, or user-stated) +
   nowhere-else -> promote, kept CONCRETE. (Case model + guards: `bitranox:meta-dream-project`
   "CLAUDE.md reconciliation"; every `CLAUDE.md` edit is propose-first, never without confirmation.)
4. **Org-chart audit (deep dream only - propose, never apply).** With the cross-tree view, assess whether
   the directory structure still fits. Using each project's scope descriptor + what it has learned, look
   for: a project whose domain has drifted so it shares more rules with a DIFFERENT subtree (propose
   MOVING it there); a flat cluster of related projects with no common parent (propose CREATING a
   department folder and grouping them); a department gone incoherent (propose SPLITTING it). Each
   proposal MUST spell out the consequences, because a move is heavy and human-executed: moving a
   project's directory changes its path -> its Auto-memory store slug (`~/.claude/projects/<slug>`)
   must be migrated or it orphans; its `CLAUDE.md` ancestor chain changes (recheck inherited rules +
   deltas); git remotes / deploy / import paths may need updating. Decision criterion: propose only if
   it lets shared rules live at a TIGHTER common altitude AND the projects genuinely share a domain.
   Strictly propose-only and user-gated - the dream never relocates a directory, migrates a slug, or
   touches a repo; it hands you the proposal + the exact migration steps.
5. **Then steps 4-8 of meta-dream-global exactly** (outbound cross-pollination, re-dedup + reconcile via
   `reconcile_memory_index.py --check`, skill-fit batched change, report counts).

## Boundaries (unchanged from meta-dream-global)

- Global `~/.claude/rules/bitranox/` layer + private project memory (machine-local): back up, then apply.
- **`CLAUDE.md` (version-controlled): never edit without user confirmation** - propose-first in `propose`,
  apply in `auto`, only through the sanctioned bounded paths. A reconciliation delete/lift or an org-chart
  move is always PROPOSED (with consequences), never an unconfirmed edit; the dream never relocates a
  directory or migrates a memory slug itself.
- Skills / hooks (shared, public): never silently edit; route through the upstream-PR loop.
- **Never a cross-tree reference.** Bridge trees only by lift-to-common-ancestor or self-contained copy.

## Cost note

This is the expensive pass by design (dozens of subagents, every store read). Run it deliberately. If
you just want "is there anything new across projects?", run `bitranox:meta-dream-global` instead - it
convergence-checks cheaply first and asks before going deep.
