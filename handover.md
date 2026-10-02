# STALE - read 2026-10-02, work continued

## In flight

- Executing the approved plan `/home/srvadmin/.claude/plans/write-a-plan-for-piped-starfish.md`
  with bitranox:process-agents-subagent-driven-development in the worktree
  `.claude/worktrees/jev-shadow` (branch `worktree-jev-shadow`, pushed to master as each batch
  passed review).
- Tasks 1-7 are done, reviewed clean and on origin/master. 7.39.0 (Tasks 5-7) was pushed as
  e1f093b0; its CI was still running at handover time - confirm it:
  `ci_wait.py --sha e1f093b0ebfe605d5b461f85b387341b65d21d24 --repo bitranox/bitranox-skills`.
- Left: Task 8 (crosstree 4b + crosstree-deep 3b, consolidate-claude-md step 1,
  collect-knowledge stage 2), Task 9 (enforce-data-architecture-strict STEP D), Task 10 (the
  pre-registered decide-criteria OPEN-WORK line), then the final whole-branch review.
- Ledger: `.claude/worktrees/jev-shadow/.bitranox/sdd/progress.md` (gitignored). It lists every
  completed task with its commit range, the Minors carried to the final review, and the binding
  lessons for Tasks 8-9. Briefs and every task/review report sit beside it.

## Committed, or not

- Everything of Tasks 1-7 is committed and pushed. This file and OPEN-WORK.md (rank 16 updated)
  are committed together after e1f093b0.
- Uncommitted by design: the gitignored ledger, reports and `EXECUTION-USER-REVIEW.md` in this
  worktree.
- The model gate (`skill_receipt.py start plan-execution`) was armed in the old session; re-arm it
  before dispatching, and run `end plan-execution` after the final review.
- Leftover worktree `.claude/worktrees/agent-a26b133c84c5141bb` (the 7.37.1 Windows fix, all
  pushed) can be removed; a worktree-isolated session cannot do it.

## Decided, and why - do not reopen

- `classifier_skills = shadow` is ON on this machine (set for Task 4, logged in
  EXECUTION-USER-REVIEW.md); the installed 7.31.5 hooks ignore the key. Reverse with
  `settings.py set classifier_skills off`.
- `jev_shadow.py run` passes the `classifier_model` knob as `--model` (the hooks honour it; a
  shadow run on another model measures the wrong thing).
- The shared reference now states: a missing verdict loses only the pairing; `run` still asks
  and bills EVERY line of items.jsonl, so cut lines BEFORE `run` to avoid sending them.
- dream-placement keeps at most 2 lines per fact (current and routed-to level): the raw build is
  ~46k items. Firing and prune judge every fact because those steps already review every fact.
- One minor bump per pushed batch; a concurrent session pushed twice during gates today, so expect
  to fetch, rebase, and resolve CHANGELOG/plugin.json/pyproject with the newer entry on top.

## Decided against, and why

- No "verdict on every item" by default in the reference: a step that needs full coverage says
  so itself (Tasks 5-7 all do).

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on Stop-gate decide rows; rank 16 is this plan; new
today: 220 (perf-test flake), 230 (dream step 5 promotes on hold), 240 (send-mail mirror drift).
A peer session asked for the MAIN checkout to be fast-forwarded (rank 150); this session could not
touch it.

## Lessons for the next nap

- When a skill text adds a shadow or second-opinion step, a haiku RED shows it hands the decision
  to the second opinion unless the text says plainly that the agent's own verdict is the result.
- When a tool sends every line of an input file to a paid service, document that leaving an item
  unlabelled does not stop it being sent; say how to cut it before the call.
- When a probe or report says "judged all N", count the verdict lines against the items before
  believing it: the Task 4 agent left one unjudged and reported 30 of 30.
- When an error message prints a path, use %s not %r: repr doubles every backslash on Windows and
  only the windows-latest cell catches it.
- tooling: subagents sharing one scratchpad overwrite each other's same-named files (bump.py was
  clobbered); give each dispatch its own scratch subdirectory in the prompt.

## The exact next action

Rank 12 is top-ranked but blocked on data, so rank 16, which the user is waiting on: in
`.claude/worktrees/jev-shadow` read `.bitranox/sdd/progress.md`, confirm e1f093b0's CI is green,
re-arm the model gate, then dispatch the Task 8 implementer (opus) from
`.bitranox/sdd/task-5to9-36114b73-brief.md` with the ledger's lessons, the worked examples
(grep `jev_shadow` in compuse-toolbox, process-review-enhance-code-quality and meta-dream-tree
SKILL.md) and a private scratch subdirectory.

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/jev_shadow.py` (+ `jev_shadow_sites.py`,
  `jev_shadow_log.py`, `jev_shadow_report.py`, `jev_shadow_ports.py`) - the tool.
- `plugins/bitranox/skills/meta-self-improve/jev_sites/*.json` - the 10 site question files.
- `plugins/bitranox/skills/meta-self-improve/references/jev-shadow.md` - the shared procedure.
- `plugins/bitranox/skills/{compuse-toolbox,process-review-enhance-code-quality,meta-dream-tree}/SKILL.md`
  and their `.skillwriter/checklist-2026-10-02-jev-shadow.md` - the worked examples.
- `plugins/bitranox/skills/meta-dream-tree/references/dream-core.md` - the `jev shadow:` report line.

## How to verify

- `git log --oneline -3 origin/master` shows e1f093b0 (7.39.0) under this handover commit.
- `python3 plugins/bitranox/skills/meta-self-improve/jev_shadow.py status` - `shadow: on`.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with
  ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/meta-self-improve/tests/
  plugins/bitranox/skills/compuse-toolbox/tests/ -q` - green.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
