# Handover - 2026-10-29 11:35, [23] batch 8 pass 2 shipping as 10.3.30

## In flight

- [23] batch 8 pass 2: the 8 FOLD+cut rows are folded into 7 skills and go out as 10.3.30 (this
  commit), with the devops-bmk twin in the bmk repo at plugin.json 3.32.2. Data: the main
  checkout's gitignored `.plan/fold-23/batch8/pass2/` (results.json = the fold run's rows incl.
  each editor's short_hook; green2-*.json = round-2 quotes; pass2.diff / pass2-r1.diff = before
  and after the review fixes).
- Commit order for the mirrored pair: this worktree commits first, then bmk, then push this
  worktree (`git push origin HEAD:master`), then bmk.
- After the user installs 10.3.30: quote-check the installed copy of the 9 changed skill files,
  then cut the 8 pointers (see Next action).

## Decided

- USER 2026-10-29 ("Fix and log narrow cases (Recommended)", logged verbatim in the main
  checkout's EXECUTION-USER-REVIEW.md): SDD fixes and logs a plan-mandated finding whose fix only
  makes the plan's code obey a rule the plan states or only adds tests; a fix changing the plan
  text still goes to the user. Pre-flight review and BLOCKED step 4 follow the same test.
- Declined (delta review N4): changing task-reviewer-prompt.md's "plan-mandated rubric defect is
  Important" grading. It is a severity rule the user's decision did not cover; the skill now says
  it defers to that template.
- bmk's plugin.json is bumped on every pushed skill change even ahead of pyproject.

## Still open, untouched

- Everything else: `OPEN-WORK.md`.

## Next action

After CI is green and the user installs 10.3.30: diff the installed skill files against this
commit; take a `store_manifest.py backup --scope tree`; for each of the 8 slugs, find the owning
level (`find /media/srv-main-softdev -name CLAUDE.local.md -not -path "*/.claude-memory/*" -exec
grep -l "mem:<slug>" {} \;`) and apply its short hook with `factedit.py apply --slug S --level L
--hook-file f`, trimming the gate-hook one (304 chars) to 300; `--check-tree`; commit and push
the store with own paths only. Then update the [23] line and propose the next level group.

## How to verify

- `python3 plugins/bitranox/hooks/repo-gate.py --mirror-of /media/srv-main-softdev/projects/public/apps/utils/bmk`
- CI: `ci_wait.py --ref HEAD --event push` from compuse-toolbox.

## Lessons for the next nap

- When a delta review asks to change a rule beyond the scope of the user's decision (a severity
  grading next to a routing rule), decline it with the reason and make the text defer explicitly,
  rather than widening the change silently.
