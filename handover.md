# Handover - 2026-09-28 04:55, 7.29.5-7.29.7 shipped and green; ranks 100, 105, 110, 120, 121, 130 closed

## In flight

- Nothing running. 7.29.7 (`13cc6f29`) is green on every CI cell. 7.29.5 and 7.29.6 went red on
  the Windows cell only, on six new test fixtures (unquoted Windows paths), which 7.29.7 fixes.
- Two OPEN-WORK commits (`0c047bec`, `c26bdaab`) plus the commit carrying this file are pushed with
  this handover.

## Committed, or not

- This repo: all on origin/master.
- The tree-top memory store holds UNCOMMITTED edits: rank 80's, plus two from this session (rank 120's
  body edit, rank 121's archive). A worktree-isolated session is refused git there - rank 93 lists
  every path.

## Decided, and why - do not reopen

- decision-review-nudge (7.29.6): the USER chose "remind, don't block" for a running /goal, after
  the measurement that 13 of 16 goal-session blocks fired early. A met goal or an opened PR still
  blocks; the met block lands at the Stop after the one that ended the goal.
- repo-gate (7.29.5): an unreadable (`cd "$X"`) or nonexistent target falls back to the session's
  repo, the old behaviour; a readable target outside any repo is not judged. An unquoted Windows
  backslash path lands in the fallback - bash reads it the same way.
- repo-gate `--mirror-of` prefers the marketplace checkout it runs from only when that sits in the
  same `public/` tree as the twin.
- Rank 110: no merge of the three transcript tools - they answer different questions and must stay
  single-file (the rank-90 copy rule).
- Rank 130: closed, not retired - the review file is excluded via `.git/info/exclude` and was never
  committed.

## Decided against, and why

- Blocking on a running goal but skipping Stops with pending background work: the first pending-work
  detector was too noisy to separate the cases (on-time blocks also showed 3-4 "pending").
- Building the classifier_eval packet/harvest tool inside rank 100: its only consumer is rank 12
  step (2), so it moved into rank 12's line.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on about a day of decide rows (190 over 8 h at 01:50
UTC, fallback 1.1%). Rank 18 is deferred by the user. Ranks 91 and 93 need a session outside this
worktree.

## Lessons for the next nap

- When a test builds a shell command around a filesystem path, write the path double-quoted in
  forward-slash form: unquoted, Windows backslashes are eaten by bash and by the tokenizer alike, so
  the test silently exercises a fallback on the Windows cell.
- When a hook must judge the repository a Bash command acts on, resolve it from the event cwd plus
  the command's own `cd`/`git -C` (`shell_text.git_verb_dir`), never from the hook's working
  directory, which is where the session sits.
- When a design note justifies a trigger as "early beats never", measure how early before keeping
  it: the decision-review block on a running goal was early in 13 of 16 sessions, by up to 583 min.
- When reading Claude Code goal state, know `goal_status` is written at goal SET (`met: false`,
  `sentinel: true`) and the verdict lands AFTER the Stop hooks read the transcript.
- When a queued contribution reports a defect, check git log for a same-day fix before building
  anything: one entry had been fixed by 9d5586bc the day it was queued.
- When a backlog line says "offer X upstream", search the upstream tracker by author first: the
  issue (gesellix/bose-soundtouch#660) already existed and had been answered.
- When a CI cell fails only on Windows, reproduce on the local Windows dev box before pushing the fix (its memory fact names it): copy the
  whole `plugins/bitranox` tree (the hooks conftest imports skill modules), and read the four
  "real repo" test failures a partial copy produces as copy artifacts.
- tooling: the sha-literal-nudge caught a full sha I padded from a short one (invented identifier,
  recurrence 6); derive shas with `git rev-parse --verify -q HEAD` in its own call.
- tooling: the worktree-isolation guard refuses `for` loops over a variable, `bash -c` wait loops
  and `$(...)` inside gh commands; use a scratchpad script, or `tail --pid=<pid> -f /dev/null` to
  wait on a process.
- (carried) When a timing-ratio test fails only on a loaded host, fix the instrument before the
  bound: time the thread's CPU (`time.thread_time`), alternate the arms, and require a planted
  quadratic to still read ~16x.
- (carried) When a timing test runs on Windows, size each arm in clock TICKS: `thread_time` there
  advances in 15.625 ms steps while `time.get_clock_info` reports 1e-7 s.
- (carried) When a linear scan reads 5-6x on a 4x input, check per-char cost across sizes before
  calling it superlinear: it steps up ~1.4-1.5x once the text outgrows a cache, then stays flat.
- (carried) When redcheck reports STRONG inherited coverage on topic words, grep the cascade for the
  lesson's OWN terms before dropping the behavioural RED (false positive again this session).
- (carried) When a committed script must call a plugin-bundled script, name
  `<plugins root>/marketplaces/<marketplace>/...`, never the cache.
- (carried) When a baseline agent must run a plugin script in CI with no documented path, expect it
  to download the script from the default branch at run time - an unpinned fetch-and-execute.
- (carried) When widening a command matcher's statement anchor with shell keywords, anchor each
  keyword to a statement start and replay old against new over the corpus.
- (carried) tooling: block-masked-gate-exit refuses a backgrounded `ci_wait.py ... | tail`;
  background the jig alone.
- (carried) When staging a memory fact body for `factedit apply --body-file`, strip the leading
  newline that follows the front matter.
- (carried) When a fact says a design or change list lives in a task or backlog item, open that item
  before keeping the pointer.
- (carried) When a matcher rule must outrank a rule in its own list but yield to rules in a later
  list, encode the precedence explicitly.
- (carried) When replaying a guard or nudge change, read every changed verdict on EVERY round.
- (carried) When a regex accepts `..` as a git revision range, require a revision character on both
  sides.
- (carried) When a session reads a handover or backlog from a checkout that is not where work lands,
  compare HEAD with origin first.
- (carried) When a backlog line quotes a statusrot count, re-run `statusrot.py scan` over every
  level before triaging.
- (carried) When a fact concerns two sibling subtrees, never lift it to their common ancestor; it
  belongs in each sibling (user directive 2026-09-27).
- (carried) When Claude Code warns that instruction files exceed the 150k-char total, know it is a
  warning, not truncation.
- (carried) When a statusrot or audit hit carries an issue number or "shipped", check whether it is
  a past-tense example inside a general lesson before calling it rot.
- (carried) tooling: shell-prefix-selfref-guard blocked a plain `while` loop with no prefix
  assignment (false positive).
- (carried) When the reformat-md-tables hook re-dirties a committed file you never touched and the
  commit gate then blocks, restore and `touch -d '1 hour ago'` in ONE command, and fix it at root.
- (carried) When a backlog item or lint cites a measured multiplier, trace which variable the
  measurement varied before acting.
- (carried) When one defect sits in N template-copied repos, look for the shared library call first.
- (carried) When rebuilding derived metadata after a merge, record what the merge REPLACED.
- (carried) A GitHub run for a push can be created ~25 minutes after the push; a watcher reading
  "in_progress" with a fresh createdAt is queueing, not hung.

## The exact next action

Rank 12 is the top item (rank 18 is deferred by the user). Its step (2) opens with a tool that can
be built BEFORE the rows mature: add the `packet` and `harvest` subcommands to
`plugins/bitranox/skills/meta-self-improve/classifier_eval.py` as rank 12's line specifies (pooled
candidates from named replay logs, no arm names, a neutral override text; harvest judge JSON from
subagent transcripts, per-verdict majority, splits printed, labels keyed by row uuid), TDD in its
sibling `tests/`. Then, from about 2026-09-28 18:00 UTC, count decide rows
(`~/.claude/self-improve-audit/classifier-shadow*.jsonl`, `site == "skill_router"`, has
`decide_path`) and run step (2).

## Files that matter

- `plugins/bitranox/hooks/repo-gate.py` (`hook_root`, `_marketplace_checkout`),
  `plugins/bitranox/hooks/shell_text.py` (`git_verb_dir`, `GATED_GIT_VERBS`)
- `plugins/bitranox/hooks/decision-review-nudge.py` (`goal_started`, `_GOAL_REMINDER`)
- `plugins/bitranox/skills/process-review-uncertain-decisions/SKILL.md` and its
  `.skillwriter/checklist-20260928-a-running-goal-reminds-not-blocks.md`
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` (rank 12)

## How to verify this still stands

- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --repo bitranox/bitranox-skills --sha $(git rev-parse --verify -q HEAD)`
  exits 0 once this handover's push has run.
- `test_repo_gate.py`, `test_shell_text.py` and `test_decision_review_nudge.py` pass with CI's
  dependency set.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
