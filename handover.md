# Handover - 2026-10-08 14:35, [17] being built (plan Task 1 of 10 done, branch not pushed); [16] shipped as 8.6.0/8.6.1

Two sessions are in play. Session A (worktree `jev-shadow`) shipped [16]; its state below is carried
from its 13:30 handover (commit 8f1573be) unchanged in substance. Session B (worktree
`notify-decide-failed`) is building [17].

## In flight

- Session B, [17]: the user chose to build the memory and backlog tools as a Claude Code mod
  (option 3), then agreed the design one decision at a time. Implementation runs subagent-driven
  from `docs/plans/2026-10-08-mods-memory-backlog-tools-plan.md`. Task 1 (open_work.py read side)
  is done and reviewed clean; Tasks 2-10 are not started. The progress ledger is
  `.bitranox/sdd/progress.md` in the `notify-decide-failed` worktree (gitignored there, so resume
  FROM that worktree); it also lists the reviewer's minor findings for the final review and the two
  plan deviations already applied.
- Session A: nothing is running. CI is green on 8.6.1 (f7326534) and on the 3.14-matrix commit
  079f9a93; release v8.6.1 is published (tag on 079f9a93); 8.6.0 has no release, its CI was red.
- [12] belongs to session A and waits on time: step 6 needs about a week of decide rows, earliest
  2026-10-13.

## Committed, or not

- Branch `mods-memory-backlog-tools` (worktree `notify-decide-failed`), on top of origin 8f1573be,
  NOT pushed: the design doc, the plan, and Task 1 (977535b3: `plugins/bitranox/hooks/open_work.py`,
  its tests, the bump to 8.7.0 in plugin.json and pyproject.toml, and a CHANGELOG `## [8.7.0]`
  entry). Committed with this handover: OPEN-WORK [17] progress and the new [500].
- Session A told by message that [17] holds 8.7.0; if it ships first, re-bump above it at push.
- Not in git, nothing depends on them: the scratchpad probe plugins (`probe-both`), which answered
  the mods API questions now recorded in the memory fact on Claude Code mods.
- The `jev-shadow` worktree's gitignored `.plan/` is still the only copy of three experiment
  records ([390]).

## Decided, and why - do not reopen

- [17] design (user, 2026-10-08): v1 is backlog_list/add/close plus memory_add and contrib_add;
  shipped INSIDE the bitranox plugin (hooks.json gains `modules`); all logic in Python behind one
  JSON bridge (`hooks/mod_bridge.py`), TypeScript only relays; rank is REQUIRED on backlog_add and
  the tool only enforces it is free over every line.
- Measured on the live backlog after the design was approved, and corrected in the design doc: ranks
  are not all tens (5, 7, 12-19, 121; three ranks on two lines each) and the file is not sorted, so
  a rank must be a free positive integer (tens only suggested) and a new line goes after the item
  with the largest smaller rank.
- Probed on 2.1.290: one hooks.json holds classic hooks AND a module (both ran); a registered tool
  answers `{ result }`; `claude plugin test` has no engine beneath, so a test stubs every `$` op
  (op hooks answer `{ value }`, session.start answers `{ cwd }`, `mock.env` for env.get).
- The version bump and CHANGELOG moved into Task 1's commit: the repo gate refuses any plugins/
  change without a version above origin's and a matching CHANGELOG heading. Each later task extends
  the `[8.7.0]` entry.
- Session A's [16] decisions: see commit 8f1573be's handover (liveness via the session registry plus
  procStart; holders per platform; scratch 1 day, one-offs 7 days).

## Decided against, and why

- A backlog/status band or pane first (recommended, the user picked the tools instead); a separate
  opt-in plugin (the user chose inside, accepting the unmeasured older-CLI risk, which plan Task 8
  now measures before release); backlog logic in TypeScript (two parsers in two languages).
- Session A: pruning this machine by hand (the hook's first run is the proof, [400]).

## Still open, untouched

`OPEN-WORK.md` is the list: [12] (session A, after 2026-10-13), [18] deferred by the user, [19] dirty
worktrees and branches left to judge, [245] a locked agent worktree, [390] copy the `jev-shadow`
`.plan/` records out, [400] observe the first hook-driven prune, [410] the foreign-mount guard's
missing test, [420] two hook rows missing from docs/architecture.md, [500] the guard proposal owed
to the user for the &&-chaining rule (recurrence 3).

## Lessons for the next nap

- When a heredoc resolver's assertions are the safety check, put && on the heredoc OPENER line: a
  terminator ends the statement, so a failed assertion let the next line commit conflict markers
  (already captured, recurrence 3; the guard proposal is [500]).
- When a design fixes rules about existing data, count the live data first (already captured as
  feedback-measure-the-live-data-before-a-design-fixes-rules-about-it).
- When a plan puts the version bump in its last task, move it to the first commit that touches
  plugins/: this repo's commit gate refuses the commit otherwise, and later commits ride that bump.
- When a worktree-isolated session runs tests, drop the `env -u VIRTUAL_ENV` prefix (refused) and use
  `uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2
  python -m pytest ...`; write scripts with Write and run them with python3, never heredocs.
- When a tracked plan or handover names a test host, key or private path, scrub it before the
  push and fold the fix into the commit that introduced it (Task 9 named the Windows dev VM).
- tooling: the plan-writing skill never asks whether the repo gates version bumps per commit; a plan
  for this repo that bumps last is unexecutable as written.
- Carried from session A's 13:30 handover (rmtree onexc re-call, mutation-arm failure lines, mmap
  trackfd, unix socket path limit, Windows dev box before push, workflow-change tag refusal, run the
  route a doc names, merge a live session's handover, bump pyproject with plugin.json) and from
  session B's 11:50 handover (31b9e205): not yet confirmed napped.

## The exact next action

[17] stays the top open USER item and is mid-build: from the `notify-decide-failed` worktree, invoke
bitranox:process-agents-subagent-driven-development on
`docs/plans/2026-10-08-mods-memory-backlog-tools-plan.md`; the ledger says Task 1 is done, so it
resumes at Task 2 (`task_brief.py <plan> 2`). Arm the model gate first (the skill says how). Before
any push, `git fetch` and re-check origin's version against 8.7.0.

## Files that matter

- `docs/plans/2026-10-08-mods-memory-backlog-tools-plan.md` and `-design.md`
- `plugins/bitranox/hooks/open_work.py`, `plugins/bitranox/hooks/tests/test_open_work.py`
- `.bitranox/sdd/progress.md` (worktree-local ledger), `OPEN-WORK.md` ([17], [500])
- Session A: `plugins/bitranox/hooks/tmp_prune.py`, `plugins/bitranox/hooks/tmp-prune-hook.py`,
  `plugins/bitranox/hooks/process_liveness.py`

## How to verify

- In the `notify-decide-failed` worktree: `git log --oneline origin/master..HEAD` shows the design,
  two plan commits, Task 1 and this handover; `uv run --with pytest --with PyYAML --with lxml
  --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest
  plugins/bitranox/hooks/tests/test_open_work.py -q` passes 10.
- Session A: `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha
  f73265348c6842bf1db3e635ba963313704bbf07` exits 0.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
