# Handover - 2026-09-25 night, rank 10 slice 2 fixed and shipped as 7.24.0-7.24.1

## In flight

Nothing running. Batches A-F of the skill-script audit are fixed, released and CI-green on all
OSes (origin/master ef94aa2, plugin 7.24.1). The next step is the independent review the user
asked for, not code.

## Committed, or not

- **In git and pushed:** everything - 16 group commits, a doc-sync commit, the 7.24.0 changelog,
  the 7.24.1 Windows/macOS fix, and OPEN-WORK. This handover and the OPEN-WORK edits after
  ef94aa2 are committed with it.
- **Not in git, by design (gitignored, main checkout):** `.plan/rank10-skillscript-2026-09-25/`
  now also holds `fix-brief.md` (what every fixer was told) and `FOLLOWUPS.md` (about 40 items the
  fixers found outside their verdicts; OPEN-WORK rank 171).
- **Scratch only, will be swept:** fixer patches and scripts under this session's scratchpad.
  Everything that mattered is in git or in `.plan/`.

## Decided, and why - do not reopen

- **File ownership per adjudication group, not per batch.** Batches A-F cut across files, so 16
  fixers each owned one group's files (reassignments: pluginprune/jig_probe/ci_wait/srccount to R,
  device_profiles to W1). No two fixers touched one file except `test_sdd_scripts.py` (auto-merged).
- **Each group landed as ONE squashed commit through the normal repo-gate**, with the fixers'
  commit subjects listed in the body; the per-fixer branches stay in their worktrees (rank 160).
- **One release (7.24.0) for all of A-F**, not one per batch: the groups are file-disjoint and the
  gate ran on each commit and on the integrated tree.
- **Shared SKILL.md files (compuse-toolbox, compuse-git, SDD, crosstree) were edited by the
  coordinator in one pass** from the fixers' exact wording, with exit-code claims executed.
- **Review all 16 groups independently** (user's choice over high-risk-only) - OPEN-WORK rank 8.

## Decided against, and why

- **Placeholder version bumps in fixer worktrees**: the auto-mode classifier refused them as a gate
  bypass; the coordinator cut the real release instead.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 8 (USER): independent review of all 16 groups in 7.24.0-7.24.1.
- Rank 10 (USER): the last 5 unswept targets, then the old buckets.
- Rank 12 (USER): Jev router decision, blocked on data.
- Rank 150/160 (FOUND): main-checkout cleanup and wtclean of about 35 worktrees now.
- Rank 171 (FOUND): the fixers' follow-ups, fail-open items first.

## Lessons for the next nap

- When parallel fixers commit in worktrees under a commit-time version-bump gate, give them a sanctioned no-bump path (or have them hand back patches) up front; otherwise they route around the gate and its checklist and test checks only fire at landing.
- When landing many fixer branches, run the whole-repo gate on the INTEGRATED tree before pushing: a fixture that relied on another group's old behaviour (a directory named *.jsonl under rglob) broke only when both groups' changes met.
- When a skill's own tests/conftest.py puts its dir on sys.path, a bare sibling import in a script passes its own suite and fails for any caller that loads the script by path; pin it with a load in an isolated interpreter (python -I) from a foreign cwd.
- When a timing test plants synthetic costs with sleep, keep the base cost far above timer slack: a 4 ms base on a macOS runner flattened a planted quadratic to a ratio of 4; 100 ms survives 60 ms of slack.
- When a Windows path key is built from os.path.abspath, a drive-less rooted path gains the current drive and stops matching a key built from the given spelling; keep the given spelling too.
- When landing a subagent's work from a patch file rather than its branch, byte-compare the applied files against its live worktree first - a patch can predate its final edits.
- tooling: repo-gate's version-bump check versus parallel fixer worktrees is queued in contrib_queue.

## The exact next action

Rank 8 is the top open item. Invoke `bitranox:process-review-requesting-code-review` and dispatch
one reviewer per group commit in `git log --oneline 7b82825..ef94aa2` (16 group commits; skip the
opener, doc-sync, changelog and jig_probe-test commits or give them to one extra reviewer), each
told to check the diff against `.plan/rank10-skillscript-2026-09-25/adj/<group>/verdicts.txt` in the
main checkout and to demand an executed failing input per finding; plus one reviewer that greps
every caller of a script whose exit codes changed.

## Files that matter

- `.plan/rank10-skillscript-2026-09-25/` (main checkout): `TRIAGE.md`, `adj/*/verdicts.txt`,
  `fix-brief.md`, `FOLLOWUPS.md`.
- `CHANGELOG.md` sections `[7.24.0]` and `[7.24.1]` - what shipped, by batch.

## How to verify this still stands

- `git log --oneline -1 origin/master` shows the handover commit on top of ef94aa2.
- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --sha <full sha of
  ef94aa2> --repo bitranox/bitranox-skills` reports `workflow=success ci=success`.
- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.24.1.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
