# STALE - read 2026-09-28, work continued

## In flight

- **Rank 80 (statusrot)** - adjudication DONE, edits NOT applied. The full state, the three
  rewordings, the one question for the user and the one unread lookup are in its `OPEN-WORK.md`
  line; nothing else about it lives anywhere else.
- CI for `1a9dd89f` (the OPEN-WORK commit for ranks 18/80) was still running when this was written;
  `23f7caaa` (7.29.0) and `18f1ba9a` are green.

## Committed, or not

- Everything in this repo is on origin/master (`1a9dd89f`, plus the commit carrying this file).
- **Main checkout is 3+ commits behind** and holds MY uncommitted edit: `handover.md` line 1 changed to
  a STALE marker. That edit blocks the fast-forward (the incoming commits change the same file).
  From a session in the main checkout: `git checkout -- handover.md && git merge --ff-only origin/master`.
  The staged `PLAN-JEV-SKILL.md` / `TODO-JEV.md` there are rank 150's, not this session's; the ff keeps them.
- `.plan/new_placement_rules_plan.md` exists ONLY in the main checkout (gitignored). It is rank 18's plan.
- Worktree `.claude/worktrees/openwork-upstream` (branch `worktree-openwork-upstream`) is fully
  pushed and can be removed with the git-worktrees skill's `wtclean.py`.

## Decided, and why - do not reopen

- 7.29.0: the session-start backlog block reads `OPEN-WORK.md` from upstream (or `origin/HEAD` for a
  branch with none) when the checkout only lags behind it, and keeps the local copy with a
  "may be stale" note when the checkout changed the file itself - local edits exist nowhere else.
  Last fetch only, never the network (user chose this over a habit rule).
- Rank 18 (user, all three): shared sibling facts get ONE body with a pointer in each sibling level,
  not copies (copies would be merged back up by dedup); the routing key is an explicit `TOPICS:` line
  per level written and maintained by the DREAM, never a person; a fact appears at most once on any
  root-to-leaf path, enforced at every create/move, not only checked.

## Decided against, and why

- Leaving the openwork-upstream worktree mid-session: ExitWorktree is user-initiated only.
- Rank 150's `git rm --cached TODO-JEV.md`: not asked; only the fast-forward half was done.

## Still open, untouched

`OPEN-WORK.md` is the list (29 open). Rank 12 waits on about a day of decide-mode rows.

## Lessons for the next nap

- When a session reads a handover or backlog from a checkout that is not where work lands (worktree
  workflows), compare HEAD with origin first: the main checkout sat 219 commits behind and listed
  seven closed items as open (7.29.0 now prints the lag for OPEN-WORK.md, not for handover.md).
- When a backlog line quotes a statusrot count, re-run `statusrot.py scan` over every level before
  triaging: the baseline records cleared entries, and 57 flagged became 20 actually pending.
- When a fact concerns two sibling subtrees, never lift it to their common ancestor; it belongs in
  each sibling, and never twice on one root-to-leaf path (user directive 2026-09-27; the engine and
  skills still say "lift" until rank 18 ships).
- When Claude Code warns that instruction files exceed the 150k-char total, know it is a warning,
  not truncation (CLI 2.1.283 source; the whole 138k tree-top file reached context) - the cost is
  ~68k tokens per session and per subagent.
- When a statusrot or audit hit carries an issue number or "shipped", check whether it is a
  past-tense example inside a general lesson (15 of 20 were) before calling it rot.
- tooling: shell-prefix-selfref-guard blocked a plain `while ...; do c=$(...); ...; p=$(awk ...); done`
  loop that had no prefix assignment at all (false positive).
- (carried, not yet napped) When the reformat-md-tables hook re-dirties a committed file you never
  touched and the commit gate then blocks, a plain `git checkout --` is undone by the next Bash call;
  restore and `touch -d '1 hour ago'` in ONE command, and fix the file at root.
- (carried) When a backlog item or lint cites a measured multiplier, trace which variable the
  measurement varied before acting: "unframed" meant no-frontmatter in the probe and missing-labels
  in the lint.
- (carried) When one defect sits in N template-copied repos, look for the shared library call first:
  a library-default fix reaches every consumer through floating floors with zero repo edits.
- (carried) When rebuilding derived metadata after a merge, record what the merge REPLACED rather
  than re-walking the merged leaves.
- (carried) A GitHub run for a push can be created ~25 minutes after the push; a watcher reading
  "in_progress" with a fresh createdAt is queueing, not hung.
- (carried) tooling: `repo-gate.py --mirror-of` compares against the MAIN checkout's twin, not the
  worktree's; diff the two files directly to verify a mirror sync from a worktree.

## The exact next action

Rank 12 is the top item but blocked on data until about a day of decide rows exists; rank 18 is
the user's, deferred by them on 2026-09-27 ("save that plan for later"). So rank 80 goes first:
read the owning project's `TODO.md` entry for "#73" (the MANA fact's level), then apply the three
rewordings from rank 80's line with `memory_engine.py add` at each fact's OWNING level, ask the user
about the missing lsdsk article, and `statusrot.py clear --slug <s>` only for the adjudicated slugs.

## Files that matter

- `plugins/bitranox/hooks/session-start.py` (`_backlog_text`, `_upstream_ref`, `_git`) and
  `plugins/bitranox/hooks/tests/test_session_start.py` (the behind-clone tests at the end)
- `plugins/bitranox/skills/meta-dream-tree/statusrot.py`
- `.plan/new_placement_rules_plan.md` (main checkout only)

## How to verify this still stands

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha 1a9dd89f91868038569ff92c3b6c760bc8988aa6`
  exits 0.
- In a lagging checkout, the SessionStart backlog block begins "This checkout is N commit(s) behind".

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
