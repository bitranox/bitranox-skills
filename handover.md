# Handover - 2026-09-25, ranks 7 and 14 closed (7.23.0-7.23.6 shipped), rank 12 blocked on data

## In flight

Nothing running. All seven releases 7.23.0-7.23.6 are on origin/master and CI-green on the last one.
No agent, fixer or landing branch is outstanding.

## Committed, or not

- **Pushed:** 7.23.0 (rank 14 sha-literal-nudge) through 7.23.6. This handover plus the OPEN-WORK.md
  reconcile go in one commit on top.
- **Not in git, by design (gitignored, main checkout):** `.plan/jev-choicev1-2026-09-25/` (rank 12
  eligible-row counts and report). `EXECUTION-USER-REVIEW.md` from the jev-roster worktree is now
  copied to the main checkout root (cmp identical), so the worktree can be removed.
- **Scratch only, will be swept:** the eight reviewers' probes and the fixers' replay artifacts under
  this session's scratchpad. Nothing in them is needed again; findings and numbers are in
  OPEN-WORK.md rank 7's closed line and in CHANGELOG 7.23.0-7.23.6.

## Decided, and why - do not reopen

- **Review first, then fix, one fixer per module** (secret_patterns, memory store, shell_text+masking,
  low batch). Every fixer had to turn each reviewer finding into a failing test before fixing, and
  report NOT REPRODUCED otherwise, so the coordinator did not have to rebuild fixtures itself.
- **Fixers use provisional versions; a landing agent renumbers at landing, strictly in order.**
- **Cookie values are now always redacted** (7.23.2), including harmless ones - acceptable for egress.
- **A fixed wall-clock ceiling in a perf test is a defect**; 7.23.4 asserts growth ratio (< 8 for 4x).
- **Rank 12 is blocked on data, not dropped** - only 3 eligible rows existed.

## Decided against, and why

- **Parens in the SEP/LIST_SEP regexes** (7.23.3): the replay showed it cut quoted `echo "(...)"`
  labels; the subshell gap stays open as OPEN-WORK rank 172.
- **Re-running the Windows CI flake until green**: it was a real lock defect, fixed in 7.23.5.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): next sweep slice, skill-script (79 targets).
- Rank 12 (USER): Jev router decision - wait for >= 40 eligible rows, then the blind panel.
- Rank 150 / 160 (FOUND): main-checkout TODO-JEV.md + fast-forward; wtclean now 17 worktrees.
- Rank 172-178 (FOUND): this session's leftovers (SEP subshell gap, commit-tell-sweep 0 blocks,
  non-canonical SKILL.md tables, sha-nudge design points).

## Lessons for the next nap

- When a subagent needs a test VM, it must check the host's free memory against the VM's size and ask before starting it: starting the 32 GB Windows test VM on a 62 GB cluster node with ~37 GB already committed wedged the node ~25 min until it rebooted, taking its guests down.
- When a perf test guards against superlinear time, assert the growth ratio between two sizes, never a fixed wall-clock ceiling: 0.5 s passed locally at 0.11 s and failed CI at 0.515 s on two OSes.
- When a subagent changes a secret redactor, require a replay listing every span the OLD code redacted and the new does not, adjudicated in full - it recurred: batch A shipped five new leaks (`*_PWD`, `$`-leading passwords, secret_id, long digit tokens, ALL_CAPS slugs) past its own tests.
- When a concurrency fix is proven only on Linux, expect Windows to break it: an O_EXCL lock file that was just deleted fails PermissionError while delete-pending on Windows; a lock must treat that as contention.
- When a reviewer's finding would need fixture trees to verify, hand the verification to the fixer as "write the failing test first, report NOT REPRODUCED otherwise" rather than rebuilding it in the coordinator.
- When parallel implementers must commit under a gate that demands a version bump, give them one provisional bump and renumber each branch at landing, in order.
- When a replay measures a guard that decides on the event's cwd, pass the recorded cwd - a command-only replay read block-partial-typecheck as 0 firings while it had blocked 88 real calls.
- When a subagent's post-push `git rev-parse` is refused by the auto-mode classifier, the coordinator resolves the sha from origin/master and runs ci_wait itself.
- When `git checkout --ours <file>` resolves a cherry-pick conflict, it replaces the WHOLE file, dropping the other side's auto-merged hunks; diff against the source commit afterwards.
- The fact reference-the-skill-edit-guard-s-receipt-is-machine-global-for-8h-not-session-scoped is STALE since 7.22.4 (receipts are per skill and session) - rewrite it via the engine.
- The fact reference-a-clobbered-audit-report-is-reported-clean-so-verify-every-clean-against-the-transcript is partly stale: audit_skills now flags a clobbered report REPORT-MISSING instead of clean.
- tooling: audit_skills reviewers inherit every user hook (the self-improve Stop gate clobbered a report; reviewers write Jev shadow rows) - queued in contrib_queue.
- tooling: decision-review-nudge fired "a /goal objective was met" while the goal was unmet - queued.

## The exact next action

Rank 10 is the top open USER item that can move today (rank 12 is blocked on data). From the MAIN
checkout (`/media/srv-main-softdev/projects/public/KI/bitranox-skills`), fast-forward it first
(rank 150), then start the skill-script slice: `audit_skills.py --scripts --kind skill-script` with
recall walled, adjudicate every claim with controls, then ask the user which batch goes first.

## Files that matter

- `plugins/bitranox/hooks/secret_patterns.py`, `shell_text.py`, `memory_engine.py`, `uuid_store.py`,
  `self_improve_signals.py` (memory_lock), `ci_watch_state.py`, `sha-literal-nudge.py`, `hatch_build.py`.
- `CHANGELOG.md` entries 7.23.0-7.23.6.
- `.plan/jev-choicev1-2026-09-25/` (main checkout) for rank 12.

## How to verify this still stands

- `git log --oneline origin/master -8` shows 7.23.0-7.23.6 plus this handover commit.
- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha $(git rev-parse --verify HEAD) --repo bitranox/bitranox-skills`
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q`

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
