# Handover - 2026-09-26 late, rank 10's last five targets fixed as 7.25.9, CI green

## In flight

Nothing. The five targets added to the review since 2026-08-28 (run-python.sh, sha-literal-nudge,
skill-listing-budget, render-graphs.js, detectors.js) were swept, adjudicated (23 findings: 22
confirmed, 1 partial, 0 refuted, about 11 new), fixed test-first by one fixer per file, and
released as 7.25.9 (d96ce52c). CI green on that sha in both workflows.

## Committed, or not

- **In git and pushed:** the five fix commits and the 7.25.9 release commit on master
  (`git log --oneline -7`), plus this file.
- **Not in git, by design (gitignored, main checkout):** `.plan/rank10-last5-2026-09-26/` -
  `reports/` (the sweep), `adj/*.verdicts.txt` (the adjudications, verbatim), `fix/*.fixer-report.txt`
  (the fixers' reports, verbatim, including what they noticed and left), `TRIAGE.md` (batches and
  the user's decisions D1-D8).
- **The main checkout is 121+ commits behind origin/master** and has `PLAN-JEV-SKILL.md` and
  `TODO-JEV.md` staged, which this session did not do and left alone. Work from a worktree created
  off `origin/master` explicitly; one based on the main checkout's HEAD starts on 7.0.0-era code.

## Decided, and why - do not reopen

The user's decisions, all implemented in 7.25.9:
- D1: `SHA=$(git rev-parse ...); test "$SHA" = <literal>` nudges (the docstring lists a test
  comparison as a silent consumer).
- D2: run-python.sh launches through a `-c` bootstrap so the shim can never exit 2 on its own
  (about 3 ms more per hook launch).
- D3: Cygwin stays accepted, best-effort; the three doc sites say so.
- D4: cygpath converts only the script path.
- D5: render-graphs suffixes a repeated diagram name; D6: `--combine` refuses shared node ids.
- D7: skill-listing-budget manages only the user-level fraction; a listing from a project with
  its own is skipped (only `~/.claude/settings.json` sets it on this machine, of 68 files).
- D8: inside a subagent, a sha from its brief counts as shown only if the parent showed it.

## Decided against, and why

- A behavioural RED for the meta-skill-writer doc sync: redcheck reported STRONG on function
  words; the quote-back text check on pasted passages was used instead (checklist in
  `plugins/bitranox/skills/meta-skill-writer/.skillwriter/checklist-20260926-render-graphs-and-shim-scope.md`).

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): only the old buckets are left - 17 unadjudicated guard-slice claims and 5
  coverage gaps, written against 2026-08-28 code.
- Rank 177 (FOUND, blocked on the user): 16 design decisions from the 7.25.6 LOW fixers.
- Rank 182 (FOUND): about 18 things the 7.25.9 fixers noticed and left.
- Ranks 160, 175, 181 unchanged.

## Lessons for the next nap

- When harvesting a subagent's handback from its transcript, take the handback tool_use input and
  not the last long text block: a short summary written after the handback overwrote it.
- When a fan-out's fixers each work in their own worktree, create those worktrees from
  `origin/master` yourself; Agent `isolation: worktree` bases them on the main checkout's HEAD,
  which here was 121 commits stale.
- When a fix changes a parser that several hooks share, have the fixer name every consumer and
  run each consumer's suite; the shell_text sink change reached four hooks.
- tooling: `ci_wait.py` backgrounded inside a compound command is refused by
  block-masked-gate-exit; background it alone.
- `~/.claude/settings.json` was rewritten at 22:34:50 by something other than
  skill-listing-budget (hash changed, fraction unchanged); nobody identified the writer.

## The exact next action

Rank 10 is the top open USER item. Re-check the 17 guard-slice claims and 5 coverage gaps in
`.plan/rank10-review-2026-08-28/TRIAGE.md` (main checkout) against master at 7.25.9, one
adjudicator per group with a control per claim, then ask the user which confirmed items to fix.
The user is usually present, so put the rank 177 decisions to them one at a time as well.

## Files that matter

- `OPEN-WORK.md` ranks 10, 177, 182.
- `.plan/rank10-review-2026-08-28/TRIAGE.md` and `.plan/rank10-last5-2026-09-26/` (main checkout).
- `CHANGELOG.md` `## [7.25.9]`.

## How to verify this still stands

- `git show origin/master:plugins/bitranox/.claude-plugin/plugin.json | grep version` prints 7.25.9.
- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha d96ce52cb40f85f1c2014ead1c3b37f16a4f9058`
  reports `workflow=success ci=success`.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
