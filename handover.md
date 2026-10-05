# Handover - 2026-10-05 16:45, open-work batch: 7.41.0 shipped, CI red on macOS/Windows (fix in flight), wave D planned

Working tree for all of this: the `jev-shadow` worktree (`.claude/worktrees/jev-shadow`, branch
`worktree-jev-shadow`) is the INTEGRATION branch. Batch records are in its gitignored
`.plan/openwork-batch-2026-10-04/` (PLAN.md, FIXER-RULES.md, DECISIONS-TAKEN.md, CLOSURES.md,
waveB/, waveC/, waveD/). They exist only in that worktree: copy that dir out before removing it.

## In flight

- **master is RED.** 7.41.0 (de455179, pushed) failed CI run 37321834982 on
  `tests (macos-latest, py3.13)` and `tests (windows-latest, py3.13)`; every ubuntu cell and the
  conventions gate passed. A fixer subagent was dispatched (own worktree under
  `.claude/worktrees/agent-a6fa9...`) to root-cause, verify on the Windows dev VM, bump to 7.41.1, push
  and wait on CI. FIRST ACTION of the next session: `git fetch origin`, then
  `gh run list --repo bitranox/bitranox-skills --branch master --limit 5 --json headSha,name,conclusion`
  and check whether a 7.41.1 commit landed and went green. If not, re-run the failing tests
  (`gh run view 37321834982 --log-failed`) and fix them first; nothing else ships onto red master.
- The user was given `main-housekeeping.sh` (session scratchpad) for ranks 150/245: park
  TODO-JEV.md, fast-forward the main checkout, remove the leftover agent worktree. As of 16:40 it
  had not run (TODO-JEV.md still in the main checkout). Its logic is in OPEN-WORK [150]/[245].

## Committed, or not

- On origin: 7.41.0 = waves A+B (ranks 99/191, 125, 135, 172, 174, 176, 190, 192, 193, 220, 230
  closed; 170-186 largely fixed). Template repo `libs/bitranox_template_py_lib` has commit 01cb988
  (plugin 2.0.3, the 176 table re-pad) NOT pushed: push it only after master is green, since its
  `--mirror-of` compares against marketplace origin text. It also carries someone else's earlier
  unpushed 09b1d2e.
- Committed locally on the integration branch, NOT pushed: this handover + OPEN-WORK reconcile
  (210 and 175 closed, new USER [13], 177/245 updated). Push it after the 7.41.1 fix lands:
  `git fetch origin && git rebase origin/master` in the jev-shadow worktree, then push.
- Memory store: 88 fact bodies edited (rank 210), store commit 3332c791, pushed.
- Uncommitted on disk, by convention: `btx-skill-jev-judge/CLAUDE.md` (rank 192; that repo
  gitignores its CLAUDE.md). The 186.3 coding-python-gitignore caveat draft is in the session
  scratchpad (`b9/`), not landed: it needs the igittigitt twin changed in the same step.

## Decided, and why - do not reopen

- 30 design decisions, asked one at a time, are in DECISIONS-TAKEN.md (`.plan/...`). Two went
  against the recommendation: D26 (contrib_queue store error -> exit 2) and rank 99 (a slash
  command's args text counts as a typed prompt - replay every human_text consumer before shipping).
- User directive 2026-10-05: "unify the 0/1/2 exit codes" (0 yes, 1 ran-and-no, 2 could not run).
  Policy answers NU-1..NU-9 (all as recommended): a whole-action refusal -> 2; gate.py and
  fleet_ssh pass the wrapped code through; only yes/no verbs move to 1; the --json ok rule
  (ok = ran without error, an envelope on every exit 2) applies plugin-wide; blockless pointer
  files are not a level; audit_skills lists tracked files only; 7 other-repo queue entries get
  re-filed in their own repos; the two homeless Python lessons go into
  coding-python-use-modern-libraries and process-test-design; new OPEN-WORK/handover lines use
  repo-relative paths (no rewrite of old lines).
- One integration branch with a version bump as its first commit; every fixer branches from it, so
  the repo-gate commit hook passes inside fixer worktrees.

## Decided against, and why

- No history rewrite for paths already in OPEN-WORK.md (append-only master).
- D17, D19, D23, D25, D6: keep current behaviour (each measured or argued in waveB/DECISIONS.md).

## Still open, untouched

`OPEN-WORK.md` is the list. [13] (wave D) is the top workable USER item; [12] and [14] wait on
data; [18] is deferred by the user; [96] waits on shadow data; [150]/[245] wait on the user's script.

## Lessons for the next nap

- When a worktree-isolated session must touch the main checkout or another worktree with git, it
  cannot (cd, -C and GIT_DIR forms are all refused); hand the user one guarded script to run with `!`.
- When a fixer's commit is blocked by reformat-md-tables re-dirtying a file it does not own, copy
  its finished files into the integration worktree (cp + cmp) and commit there.
- When asking a user ~30 design questions, first offer the meta-choice (one at a time / accept all /
  only the weighty ones); this user chose one at a time.
- When arming ci_wait in the background, pass `--timeout` (there is no `--deadline`) and run it
  ALONE, nothing chained after it; block-masked-gate-exit refuses a trailing command.
- When a release is green on Linux, CI can still be red on macOS/Windows: run the touched hook test
  dirs on the Windows dev VM before pushing a batch that changed path, quoting or file-write code.
- tooling: `git rev-parse` bare prints an unresolvable name back; the nudge fired on a read-only use.

## The exact next action

Check master's CI (In flight, first bullet). Once master is green: rebase and push the local
handover commit, then work [13]: update FIXER-RULES.md's base sha to the integration head and
dispatch the 13 groups of `.plan/openwork-batch-2026-10-04/waveD/PARTITION.json`, group D-8
(repo-gate crash exits 0) first.

## Files that matter

- `.plan/openwork-batch-2026-10-04/` (in the jev-shadow worktree): FIXER-RULES.md,
  DECISIONS-TAKEN.md, CLOSURES.md, waveD/PARTITION.json, waveD/EXITCODES.md, waveD/PLAN.md.
- `plugins/bitranox/hooks/repo-gate.py` (D-8 first), `OPEN-WORK.md`, `CHANGELOG.md`.

## How to verify

- `git log --oneline -3 origin/master` shows de455179 (7.41.0) or a 7.41.1 fix on top.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci`
  ends with `repo-gate: all checks passed.`

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
