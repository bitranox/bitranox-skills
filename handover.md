# Handover - 2026-10-15 12:45, [9] closed (8.20.0, 8.21.0), ci_wait --ref shipped (8.22.0); next is [12] step (6)

## In flight

- Nothing part-done. 8.20.0 (27c81af8), 8.21.0 (3027f3f8) and 8.22.0 (96b4c427) are on
  origin/master, each CI-green (`ci` and `workflow` runs).

## Committed, or not

- This handover is committed from the worktree `.claude/worktrees/bg-waiter-refusal` (branch
  `worktree-bg-waiter-refusal`), which holds nothing else uncommitted. Remove it with git-worktrees'
  `wtclean.py bg-waiter-refusal` once this is on origin.
- The MAIN checkout's local `master` is 3+ commits behind origin, and its `handover.md` carries an
  uncommitted STALE first line written by this session. Discard that line (`git checkout --
  handover.md` there) and fast-forward `master` before working in the main checkout.
- Open sessions keep old plugin text until `/plugin marketplace update` plus `/reload-plugins`.

## Decided, and why - do not reopen

- [9](2) the refusal covers a GATE detached with `&`, not only a waiter: the user's 2026-10-12
  answer recorded that the recurrence was a subagent's `make test &`. Replay over 143,483 commands:
  49 refusals, 47 real detached jobs, 2 a fixture naming a fake process `pytest-control` (accepted).
  The 8 inline `( gate; echo RC=$? >> log ) &` forms are refused too; the refusal names the route
  for a job that must outlive the session (a script appending its own RC, launched with setsid nohup).
- [9](3) refuses the first EnterWorktree once per SESSION (flag stays set), unlike the question
  refusal, which refuses each new question. Probed first on CLI 2.1.300: the deny stops it before
  the switch.
- `ci_wait --ref` was built on the user's word ("build the ci_wait --ref option"); `--sha` stays for
  a sha from outside. Making sha-literal-nudge BLOCK stays rejected (priced at 39% precision earlier).

## Still open, untouched

- Everything else: `OPEN-WORK.md`, top open item [12].
- A memory consolidation is due (`bitranox:meta-dream-tree`); the user has not been asked.

## Lessons for the next nap

- When classifying replay firings, read each command WHOLE before judging it: a 700-character view
  hid the `& wait` that made firing #23 a correctly collected pair, and it was misread as a miss.
- When a mutation arm survives on text that appears twice in the subject, pin each clause in the
  test rather than one substring: removing one copy cannot fail a check the other copy satisfies.
- When a regex alternation is `(?:^|[;&]\s*)word`, the `^` branch allows no leading space: move
  `\s*` outside the group, or ` word` at the start of the remainder never matches.
- tooling: a worktree-isolated session refuses a Bash command whose argument merely contains the
  word git, a heredoc whose body names git, and `$(git ...)` as an option value (recorded in the
  worktree-isolation fact; the store already has it).

## The exact next action

[12] step (6), the top open item in `OPEN-WORK.md`: a fresh pre-registered blind panel on
recall_rerank DECIDE rows since 8.3.0 (bar: Jev picks >= 60% relevant), and the decide rows'
fallback-deadline share. Start by counting eligible rows with
`python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report` (read `--help`
first), write the PREREG before any label, and model it on `.plan/jev-recall-2026-10-06/`
(PREREG.md, RESULTS.md) in the MAIN checkout (gitignored `.plan/`). Build packets with
`classifier_eval.py packet` and labels with `harvest`.

## Files that matter

- `OPEN-WORK.md` ([12] line, its "step (5) DONE" note names the bar and the record)
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`, `judge_panel.py`
- `plugins/bitranox/hooks/arbitrary-sleep-nudge.py`, `plugins/bitranox/hooks/enter-worktree-first-refusal.py`
- `plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py`

## How to verify

- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --ref origin/master` exits 0
  on the commit carrying this handover.
- `grep -c '^- \[x\] (2026-10-12) \[9\]' OPEN-WORK.md` prints 1.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
