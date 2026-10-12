# Handover - 2026-10-12 19:40, [200] six decisions taken, three shipped (8.16.0, 8.17.0), four builds open as [9]

## In flight

- Nothing part-done. 8.16.0 (6e136180, missing-mechanism-nudge refuses the first AskUserQuestion
  of each question once) and 8.17.0 (13eeafa0, new hook user-decision-log writing
  USER-DECISIONS.jsonl) are on origin with CI green; both queue entries are closed. Other sessions
  pushed 8.17.1 (969851ac) and announced 8.17.2 (a test-only macOS flake fix), so the next bump is
  8.18.0 or higher - re-read plugin.json from origin/master before bumping.

## Committed, or not

- This handover and OPEN-WORK.md ([9], [575], [580] added) ship in one commit from the worktree
  `.claude/worktrees/200-premise-refuse-first-ask` (branch worktree-200-premise-refuse-first-ask).
  Everything else of this session is on origin.
- EXECUTION-USER-REVIEW.md (gitignored, MAIN checkout only) holds all eight of today's user
  decisions verbatim, newest first; controller-added must-not lines are labelled "(my reading)".
- The MAIN checkout sits behind origin with an uncommitted `# STALE` first line in handover.md.
  From the main checkout run `git checkout -- handover.md && git merge --ff-only origin/master`.
  A worktree-isolated session cannot run it, a typed `!` command included.
- The worktree above has landed completely (its commits are on origin as-is): remove it when the
  session ends.

## Decided, and why - do not reopen

- Question refusal keys on "the previous ask of this session was refused" (one per-session flag),
  not a hash of the question text: a hash refuses the revised re-send the refusal asks for.
- user-decision-log writes to the MAIN checkout's root (a worktree's log would die with the
  worktree) and excludes the file even when track_private is set (the user ruled out committable).
- The six [200] answers (detector jig -> extend adjudicate; nudge noise -> accept; EnterWorktree ->
  refuse first entry; three rules -> block trailing & only; relay fact -> update hook+body, done;
  rule hash -> casefold) are in EXECUTION-USER-REVIEW.md; build them from there, not from this list.

## Decided against, and why

- additionalContext on AskUserQuestion or EnterWorktree as the warning channel: measured, it reaches
  the model only with the tool's result, too late to change the action.
- Suppressing the self-improve nudge on a keyword match: plain overlap against the store matches
  almost everything and would silence real lessons.

## Still open, untouched

OPEN-WORK.md is the list. [9] the four builds from today's decisions (new, top); [12] can start
2026-10-13; [18] user-deferred; [96] waits on shadow data; [200] remaining untriaged queues
(projects, bmk, soundtouch-watchdog, lib_layered_config); [560] leftover worktrees; [570] fact
correction; [575] guard proposal for the relay rule; [580] pyproject hook count.

## Lessons for the next nap

- When probing a hook on AskUserQuestion or another interactive-only tool, run an interactive
  claude in tmux with a throwaway --settings hook: headless -p does not offer the tool (fact already
  written: reference-probe-an-askuserquestion-hook-interactively-...).
- When a peer session pushes between your rebase and your push, rebase again and keep your number
  if it is still the highest; a CHANGELOG/version conflict after a peer push took three throwaway
  resolver scripts today - a candidate for a toolbox jig (propose-first, not raised yet).
- When you write must-not lines under a quoted user decision, label them "(my reading)" in the same
  line (recurrence 4 of the relay fact, already captured).
- tooling: a worktree-isolated session refuses many plain read commands (a computed sed argument, a
  loop over variables, python with a variable script path); split them or use literal paths.

## The exact next action

[9] item (4): in `plugins/bitranox/skills/compuse-toolbox/scripts/pushcheck.py`, RED test that the
patterns spelled with a sharp s and with SS share one `Rule.digest`, then hash
`fold_case(self.pattern)`; then the SKILL.md pushcheck row (via bitranox:meta-skill-writer). Work
in a fresh worktree off origin/master.

## Files that matter

- `plugins/bitranox/hooks/missing-mechanism-nudge.py` (`_answer_question`, `QUESTION_REFUSAL`)
- `plugins/bitranox/hooks/user-decision-log.py` and `plugins/bitranox/hooks/tests/test_user_decision_log.py`
- `plugins/bitranox/hooks/arbitrary-sleep-nudge.py` ([9] item 2)
- `plugins/bitranox/skills/compuse-toolbox/scripts/adjudicate.py`, `scripts/pushcheck.py`, `SKILL.md`
- `OPEN-WORK.md` ([9], [575], [580])

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha $(git rev-parse --verify origin/master)`
  exits 0.
- `python3 <plugin>/skills/meta-self-improve/contrib_queue.py queues`: the provmm-umbrella queue is
  empty; lsdsk shows 2 open (planted-pair jig, three-guards), soundtouch-zonemaster 1 (pushcheck).
- `uv run --no-project --with pytest --with PyYAML python -m pytest
  plugins/bitranox/hooks/tests/test_missing_mechanism_nudge.py
  plugins/bitranox/hooks/tests/test_user_decision_log.py -q` passes.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
