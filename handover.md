# STALE - read 2026-10-08, work continued

Session A (worktree `jev-shadow`). Session B (worktree `notify-decide-failed`, branch
`mods-memory-backlog-tools`) is building [17] as option (3), memory and backlog as model-callable
tools; it holds the 8.7.x bump on that branch and re-bumps above master at push time.

## In flight

- Nothing part-done. CI for 4bbad193 (the [19] closure, OPEN-WORK.md only) was still running at
  writing time; the three earlier backlog pushes today (ed7a1ae8, a2c8f976, b766189d) were green
  on every cell.

## Committed, or not

- Pushed to master: ed7a1ae8 ([19] worktrees and branches; [430]/[440] carried in), a2c8f976
  ([400] closed), b766189d ([150] closed), 4bbad193 ([19] closed).
- Memory store (the softdev tree-top `.claude-memory/`, its own git): commit 5439f45 holds this
  session's 6 new and 2 amended facts plus store OPEN-WORK [70]/[80]. Peer sessions have UNCOMMITTED
  edits in that store (about 20 facts); they are not ours, leave them to their sessions or the
  dream.
- Not in any git: `apps/utils/bmk/OPEN-WORK.md` gained [20] (that file is untracked by the user's
  open decision, bmk [5]). The main checkout's gitignored `.plan/` holds `TODO-JEV.md` and
  `TODO-JEV.staged.md` ([150]) and `worktree-archive-2026-10-08/` (diffs of the 4 removed dirty
  worktrees, `deleted-branches.txt` now 129 rows).
- Contribution queue gained 3 entries this session: a landed-on-master jig (target compuse-toolbox
  or git-worktrees), a compuse-git row for `git rm --cached` on an AM file, and a
  shell-prefix-selfref-guard false positive (a standalone `c=$(...);` followed by `"$c"` was
  refused as a prefix assignment).

## Decided, and why - do not reopen

- [19]: every object was shown to the user and removed on their yes. Evidence per object is on the
  [19] line; `git branch <name> <sha>` from `deleted-branches.txt` restores any branch.
- `dream-open-work` worktree's 5 unlanded backlog lines: tool work went to this repo ([430], [440]),
  store content to the store's backlog ([70], [80]), one was already store [50].
- [150]: the index held an older TODO-JEV.md than the file, so both versions were kept in `.plan/`.
- Git in another checkout from this isolated session goes through `ExitWorktree` with `keep` on the
  user's request, not a script with `cwd=`. This session used the script route before finding that
  rule (misfiled at the soundtouch-watchdog level); the worktree-isolation fact now says so.

## Decided against, and why

- [245] now: its two worktrees are locked by THIS session's process (pid 260379, its own earlier
  subagents), so removing them needs ExitWorktree; the lock lifts when this session ends, after
  which `git worktree remove --force` on each (no own commits; a26b133c's work is on origin) is
  one step from any session.
- Capturing session B's carried lessons in this nap: B is live and can nap them itself.

## Still open, untouched

`OPEN-WORK.md` is the list: [12] (after 2026-10-13), [17] (session B), [18] deferred by the user,
[96] waits on Jev data, [170]-[186] review leftovers, [200] contribution queue, [245] (see above),
[290]-[360], [390], [410], [420], [430], [440].

## Lessons for the next nap

- When a fact seems missing, remember a fact filed at a SIBLING level never loads here: the
  ExitWorktree rule sat at soundtouch-watchdog while this repo needed it; the tree dream should
  re-home it and merge it with reference-in-a-worktree-isolated-session-scratchpad-scripts-edit-then-cp.
- Carried from session B (still not confirmed napped, B may take them): take a run id from the
  listing's JSON in the same step; convert a token count with the recorded price before deciding
  on it; a blind panel over the non-chosen kinds is cheap; tooling: EnterWorktree on an existing
  path tightens every later Bash call - prefer `git worktree add` plus absolute paths; tooling:
  `claude -p` takes the prompt right after `-p`; and the 10:35 list in commit 31b9e205.

## The exact next action

Top live items are not workable now: [12] waits on a date, [17] is session B's, [18] is deferred,
[96] waits on data. So take [170], the top found item that can be worked: read its line in
`OPEN-WORK.md`, re-verify each of its 12 follow-ups against current master (several may be fixed
since 2026-09-25), and ask the user before fixing the ones that still hold.

## Files that matter

- `OPEN-WORK.md` ([19], [150], [400] closed today; [430], [440] new)
- the memory store's `OPEN-WORK.md` (store backlog, [70] and [80] new)
- the bmk repo's `OPEN-WORK.md` (sibling `apps/utils/bmk`, [20] new)

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha 4bbad1934b95c9febe157e537178b09eeca76dac`
  exits 0.
- `git worktree list` shows only `jev-shadow`, session B's worktrees and the two locked agent
  worktrees of [245]; `git branch` lists no `worktree-agent-*` other than those two.
- In the memory store, `git show --stat 5439f45` lists the 6 new facts and 2 amended ones.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
