# Handover - 2026-10-30, contribution sweep wave 3: 10.7.0 under review fixes, twin batch next

## In flight

- The user's scope decision stands: work every open OPEN-WORK item (main checkout
  EXECUTION-USER-REVIEW.md, "Backlog sweep scope"). Current item: [200] wave 3; its line says
  where each batch stands.
- 10.7.0 (b1 toolbox + b7 hooks) is integrated UNCOMMITTED in this worktree
  (`.claude/worktrees/bl4-int`, branch bl4-int, based on origin/master b26e0198 = 10.6.1). Bumped
  to 10.7.0, CHANGELOG [10.7.0] written, artifacts regenerated, CI-parity gate passed BEFORE the
  review fixes (not valid any more).
- An independent review found 14 defects; four fix agents work in this worktree on disjoint files.
  Three reported FIXED (findings 1-6, 10, 11, 14 and the lows; CHANGELOG and the compuse-toolbox
  gate row updated to match). STILL RUNNING: the agent for winpytest (7), markerwatch (8, 9),
  bump_version --rebase bytes (12), mutation_arm Windows split and tree kill (13). Its report
  arrives as a message; a 60-minute pure-deadline shell (sleep 3600) backs it up.
- Mirrored-skill work (m1 devops-bmk, m2 five twins) is held OUT of 10.7.0: restored to HEAD in
  this worktree; the edits live in `.claude/worktrees/bl3-m1`, `bl3-m2` and in the tool-repo
  worktrees `apps/utils/bmk-bl3`, `KI/btx-skill-jev-judge-bl3`, `libs/lib_layered_config-bl3`
  (already fast-forwarded to origin 7.6.0 and the twin 3-way merged, clean),
  `libs/bitranox_template_py_lib-bl3`, `libs/btx_lib_mail-bl3`, `apps/pve-bindsnap-bl3`.

## Decided

- User decision (verbatim in EXECUTION-USER-REVIEW.md): "Push, bump and release" for the six tool
  repos (five PyPI releases; pve-bindsnap push only).
- Order that avoids the mirror-gate deadlock with the INSTALLED (10.4.1) PreToolUse gate, which
  reads twins from main checkouts: (1) ship 10.7.0; (2) commit each twin in the tool repo's MAIN
  checkout after a ff pull, pathspec only, with a bmk patch bump (bump writes pyproject, CHANGELOG,
  plugin.json, uv.lock); (3) marketplace commit + push of m1+m2 as 10.7.1; (4) push each tool repo,
  wait CI, make release (release from a checkout on the default branch; btx_lib_mail's main has a
  peer's tracked handover.md edit, so release it from `git worktree add -f <path> master`).
- Peer sessions told: the lib_layered_config one (go; check `git diff uv.lock` shows only the
  version line and `grep -c '^agentdag = false' uv.lock` prints 0), the one near bmk (go), the
  jev-judge one (no reply yet).
- Review rounds for 10.7.0: one re-review of the fix round, against its real parent; no third
  round for exotic-path findings.

## Still open, untouched

- [30], [96], [1040]-[1080] in OPEN-WORK.md; the NEEDS-USER builds NU1-NU9 under [200].

## Next action

When the last fix agent reports: grep all four fix diffs' ADDED lines for monkeypatch/noqa/ignore,
update CHANGELOG for its findings, rerun `env -u VIRTUAL_ENV PYTHONUNBUFFERED=1 python3
plugins/bitranox/hooks/repo-gate.py --ci` and `--mirrors`, dispatch one re-review of the fix round,
then commit 10.7.0 (message file first, no attribution), push in the background (pre-push suite),
ci_wait twice, ship the b1/b7 queue entries (`--note 10.7.0`; b7 line 8 is "partial", keep it).

## How to verify

- `env -u VIRTUAL_ENV python3 plugins/bitranox/hooks/repo-gate.py --ci` and `--mirrors`.
- CI: `uv run <toolbox>/scripts/ci_wait.py --ref HEAD --repo bitranox/bitranox-skills --event push --timeout 590`.

## Lessons for the next nap

- tooling: When a PreToolUse gate fix ships in the marketplace, it does not gate the shipping session: the hook runs from the installed cache until the user updates and reloads, so plan push order against the OLD gate.
- When a reviewer is handed a merged branch, ask it to check verdict precedence across the merged parameters: the ci_wait merge kept every parameter wired and still let a completed failed run wait into a timeout.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
