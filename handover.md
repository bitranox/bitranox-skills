# Handover - written 2026-09-04, nothing in flight

## In flight

Nothing. Four levers against end-of-session instrumentation shipped as 6.6.0, 6.7.0, 6.8.0,
6.9.0 and the Windows fix 6.9.1; CI green on `353f6b8` in every cell.

## Committed, or not

- `bitranox-skills`: `HEAD == origin/master == 353f6b8`, plugin `6.9.1`. The work was done in the
  linked worktree `.claude/worktrees/defer-instrumentation-to-dream` (branch
  `worktree-defer-instrumentation-to-dream`, equal to master); it holds nothing unpushed and can
  be removed.
- Memory store `/media/srv-main-softdev/.claude-memory`: one new fact written and NOT committed
  there - `feedback-queue-a-misbehaving-bitranox-tool-from-a-work-session-never-fix-it-in-place`,
  tree-top level. The store's own commit is the dreamer's.
- The running plugin in this machine's sessions is still the cached 6.5.1 until
  `/reload-plugins` or a new session; the old Stop hooks fire in their old form until then.

## Decided, and why - do not reopen

- **The decision review is silent on commits and pushes everywhere, this repo included.** User
  decision 2026-09-04 after the walk. A release from this repo gets its walk only via `/goal` or
  by asking for `process-review-uncertain-decisions`.
- **The tooling-detour nudge is non-blocking and speaks once per session.** The user may have
  asked for the fix, and a nudge that repeats gets ignored; priced with every firing classified,
  it would speak in 34 of the last three weeks' 379 work sessions.
- **The room test is structural.** A dream room is the marketplace whose `marketplace.json`
  names the marketplace two levels above `CLAUDE_PLUGIN_ROOT`, or the memory store, or any cwd
  under `dream_mode` auto. A repo that merely ships its own usage skill is ordinary work: the
  corpus showed the marketplace.json-anywhere test flagging tool repos.
- **The handover records lessons; it does not capture them.** Step 1 of the procedure was the
  measured bridge from every handover into the memory engine and from there into a plugin fix.

## Decided against, and why

- Re-arming the decision review on pushes from inside the plugin repo: the same session's
  measurement put 227 of the walk's episodes on the road to the memory store, and a second room
  test in a second hook buys a walk the user can request by name.
- Building the measurement classifier as a jig now: queued (`contrib_queue`), because this
  session was at 618k tokens and the whole point of the change was to stop shipping tooling at
  the end of a session.

## Still open, untouched

Eighteen items in `OPEN-WORK.md`, ranked; item 125 is new and names the re-measurement.

## Lessons for the next nap

- When a Stop hook prescribes a procedure at the end of a work session, the first step of that
  procedure that reaches a tool is where the spiral starts: measured chain hook -> skill ->
  capture -> engine -> fix -> release, from a project that had nothing to do with the tool.
- When pricing a guard whose predicate keys on a PATH, replay it with `guard_replay.py --field
  file_path`; a content replay measures the wrong question and reports a confident rate.
- When classifying corpus firings into shape buckets, test the body-write shape BEFORE the
  redirect shape; the other order labels heredoc edits as redirects and hides what fired.
- When a Bash-tool path scanner is written on POSIX, include the drive-letter form
  (`[A-Za-z]:[\/]`): three tests green on Linux were red on the windows-latest cell.
- tooling: the session that ships a hook still runs the CACHED older copy; three Stop hooks
  fired in their old form on the very session that replaced them. Reload before judging a hook
  change by what fires.
- A repo is a marketplace the moment it ships a skill; the plugin's SOURCE is the one whose
  `marketplace.json` names the running marketplace, and nothing else counts as a dream room.

## The exact next action

`OPEN-WORK.md` item 10, as before - it is still the top-ranked USER item and the eight confirmed
findings are still unfixed. The user's steer from this session applies to how it is worked, not
whether: it is this repo's own work, done from this repo.

## Files that matter

- `OPEN-WORK.md` - the backlog.
- `plugins/bitranox/hooks/tooling-detour-nudge.py`, `plugins/bitranox/hooks/session-start.py`
  (`dream_room`), `plugins/bitranox/hooks/decision-review-nudge.py` - the three hooks this
  session changed.
- `plugins/bitranox/skills/meta-context-watcher/SKILL.md` - the procedure this file follows.
- `CHANGELOG.md` 6.6.0 to 6.9.1 - the measurements behind each lever, with their numbers.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

`repo-gate: all checks passed`; 4757 passed / 13 skipped / 1 xfailed at `fb54472`, plus one test
at `353f6b8`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
