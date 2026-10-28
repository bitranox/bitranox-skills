# Handover - 2026-10-29 00:40, [23] batch 7 done

## In flight

- Nothing part-done. [23] batch 7 is complete: pass 1 in 10.3.19, pass 2 in 10.3.23, installed
  text quote-checked (22 of 22 files identical), 34 pass-1 facts archived and 13 pass-2 hooks cut
  (memory store commit bb7b45e, pushed). btx-skill-jev-judge 0.3.6 is on PyPI, its main is pushed
  with CI green, and the GitHub release v0.3.6 exists.
- Check: `ci_wait.py --ref HEAD` for this repo's latest push.

## Decided

- Mine (logged in EXECUTION-USER-REVIEW.md): the jev paid-service fact is CUT, not archived (its
  rule is general beyond jev-judge). The 8 already-cut rows keep their hooks (KEEP).

## Noticed, not mine

- `reconcile_memory_index.py --check-tree` reports 2 sideways refs, both in rotek levels and both
  other sessions' work: `reference-a-one-shot-system-task-on-windows-...` (projects/rotek) and the
  untracked `reference-a-stuck-unresizable-window-...` (lxc-pydev level).

## Next action

[23] batch 8: list which levels' phase-1 FOLD/ALREADY rows (`.plan/fold-23/rows.json`) no batch
recorded on the [23] line has handled yet, and propose the next group to the user.

## Lessons for the next nap

- tooling: When a tag-only push is refused by repo-gate's mirror check, drop any redirection
  (`2>&1`, `> f`) from the push command: pushes_only_tags reads it as a refspec ([880]).
- tooling: When a `memory_engine`/`heal` call runs with its cwd under a gitignored scratch dir
  such as `.plan/`, check afterwards for scaffolded empty CLAUDE.local.md/CLAUDE.md pairs there
  (eight appeared at once on 2026-10-28) and delete them by exact path.
