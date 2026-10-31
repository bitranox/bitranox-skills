# Handover - 2026-10-31, [210] sweep: (a)-(c), (i)-(o) shipped in 10.9.4-10.9.8; (k) next

## In flight

- 10.9.7 (compuse-ssh: remote-state waiters, stdout JSON envelopes) is pushed (147e1f65); its CI
  wait runs as a background shell `ci_wait.py --sha 147e1f651af71de26a5159bb0c73aaa199db2487`.
  When it reports, confirm both workflows green; nothing else waits on it.
- Uncommitted in this worktree (`.claude/worktrees/bl9-twins`, branch bl9-twins, pushes go
  HEAD:master): `OPEN-WORK.md` ([210] gained (p)-(s)) and this file. Both ride the next commit.
- 10.9.6 (contrib_queue claim/release) and 10.9.4 (git_verb_dir leading assignments) are on
  origin with CI and the release workflow green.

## Decided

- repo-gate unreadable commit/push target: "Keep fallback + note (Recommended)" (user,
  2026-10-31, verbatim in the main checkout's EXECUTION-USER-REVIEW.md); no code change follows.
- Queue entries for (a), (b), (c), (m) are shipped; claims are this session's (ca45088c) only on
  entries already shipped, so nothing is held.
- The pve-bindsnap pair drifts in `--mirrors` because a peer session has two unpushed 1.3.0
  commits there; theirs to mirror, not this session's.

## Still open, untouched

- OPEN-WORK.md [30], [96] (both waiting on live data), [210] (rest of the sweep), [510] (two user
  decisions).

## Next action

[210] (k) devops-bmk: it is mirrored with apps/utils/bmk, so change the bmk repo's twin, release
bmk, and only then let the marketplace copy name the version. Then (q) a claim count in
`contrib_queue.py queues`, then (e), (d), (f). (i), (j), (l), (n), (o) shipped together in 10.9.8.

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

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
