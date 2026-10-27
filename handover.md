# Handover 2026-10-27 08:30: nothing in flight; the small-points plan, the devops-bmk twin and [840] are all shipped

## In flight

Nothing. No background subagent or shell of this session is running, and no worktree of it is
left (`git worktree list` shows only peers' `ipscout-contribs` and a detached template-sweep checkout).

## Committed, or not

- Everything this session wrote is on origin/master: 10.3.0 (small points plus [760]), 10.3.1
  (devops-bmk twin of bmk b787f4e), 10.3.2 and 10.3.3 (the [840] `--mirrors` fix and its Windows
  test fix). ipscout pushed 10.3.4 on top.
- Local toolbox `~/.claude/skills/toolbox` (no remote): all committed, tree clean (quotecheck
  repeated `--quote` fix; libstate, conflictres and the backlogcheck pushed-state extension,
  committed as-is on the user's choice).
- Untracked `o` in the repo root (19 bytes, dated 2026-10-24) is NOT this session's: left alone.

## Decided, and why

- `_in_main_checkout()` in `plugins/bitranox/hooks/repo-gate.py` maps a twin inside a linked
  worktree onto its main checkout; a separate clone and a worktree of an UNLISTED repo are still
  reported on purpose, so a real duplicate never hides.
- The relative-gitdir test unlinks the worktree's `.git` before rewriting it (comment in
  `plugins/bitranox/hooks/tests/test_repo_gate.py`), instead of skipping Windows: that branch keeps
  a Windows run.

## Still open, untouched

- OPEN-WORK.md is the backlog; top open items are [23] (USER, memory-line fold into skills), [28]
  (USER, second wave of Jev sites), [30] (USER, purge handover mode - waits on compact mode).

## Exact next action

[23] is the top-ranked open item. Its line's `next:` text still names batch 4, while
`git log -- OPEN-WORK.md` shows a later "[23] batch 6 pass 2" commit, so first run
`uv run ~/.claude/skills/toolbox/tools/backlogcheck.py --file OPEN-WORK.md` and read line [23] to
its end, rewrite its `next:` to the real state, then classify the next batch read-only and put it
to the user as that line says (each batch needs its own approval).

## Lessons for the next nap

- When a subagent prompt is built from a template, check it holds no unfilled placeholder before dispatching (queued as a contribution to process-agents-subagent-driven-development).
- When an older installed repo-gate refuses a mirrored-twin commit as DRIFT with the "+" side holding the OLD text, it is reading the index: git add the files first (10.3.0 reads the commit's selection instead).
- When a CLI option may be passed more than once, check its parser uses action="append": argparse's default store silently keeps only the LAST value, so a check fed several values verifies one (quotecheck --quote did this; fixed in toolbox, RED test added).
- When a quote-back probe reads a bold lead sentence against its body, check the two agree: a lead that names one condition while the body needs two is the sentence a skimming reader acts on.
- When a test rewrites a file git created inside a worktree or repo (`.git` file, index), expect Windows to refuse a truncate-write on it because git marks it hidden: unlink it first, or open r+ and truncate.
- When a commit command reaches the repo through a variable (`cd $T`), the repo-gate cannot read the target and judges the session repo instead: name the repo path literally in the command.
- When a Windows-only CI cell fails, reproduce it on the Windows dev VM with a `git archive` of HEAD (the hooks conftest needs the full tree) plus an OLD-test control arm, before pushing a fix: the control proves the VM reproduces CI's failure.
- When a peer session will push the same repo, tell it exactly which functions and test anchors you changed and when you push; ipscout rebased onto 10.3.3 cleanly that way.

## How to verify

- `git -C /media/srv-main-softdev/projects/public/KI/bitranox-skills log --oneline -5 origin/master`
- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (all pairs in sync, exit 0)
- `python3 ~/.claude/plugins/cache/bitranox-skills/bitranox/10.3.4/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
