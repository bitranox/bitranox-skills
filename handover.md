# Handover - 2026-09-27 early, rank 10 guard slice fixed as 7.25.10 + 7.25.11, CI green

## In flight

Nothing. The old rank 10 guard slice (38 claims from the 2026-08-28 review) and its 5 coverage
gaps were re-adjudicated against 7.25.9, triaged into batches A-D, and all four batches were fixed
on the user's choice ("All, A to D") by 8 test-first fixers: 7.25.10 (0094ea68). The windows-latest
cell then failed on a store-edit-guard regression (CRLF, see lessons), fixed as 7.25.11 (a76f068e).
CI green on a76f068e in both workflows.

## Committed, or not

- **In git and pushed:** everything above, the CHANGELOG entries for 7.25.10 and 7.25.11, the
  corrected CLAUDE.md lxml note, OPEN-WORK rank 10 progress and the new FOUND line at rank 183.
- **Not in git, by design (gitignored, main checkout):** `.plan/rank10-guardreadj-2026-09-26/` -
  `TRIAGE.md` (batches A-D) and `verdicts/*.verdicts.txt` (the 8 adjudications, verbatim).
- **The main checkout is still 120+ commits behind origin/master** and has `PLAN-JEV-SKILL.md` and
  `TODO-JEV.md` staged by another session; left alone. Work from a worktree created off
  `origin/master` explicitly.

## Decided, and why - do not reopen

- block-pgrep: the bracket-leak haystack is now the RAW command (heredoc bodies and commit
  messages count), because `bash -c` receives the whole string and `pgrep -f` matches it. Gated on
  a replay over 88.5k real commands: 1 false positive removed, 3 real self-matches newly caught.
- block-pgrep: `grep "pkill -f x"` still blocks; grep is not in `shell_text._DATA_SINK_PROGRAMS`
  and adding it changes every guard at once (filed under 183).
- probe-capability-gate: "Do not use tools that <verb>" stays a DENY (a wrong allow is the silent
  direction); only its message changed, naming the spelling that passes.
- subagent-model-gate: a project agent definition shadows a user one of the same name; `inherit`
  or blank counts as unpinned; bare names do not resolve to plugin agents.
- validate-structured-files: the `{{` lookahead is narrower than the adjudicator prescribed,
  because the prescribed one false-blocked Helm `{{ "foo" | quote }}`.

## Decided against, and why

- Removing NotebookEdit from the matchers: the guards now read `notebook_path` instead
  (store-edit, skill-edit, config-edit, validate); the other NotebookEdit-matched hooks are in 183.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): only "about 7 reports named only in passing" is left.
- Rank 177 (FOUND, blocked on the user): 16 design decisions from the 7.25.6 LOW fixers.
- Rank 182 and 183 (FOUND): what the 7.25.9 and 7.25.10 fixers noticed and left.
- Ranks 160, 175, 181 unchanged.

## Lessons for the next nap

- When replacing a text-mode read (`read_text`, `open(..., "r")`) with `read_bytes().decode`,
  restore newline normalisation: universal-newline translation is lost and a CRLF file stops
  matching the LF text the tools hand a hook (7.25.10 went red on windows-latest only).
- When a background watcher (ci_wait) runs with its cwd inside a worktree, do not remove that
  worktree until it finishes; gh then fails every poll and the watcher reads as a CI failure.
  Launch watchers from the main checkout.
- When fanning fixers out into worktrees in bitranox-skills, commit the version bump and a
  CHANGELOG stub on an integration base first and branch the worktrees from it: the local
  `check_version_bumped` refuses a `plugins/` commit whose version equals origin/master's.
- `pgrep -f` matches text inside a heredoc body or a commit message in the same command, because
  `bash -c` carries the whole command string in its /proc cmdline (measured by the pgrep fixer).
- tooling: guard_replay reports one predicate's rate; diffing the FIRING SETS of an old and a new
  predicate took a hand-written script. A `--baseline <module>` option would make that the jig.
- Carried from the 2026-09-26 handover, in case its nap never ran: take a subagent's handback
  from the tool_use input, not the last long text; Agent `isolation: worktree` bases on the main
  checkout's stale HEAD, so create worktrees from origin/master yourself; when a fix changes a
  shared parser, have the fixer run every consumer's suite; tooling: ci_wait backgrounded inside
  a compound command is refused by block-masked-gate-exit, background it alone;
  `~/.claude/settings.json` was rewritten 2026-09-26 22:34:50 by an unidentified writer.

## The exact next action

Rank 10 is still the top open USER item. Find the "about 7 reports named only in passing" in the
main checkout's `.plan/rank10-review-2026-08-28/TRIAGE.md` (search for the reports it mentions
without adjudicating), list them, re-check each against current master with a control, then ask
the user what to fix. The user is usually present, so put the rank 177 decisions to them one at a
time as well.

## Files that matter

- `OPEN-WORK.md` ranks 10, 177, 182, 183.
- `.plan/rank10-review-2026-08-28/TRIAGE.md` and `.plan/rank10-guardreadj-2026-09-26/` (main
  checkout, gitignored).
- `CHANGELOG.md` `## [7.25.10]` and `## [7.25.11]`.

## How to verify this still stands

- `git show origin/master:plugins/bitranox/.claude-plugin/plugin.json | grep version` prints
  7.25.11 or later.
- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha a76f068eecf4fe04bee8c05f0890c9eee504a5fc`
  reports `workflow=success ci=success`.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
