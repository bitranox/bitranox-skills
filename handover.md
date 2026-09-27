# Handover - 2026-09-28 01:25, ranks 80 and 82 closed; 7.29.1 pushed, its CI still running

## In flight

- CI for `1cc1159c` (7.29.1, the rank-82 git_state nudge) was queued/in progress when this was
  written. `339ebd0d` and `d0c40e19` (rank 80) are green.

## Committed, or not

- This repo: everything is on origin/master at `1cc1159c` plus the commit carrying this file.
- The tree-top memory STORE (`.claude-memory`, its own git repo) holds uncommitted
  edits from rank 80: four reworded fact bodies, one fact archived to `.archive/`, and
  `statusrot-baseline.json` (17 slugs cleared). A worktree-isolated session could not run git
  there; the next dream commits the store.
- The main checkout still lags and carries an uncommitted STALE edit to its `handover.md` - the
  recovery command is in rank 150's line.

## Decided, and why - do not reopen

- Rank 80: the lsdsk article fact was RETIRED (archived), not reworded - the user said the article
  is finished. The retire path is `reconcile_memory_index.py --archive SLUG LEVEL`; the engine has
  no remove verb.
- Rank 82: the repo sweep is a matcher object in `_RULES` (so it outranks `claim_check`) that
  DEFERS to the pushcheck and ci_wait regexes, rather than living in the shell-only list. Moving it
  to the shell-only list was tried and lost three real sweeps to `claim_check` by list order.
- Rank 82: the sweep run on remote hosts inside an ssh command string stays a known wrong shape (3
  firings), documented in the class docstring; telling it apart needs quote parsing.

## Decided against, and why

- Fixing the `if git -C "$r" push` pushcheck gap inside rank 82: separate rule, own replay; it is
  rank 88.

## Still open, untouched

`OPEN-WORK.md` is the list (28 open). Rank 12 waits on about a day of decide-mode rows (107 rows
over 5 hours at 2026-09-27 22:47 UTC; fallback 2 of 107).

## Lessons for the next nap

- When staging a memory fact body for `factedit apply --body-file`, strip the leading newline that
  follows the front matter, or the engine writes a double blank line under it.
- When a fact says a design or change list lives in a task or backlog item, open that item before
  keeping the pointer: task #73 was a one-line entry and the design lived only in the fact body.
- When a matcher rule must outrank a rule in its own list but yield to rules in a later list,
  encode the precedence explicitly (defer to the later rules' patterns) instead of moving it
  between lists - each move traded one wrong owner for another in the replay.
- When replaying a guard or nudge change, read every changed verdict on EVERY round, not only the
  first: three rounds each surfaced a different defect (stolen push loops, lost indirect targets,
  a list-order loss, an ellipsis read as a revision range).
- When a regex accepts `..` as a git revision range, require a revision character on both sides:
  a prose ellipsis matched it.
- tooling: the worktree-isolation guard refuses any Bash command whose ARGUMENT text merely
  contains "git" (a slug ending in `gitignore`, a pytest `-k` filter, a sed on a computed path);
  put such work in a scratchpad script.
- tooling: the load-sensitive `test_adversarial_inputs_stay_linear` perf test (rank 187) blocked a
  docs-only commit on a second case; a retry passed.
- (carried) When a session reads a handover or backlog from a checkout that is not where work lands
  (worktree workflows), compare HEAD with origin first: the main checkout sat 219 commits behind
  and listed seven closed items as open.
- (carried) When a backlog line quotes a statusrot count, re-run `statusrot.py scan` over every
  level before triaging: the baseline records cleared entries, and 57 flagged became 20 pending.
- (carried) When a fact concerns two sibling subtrees, never lift it to their common ancestor; it
  belongs in each sibling, and never twice on one root-to-leaf path (user directive 2026-09-27).
- (carried) When Claude Code warns that instruction files exceed the 150k-char total, know it is a
  warning, not truncation - the cost is ~68k tokens per session and per subagent.
- (carried) When a statusrot or audit hit carries an issue number or "shipped", check whether it is
  a past-tense example inside a general lesson (15 of 20 were) before calling it rot.
- (carried) tooling: shell-prefix-selfref-guard blocked a plain `while ...; do c=$(...); done` loop
  that had no prefix assignment at all (false positive).
- (carried) When the reformat-md-tables hook re-dirties a committed file you never touched and the
  commit gate then blocks, restore and `touch -d '1 hour ago'` in ONE command, and fix the file at
  root.
- (carried) When a backlog item or lint cites a measured multiplier, trace which variable the
  measurement varied before acting.
- (carried) When one defect sits in N template-copied repos, look for the shared library call first.
- (carried) When rebuilding derived metadata after a merge, record what the merge REPLACED rather
  than re-walking the merged leaves.
- (carried) A GitHub run for a push can be created ~25 minutes after the push; a watcher reading
  "in_progress" with a fresh createdAt is queueing, not hung.
- (carried) tooling: `repo-gate.py --mirror-of` compares against the MAIN checkout's twin, not the
  worktree's; diff the two files directly to verify a mirror sync from a worktree.

## The exact next action

Rank 12 is the top item (rank 18 is deferred by the user). Its step (2) needs about a day of
decide rows, which exists from roughly 2026-09-28 18:00 UTC. So first count them - run from a
scratchpad script, reading `~/.claude/self-improve-audit/classifier-shadow*.jsonl` for rows with
`site == "skill_router"` and a `decide_path` field. If about a day has accumulated, do rank 12
step (2): read the fallback rate, then test gate 0.3 vs 0.5 on fresh rows with a new blind panel.
If not, take rank 85 (the four guard findings) and come back to rank 12 later.

## Files that matter

- `plugins/bitranox/hooks/toolbox-nudge.py` (`_RepoSweep`, `_PUSHCHECK_RX`, `_CI_WAIT_RX`) and
  `plugins/bitranox/hooks/tests/test_toolbox_nudge.py` (the git_state tests near the top)
- `plugins/bitranox/hooks/classifier.py`, `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`
  (rank 12)
- `.plan/jev-choicev1-2026-09-27/` in the MAIN checkout (rank 12's PREREG and panel record)

## How to verify this still stands

- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --sha 1cc1159ccca7f7d93f7d50ed84fa145b8dad44fc`
  exits 0.
- The toolbox-nudge suite passes: 152 tests in `plugins/bitranox/hooks/tests/test_toolbox_nudge.py`.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
