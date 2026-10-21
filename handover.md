# Handover 2026-10-21 (3): [29] shipped as 9.11.0 (review dispatches on opus at effort medium); [23] hook cut next

## In flight

- Nothing part-done. No subagent, workflow or worktree is running or left over (both [29]
  worktrees removed, branches deleted).
- bitranox-skills 9.11.0 is installed and reloaded in the user's session; the review warning was
  seen live (a "Review Task 1" opus dispatch with no effort warned, the same with effort medium did
  not).

## Committed, or not

- This commit: `OPEN-WORK.md` ([23] `next:` now says quote-check against the installed 9.11.0, not
  9.10.3) and this handover.
- Gitignored: `EXECUTION-USER-REVIEW.md` holds this session's decisions (user section: scope,
  enforcement, effort medium, haiku warn kept; autonomous section: the headless probe that missed
  its 3x bar, the haiku warning). The [29] SDD ledger and review files were copied to the session
  scratch dir only and are not needed further.

## Decided, and why - do not reopen

- Review dispatches run at effort `medium`, not `low` (user, 2026-10-21 /goal, verbatim in
  `EXECUTION-USER-REVIEW.md`). `low` stays only on the haiku mechanical-scan row.
- subagent-model-gate keeps warning on a haiku dispatch that reads as a review (user re-asked and
  chose "Keep warning (Recommended)"; the first, unread answer "Skip haiku + effort low" is
  superseded). Its message tells a haiku mechanical scan to ignore it.
- Fixers, implementers, probes (any case for probe/baseline/pressure), final synthesis and the
  product name jev-judge are not review-shaped in the hook; a review sent as a fork warns.
- Shipped skill text carries no maintainer provenance (no directive dates, no "the user's default
  effort is high"); the dated `.skillwriter/` checklist titles are the repo convention and stay.

## Decided against, and why

- Fixing the four accepted hook Minors (doubled or >30-char bracket tags, bare "synth", a review
  word inside the tag): each only makes a warn-only hook silent; recorded in the re-review.

## Still open, untouched

- [23] hook cut for the 18 folded rows, then REACH-FAILS / SAFE / KEEP-SHORTENED / STAY rows: `OPEN-WORK.md`.
- [28], [335]: blocked on Jev shadow data. Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When measuring a subagent's output by effort, use the notification's subagent_tokens minus the
  transcript input: transcript usage.output_tokens is the message_start partial (8 every time) and
  thinking text is redacted to a signature. Use a prompt that must be computed, not recalled.
- When a /goal's pre-registered threshold misses but the arms do not overlap, decide on what the
  plan actually rests on, record the weaker reading and the miss in EXECUTION-USER-REVIEW.md.
- When a user answers an AskUserQuestion without reading it and asks again, the superseding answer
  governs; log both, the second marked as replacing the first.
- tooling: `repo-gate.py --mirrors` counts a tool repo's linked worktrees (apps/utils/pwshpy-wt-*)
  as UNLISTED twins and exits 1 though 0 of 12 pairs drifted (queued in contrib_queue).
- tooling: the auto-mode classifier refused a subagent's Bash edit of plugin.json ("Modify Shared
  Resources") and then a read-only grep ("Auto-Mode Bypass"); keep version bumps in the controller.
- Carried from earlier handovers (not yet napped):
  - When a rule depends on what an OMITTED subagent field inherits, read `~/.claude/settings.json`
    (effortLevel, modelSettings) first and probe the override before building on it.
  - When an OPEN-WORK line carries several dated segments, the latest segment's "Next:" is current
    and the `next:` field can be stale: fix the field whenever you touch the item.
  - When a handover's next action names counts, recount them from the cited data first: one said
    9 better owners and 18 partial rows, `merged.json` held 5 and 19.
  - When a mirrored skill's text carries a package version floor, check every pin of that floor
    first (the twin's metadata test, `jev_shadow.py`): a skill-only change then needs a package
    release, and the marketplace push has to be ordered around PyPI.
  - tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp for a
    package no declared floor needs; declare the floor (a CVE pin) and let bmk write the pin.
  - When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command:
    the gate judges the index as it was before the command ran.

## The exact next action

[23] is the top-ranked open item: in `.plan/fold-23/batch3/fold18/`, quote-check the 18 rows' GREEN
quotes against `~/.claude/plugins/cache/bitranox-skills/bitranox/9.11.0/skills` (adapt
`.plan/fold-23/batch3/quotecheck_installed.py`: set INST to 9.11.0, read `fold-result.json` here).
A quote 9.11.0 rewrote (review-dispatch lines) must be re-checked against the new text before its
fact is cut. Then cut each hook to <= 250 chars ending "Detail: bitranox:<skill>." with factedit.

## Files that matter

- `plugins/bitranox/skills/process-agents-subagent-driven-development/SKILL.md` - the canonical
  "Review dispatches" rule and the effort table.
- `plugins/bitranox/hooks/subagent-model-gate.py` - the review nudge (warn-only).
- `docs/plans/2026-10-21-review-dispatch-effort-plan.md` - the [29] plan as amended to medium.
- `.plan/fold-23/batch3/fold18/` (gitignored) - [23] batch-3b data: fold-result.json, qcheck.py.

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- `gh release view v9.11.0` resolves; `git rev-list -n1 v9.11.0` is cb4d0857, the [29] close commit.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
