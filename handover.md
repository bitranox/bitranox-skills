# STALE - read 2026-10-08 17:15, work continued

## In flight

- [17] (the user's top live item): the memory and backlog tools as a Claude Code mod, built
  subagent-driven from `docs/plans/2026-10-08-mods-memory-backlog-tools-plan.md` in the
  `notify-decide-failed` worktree. Tasks 1-7 are done and reviewed; Tasks 8, 9 and 10 are not
  started. The progress ledger `.bitranox/sdd/progress.md` (gitignored, worktree-local - resume FROM
  that worktree) lists every task's commits, the minor findings for the final whole-branch review,
  the plan deviations, and the Task 7 findings.
- Fix `2421f869` (the mod answers each tool call with the envelope as JSON TEXT) was verified live
  (Task 7 run 2) but has NOT had its own subagent task review yet. Do that first.
- [12] belongs to the `jev-shadow` session and waits on time (earliest 2026-10-13).

## Committed, or not

- Branch `mods-memory-backlog-tools`, NOT pushed, version 8.7.0: the design, the plan, Tasks 1-6 and
  fix `2421f869`. ORIGIN SHIPPED 8.7.0 ITSELF at about 17:00 (1d5e1ced, the coding-python-logging
  skill) and closed [150] and [400] in its OPEN-WORK.md, so the repo gate now refuses every commit on
  this branch until it is rebased and re-bumped above origin.
- THIS handover.md and the reconciled OPEN-WORK.md ([17] updated, [440] added) are UNCOMMITTED in the
  worktree for that reason - the commit was refused, not skipped. Commit them right after the rebase.
- Uncommitted and NOT mine to judge blind: `plugins/bitranox/tsconfig.json` (untracked; appeared
  after the Task 6 fix - written by `claude plugin test` or the fixer). Decide commit or ignore
  before Task 10. `plugins/bitranox/.claude-plugin/types/` is gitignored by its own .gitignore.
- The previous handover text is copied to `.bitranox/sdd/handover.prev.md` (ignored).

## Decided, and why - do not reopen

- The bridge (`plugins/bitranox/hooks/mod_bridge.py`) answers every path with exactly one ASCII
  JSON line: exit 0 ok, 1 refused (kind named), 2 could not run (BadRequest, or `Internal` for any
  non-refusal exception, traceback on stderr). The `Internal` catch-all and `ExcludedLevel` as a
  refusal were added beyond the plan, because a model must always get an envelope it can act on.
- A wrong-typed field from the model is a refusal (exit 1), never `Internal`; `level` absent or
  null means the session cwd, anything else must be a non-empty string.
- `memory_add` may create a new tree top or scaffold any sub-level, like the CLI's `--proj` (design
  doc line 60).
- A registered tool's `{ result }` must be a STRING or a content-block array: core validates it,
  and the plugin test kit (no engine) does not. The mod returns `JSON.stringify(envelope)`.
- The plan's Task 7 pass criterion (the FILE only) was insufficient: run 1 wrote the file while every
  call reached the model as an error. Judge a tool e2e by the transcript's tool_result too.

## Decided against, and why

- Unrolling the `tool.call` loop into five literal calls: `validate` lists the computed matcher as
  `tool=?`, but routing is at runtime (d.ts), so it is cosmetic.
- Using `deny` for a refusal: a refusal envelope is a normal answer the model acts on.

## Still open, untouched

`OPEN-WORK.md` holds them: [12], [18], [19], [245], [390], [400], [410], [420], [430], and the new
[440] (the escape-trap guard proposal, unanswered).

Two plan-mandated minors wait for the user at the final review (ledger): `OSError` in REFUSALS
reports an environment fault as exit 1 not 2; `body` is required on every `memory_add`.

## Lessons for the next nap

- When a plugin's tool behaviour is unit-tested with `claude plugin test`, run one headless
  `claude -p --plugin-dir` session too and read the transcript's tool_result `is_error`: the kit has
  no engine, so core's output-shape validation never runs (captured in no fact yet).
- When a mod hook answers a registered `mcp__<plugin>__*` tool, return `{ result: <string> }` or a
  content-block array, never an object (measured on 2.1.294; extends the mods memory fact).
- When a subagent prompt or a Write must carry a backslash-u escape, name the character by
  codepoint (U+0662) and build it with chr(0x0662), never type the escape: it hit a third time
  writing THIS handover (captured: recurrence 2 before that, guard proposal [440]).
- When validating a whole value with a Python regex, use `fullmatch` and `re.ASCII` (captured as
  reference-python-re-dollar-matches-before-a-trailing-newline-and-d-is-not-ascii).
- When a parametrize case holds a huge string, give it an explicit `pytest.param(id=...)`: the raw
  id lands in PYTEST_CURRENT_TEST and a child subprocess fails with E2BIG.
- When a haiku implementer reports a suite count far below the known size, run the full suite
  yourself before review (Task 4 reported 276 of about 6,700).
- When checking a rank or any line-anchored field with grep, prove the pattern on a known-present
  value first (a `\] \[440\]` check could never match and read as "free").
- tooling: the stop-repeating-failure nudge blames the last git subcommand of a compound command
  the worktree guard refused (queued via contrib_queue).
- tooling: a worktree-isolated session cannot edit the shared `.git/info/exclude`.
- Not yet confirmed napped: the lessons of the 14:35 handover (commit a0f7310d) and those it carried
  from the 13:30 (8f1573be) and 11:50 (31b9e205) handovers - read them from `git show <sha>:handover.md`.

## The exact next action

From the `notify-decide-failed` worktree, first restore a committable branch: set this handover and
OPEN-WORK.md aside in a temporary WIP commit is impossible (gate), so copy both into
`.bitranox/sdd/` (ignored), `git checkout -- handover.md OPEN-WORK.md`, rebase onto origin/master
(OPEN-WORK.md will conflict: keep origin's [150]/[400] closes AND this branch's lines), re-bump to
8.8.0 in `plugins/bitranox/.claude-plugin/plugin.json` and `pyproject.toml` (assert the old value;
round-trip) and rename this branch's CHANGELOG `## [8.7.0]` entry to `## [8.8.0]` above origin's,
fold the bump into the branch's first plugins/ commit or a new one, then re-apply the two copied files
and commit them. Then invoke bitranox:process-agents-subagent-driven-development, arm the model gate,
review fix `2421f869` (its sha changes after the rebase - re-derive it), then Task 8.

## Files that matter

- `docs/plans/2026-10-08-mods-memory-backlog-tools-plan.md`, `-design.md`
- `plugins/bitranox/hooks/open_work.py`, `mod_bridge.py`, `memory_engine.py` (add_with_advice),
  `self_improve_signals.py` (why_not_queued), `plugins/bitranox/hooks/mods/register.ts` and its test,
  `plugins/bitranox/hooks/hooks.json` (`modules` key)
- `.bitranox/sdd/progress.md` (ledger) and `.bitranox/sdd/task-*-07123228-{brief,report}.md`

## How to verify

- `git log --oneline origin/master..HEAD` in the worktree shows the design, plan, Tasks 1-6, the
  fixes and this handover.
- `uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2
  python -m pytest plugins/bitranox/hooks/tests/test_open_work.py plugins/bitranox/hooks/tests/test_mod_bridge.py -q`
  passes; `claude plugin test plugins/bitranox` reports 6 pass; `claude plugin validate
  plugins/bitranox` passes.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
