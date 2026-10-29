# Handover - 2026-10-29, [23] batch 8 pass 1 archived, pass 2 waits on one user decision

## In flight

- [23] batch 8 (KI levels) pass 1 is COMPLETE: shipped as 10.3.28 (d4b4077e), bmk twin 527f82f
  (plugin.json 3.32.1), and the 24 folded facts archived in the memory store (22ba62e, pushed).
  The 25th (never-capture-a-negative-tool-claim) was already archived by a peer dream.
- Pass 2 (the 8 FOLD+cut rows) has not started. Its data: the main checkout's gitignored
  `.plan/fold-23/batch8/dispositions.json` (rows with disposition FOLD+cut).
- This worktree (`.claude/worktrees/fold-23-b7p2`): handover.md and the [23] line in
  OPEN-WORK.md are committed in the same change as this file.

## Decided

- bmk's own marketplace bumps plugin.json on every pushed skill change, even ahead of its
  pyproject version (bmk's sync only raises it): 3.32.1 at pyproject 3.32.0 is correct.

## Open decision (ask the user, one question, before pass 2)

- `feedback-tests-written-from-a-plan-cannot-catch-a-defect-in-the-plan` (tree top) says a
  plan-mandated fix that only makes code obey a rule the plan states, or only adds tests, is fixed
  and logged; process-agents-subagent-driven-development SKILL.md says every plan-mandated
  finding is the human's decision. The fold would change the skill's policy.

## Next action

Put the open decision above to the user as one AskUserQuestion. Then run pass 2 with the
skill-writer flow used for pass 1 (skill_receipt start, snapshots, RED, editors, GREEN, qcheck,
review, checklists, CHANGELOG + bump, repo-gate --ci, push, CI; after install: quote-check,
ref_map + citer grep, store_manifest backup, archive, verify, store commit).

## How to verify

- Store: `reconcile_memory_index.py --check-tree /media/srv-main-softdev` reports
  `TOTAL tree problems: 0`; no pointer `(mem:<slug>)` for the 24 slugs in
  `.plan/fold-23/batch8/pass1/` remains in any CLAUDE.local.md.
- CI for 10.3.28: `ci_wait.py --sha` with the full sha of d4b4077e.

## Lessons for the next nap

- (none open)
