# Handover - 2026-10-08 11:50, [14] shipped as 8.5.0 (CI green), [17] identified and probed (awaits the user's pick)

## In flight

- Nothing is running. 8.5.0 (2244924a) is on origin/master with CI green on every workflow,
  windows-latest included (ci_wait exit 0 at 11:48).
- [17] is part-done: the feature is identified and probed, and the user was asked which use to
  build first. No answer yet. The recommendation was (1), a backlog/status band or pane.
- Other sessions own other items right now: the jev-shadow session owns [12] (step 6 waits until
  about 2026-10-13); another session is working [16] (/tmp cleanup). Do not start either here.

## Committed, or not

- Committed and pushed: 8.5.0 (skill-router decides a failed background command's notification,
  [14] closed with its measurement, the meta-memory-settings row and docs/reference.md, the
  skill-writer checklist).
- Committed with this handover: OPEN-WORK [17] gains the probe findings and its next action.
- Not in git: the probe mod, the notification tally script and the blind-panel packets lived in
  the session scratchpad and are gone with it; the measurement itself is recorded on the [14] line.
- The worktree `.claude/worktrees/notify-decide-failed` (branch `notify-decide-failed`) holds
  nothing that is not on origin; remove it (CI is green).

## Decided, and why - do not reopen

- [14]: decide mode covers FAILED BACKGROUND COMMANDS only (user's choice, 2026-10-08). Jev picked
  a skill on 73 of 77 of them, the keyword match on none; a silent Jev nudges nothing there.
  Cost was ruled out as an argument by the user ($0.042 per million input tokens); latency is
  p50 0.53 s, capped at the 1.5 s deadline.
- Every other notification kind stays nudged as with `off` and shadowed: 3 blind judges rated 4 of
  Jev's 29 picks there helpful, 25 neutral, and named no helpful skill on 98 sampled notifications
  (no planted positive control - "no benefit found", not "none possible").
- A failed background command is recognised by status `failed` plus a summary opening
  `Background command ` (`prompt_text.failed_background_command`): the envelope has no kind field.
- [17]: a user mod CANNOT reach prompt.compose/section/context, attribution.text or any classic.*
  event on build 2.1.290 (skipped by the prepend-tier cc-plugin-sec-default), so no system-prompt
  or attribution rewrite and no wrapping of the Python hooks.

## Decided against, and why

- Porting the Python guards to tool.call mods: a rewrite of heavily tested code onto an API the
  docs call early access, for a latency gain on hooks that are not the slow part.
- A fixed "failed command -> compuse-bash" rule instead of Jev: matches 87% but loses the specific
  picks (devops-bmk, compuse-git), and cost/latency do not argue for it.

## Still open, untouched

`OPEN-WORK.md` is the list: [12] (jev-shadow session), [16] (other session), [17] (user's pick),
[18] deferred by the user, [19] dirty worktrees and branches left to judge, [245] a locked agent
worktree, [390] copy the jev-shadow `.plan/` records out.

## Lessons for the next nap

- When a run, PR or job id is needed, take it from the listing's JSON in the same step: a typed
  run id returned HTTP 404 while the real one was in the output just above.
- When classifying a task notification's kind, match the summary's opening words: the word "agent"
  inside a background command's summary mislabelled 11 rows (captured as a reference fact).
- When a decision rests on a token count, convert it with the recorded price first: 15.5M Jev
  tokens is about $0.65 (fact feedback-labelling-a-parameter-assumed-..., recurrence 3).
- When a decide-mode cut is chosen from a shadow log, a blind panel over the NON-chosen kinds is
  cheap (two packets, 6 sonnet judges, about 2 minutes) and turns "probably not useful" into a
  measured answer.
- tooling: EnterWorktree on an existing path makes every later Bash call in the session pass the
  worktree-isolation guard (no `$VAR` arguments, no pipes into claude), and ExitWorktree is only
  for when the user asks - for a short change, prefer `git worktree add` plus absolute paths.
- tooling: `claude -p ... --allowedTools Read "prompt"` loses the prompt (variadic flag); put the
  prompt right after `-p`.
- Carried, not yet confirmed napped (from the 10:35 handover): raise `request_queue_size` on a
  ThreadingHTTPServer test fake (Windows WinError 10053); assert a concurrency bound, never a
  request count, under a deadline; reproduce Windows-only CI failures on the Windows dev box
  first; present a pre-registered panel that lands in no branch as post-hoc and record the user's
  choice; merge two simultaneous handovers rather than overwrite; reverse-apply a worktree diff
  onto an index read from origin/master to test containment; `git merge-tree --write-tree` proves
  a squash-merged branch landed; never `git add -N .` in another worktree; check the PREVIOUS
  commit's CI before investigating a red after your push; tooling: bump pyproject.toml with
  plugin.json; tooling: run pytest through a script in a worktree-isolated session.

## The exact next action

[17]: put the user's pick to them again - build (1) the
backlog/status band or pane, or another of the four options on the [17] line. [17] is the
top-ranked open item this session may take ([12] and [16] belong to other sessions).

## Files that matter

- `OPEN-WORK.md` ([14] closed with the measurement, [17] the probe findings and options)
- `plugins/bitranox/hooks/skill-router.py` (`_decides`, `_shadows`)
- `plugins/bitranox/hooks/prompt_text.py` (`failed_background_command`)
- `plugins/bitranox/hooks/tests/test_skill_router_decide.py` (failed-command and other-kind tests)

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha 2244924ae26bf68f47ff2fdb714fb2c87cf6a64d`
  exits 0 (every cell green, windows-latest included).
- `git log --oneline -3 origin/master` shows this handover commit on top of 2244924a.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
