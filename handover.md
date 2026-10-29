# Handover - 2026-10-29 22:30, sweep wave 1 shipped, [200] triaged

## In flight

- The user's scope decision (main checkout EXECUTION-USER-REVIEW.md, "2026-10-29 Backlog sweep
  scope"): work every open OPEN-WORK item, skip only items waiting on something outside the
  session. Wave 1 is done: 34 items closed in 10.5.0, a Windows fix in 10.5.1, CI green on both.
- Wave 2 ([200] triage) is done: 310 entries classified, 72 SHIPPED/STALE closed; 229 ACTIONABLE
  and 9 NEEDS-USER remain (notes: main checkout .plan/contrib-triage-2026-10-29/).
- [28] closed: the user chose "Stay regex-only (Recommended)" (EXECUTION-USER-REVIEW.md).
- User decisions still owed, one at a time: [510] (4) bridge OSError exit 1 vs 2 (agent
  recommends 2); [510] (5) memory_add body optional on an update (agent recommends optional);
  then the 9 NEEDS-USER triage entries.
- Still owed by the USER: install the current plugin (`/plugin marketplace update
  bitranox-skills`, then `/reload-plugins`); the cache here is behind origin.

## Committed, or not

- All pushed to master. The integration worktree `.claude/worktrees/bl-integrate` and the old
  `fold-23-b7p2` checkpoint worktree are expendable once this handover lands.

## Decided

- Agents left uncommitted diffs; one integration worktree applied them with `git apply --3way`,
  byte-compared every single-owner file against its owner, and resolved the one real conflict
  (repo-gate's tool-repo verdict block) by hand. An opus review confirmed the resolution.
- The peer bmk session's devops-bmk twin line rode in 10.5.0 instead of a separate 10.4.5, so two
  sessions did not race for the version number.
- The compuse-vnc twin drift seen mid-sweep was a peer's in-flight change; it landed as 10.4.4.

## Still open, untouched

- [30] (blocked on compact mode proving itself), [96] (waits for dream runs), [1040]-[1080]
  (found by the sweep): `OPEN-WORK.md`.

## Next action

Wave 3: group the 229 ACTIONABLE entries by target file or skill (awk over the notes' plan
column), fan batches out to worktree agents, integrate, release, then ship each entry with
`contrib_queue.py ship queue_key:<key> --match <text> --note <version>`.

## How to verify

- `uv run <toolbox>/scripts/ci_wait.py --ref HEAD --repo bitranox/bitranox-skills --event push`
  on master.
- `python3 plugins/bitranox/hooks/repo-gate.py --ci` and `--mirrors`.

## Lessons for the next nap

- When a census script decides "handled" from a hard-coded list of batch dirs, add each new batch
  to that list in the same step that ships it, or the census reports finished work as open.
- When a Jev shadow site's AGENT label is constant across hundreds of rows, treat the agreement
  clause as measured against a possibly broken instrument before applying the drop rule.
- When code compares st_dev from os.DirEntry.stat() on Windows, use os.lstat instead: DirEntry
  leaves st_dev at 0 there, so every subdir reads as another filesystem.
- When several agents edit separate copies of one base, integrate with `git apply --3way` into one
  worktree and byte-compare each single-owner file against its owner before trusting the merge.
- When packing a git file list into a tar, use `git archive`, not `git ls-files | xargs tar cf -`:
  xargs splits the list and the concatenated archives die with SIGPIPE.
