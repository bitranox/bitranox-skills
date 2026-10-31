# Handover - 2026-10-31, [210] sweep: (d)(e)(f)(r)(s) done through 10.9.13; (p) next

## In flight

- 10.9.10 (block-env-dump: git remote -v, git config --list, .env and credentials reads) is pushed
  as ca506fa8; 10.9.11 (git_verb_dir tilde expansion, 4a356a9e) and 10.9.12 (toolbox nudge for a written
  template-distribution script) follow it, from this
  worktree (`.claude/worktrees/bl9-twins`, branch bl9-twins, pushes go HEAD:master). Watch each with
  `ci_wait.py --sha <full sha>`.
- bmk plugin 3.33.3 (devops-bmk mirror of 10.9.9) is on origin with CI and CodeQL green; bmk's
  release workflow fires on `v*` tags only, so no PyPI release followed.

## Decided

- `git remote -v` is refused even though the replay found 277 harmless hits and no https userinfo:
  logged with the reason in the main checkout's EXECUTION-USER-REVIEW.md ("secret-print guard").
- repo-gate unreadable commit/push target: "Keep fallback + note (Recommended)" (user,
  2026-10-31); no code change follows.
- The pve-bindsnap pair drifts in `--mirrors` because a peer session has unpushed 1.3.0 commits
  there; theirs to mirror.

## Still open, untouched

- OPEN-WORK.md [30], [96] (both waiting on live data), [210] (rest of the sweep), [510] (two user
  decisions).

## Next action

[210] (p): reproduce first. Does the user-decision-log hook miss the answer to an AskUserQuestion
whose first send the premise hook refused? This session's own refused-then-resent answer WAS
logged (queue e8eb6925, a private repo's queue). Replay the hook on the two events and compare
before changing anything. (r) shipped in 10.9.13, (f) moved to the template's OPEN-WORK.md [40],
(d) 10.9.12, (s) 10.9.11, (e) 10.9.10.

## How to verify

- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`.
- `env -u VIRTUAL_ENV python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (only the peer's
  pve-bindsnap pair may drift).
- `contrib_queue.py queues` lists the entries [210] names.

## Lessons for the next nap

- When a batch's work lands in another repo (a private repo, a local toolbox, a user command), close its queue entries in the same pass: wave-3 b9a/b9b landed on 10-29 and 22 entries stayed open a day, reading as unworked.
- When a background CI wait uses `--ref HEAD` and a later local commit moves HEAD, read the sha it printed before trusting its verdict; pass `--sha <full sha>` for a wait that outlives the next commit.
- When peers push to the marketplace during the 5-6 minute pre-push gate (three times on 2026-10-30/31), expect the cannot-lock-ref refusal and rebase plus re-bump from origin's plugin.json; consider messaging the active peers before a push.
- tooling: the dream_state nap flag is keyed by cwd, so a nap marked done from the main checkout does not clear the gate for a session whose cwd is a worktree; mark it for the session's own cwd.
- When a refusal guard adds firings that a replay shows are all harmless, put a form the guard itself passes into the refusal text, so each block costs one retry (block-env-dump's redacted `git remote -v | sed` hint).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
