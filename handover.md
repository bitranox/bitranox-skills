# Handover - 2026-10-13 17:00, [9](1) shipped in 8.19.0, premise hook kept (8.19.3); next is [9](2)

## In flight

- Nothing part-done by this session. Everything it changed is on origin/master and CI-green:
  8.19.0 (1a14e172, adjudicate path mode), ac16326e (backlog), 8.19.3 (bdc9c485, premise-hook
  docstring + [21] closed). 8.19.1 and 8.19.2 are other sessions' (btx-lib-mail-35, projects-33).

## Committed, or not

- The main checkout is NOT clean, and none of it is this session's: btx-lib-mail-35 has an
  uncommitted `plugins/bitranox/skills/coding-python-send-mail/SKILL.md` edit plus an untracked
  `.skillwriter/checklist-20261013-ehlo-deadline-mirror.md`. repo-gate judges the whole working
  tree, so any commit from the main checkout is refused while that sits there: commit and push from
  a clean worktree off origin/master (this handover was committed that way). Do not touch their files.
- Worktree `.claude/worktrees/jev-judge-floor` belongs to projects-33; leave it.

## Decided, and why - do not reopen

- Premise hook (`plugins/bitranox/hooks/missing-mechanism-nudge.py`) keeps refusing EVERY first
  AskUserQuestion. User, verbatim: "keep it" (EXECUTION-USER-REVIEW.md, 2026-10-13 15:2x). Basis:
  of 61 refused first asks, 20 re-sends corrected a wrong premise, 17 dropped an unmeasured claim,
  22 only gained labels, 2 unchanged; no Jev question separated them ([21], closed).
- adjudicate's path-mode template goes after a bare `--`, not a repeatable `--subject-arg`:
  argparse reads an option value starting with `--` as the next option.

## Decided against, and why

- A Jev gate for the premise hook: a premise question went flat (0.62-0.94 on every pilot item),
  a stakes gate let 9 of 20 real corrections through.

## Still open, untouched

- lsdsk: its OPEN-WORK [20] line still restates the old review exit rule; lsdsk-2f confirmed it is
  on that session's ledger, to fix when it leaves its fragmentation worktree. Not this repo's work.
- Open sessions run old plugin text until `/plugin marketplace update` + `/reload-plugins`.
- A memory consolidation is due (`bitranox:meta-dream-tree`); the user has not been asked.
- Everything else: `OPEN-WORK.md`, top item [9].

## Lessons for the next nap

- When a background job's cwd is a worktree you later remove, its exit code can read 1 from a
  failed getcwd after a successful run; read its output (ci_wait printed all-success, then failed).
- tooling: a worktree-isolated session cannot write the gitignored EXECUTION-USER-REVIEW.md in the
  main checkout (Edit refused); the entry has to wait for ExitWorktree (lsdsk 2026-10-13 did that),
  while USER-DECISIONS.jsonl already holds the answer verbatim.
- Carried from the 2026-10-13 handovers (not yet napped):
- When auto mode refuses `wtclean.py --discard-uncommitted` after a general "yes" to a cleanup
  plan, ask the user for an explicit "do it" naming the discard: it passed only after that.
- When a batch of worktree-dispatched items ships, remove its worktrees with `wtclean.py` in the
  same session: the cleanup line [560] counted 11 while 16 had piled up by the time it was worked.
- When a review loop will not end, look for a backlog or handover line that RESTATES the skill's
  exit rule: sessions resuming with "what next" follow the frozen paraphrase, not the skill.
- When a gate says "a realistic caller reaches it", ask whether the finding is wrong BEHAVIOUR:
  test gaps and doc wording are always "reachable", so a reach-only gate never closes.
- When testing a skill text against a model, run `claude -p --tools "" --disable-slash-commands
  --setting-sources project` from a directory whose cascade assembles 0 documents.
- tooling: a worktree-isolated session refuses `$VAR`-built paths and heredoc-fed python; use
  literal paths and a script file in the scratchpad.

## The exact next action

[9](2), the top item in `OPEN-WORK.md`: the trailing-`&` waiter shape in
`plugins/bitranox/hooks/arbitrary-sleep-nudge.py` becomes a refusal, widened to a gate detached with
`&` (`( ... ) &` collected by a later wait and PowerShell exempt). Corpus replay FIRST
(compuse-toolbox `guard_replay.py`), then TDD with mutation arms, in a fresh worktree from
origin/master. Read the decision verbatim in EXECUTION-USER-REVIEW.md (2026-10-12 18:3x-19:2x).

## Files that matter

- `OPEN-WORK.md` (items [9], [21])
- `plugins/bitranox/hooks/arbitrary-sleep-nudge.py`, `plugins/bitranox/hooks/tests/`
- `EXECUTION-USER-REVIEW.md` (gitignored; the decisions)

## How to verify

- `git log --oneline -1 origin/master` is bdc9c485 or later; `gh run list --commit bdc9c485...`
  shows ci and workflow success.
- `grep -c '^- \[x\] (2026-10-13) \[21\]' OPEN-WORK.md` prints 1.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
