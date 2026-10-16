# Handover 2026-10-16 (late): [23] phase 2 step 6 done, 9.2.1 shipped

## In flight

- Nothing part-done. One background watcher may report into the next conversation: `ci_wait.py`
  on `2d056f71` (the OPEN-WORK-only commit). If it never arrives, run the check under "How to
  verify" yourself.
- No subagents are running.

## Committed, or not

- Pushed: 9.2.0 (the fold) and 9.2.1 (`bmk-gate-nudge` test fixture fix; CI green on
  `0b4288ad`), and `2d056f71` (OPEN-WORK [23] update). This handover is committed on top.
- Memory store (`<softdev-root>/.claude-memory`, the tree-top store): uncommitted, as before, plus this
  session's changes: 29 facts archived, 25 citing facts re-pointed, 41 hooks shortened, one fact
  updated (`reference-split-a-hook-s-tool-input-command-by-the-tool-never-by-os-name`, test-side
  delta). Peer sessions' captures sit there too; the next dream commits them, staging
  deliberately (never bare `git add -A`).
- `uv.lock` holds a local 9.2.0 -> 9.2.1 edit; it is gitignored, so it is harmless.

## Decided, and why - do not reopen

- Pointers were removed or shortened only after a fresh verifier quoted the governing line from
  the INSTALLED 9.2.1 text and the quote was substring-checked. `.plan/fold-23/edits-verify.json`
  is the FIRST verify round only (13 of the 32 read FAIL/NOT-ADDED there and were in fact applied
  later); the `.skillwriter` checklists and `.plan/fold-23/step6/*.json` hold the final evidence.
- The 3 PARTIAL FOLD-THEN-REMOVE pointers stay because what the skill lacks is machine-local and
  cannot ship publicly (see [23] in `OPEN-WORK.md`).
- The 10 FOLD-KEEP-POINTER rows owned by mirrored skills (devops-bmk, coding-python-pwshpy,
  coding-python-send-mail) and provmm-benchmark keep their full hooks: never folded.
- The 9.2.0 CI red was the test, not the hook: a Bash command built from a native Windows path
  loses its backslashes exactly as Git Bash does. Fixed with `as_posix()` in the test.

## Still open, untouched

- [12] waits for decide rows (earliest ~2026-10-18). [26] (the user's request about skill-caused
  memory entries) and everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When deleting always-loaded pointers after a fold, verify each rule against the INSTALLED plugin cache text with a substring-checked quote, never against a pipeline's verify record: the round-1 record showed 13 of 32 as not applied that a later round had applied.
- When a new hook test passes a pytest `tmp_path` into a Bash-tool command string, run it on the Windows VM before pushing: both local gates run on Linux, and the 9.2.0 push went red only on the Windows cell (already captured in the hooks-level fact; nap: confirm, no new fact).
- When extracting a subagent's JSON result from its transcript, read assistant records only: the brief you sent it contains the same keys and matches first.
- When building a dash/underscore-tolerant slug regex, join the escaped parts with `[-_]`; a chained `.replace()` rewrites the `-` inside the class it just inserted.
- tooling: `factedit apply --body-file` with a body that starts with a blank line doubles the blank line after the frontmatter; strip leading newlines (or the engine could normalise them).
- Carried over, not napped yet: the three lessons in `git show 2d056f71:handover.md` and the ten in `git show 6c1370ea:handover.md` (section "Lessons for the next nap" in each).

## The exact next action

[12] is blocked until ~2026-10-18, so [23] is the top workable item. Shorten the 3 kept
FOLD-THEN-REMOVE pointers to their machine-local delta, through the engine:

    python3 <plugin>/skills/meta-dream-tree/factedit.py show --slug remote-powershell-file-not-inline

then the same for `memory-store-local-git-durability` and
`feedback-a-recorded-review-verdict-goes-stale-when-the-reviewer-posts-again`; write a
trigger-first hook naming only what the skill lacks plus `Detail: bitranox:<skill>.`, and apply
with `factedit.py apply --slug <s> --level <softdev-root> --hook-file <f>
--stage-dir <scratch>`. After that, [23] next items (2)-(4).

## Files that matter

- `OPEN-WORK.md` ([23] carries the step-6 numbers and next steps; [590], [610])
- `.plan/fold-23/step6/` (`verify32.json`, `plan32.json`, `keep-verify.json`, `keep57.json`,
  `refmap32.json`), `.plan/fold-23/rows.json`
- `.plan/fold-23/backup-pre-archive-32.tgz`, `.plan/fold-23/backup-pre-hookcap-41.tgz`
- `~/.claude/plans/curried-mapping-dolphin.md` (the [23] plan; Phase 3 = lower levels)

## How to verify

- CI on the pushed commits: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`).
- `grep -c '](mem:' <softdev-root>/CLAUDE.local.md` printed 321 after step 6 (more if
  peer sessions captured since).
- `reconcile_memory_index.py --check-tree <softdev-root>` reported TOTAL 1 after step 6:
  the rct-bose sideways ref already in [590].

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
