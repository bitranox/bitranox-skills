# STALE - read 2026-10-26, work continued and shipped as 10.2.2. Was: Checkpoint 2026-10-26 (compact mode): building the `tail -N` multi-file nudge, OPEN-WORK [40]

## In flight

Building `plugins/bitranox/hooks/tail-obsolete-count-nudge.py`, a warn-only PreToolUse(Bash|PowerShell)
nudge: `tail` with an obsolete count (`-1`, `-5f`, `+2`) and two or more file operands exits 1 on
uutils tail ("unexpected argument"). All of it is UNCOMMITTED in this worktree
(`.claude/worktrees/tail-guard`, branch `tail-guard`, based on origin/master 6bd10408).

Done:
- the hook (token walk over `iter_segments` + `argv_for_match` + `program_word_at`; skips option
  values, redirects, everything after `--` counts as a file; heredoc bodies stripped);
- `plugins/bitranox/hooks/tests/test_tail_obsolete_count_nudge.py`, 23 tests, green; registered
  in `hooks/tests/conftest.py` `_HOOK_MODULES`;
- mutation check: all 7 guard clauses go RED when removed (two needed added tests: the `--` case
  and a file name with `-<digits>` inside);
- corpus replay (`guard_replay.py`, whole `~/.claude/projects`): 42 firings in 192,418 commands
  (0.022%); every firing is the true shape, 21 recorded the real "unexpected argument" error, the
  other 21 ran on GNU tail or mid-chain with the exit masked. The tool's "precision" column counts
  gate blocks and is meaningless for a nudge;
- registered in `plugins/bitranox/hooks/hooks.json` right after `sed-line1-range-nudge.py`,
  matcher `Bash|PowerShell`.

Left, in order:
1. `docs/architecture.md`: a hook-table row (`PreToolUse` Bash, `tail-obsolete-count-nudge.py`,
   "Nudge `tail -N` / `+N` with two or more files: uutils tail exits 1; use `tail -n N`"), then
   `reformat_tables.py --check --strict docs/architecture.md`.
2. Version: re-read plugin.json on origin/master after a fetch and take origin + 1; bump
   plugin.json AND pyproject.toml, add a `## [x.y.z]` CHANGELOG entry (Added).
3. Run the full hooks suite with CI's set and `python3 plugins/bitranox/hooks/repo-gate.py --ci`.
4. Before pushing, SendMessage `lib_log_rich` (holds 10.1.4 locally until lib_log_rich 7.3.0 is on
   PyPI) and `bmk` (building a \u-escape PostToolUse hook in its own worktree) with the version you
   take. Stage named paths only, commit with `-F`, push `HEAD:master`, watch CI with
   `ci_wait.py --sha <full sha>`.
5. After CI is green, delete OPEN-WORK [40] in a follow-up commit (or in the release commit, with
   the reason in its message), then remove this worktree and its branch.

## Decided, and why

- Nudge, not block: the obsolete form is correct on GNU tail; a block on a working command teaches
  the reader to ignore the channel. Same reasoning as the sed-line1 sibling.
- Token walk, not a whole-command regex: a nested quantifier in a hook can backtrack exponentially
  and hang the session.
- `head -N` with several files is left alone: uutils head accepts it (measured).

## Decided against

- Probing `tail --version` inside the hook to stay quiet on GNU hosts: a subprocess per Bash call
  for a 0.022% event, and `tail -n N` is the POSIX spelling anyway.

## Still open, untouched

See `OPEN-WORK.md` (top: [23] fold top-level memory lines into skills, batch 7; a tree dream is
due, [730] is its input).

## Lessons for the next nap

- tooling: the first live compact-mode checkpoint request fired at 423,897 tokens with a 500k limit (predicted save point about 420,300), so the save-point arithmetic holds on CLI 2.1.310.
- When pricing a warn-only nudge with guard_replay, ignore its precision column (it counts gate blocks); classify every firing by its recorded tool_result error instead.
- When a commit in a marketplace worktree is refused as DRIFT on a skill the commit does not touch, the worktree is behind an origin commit that mirrored that twin: `git merge --ff-only origin/master` (no stash needed when your files do not overlap), then commit.
- When a peer session asks you to edit a file in ITS checkout, prepare the change in your own worktree and send it a patch (`git diff --relative=<prefix>` so its paths match the peer repo, proven with `git -C <peer> apply --check`); the peer applies it itself.

## How to verify

- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q`
- `python3 plugins/bitranox/hooks/repo-gate.py --ci`

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
