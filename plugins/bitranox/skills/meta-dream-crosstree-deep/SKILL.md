---
name: meta-dream-crosstree-deep
description: Use on "deep crosstree dream", "/dream-crosstree-deep", "deep cross-project scan", or when you want the exhaustive cross-project/cross-tree read regardless of whether anything obviously changed - the full semantic fan-out over ALL project memory stores AND their CLAUDE.md files, no convergence shortcut, no asking. For the normal, cheaper global dream that convergence-checks first and asks before the expensive scan, use meta-dream-crosstree.
---

# meta-dream-crosstree-deep

The exhaustive variant of `bitranox:meta-dream-crosstree`. Same goal, same safety model, same outputs -
the ONE difference is that the **deep cross-project semantic scan is mandatory here, not opt-in**:
this skill always reads every store (and every CLAUDE.md), even if the cheap convergence pre-check
says nothing changed. Use it when you want the thorough read; use `bitranox:meta-dream-crosstree` for the
routine, convergence-gated pass that asks before going deep.

**REQUIRED BACKGROUND:** Follow `bitranox:meta-dream-crosstree` for the full procedure (capture-first
reading the session from DISK via `dream_state.py session-review`, backup, inbound gather, promotion
gate, outbound cross-pollination, re-dedup + reconcile, skill-fit, report) and
`bitranox:meta-self-improve` for the altitude/normalization primitives. This skill only overrides how
the scan in step 3 is run; do not duplicate the rest.

## What changes vs meta-dream-crosstree

1. **Back up first** (per-run snapshot of each affected tree's TOP store + any store you will write) - unchanged.
2. **Always run the semantic fan-out - no convergence shortcut, no asking.** FAN OUT one **`sonnet`**
   subagent per project store, OR (for many stores) one per thematic batch, in parallel. Each reads its
   stores and returns ONLY cross-project-generalizable candidates (general dev/tooling/test/security/
   workflow practice), pre-filtered against the existing global rules and shipped skills. A subagent
   flags a DUPLICATE/MERGE only from the BODIES (not a title/topic match), and every such finding is a
   CANDIDATE the main agent VERIFIES before merging - a summary+detail pair, a valid cross-link, or a
   cited-across-a-subtree fact is not a duplicate (see "Dedup semantics" in references/dream-core.md). Keep the
   promotion gate and altitude/normalization decisions INLINE on the main agent at **opus-class OR
   ABOVE** (opus is the universally-available deep tier; fable sits above it but needs paid API
   credits) - if the session is below opus-class, offer switch-model-or-continue per "The session
   model is fixed" in `bitranox:process-agents-subagent-driven-development` (a /model switch keeps
   the conversation; the main agent cannot self-switch). (Tiers: "Concrete tiers" in the same skill.)
3. **Promotion gate + CLAUDE.md reconciliation.** Before promoting any candidate to a tree's top,
   dedup it against that tree's existing top store, the shipped skills, AND every `CLAUDE.md` in the tree
   (project roots + ancestors + the workspace), not just the memory stores. During the conversion phase
   many rules still live in `CLAUDE.md`; promoting one already there would DUPLICATE it. Classify:
   already-global/skill -> skip; already in a `CLAUDE.md` -> ROUTE through the reconciliation model
   (delete the lower copy if a broader tier covers it / lift it up + leave the delta / keep if local),
   and CONSOLIDATE a rule duplicated across many sibling `CLAUDE.md` UP to their common ancestor (the
   biggest cross-tree context saving); new + corroborated (>= 2 distinct projects, or user-stated) +
   nowhere-else -> promote, kept CONCRETE. (Case model + guards: `bitranox:meta-dream-tree`
   "CLAUDE.md reconciliation"; a removal needs an ANCESTOR covering home, and is backed up + reported.)
   **For the CONSOLIDATION half - a section copy-pasted across many repos and since drifted - run
   `bitranox:meta-consolidate-claude-md` and follow it.** It owns measure -> verify -> converge ->
   lift, and above all the rule that the copies must be checked against GROUND TRUTH before one is
   promoted: drift means most of them are now wrong, so deduplicating by picking the most-copied
   variant installs a stale claim at an ancestor where it binds every repo below. Do not re-derive
   that procedure here.
3b. **Misplacement audit - EXHAUSTIVE here.** Run crosstree's step 4b
   (`reconcile_memory_index.py --check-misplaced <anchor>`) over EVERY tree, not just the ones this
   run touched: a wrong-tree fact is invisible from inside its own tree, so it survives every
   routine dream until a full sweep finds it. Judge each candidate (a cited neighbour path is not a
   misfile) and `relocate` only the confirmed ones. Report the candidates rejected as well as the
   ones moved - a rejected candidate is a result, not a non-event.

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
     folder's `CLAUDE.md` (a home for the lifted shared rule[s]) at the LOWEST common ancestor whose
     children share a domain - NEVER a generic bucket (`projects/`, `apps/`, `public/`); its child-derived
     scope descriptor is synthesized by the per-level scope-descriptor subagent described in step 4
     below and
     written into that rung's pointer-block scope (in `CLAUDE.local.md`), not hand-typed into the `CLAUDE.md`. A
     structural-only look-alike (siblings that merely seem related, no shared-rule evidence) is SURFACED
     as a question, not auto-proposed. The **workspace-root `CLAUDE.md`** is the file-tree HQ; because the
     global curated store now lives at the TOPMOST ancestor with a `CLAUDE.md` (not `~/.claude`) - note
     bodies central in that anchor's `.claude-memory/`, pointer blocks per-rung in `CLAUDE.local.md` - the head
     office IS that top-`CLAUDE.md` rung - and proposing a brand-new `CLAUDE.md` ABOVE the current highest
     existing one is the one case allowed to go above the highest rung (the reactive gap-fill in
     `bitranox:meta-self-improve` never does this on its own). Creating a rung is light - a new
     `CLAUDE.md`, NO slug migration - but it adds a tier to the ancestor chain of every project beneath
     it, so recheck their deltas. Reuse the per-level scope-descriptor synthesis mechanism
     (`bitranox:meta-dream-tree` step 0b "Scope-descriptor synthesis" + the
     `<!-- bitranox:self-learning -->` scope block in the `CLAUDE.local.md` pointer block): a SUBAGENT (capable model, not haiku) reads
     the docs of the directories directly beneath the new rung and returns its descriptor. Propose-first,
     never created without confirmation.
   - **A rung on an untracked folder is a normal rung - git tracking NEVER gates the trim.** When the
     folder that should hold the rung is a plain directory whose members are each their OWN repos
     (common for a fleet or host tree), its `CLAUDE.md` is machine-local. That is not a reason to skip
     the rung, and not a reason to leave the members' tracked copies in place. The cascade loads a file
     by PATH, not by repo membership, and the machine is backed up as a machine. Judge the trim by the
     REACHABILITY INVARIANT alone (`bitranox:meta-dream-tree` -> references/dream-passes.md): is there a
     covering rule at an ANCESTOR DIRECTORY, delivered as always-loaded text? Nothing else - not
     tracked-vs-ignored, not the remote, not who else could clone it - enters that decision.
     An **umbrella repo** (a thin `umbrella-<topic>` repo version-controlling ONLY the rung `CLAUDE.md`
     files and ignoring the nested member repos via a whitelist `.gitignore`; see
     `bitranox:coding-python-gitignore`) is worth PROPOSING when the user wants the rung's history
     reviewable or shared to other machines. Ask private-or-public (default: private) then. It is a
     distribution choice, raised on its own merits, never a precondition for lifting.
4b. **Local harness audit - the PERSONAL half (machine-global, deep dream only).** `~/.claude/skills`
   and `~/.claude/hooks` plus the hooks wired in `~/.claude/settings.json` load in EVERY session on
   this machine whatever the cwd, and no marketplace gate reaches any of them. Run
   `bitranox:meta-audit-local-skills-and-hooks` for the personal half; follow that skill for the
   procedure and for its refusal to edit a dir a plugin owns. The per-tree dream owns the PROJECT
   half (its own `.claude/skills`, with `--no-personal`), so do not repeat that here.

5. **Then steps 5-8 of meta-dream-crosstree exactly** (step 4, the promotion gate, is already
   done above as this skill's step 3 - do not run it twice) (outbound cross-pollination, re-dedup + reconcile via
   `reconcile_memory_index.py --check` over the LEVEL dirs AND `--check-tree <anchor>` per affected tree
   for `TOTAL tree problems: 0` - home: `<plugin>/skills/meta-self-improve/` - skill-fit batched change,
   the toolbox contribute pass (step 7b: propose contributing a broadly-useful local tool + a
   cross-session recurring chore -> a new tool), report counts). The tree-wide check matters MORE here:
   promoting to common ancestors across many trees is exactly what can leave a slug pointed at from two
   levels, which the chain-only `--check` cannot see.
   **Add two lines crosstree's report list has no slot for: the org-chart proposals from step 4**
   (moves / new rungs / splits / umbrella-repo suggestions, applied or proposed) **and the personal
   harness findings from step 4b** (counts per check, plus how many dirs were REFUSED as
   plugin-owned - a refusal count of zero on a machine holding tool repos means the ownership
   filter did not run). Without them a deep run can generate both and never surface either.

## Boundaries (unchanged from meta-dream-crosstree)

- The family Boundaries (memory, CLAUDE.md, skills/hooks, pinned entries, structural moves) live in
  `bitranox:meta-dream-tree` -> references/dream-core.md and apply here unchanged. The CLAUDE.md
  case model + guards are in references/dream-passes.md "CLAUDE.md reconciliation".
- An ORG-CHART proposal (moving a project, creating a rung, splitting a department) is the one this
  skill adds: always PROPOSED with its consequences, never applied - the dream never relocates a
  directory, migrates a memory slug, or touches a repo.
- **Never a cross-tree reference.** Bridge trees only by lift-to-common-ancestor or self-contained copy.

## Cost note

This is the expensive pass by design (dozens of subagents, every store read). Run it deliberately. If
you just want "is there anything new across projects?", run `bitranox:meta-dream-crosstree` instead - it
convergence-checks cheaply first and asks before going deep.
