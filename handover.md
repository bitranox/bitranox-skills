# Handover 2026-10-20: [28] site A shipped (9.10.0, subagent_signal shadow), next [23] Phase 3

## In flight

- Nothing part-done. No subagent, workflow or background job is running.
- Worktree `.claude/worktrees/jev-subagent-signal` (branch `jev-subagent-signal`) is fully pushed:
  its HEAD equals origin/master after the fast-forward to the peer's 9.10.1. Remove it with
  `git worktree remove .claude/worktrees/jev-subagent-signal` and `git branch -d jev-subagent-signal`.

## Committed, or not

- bitranox-skills 9.10.0 (`602a8ca0`, the `subagent_signal` shadow site) is on origin/master.
  CI on `8127a9a0` (9.10.1, a peer session's Windows test fix stacked on top) concluded success.
- `~/.claude/.bitranox-memory.json` now has `classifier_subagent_signal = shadow`. It acts only in
  sessions running 9.10.0 or later (`/plugin marketplace update bitranox-skills`, then `/reload-plugins`).
- `~/.claude/settings.json` has `"idleCompaction": false` (the user's request this session).
- This commit carries `OPEN-WORK.md` ([28] progress, new [335]) and this file.
- `.plan/jev-28/` (gitignored) holds the 30-day sizing script and its result `size30b.json`.
- `EXECUTION-USER-REVIEW.md` (gitignored) holds the [28] site choice verbatim.

## Decided, and why - do not reopen

- [28]: the user chose site A, "A subagent capture (Recommended)": a Jev SHADOW of
  subagent-capture.py that changes no behaviour. So [335] (broad patterns blocking the Stop) is NOT
  fixed yet on purpose: it waits for the shadow's data.
- The site asks the Stop gate's two reply questions verbatim (self_admission, realization), never
  the user-message families: a subagent's user-role text is the parent's dispatch brief.
- Shadow sends EVERY assistant message (last 12), not only the buffered ones, so the log can show
  misses as well as broad-only noise.

## Decided against, and why

- A duplicate fix for `test_cli_preserves_the_file_mode` (Windows): a peer pushed 9.10.1 first.

## Still open, untouched

- [23] (2b), (2c) and batch 1 (c): see the `[23]` line in `OPEN-WORK.md`.
- [28] next steps and [335]: see their lines.
- Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a backlog line says something was "never named" or "never done", grep the design docs
  before relaying it: [28] said the six second-wave sites were never named, and
  docs/jev-design.md's "Second wave" table names all six.
- (recurrence of feedback-verify-a-hand-rolled-detector-against-a-known-negative) When a replay
  counts a hook firing on every input (2,607 of 2,607), read the predicate's return contract first:
  one `assess` returned a tuple (always truthy), another fires on every dispatch by design.
- (recurrence of reference-redcheck-inherited-coverage-can-be-a-false-positive) redcheck flagged a
  RED as inherited on generic shared terms (classifier, judge, settings); a grep for the new knob
  name in the named docs and the facts returned 0, so the RED stood and failed honestly.
- (recurrence of feedback-two-sessions-on-one-host-coordinate) When CI is red on a shared repo, fetch
  and compare origin/master before writing a fix: a peer had already pushed the same fix as 9.10.1.
- tooling: settings.py accepts ANY value for a knob in DEFAULT_CONFIG that its choices table does
  not list, so a new knob silently takes `decide` until the table names it (caught by a test).

## The exact next action

`[23]` is the top-ranked open item ([28] now waits on shadow data). Start Phase 3's next level
group: take the FOLD-UNCHECKED rows of the bitranox-skills and KI levels from
`.plan/fold-23/rows.json` (main checkout), copy the batch-2 workflows (reach + skeptic, then
scenario/RED/edit/GREEN) and their input builders from
`~/.claude/projects/-media-srv-main-softdev-projects-public-KI-bitranox-skills/a03de64b-f570-4dce-96b1-bdc8920fc6df/workflows/scripts/`,
run reach + skeptic, and put the surviving batch to the user as ONE question before any edit.

## Files that matter

- `OPEN-WORK.md` (`[23]`, `[28]`, `[335]` lines)
- `plugins/bitranox/hooks/subagent-capture.py` (`shadow_request`, `_shadow`),
  `plugins/bitranox/hooks/classifier.py` (`subagent_signal_questions`, `SITES`, `SITE_THRESHOLDS`),
  `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` (`summarize_subagent_signal`)
- `docs/jev-design.md` ("Second wave" table: the six design-listed sites, B and D among them)
- `.plan/jev-28/size30b.json`, `.plan/fold-23/rows.json`

## How to verify

- The site's rows: `python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report`
  shows a `subagent_signal` section once 9.10.0 sessions have finished subagents (hand-run probe rows
  use session ids starting `probe-` and are excluded by default).
- CI on HEAD: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`); `8127a9a0` was green.
- Settings: `python3 plugins/bitranox/skills/meta-memory-settings/settings.py view | grep subagent`.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
