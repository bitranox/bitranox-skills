# STALE - read 2026-10-08 14:37, work continued

Two sessions are in play. Session A (worktree `jev-shadow`) shipped [16]. Session B (worktree
`notify-decide-failed`) shipped [14] as 8.5.0 and is on [17]; its 11:50 handover is in git as
commit 31b9e205, and its state is carried below unchanged in substance.

## In flight

- Session A: nothing is running. 8.6.0 (559d24ab) went red on windows-latest only: 22 prune tests
  errored in a fixture calling `os.utime(follow_symlinks=False)`, which Windows lacks. 8.6.1 fixes
  the fixture (45 passed, 6 POSIX-only skips on a real Windows machine). CI on 8.6.1 (f7326534): green
  on every cell (ci_wait exit 0). CI on the 3.14 matrix commit 079f9a93:
  green, windows-latest and macos-latest now on py3.14. Release v8.6.1 is published, its tag on
  079f9a93 (same plugin content as f7326534); 8.6.0 has no release, since its CI was red.
- Session B: [17] is part-done - identified and probed, and the user was asked which use to build
  first, with (1) a backlog/status band or pane recommended. No answer yet.
- [12] belongs to session A and waits on time: step 6 needs about a week of decide rows, earliest
  2026-10-13.

## Committed, or not

- Pushed: 8.5.0 (session B, [14]); a ci.yml change moving the windows-latest and macos-latest
  cells to Python 3.14 (user request, 2026-10-08); 8.6.1 (session A, the Windows fixture fix); 8.6.0 (session A, [16]: `tmp-prune-hook.py`, `tmp_prune.py`,
  `process_liveness.py`, knob `tmp_prune`, docs, the meta-memory-settings row and its skill-writer
  checklist). Committed with this handover: OPEN-WORK [400], [410], [420].
- Not in git, and nothing depends on them: session A's scratch scripts (arms, plan listing,
  Windows probe) and session B's probe mod and tally scripts.
- Worktree `.claude/worktrees/notify-decide-failed` holds nothing not on origin (session B may
  still be using it). The `jev-shadow` worktree's gitignored `.plan/` is still the only copy of
  three experiment records ([390]).
- This machine still runs 8.4.1 in open sessions until `/reload-plugins`; the prune hook only
  starts once a session is on 8.6.0.

## Decided, and why - do not reopen

- [16] design, every answer the user's (2026-10-08), recorded on the [16] line: SessionStart plus
  a throttled Stop check, at most hourly across the machine; scope is Claude scratch (1 day) plus
  the user's own one-off temp dirs (7 days, chosen over scratch-only); all platforms.
- Liveness is the session registry `~/.claude/sessions/<pid>.json` plus a `procStart` match
  (measured: field 22 of `/proc/<pid>/stat`, 9 of 9 live sessions matched). An unreadable registry
  entry keeps every scratch dir.
- Holders: `/proc` fd, cwd, root AND maps on Linux; `lsof` on macOS; on Windows a rename before
  delete (measured on a real Windows machine: refused with WinError 5 for an open file, 32 for a
  cwd, control renamed). One-offs are kept on a platform with no holder check.
- With `CLAUDE_CODE_TMPDIR` set, scratch is scanned under it AND the system default (Claude Code's
  long-path fallback); one-offs only in the system temp dir. Windows accepts `claude-0` (what the
  2.1.294 binary builds) and `claude` (what the docs say); which is real is unverified.
- `pluginprune.py` imports its liveness helpers from `hooks/process_liveness.py`, one copy.
- Session B's [14] and [17] decisions: see commit 31b9e205 (decide covers failed background
  commands only; a user mod cannot reach prompt composition or attribution on 2.1.290).

## Decided against, and why

- Pruning this machine by hand with `--apply`: the hook doing it after a reload is the
  end-to-end proof ([400]); a dry run here listed 16 dirs / 182k inodes, every one cross-checked
  dead (no registered session, newest file and transcript at least 42 h old).
- Changing the meta-memory-settings description for the new knob: no routing keyword moves.
- Session B: porting the Python guards to tool.call mods; a fixed rule instead of Jev for failed
  commands (both in 31b9e205).

## Still open, untouched

`OPEN-WORK.md` is the list: [12] (session A, after 2026-10-13), [17] (session B, user's pick),
[18] deferred by the user, [19] dirty worktrees and branches left to judge, [245] a locked agent
worktree, [390] copy the `jev-shadow` `.plan/` records out, [400] observe the first hook-driven
prune, [410] the foreign-mount guard's missing test, [420] two hook rows missing from
docs/architecture.md.

## Lessons for the next nap

- When an rmtree onexc/onerror handler retries the failed call, re-call only a removal function:
  rmtree also reports `os.open(path, flags, dir_fd=...)`, and re-calling that with one argument
  raises TypeError, escapes rmtree and aborts every directory after it.
- When a mutation arm is "killed", read its failure line: one killed by a TypeError instead of an
  assertion exposed a production bug, and one that SURVIVED showed a test never isolated its guard.
- When a test must show a file held only through a memory map, use `mmap(..., trackfd=False)`
  (3.13+): plain `mmap` dups the fd, so an fd scan alone passes the test.
- When a test binds a unix socket under pytest's tmp_path, chdir into the dir and bind a relative
  name: the absolute path exceeds the socket path limit and a skip branch leaks the socket.
- When a new test file must run on Windows, run it on the Windows dev box BEFORE the first push:
  8.6.0 shipped with every prune test erroring there on a call Windows does not implement.
- When a .github/workflows change is pushed while the previous commit's release run is still
  pending, that run's tag push is refused ("refusing to allow a GitHub App to create or update
  workflow ... without `workflows` permission"); the next green CI's release tags the newer sha.
  Check `gh release list` and the tag target before calling a release lost.
- When a doc names a command route ("run X for the list"), run it before shipping: the CLI printed
  counts only until a test pinned the list.
- When an outgoing handover belongs to a session that is still working, merge it into yours.
- tooling: bump pyproject.toml together with plugin.json - repo-gate's version-drift check failed
  the first gate run (recurred; carried from the 11:50 handover).
- Carried from session B, not yet confirmed napped: take a run id from the listing's JSON in the
  same step; classify a notification's kind by the summary's opening words; convert a token count
  with the recorded price before deciding on it; a blind panel over the non-chosen kinds is cheap;
  tooling: EnterWorktree on an existing path tightens every later Bash call - prefer
  `git worktree add` plus absolute paths; tooling: `claude -p` takes the prompt right after `-p`;
  and the 10:35 list in commit 31b9e205.

## The exact next action

[17] is the top-ranked open item, and it is session B's: if that session is gone, put the
user's pick to them again (build (1) the backlog/status band or pane, or another option on the
[17] line). Otherwise take [19], the next live USER item: judge the 4 dirty worktrees and 24
branches its line lists. [12] waits until 2026-10-13.

## Files that matter

- `OPEN-WORK.md` ([16] closed with the outcome, [400]/[410]/[420] new, [17] options)
- `plugins/bitranox/hooks/tmp_prune.py`, `plugins/bitranox/hooks/tmp-prune-hook.py`,
  `plugins/bitranox/hooks/process_liveness.py`, `plugins/bitranox/hooks/tests/test_tmp_prune.py`
- `plugins/bitranox/skills/meta-memory-settings/settings.py` (`ENUM_CHOICES["tmp_prune"]`)

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha f73265348c6842bf1db3e635ba963313704bbf07`
  exits 0.
- `python3 plugins/bitranox/hooks/tmp_prune.py --json` prints a dry-run envelope with
  `examined_dirs` > 0 and a `removed` list; nothing is deleted.
- After `/reload-plugins` and one finished turn: a new last line in
  `~/.claude/self-improve-audit/tmp-prune.log.jsonl` ([400]).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
