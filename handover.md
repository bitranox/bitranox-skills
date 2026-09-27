# Handover - 2026-09-27 10:30, rank 20 adjudicated and triaged, fixing not started

## In flight

Nothing is part-done. Rank 20 (the skills half of the 2026-08-27 audit directive) is sized,
re-adjudicated and triaged; the user chose ALL FIVE batches. No fixer has been dispatched.

## Committed, or not

- Pushed this session: 7.25.12 (rank 10 fixes) and 7.25.13 (its Windows follow-up), CI green on
  f69a23c3; rank 10 closed (1606880b); rank 15 closed (43172d99); this file and the OPEN-WORK update
  for ranks 20 and 95 (the commit carrying this file).
- Memory store (the private tree-top store, not this repo): 72fc56b lifts the
  private-Gitea fact to the tree top and clears the last sideways ref; --check-tree TOTAL 0. Other
  sessions' uncommitted edits sit in that store too - they are not ours, leave them.
- Main checkout: still ~140 commits behind origin/master with another session's PLAN-JEV-SKILL.md /
  TODO-JEV.md staged. Leave it alone; work from worktrees off origin/master.
- Gitignored, main checkout only: .plan/rank20-skills-2026-09-27/ (TRIAGE.md, input/, verdicts/)
  and .sweep-2026-08-27/verified.tsv (the August source record).

## Decided, and why - do not reopen

- "The reviewer half" (rank 20's old wording) means the SKILLS half of "review all skills and
  scripts"; the scripts half was rank 10. No record kept the label's meaning; the user confirmed.
- Scope: re-adjudicate only the 53 August findings whose quote still stood (not a fresh sweep).
  Result 49 fixed, 1 never true, 3 partial, 8 new.
- All five batches B1-B5 go in one release; B5 is rank 95 and closes it.
- Rank 15: the fact's two refs to facts at its old project level were demoted to prose rather than
  lifted - both targets are project-local, lifting them would put project rules above every project.
- 7.25.13 test fix: Bash-command tests quote native paths with shlex.quote (bash strips unquoted
  backslashes); the hooks were right. venv-guard and block-partial-typecheck had real Windows defects.

## Still open, untouched

`OPEN-WORK.md` is the list - read it first. Rank 20 is now top; its line names all five batches.

## Lessons for the next nap

- When a backlog line names work by a relative label ("the reviewer half"), write what the thing IS
  in the line itself: the label outlived every record of its meaning and cost a transcript hunt.
- When a PreToolUse nudge names a shipped jig for a memory fact edit (factedit.py), use it instead
  of hand-rolling the frontmatter strip and re-add.
- When a subagent probes a public package index (crates.io, PyPI JSON), tell it never to put the
  user's email in a User-Agent or contact field: G5 did it once on crates.io.
- The memory fact reference-claude-code-hooks-cannot-read-or-change-the-session-model is partly
  stale: PreModelSwitch (CLI 2.1.251+) can block a switch, both model-switch events get from/to_model.
- When a Windows CI cell fails on tests that build Bash commands from tmp_path, check the command
  quotes the path before blaming the hook: bash strips unquoted backslashes.
- When a green-looking assertion was built from a mangled input, fixing the input can expose a real
  defect (venv-guard only counted "/" as a separator on Windows under Bash).
- Windows Python 3.13: Path.resolve() does not raise on an embedded NUL; os.path.isabs("\\r") is
  False (drive-relative).
- tooling: wtclean dry-run then --apply worked cleanly for 12 worktrees; git worktree add -b from
  origin/master is the pattern for OPEN-WORK-only commits while the main checkout is stale.

## The exact next action

Rank 20 (top of OPEN-WORK). Read `.plan/rank20-skills-2026-09-27/TRIAGE.md` in the main checkout,
then dispatch one TDD fixer per batch (B1-B5), each in its own worktree off origin/master, disjoint
files, every SKILL.md edit through bitranox:meta-skill-writer with a .skillwriter checklist. B5 also
rewords the stale memory fact named above (engine add at its owning level, --slug). Integrate, one
release, repo-gate --ci, push, ci_wait by full sha, close ranks 20 and 95.

## Files that matter

- `.plan/rank20-skills-2026-09-27/TRIAGE.md`, `verdicts/G1..G6.verdicts.txt` (main checkout).
- `plugins/bitranox/skills/docs-convert-markitdown/references/api_reference.md` (B1)
- `plugins/bitranox/skills/infra-modulejail/SKILL.md` (B2)
- `plugins/bitranox/skills/infra-swap-tuning/SKILL.md` (B3)
- `plugins/bitranox/skills/coding-python-rpyc/docs/howto.md`, `docs-generate-schematics/SKILL.md`,
  `coding-python-gitignore/SKILL.md` (B4)
- `plugins/bitranox/skills/meta-claude-hooks/` (B5; `scripts/hookdoc_stamp.py check` is the detector)

## How to verify this still stands

- `git fetch origin && git log --oneline -3 origin/master` shows this handover's commit on top.
- `gh run list --commit <that sha> --json conclusion` is success.
- `ls .plan/rank20-skills-2026-09-27/verdicts/` in the main checkout lists G1..G6.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
