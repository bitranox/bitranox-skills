# skill-writer checklist - meta-dream-tree (2026-07-18, toolbox consolidation pass)

Change: added step 10b "Toolbox pass (consolidate; PROPOSE-ONLY)" + a report line in step 11, and
authored the shared "## Toolbox pass" section in references/dream-core.md (single source cited by
all dream modes). The tree dream now proposes merging near-duplicate local tools and flagging stale
ones - detect + propose only, never editing tool code.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] RED: the tool endpoint lived only in per-turn capture (meta-self-improve). The dreams
      consolidate memory but knew nothing about the local toolbox, so it was never deduped/merged -
      the tool analogue of the dedup the dream already does for memory was missing.
- [x] GREEN: step 10b runs the CONSOLIDATE delta from dream-core "Toolbox pass" (list the toolbox,
      propose merges/flags), PROPOSE-ONLY (the actual merge is a TDD change via meta-self-improve),
      no usage-based prune (forgetting-is-usage-based-only), skip when no toolbox exists. Report line
      added.
- [x] Single-sourced: the mechanics live once in dream-core.md; the SKILL.md states only its delta.
- [x] Security scan: prose only; no secrets/hosts/paths (the ~/.claude/skills/toolbox path is a
      generic local location).
- [x] CSO description: unchanged (body edit).
- [x] Token budget: one step + one report clause; skill stays within budget.
