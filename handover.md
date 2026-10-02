# Handover - 2026-10-03 00:10, rank 16 Jev shadow plan shipped in full (7.40.0); nothing in flight

## In flight

- Nothing part-done. The rank 16 plan (Tasks 1-10 plus the final whole-branch review and its
  fixes) is on origin/master: 7.40.0 = 90299b94 (CI green), rank 16 closed in f6d6f2fe (CI green).
- This worktree (`.claude/worktrees/jev-shadow`, branch `worktree-jev-shadow`) equals origin/master
  apart from this handover and the OPEN-WORK reconcile committed with it. It can be removed once
  nobody needs its gitignored ledger (`.bitranox/sdd/`: progress.md, briefs, every task, review
  and fix report, `final-review-findings.md`).

## Committed, or not

- All code and skill text is committed and pushed. This file and OPEN-WORK.md (rank 240 closed,
  rank 245 added) go in one commit after f6d6f2fe.
- Uncommitted by design: the gitignored `.bitranox/sdd/` ledger and reports in this worktree.
- The model gate (`skill_receipt.py ... plan-execution`) is disarmed.

## Decided, and why - do not reopen

- `classifier_skills = shadow` stays ON on this machine, so dreams and the 11 wired steps send
  their items to Jev (cents per run): the decide rule at rank 96 needs that data. Reverse with
  `settings.py set classifier_skills off`.
- Leaving shadow for decide is governed ONLY by the pre-registered rule at OPEN-WORK rank 96
  (written before any data); it must not be loosened after the data is seen.
- The log-locked case writes an exclusive side file `jev-skill-shadow-YYYY-MM-<run id>.jsonl`
  (read by `report`, aged by retention) instead of retrying: a paid run never loses its records.
- The data-arch STEP D shadow bullet stays where it is: 5 more haiku arms (old and new text) all
  took the violation branch; the one earlier "clean" summary did not recur.

## Decided against, and why

- No `items --out` refusal inside a git work tree: it would cover only the 5 store-built sites;
  the shared procedure's temp-dir step covers all 10.
- crosstree 4b's exit-1 path ("no candidates, skip run") can leave an EMPTY temp dir outside any
  repo; cosmetic, left.
- Commit d2be23ec (now fa3ba3e3 after the rebase) says "8 of the 9 wired skills"; the true count
  is 11 bullets in 8 skills. History is append-only, so the message stays; CHANGELOG 7.40.0 is right.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on Stop-gate decide rows; rank 14 (USER, notification
routing measurement) is the top workable item; rank 96 waits on shadow data; rank 150 (main
checkout behind origin) and the new rank 245 (leftover worktree) need a session in the main
checkout.

## Lessons for the next nap

- When an SDD task brief forbids a version bump in bitranox-skills and HEAD is already on origin,
  the repo-gate commit hook refuses every plugins/ commit; put the bump (plugin.json, pyproject AND
  a CHANGELOG heading in the same commit) in the FIRST task of the batch, not the release step.
- When the auto-mode classifier refuses a version-bump script, ask the user to run it with `!`;
  it took one command and unblocked the whole batch.
- When arming ci_wait after a push, take the sha from `git rev-parse --verify -q HEAD` output; I
  padded a short sha to 40 characters and the wait polled a commit that does not exist.
- When skill text tells an agent to make a temp dir with `D=$(mktemp -d)`, say to reuse the
  LITERAL printed path: a Claude Code Bash call is a fresh shell, so `$D` is empty in the next call.
- tooling: a worktree-isolated session refuses any Bash call that mixes git with pipes, `$(...)`,
  loops or a python heredoc mentioning git; one plain git command per call, file edits via Edit.

## The exact next action

Rank 12 is top-ranked but blocked on data, so rank 14 (USER, "MEASURE ! ... compare them to the
keyword based approach"): read its `next:` field in OPEN-WORK.md and re-measure the background-task
notification rows logged since 7.30.9 against the keyword router, then decide per notification kind.
Do it from a fresh worktree off origin/master (this one is finished).

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/jev_shadow.py` (+ `jev_shadow_sites.py`,
  `jev_shadow_log.py`, `jev_shadow_report.py`, `jev_shadow_ports.py`) and `jev_sites/*.json`.
- `plugins/bitranox/skills/meta-self-improve/references/jev-shadow.md` - the shared procedure,
  including "The report line" (the four forms every dream report uses).
- The 11 wired bullets: `grep -rn 'Jev shadow' plugins/bitranox/skills/*/SKILL.md`.
- Shadow log: `~/.claude/self-improve-audit/jev-skill-shadow-YYYY-MM*.jsonl`; analyse with
  `jev_shadow.py report`.

## How to verify

- `git log --oneline -3 origin/master` shows f6d6f2fe (close rank 16) on 90299b94 (7.40.0).
- `python3 plugins/bitranox/skills/meta-self-improve/jev_shadow.py status` - shadow on here.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with
  ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/meta-self-improve/tests/ -q`
  - green.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
