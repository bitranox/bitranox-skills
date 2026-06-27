---
name: meta-dream
description: Use to consolidate memory like sleep - periodically, when memory has grown, or before context compaction would lose detail - and on "dream", "consolidate memory", "tidy memory", or when the SessionStart nudge says a consolidation is due. Runs AFTER per-turn capture (bitranox:meta-self-improve): dedups/merges/generalizes/re-wires/prunes the whole MEMORY.md store and the session, routes generalized rules to the right-altitude CLAUDE.md, and batches skill-worthy generalizations into one self-PR. Honors an off/auto/propose mode.
---

# meta-dream

Memory consolidation, the way a brain reorganizes during sleep. `bitranox:meta-self-improve` is the
fast per-turn CAPTURE (note each learning as it happens). **meta-dream is the periodic, batch
CONSOLIDATION on top:** take the WHOLE memory store plus the session and dedup, merge, generalize,
re-categorize, re-wire (cross-link), prune detail, and refine concepts - so memory gets smaller and
sharper, not bigger. It extends `bitranox:meta-self-improve` (its lanes, the step-3b altitude logic,
the upstream-PR loop, the native-memory backend rules, `reconcile_memory_index.py`); follow that
skill for the primitives, this one for the batch pass. Do not duplicate its content.

**The consolidation must SHRINK noise, never add it.** If a pass would grow the store, it is wrong.

## Mode (user can switch off the asking)

Read the mode first (or run `dream_state.py mode`). Controlled by opt-out sentinels in `~/.claude`
(no config edit needed):

- **`propose`** (default): apply the safe private-memory consolidation, but ASK before editing a
  version-controlled CLAUDE.md and route skill changes to a self-PR for review. End the run by
  telling the user they can switch off the asking: `touch ~/.claude/.bitranox-dream-auto` for auto
  mode, or `touch ~/.claude/.bitranox-dream-off` to disable dreams.
- **`auto`** (`~/.claude/.bitranox-dream-auto`): the proposals are annoying, so do not ask - apply
  CLAUDE.md edits directly and ship skill changes (commit or self-PR) without per-change prompts.
- **`off`** (`~/.claude/.bitranox-dream-off`): no nudges; a manual dream consolidates PRIVATE MEMORY
  ONLY and skips all CLAUDE.md and skill proposals.

## When to run

- **Nudged when due:** the SessionStart hook surfaces "a memory consolidation is due" (threshold:
  memory changed since the last dream and the last dream is old). Run it then, or say "skip".
- **Around compaction:** the PreCompact hook salvages candidate learnings from the still-full
  transcript and PostCompact nudges you to capture/consolidate them - run a dream then so detail is
  not lost. (A hook cannot run the model, so it can only salvage + nudge; you do the dream.)
- **Manual:** "dream", "consolidate memory".

Check due-ness with `python3 <this-skill-dir>/dream_state.py due`; you do not need to dream if it
says `not-due` and nothing notable happened.

## Procedure

Create one todo per step.

1. **Capture first.** If the gate/audit flagged anything this session, run `bitranox:meta-self-improve`
   so the dream consolidates a COMPLETE store, not a half-captured one.
2. **Back up** the memory dir to a timestamped copy before any edit (reversible safety), e.g.
   `cp -r ~/.claude/projects/<proj>/memory ~/.claude/projects/<proj>/memory.bak-<ts>`.
3. **Load** the whole `MEMORY.md` index + topic files. Also skim the session (transcript tail / the
   `remember` buffer) for durable items not yet captured.
4. **Dedup / merge.** Fold near-duplicate or overlapping entries into one sharpened entry; update the
   index line; cross-link related entries with `[[name]]`. Edit-over-append (the core anti-bloat rule).
5. **Generalize - with dual representation.** Lift broadly-useful specifics into a general principle.
   For each, choose the representation deliberately:
   - **Combine** the general rule plus the specialized detail in one entry, OR
   - **Split** across altitudes: the general principle at the broad layer, the concrete instance at
     the narrow layer, cross-linked, never duplicated (step-3b).
   This applies to BOTH tiers: **memory** (a generalized entry linked to a specialized one) and
   **CLAUDE.md** (a parent/higher-altitude CLAUDE.md holds the generalized rule; the project's
   CLAUDE.md holds the specialized version; linked). Route a must-hold standing rule to the
   right-altitude CLAUDE.md; keep the rest as generalized memory.
   - **If no CLAUDE.md exists at the chosen altitude, create it** (with the rule). Creating/editing a
     CLAUDE.md that is version-controlled is propose-first in `propose` mode (auto in `auto` mode); a
     CLAUDE.md outside version control may be created directly.
6. **Re-categorize / re-wire.** Move entries to the right layer/altitude; add cross-links; drop stale
   or superseded ones.
7. **Prune.** Remove unimportant detail, leaked task-state, and obsolete entries (the backup makes
   this safe). Refine wording: state the fact and the why, nothing more.
8. **Reconcile the index.** Run `reconcile_memory_index.py` (in the meta-self-improve skill dir) so
   every topic file has a `MEMORY.md` line and there are no orphans after the churn.
9. **Skill-fit -> batched change.** Collect generalizations that match or warrant a skill. Deliver
   them through `bitranox:meta-self-improve` -> "Propagating skill (or hook) improvements upstream":
   adjust an existing skill when it fits, propose a new one (via `bitranox:skill-writer`) when it does
   not. Batch them into ONE structured change - secret/PII scan, `plugin.json` bump, repo-gate green,
   structured title/body. In `propose`/default, route as a **self-PR** for review; in `auto`, commit
   or self-PR without asking; in `off`, skip skill changes entirely.
10. **Mark done + report.** Run `python3 <this-skill-dir>/dream_state.py done` to silence the nudge
    until memory changes again. Then report: counts and one line each for merges / generalizations /
    prunes, any CLAUDE.md edits (applied or proposed), and the skill change (PR link or proposal). In
    `propose` mode, remind the user they can enable `auto` to stop the asking, or `off` to disable.

## Boundaries

- **Private memory:** back up, then apply (the whole point of a dream). Reversible via the backup.
- **CLAUDE.md (version-controlled):** propose-first in `propose`; apply in `auto`. Create it if the
  right-altitude file is missing.
- **Skills / hooks (shared, public):** never silently edit; route through the upstream-PR loop
  (self-PR in `propose`, commit-or-PR in `auto`, skipped in `off`).
- **Circle-breaker still applies:** if the same item has been consolidated twice and keeps coming
  back, stop re-writing it - escalate to a guard or hand it to the user.

## Common mistakes

- Growing the store. A dream must net-shrink noise; if it added entries, reclassify or merge.
- Dreaming without capturing first (consolidating a half-recorded session).
- Auto-editing CLAUDE.md or skills in `propose` mode (those are propose / self-PR).
- Forgetting `dream_state.py done`, so the nudge keeps firing.
- Duplicating the general and specific text instead of cross-linking them.
