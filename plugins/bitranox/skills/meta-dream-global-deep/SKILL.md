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
   - **Missing rung (department / HQ) - evidence-gated.** Also detect a rung that SHOULD exist but does
     not: a folder that ought to carry a `CLAUDE.md` (scope descriptor + a home for shared rules) but has
     none. A **missing department** = the nearest common-ancestor folder of >= 2 RELATED projects has no
     `CLAUDE.md`; a **missing HQ** = the top of the tree has no head-office rung. The trigger is EVIDENCE,
     not structure: a rung is "missing" only when something wants to live there - a rule duplicated across
     those related siblings that would consolidate into the rung (so it surfaces straight out of the
     cross-tree consolidation above), or a truly-universal rule with no top home. Propose CREATING that
     folder's `CLAUDE.md` (its scope-descriptor block + the lifted shared rule[s]) at the LOWEST common
     ancestor whose children share a domain - NEVER a generic bucket (`projects/`, `apps/`, `public/`);
     a structural-only look-alike (siblings that merely seem related, no shared-rule evidence) is SURFACED
     as a question, not auto-proposed. Two HQ senses: the machine-global layer `~/.claude/rules/bitranox/`
     is auto-created on the first promotion (no detection needed); the **workspace-root `CLAUDE.md`** is the
     file-tree HQ, and proposing a brand-new one ABOVE the current highest existing `CLAUDE.md` is the one
     case allowed to go above the highest rung (the reactive gap-fill in `bitranox:meta-self-improve` never
     does this on its own). Creating a rung is light - a new `CLAUDE.md`, NO slug migration - but it adds a
     tier to the ancestor chain of every project beneath it, so recheck their deltas. Reuse the descriptor
     mechanism (`meta-self-improve` "Fill descriptor gaps" + the `<!-- bitranox:self-learning -->` block);
     propose-first, never created without confirmation.
   - **No shared/tracked home for the rung? Propose an umbrella repo.** If the folder that should hold the
     rung is NOT itself a tracked, shareable git repo (it is a plain directory whose members are each
     their OWN independent repos - common for a fleet/host tree), then a `CLAUDE.md` placed there is
     untracked and machine-local, and trimming the members' TRACKED copies into it would LOSE
     version-controlled knowledge (other clones never see the rung). In that case do NOT create a bare
     untracked rung and do NOT trim; instead PROPOSE an **umbrella repo** to host the rung: a thin repo
     named **`umbrella-<topic>`** (e.g. `umbrella-machines`) that version-controls ONLY the rung
     `CLAUDE.md` files and ignores the nested member repos (a whitelist `.gitignore`; see
     `bitranox:coding-python-gitignore`). ASK the user whether it should be **private or public
     (default: private)**, and whether it stays local-only or gets a remote (a remote is needed only to
     share the rung to other machines/people; local-only still gives version history + makes a trim
     safe ON THIS MACHINE). Until that shared home exists, keep the rung additive (no trim).
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
