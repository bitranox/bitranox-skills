# Handover - 2026-10-29 03:00, [23] batch 8 pass 1 shipped

## In flight

- [23] batch 8 (KI levels) pass 1 SHIPPED as 10.3.28 (d4b4077e on origin/master): the 25 archive
  rows (20 folded, 5 already covered) into 12 skills. The bmk twin landed as 527f82f on bmk
  origin/master (plugin.json 3.32.1, rebased by the bmk session over a peer's 5e6b9c2). Pass-1
  data is in the main checkout's gitignored `.plan/fold-23/batch8/pass1/`: all.json, e1-e3.json,
  pre/ (snapshots), results.json + results-r2.json (RED/GREEN), pass1.diff + pass1-r2.diff,
  fix_r1.py, make_checklists.py.
- The 25 facts are NOT archived yet: the user must install 10.3.28 first.
- CI for d4b4077e (10.3.28) passed (workflow and ci both success); verify with
  `ci_wait.py --sha $(git rev-parse --verify -q d4b4077e)`.
- The owed nap ran: this session's transcript is marked reviewed, 5 lessons went to the
  contrib queue. Deferred to the next full dream: 40 chain facts with superseded version claims
  (`versionrot.py scan --chain`), and 61 older unreviewed transcripts of this project.
- This worktree (`.claude/worktrees/fold-23-b7p2`): handover.md and the [23] line in
  OPEN-WORK.md are uncommitted.

## Decided

- bmk's own marketplace bumps plugin.json on every pushed skill change, even ahead of its
  pyproject version (bmk's sync only raises it): 3.32.1 at pyproject 3.32.0 is correct.

## Open decision (ask the user, one question, before pass 2)

- `feedback-tests-written-from-a-plan-cannot-catch-a-defect-in-the-plan` (tree top) says a
  plan-mandated fix that only makes code obey a rule the plan states, or only adds tests, is fixed
  and logged; process-agents-subagent-driven-development SKILL.md says every plan-mandated
  finding is the human's decision. The fold would change the skill's policy.

## Next action

After the user installs 10.3.28 (`/plugin marketplace update bitranox-skills`, `/reload-plugins`):
quote-check the installed copy against the worktree (the 12 changed skills), run ref_map and a
citer grep over the 25 slugs, take a store_manifest backup, `reconcile_memory_index.py --archive`
each of the 25 at its level, verify the manifest diff, commit and push the store (own paths only).
Then put the pass-2 policy question above to the user.

## Lessons for the next nap

- (none open: the 03:00 nap captured this session's lessons as five contrib_queue entries)
