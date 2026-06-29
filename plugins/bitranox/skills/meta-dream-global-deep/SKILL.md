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
3. **Promotion gate - dedup against CLAUDE.md too.** Before promoting any candidate to the global layer,
   dedup it against the existing global layer, the shipped skills, AND every `CLAUDE.md` in the tree
   (project roots + ancestors + the workspace), not just the memory stores. During the conversion phase
   many rules still live in `CLAUDE.md`; promoting one already there would DUPLICATE it. Classify:
   already-global/skill -> skip; already in a `CLAUDE.md` -> do NOT duplicate, FLAG for the user;
   new + corroborated (>= 2 distinct projects, or user-stated) + nowhere-else -> promote, kept CONCRETE.
4. **Then steps 4-8 of meta-dream-global exactly** (outbound cross-pollination, re-dedup + reconcile via
   `reconcile_memory_index.py --check`, skill-fit batched change, report counts).

## Boundaries (unchanged from meta-dream-global)

- Global `~/.claude/rules/bitranox/` layer + private project memory (machine-local): back up, then apply.
- **`CLAUDE.md` (version-controlled): never edit without user confirmation** - propose-first in `propose`,
  apply in `auto`, only through the sanctioned bounded paths. Surfacing a duplicate is a FLAG, not an edit.
- Skills / hooks (shared, public): never silently edit; route through the upstream-PR loop.
- **Never a cross-tree reference.** Bridge trees only by lift-to-common-ancestor or self-contained copy.

## Cost note

This is the expensive pass by design (dozens of subagents, every store read). Run it deliberately. If
you just want "is there anything new across projects?", run `bitranox:meta-dream-global` instead - it
convergence-checks cheaply first and asks before going deep.
