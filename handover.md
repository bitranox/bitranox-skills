# Handover - 2026-09-27 02:00, rank 10 hook-report fixes done on 8 local branches, NOT integrated

## In flight

Integration of the rank 10 fixes. Everything below is committed on LOCAL branches in the shared
repo (`git branch --list 'rank10-fix*'`), nothing of it is pushed.

- `rank10-fix` (worktree `.claude/worktrees/rank10-fix`), tip `97dda56d`: the 7.25.12 bump of
  `plugin.json` + `pyproject.toml`, a CHANGELOG `## [7.25.12]` STUB (one placeholder bullet, to be
  replaced), and S0's additive `shell_text.blank_heredoc_bodies` / `commands_only_aligned`.
- `rank10-fix-F1` .. `rank10-fix-F7` (worktrees `.claude/worktrees/rank10-fix-F<n>`), each branched
  from `97dda56d`, disjoint file ownership, 34 commits in total, each fixer's whole-hooks suite green
  (4821-4851 passed). Tips: F1 881191c2, F2 b017f711, F3 1c2c293f, F4 89998a39, F5 d362ee44,
  F6 53bb6bd1, F7 66a718f4.
- Reports (FIXED / NOT FIXED / NOTICED / CHANGELOG lines / SUITE / COMMITS), harvested verbatim
  from the transcripts: main checkout `.plan/rank10-passing-2026-09-27/fix/F<n>.report.txt`, with
  the briefs (`COMMON.txt`, `F<n>.txt`) and `INTEGRATION-TODO.txt` beside them. The adjudication
  that produced the work is `.plan/rank10-passing-2026-09-27/TRIAGE.md` + `verdicts/`.

## Committed, or not

- Pushed: `8f4960e1` (rank 10 line corrected from "about 7" to 29 reports; CI green) and the commit
  carrying this file and the OPEN-WORK update.
- Local only: the 8 branches above. The main checkout is still ~140 commits behind origin/master
  with another session's `PLAN-JEV-SKILL.md` / `TODO-JEV.md` staged - leave it alone.

## Decided, and why - do not reopen

- The user chose ALL batches (S B H R N D T), H B S R first. Done as one release, 7.25.12 (patch:
  every change is a fix).
- skill-router c1 (compound keyword double-counts) is NOT fixed: F5 replayed 1,311 real prompts and
  the fix removed only true positives. Pinned as intended with a test. It is recorded as a design
  question for the user in OPEN-WORK 184, not as work.
- toolbox-nudge NEW 1 (blank double-quoted prose) NOT done: replay showed 12% of firings would
  change, nearly all real chores.
- repo-gate c2 (read the blob for CRLF) NOT done: F7 proved it would turn a false block this repo
  cannot hit into a real false pass.
- post-compact-nudge now prints nothing and no longer deletes the salvaged audit (PostCompact
  delivers no context per the official hooks doc; the Stop gate already carries the nap hint).
- self-improve-gate routing hint now says "this session", because touched-paths evidence is
  session-cumulative (clear_touched_paths has no production caller).

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file. Rank 10 (its `next:` names the integration),
184 (fixer follow-ups, NEW), 177, 182, 183 as before.

## Lessons for the next nap

- When a backlog line carries a count of what is left ("about 7 reports"), recount it from the
  source record before working it: this one had eroded from 20 to 7 while the real remainder was
  29.
- When harvesting a subagent's report, parse its transcript for the SubagentHandback tool_use input
  (a small marker-keyed script did it: `/tmp/claude-1000/rank10-passing/harvest.py`, markers
  `FIXED:` `SUITE:` or `VERDICT:` `SUMMARY`), not the delivered message.
- When an offset-sliced parser strips heredoc bodies, it must slice from a length-preserving copy:
  three hooks recorded wrong values after a heredoc; shell_text now has blank_heredoc_bodies.
- When a hook's output must reach the model, check the channel against the event: exit-0 stderr
  and PostCompact stdout reach nobody (git-commit-branch-guard had never been seen by the model).
- tooling: the brief-writing heredoc was blocked by shell-prefix-selfref-guard over `$V`; write
  briefs with the Write tool.
- tooling: the installed 7.25.9 venv-guard fired WRONG VENV on this session's own printf of quoted
  text (the defect F6 fixed); expect such noise until 7.25.12 is installed.

## The exact next action

Integrate, in order, from `.claude/worktrees/rank10-fix`:

1. `git merge --no-ff rank10-fix-F1` ... `rank10-fix-F7` (disjoint files: expect no conflicts; if
   one appears it is a real overlap - read both sides). Remove the stale `rank10-fix-S0` worktree.
2. Do the "at integration" items of OPEN-WORK 184 (docs describing the old post-compact-nudge,
   meta-self-improve SKILL.md "this turn" - SKILL.md edits go through bitranox:meta-skill-writer,
   self-improve-audit.py snippet via `inert_snippet(..., around=sig.asst_signal_offset(...))`,
   TRIGGERS entries). Or carry them to 7.25.13 if the release should stay pure.
3. Replace the CHANGELOG stub with the fixers' CHANGELOG lines (in each report), then
   `repo-gate.py --ci` with CI's dependency set, commit, push to master (pre-push runs the suite),
   and watch CI with `ci_wait.py --sha <full sha>` launched from the main checkout.
4. Close rank 10 in OPEN-WORK, remove the rank10-* worktrees with bitranox:git-worktrees / wtclean.

## Files that matter

- `.claude/worktrees/rank10-fix*` - the integration base and the 7 fixer worktrees.
- `.plan/rank10-passing-2026-09-27/` (main checkout, gitignored) - TRIAGE.md, verdicts/, fix/.
- `plugins/bitranox/hooks/shell_text.py` - the new aligned helpers.
- `OPEN-WORK.md` ranks 10 and 184.

## How to verify this still stands

- `git -C <repo> branch --list 'rank10-fix*' -v` shows the 9 branches at the tips above.
- In each F worktree: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with
  defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/ -q`
  is green.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
