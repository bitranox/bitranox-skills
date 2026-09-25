# Handover - 2026-09-25 late, rank 171 fixed and shipped as 7.25.0-7.25.2

## In flight

Nothing running. Rank 171 (about 40 follow-ups) is fixed and released as 7.25.0; the ~15 problems
its fixers found are fixed and released as 7.25.1. The next step is the top backlog item, not code.

## Committed, or not

- **In git and pushed:** 7.25.0 (8 group commits, `cabea193..cea4c5e7`, CI green on all OSes),
  7.25.1 (5 commits, `cea4c5e7..274762b4`; CI red on windows-latest only, one test whose fixture
  was written in text mode) and 7.25.2 (`68414a2c`, that fixture written as bytes; CI green on
  every OS). This handover and the OPEN-WORK edits are committed on top of `68414a2c`.
- **Not in git, by design (gitignored, main checkout):** `.plan/rank10-skillscript-2026-09-25/`
  now also holds `FOLLOWUPS-2.md`, the list behind OPEN-WORK rank 173.
- **Worktrees left on disk:** this session's `jev-roster` (equal to master after the push) and 12
  fixer worktrees `.claude/worktrees/agent-*` from this session, all folded into master through
  byte-compared patches. They are rank 160 cleanup; wtclean them, never `rm -rf`.
- `EXECUTION-USER-REVIEW.md` (clone-local, gitignored) has three new decisions from this session.

## Decided, and why - do not reopen

- **run-python.sh is strict by default; `hooks.json` opts into fail-open with `--hook`.** Adding
  `BITRANOX_RUN_PYTHON_STRICT=1` to 14 SKILL.md files would have left the next doc that forgot it
  silent again. A catalogue test now refuses any SKILL.md line that launches through `--hook`.
- **Fixers hand back `git diff --binary` patches; the coordinator commits.** repo-gate has no
  no-bump path, and each patch was byte-compared against its fixer's worktree before applying.
- **Every item was reproduced with a control before it was fixed.** None came back
  NOT-REPRODUCED; two were only half true (audit_headers `data-foo`, corpus_prompts' split).
- **Whitespace-only table re-padding ships with a cell-by-cell proof in its checklist** instead of a
  RED/GREEN arm (logged as a judgement; rank 175 (c) asks the user whether to make it a rule).

## Decided against, and why

- Re-padding `coding-python-new-public-library`'s table alone: it is a mirrored skill and one side
  fails the mirror gate; both twins go together (rank 176).
- Fixing rank 173's items in this session: they are unadjudicated and the session was past the
  handover threshold.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 8 (USER): independent review of the 16 fix groups in 7.24.0-7.24.1.
- Rank 173 (FOUND): 15 follow-ups from the 7.25.x fixers; decide the toolbox `--json` "ok" rule first.
- Rank 175 (FOUND): the user decided all three on 2026-09-26. (a) schematic below threshold exits
  1 and (c) repo-gate verifies padding-only table diffs and waives the checklist - both to
  implement; (b) the real-store tombstone repair is DONE (backup verified, 15 files / 63 records),
  with one re-run owed after every session is on 7.25.x.
- Rank 176 (FOUND): one mirrored table left.

## Lessons for the next nap

- When a test asserts BYTE offsets into a fixture file, write the fixture with write_bytes: text
  mode writes CRLF on Windows, and only the windows-latest cell sees it (7.25.1).
- When landing parallel fixers' patches, run the whole-repo gate on the INTEGRATED tree: two
  individually green fixes (a catalogue test and a doc example) failed only together.
- When a PostToolUse formatter keys on mtime, restore a file with git and back-date it in the same
  call (`touch -d`), or the next command's time window reformats it again.
- When a skill doc must show a hooks.json registration, state the argument order and point at
  `hooks/hooks.json` rather than writing a launch line a skill step could copy.
- When a fixer brief says items are unadjudicated, require the arm AND a control per item: every
  one of 40 reproduced, and the controls caught two half-true items.
- tooling: reformat-md-tables re-dirties a file a git tree-writer just wrote, via the next non-git
  command's 120 s mtime window (in FOLLOWUPS-2.md).
- tooling: two memory facts still say run-python.sh exits 0 on a missing script
  (`reference-run-python-sh-exits-0-when-the-script-is-missing-so-a-mistyped-gate-path-passes-silently`,
  `reference-a-hook-gets-a-bare-interpreter-and-fails-open-so-its-bugs-read-as-approval`); since
  7.25.0 that holds only for `--hook` launches.

## The exact next action

Rank 8 is the top open USER item. Invoke `bitranox:process-review-requesting-code-review` and
dispatch one reviewer per group commit in `git log --oneline 7b82825..ef94aa2` (16 group commits),
each told to check its diff against `.plan/rank10-skillscript-2026-09-25/adj/<group>/verdicts.txt`
in the main checkout and to demand an executed failing input per finding. Rank 175's two decided
implementations (schematic exit 1; the gate's padding-only waiver) are the natural next release
after it.

## Files that matter

- `.plan/rank10-skillscript-2026-09-25/FOLLOWUPS.md` (done) and `FOLLOWUPS-2.md` (rank 173).
- `CHANGELOG.md` sections `[7.25.0]` and `[7.25.1]` - what shipped.
- `plugins/bitranox/hooks/run-python.sh`, `plugins/bitranox/hooks/hooks.json` - the `--hook` split.

## How to verify this still stands

- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.25.2.
- `uv run plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --sha
  68414a2c1dce457a2f424b7c4e4f813a0cb8728b` reports every workflow successful.
- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports 0 drifted pairs.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
