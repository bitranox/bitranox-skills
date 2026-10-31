# Handover - 2026-10-31, [210] and [510] closed; 10.9.14 pushed; cleanup next

## In flight

- Pushed today from this worktree (`.claude/worktrees/bl9-twins`, branch bl9-twins, pushes go
  HEAD:master): 10.9.10 through 10.9.14. CI is green on 10.9.10 through 10.9.12; 10.9.13 and
  10.9.14 have CI waits running as background shells. Confirm both.
- The local toolbox (~/.claude/skills/toolbox, no remote) has commit e161c0b (the decisionlog
  nested-log pointer).

## Decided

- `git remote -v` is refused even though the replay found 277 harmless hits. Logged with the
  reason in the main checkout's EXECUTION-USER-REVIEW.md ("secret-print guard").
- (p) refuted: the hook logged the M6 answer at 18:14:00Z into provmm_proxmox_shim's log, because
  the event cwd was there. The lookup ran from the umbrella. Fixed in the decisionlog lookup, not
  in the hook.
- (f): fixed at the source (the template CLAUDE.md, and rename_project 1ff508a). The 14 stale
  derived copies moved to bitranox_template_py_cli's OPEN-WORK.md [40].
- The datamax "serialise implementers in one worktree" entry was dropped: the SDD skill's Never
  list already covers it.
- [510] closed: (4) and (5) were both fixed in 10.6.0 (9e44f63f) and are test-pinned, so no
  user decision is left.
- repo-gate unreadable target: "Keep fallback + note (Recommended)" (user, 2026-10-31).

## Still open, untouched

- OPEN-WORK.md [30], [96]: both waiting on live data.

## Next action

Cleanup: once CI is green on the last push, remove this worktree and its branch, then fast-forward
the main checkout. Final report to the user: run `/plugin marketplace update bitranox-skills`
then `/reload-plugins` (installed 10.7.2); the pinned-fact recurrence mismatch (index 12 vs body
13); the template notebook git+https finding (template OPEN-WORK [30]).

## How to verify

- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`.
- `env -u VIRTUAL_ENV python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (only the peer's
  pve-bindsnap pair may drift).
- `contrib_queue.py queues` lists what is still open.

## Lessons for the next nap

- When a batch's work lands in another repo (a private repo, a local toolbox, a user command), close its queue entries in the same pass: wave-3 b9a/b9b landed on 10-29 and 22 entries stayed open a day, reading as unworked.
- When a background CI wait uses `--ref HEAD` and a later local commit moves HEAD, read the sha it printed before trusting its verdict; pass `--sha <full sha>` for a wait that outlives the next commit.
- When peers push to the marketplace during the 5-6 minute pre-push gate (three times on 2026-10-30/31), expect the cannot-lock-ref refusal and rebase plus re-bump from origin's plugin.json; consider messaging the active peers before a push.
- tooling: the dream_state nap flag is keyed by cwd, so a nap marked done from the main checkout does not clear the gate for a session whose cwd is a worktree; mark it for the session's own cwd.
- When a refusal guard adds firings that a replay shows are all harmless, put a form the guard itself passes into the refusal text, so each block costs one retry (block-env-dump's redacted `git remote -v | sed` hint).
- When an answer reads as missing from USER-DECISIONS.jsonl, search the logs of nested repos too: the hook writes where the session's cwd was at answer time (found 2026-10-31, M6 in the shim's log).
- When a queue entry says a skill "says nothing" about X, grep the skill's Never list first: the datamax serialise-implementers entry was already a Never line.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
