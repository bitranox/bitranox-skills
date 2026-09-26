# Handover - 2026-09-26, rank 8 closed: LOW pass shipped as 7.25.6, CI fixes 7.25.7-7.25.8, green

## In flight

Nothing. The 7.24 fix-group review (rank 8) is finished: HIGH in 7.25.3, MED in 7.25.4, LOW in
7.25.6 (13 fixer groups, each landed only after its tests-only half failed on the old source).
7.25.6 failed CI on py3.14 and Windows and 7.25.7 on py3.11; both were test or depth-limit
defects, fixed in 7.25.7 and 7.25.8. CI is green on 7.25.8 in both workflows.

## Committed, or not

- **In git and pushed:** 7.25.6, 7.25.7, 7.25.8 on master (`git log --oneline -4`). This file and
  the `OPEN-WORK.md` updates are in the commit after them.
- **Not in git, by design (gitignored, main checkout):**
  `.plan/rank8-review-2026-09-26/LOW-LEDGER.txt` holds, per fixer group, the RED/GREEN counts, the
  "Left:" findings (rank 181) and the 16 DESIGN questions with options and a recommendation each
  (rank 177). `REVIEW.txt` and `MED-FOLLOWUPS.txt` beside it are now fully worked.
- The 13 fixer worktrees (`.claude/worktrees/agent-*`) still hold their changes uncommitted; the
  content is in 7.25.6. Rank 160 lists them for wtclean, to discard rather than merge.
- Both queued block-masked-gate-exit contributions are shipped in `contrib_queue`.

## Decided, and why - do not reopen

- **jsonl_grep's stdlib fallback refuses nesting past 1024 levels, orjson's own limit.** Measured:
  orjson reads `{"x":` + 1023 lists and refuses 1024. Leaving it to the stack made the verdict
  depend on the interpreter: CPython 3.14 reads 100,000 levels and then fails serialising, 3.11
  stops near 1000. The test's readable control sits at 500 levels for that reason.
- **orjson's serialiser refuses values its reader accepts**, so `_dumps` falls back to the stdlib
  in orjson's compact form (`separators=(",", ":")`) instead of a traceback.
- **The transfer tests for single-quote and backslash quoting run only on POSIX.** Under Windows
  command-line rules neither quotes anything, so the refusal there is right; the Windows rules have
  their own tests.
- **Every DESIGN question stayed unchanged in code**; none is decided by the coordinator.

## Decided against, and why

- Running a behavioural RED on the installed skills for the seven SKILL.md doc syncs: the installed
  text would answer both arms. The arms were pasted passages built from the porcelain word diff, on
  an inert haiku probe; each checklist records the questions and quotes.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): review all skills and scripts one by one.
- Rank 177 (FOUND, blocked on the user): 16 design decisions from the LOW fixers.
- Rank 181 (FOUND): about 45 left-alone claims from the LOW fixers.
- Rank 175 (FOUND): decision (c), the table-padding waiver in repo-gate, still to implement.
- Rank 160 (FOUND): 58 finished worktrees; wtclean from the main checkout.

## Lessons for the next nap

- When a test's control depends on how deep the stdlib JSON decoder can recurse, pin the control
  well inside every supported interpreter's limit: 3.11 stops near 1000, 3.14 reads 100,000.
- When a fixer builds a path in a test with `str.replace("/x/", ...)`, it is a no-op on Windows;
  build the variant from path parts and assert it differs.
- When a word-diff (`--word-diff=plain`) must be split into old and new text, use
  `--word-diff=porcelain`: literal text such as `[--type` is read as a deletion marker.
- When a checklist line claims a probe result, confirm the question was actually in the probe; one
  of seven was not and needed its own RED/GREEN pair.
- tooling: the cached 7.25.2 block-masked-gate-exit still blocks a lone backgrounded ci_wait in
  sessions that have not reloaded; run it in the foreground until they have.
- tooling: a worktree-isolated session refuses any Bash command naming git in a compound form, and
  `env -u` in a long command; keep scratchpad scripts (`rt.sh`, `land.sh`) for test and patch runs.

## The exact next action

Rank 10 is the top open USER item. Before starting it, put the rank 177 decisions to the user one
at a time, weightiest first, since the user is present and each only needs an answer; the options
and recommendations are in `LOW-LEDGER.txt`.

## Files that matter

- `OPEN-WORK.md` ranks 10, 160, 175, 177, 181.
- `.plan/rank8-review-2026-09-26/LOW-LEDGER.txt` (main checkout, gitignored).
- `CHANGELOG.md` `## [7.25.6]` to `## [7.25.8]`.

## How to verify this still stands

- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.25.8, and
  `pyproject.toml` says the same.
- `python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --sha <full sha of the 7.25.8
  commit, from git log>` reports `workflow=success ci=success`.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
