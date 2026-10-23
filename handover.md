# Handover 2026-10-23: [500] guard shipped (9.14.0), [28] site B shipped (9.15.0); [23] batch 4 next

## In flight

- Nothing part-done. No subagent, workflow or background job of this session is running, and both
  worktrees of this session (`bitranox-skills-wt-500`, `bitranox-skills-wt-jigjev`) are merged and
  removed.
- `classifier_jig_repetition = shadow` is set in this machine's memory config. It collects only in
  sessions running 9.15.0 or later: the user still has to run `/plugin marketplace update
  bitranox-skills` and `/reload-plugins`.

## Committed, or not

- Pushed this session: babc091d (9.14.0, [500] second rule in block-git-semicolon-chain) and
  7bce5e8b (9.15.0, Jev shadow site `jig_repetition`). CI and the release workflows passed on both.
- This commit: this file and `OPEN-WORK.md` ([28] next step after the knob was set).
- Gitignored, clone-local: `EXECUTION-USER-REVIEW.md` holds today's user decisions ([28] site B,
  [500] narrow arm and its re-confirmation at 211 firings) and two autonomous ones (the [500] rule
  lives inside the existing hook; site B's shape).
- Measurement artifacts, gitignored: `.plan/500-guard-2026-10-23/`.

## Decided, and why - do not reopen

- [500]: the user chose "Block narrow arm (Recommended)", then re-confirmed "Block as built
  (Recommended)" after the built rule replayed at 211 firings in 30 days, not the 95 first counted.
  Widening to cd/cat/printf/sed steps (at least 1,172 firings) was rejected; limiting to scripts with
  assert/raise/exit was measured (187 of 211) and is not worth it.
- [500] is a second rule inside `block-git-semicolon-chain.py`, not a new hook: it reuses the walk
  and exemptions that were priced, and avoids another process per Bash call.
- [28] site B: shadow on fired nudges only, the nudge's own same-job question over
  `{new_script, ledger}`, no decide mode, eval threshold 0.5 as a reading point. Every row is a
  nudge the filter showed, so its [96] evidence must be a blind review of Jev's not-same-job rows.

## Still open, untouched

- [23] batch 4, [28] C or D (after B collects), [96], [680], [690] (hooks reference reads
  STRUCTURAL upstream), the rest: `OPEN-WORK.md`.
- From the bmk-b3 session's handover, waiting on the user there: two memory-fact rewrites (the
  sibling-calls fact's hook, one line in the wrong-repo fact).

## Lessons for the next nap

- When pricing a narrower guard variant, replay its own predicate: filtering another predicate's
  labelled firings undercounts, because a label records one reason a command fired (95 vs 211 for
  [500]). Queued against meta-claude-hooks.
- When a negative test asserts a word is absent from a whole doc row, assert on the one cell
  instead: the row may name the word to deny it ("There is no `decide` mode").
- tooling: the meta-claude-hooks freshness check reports STRUCTURAL without naming which events
  moved; filed as [690].
- Carried from earlier handovers (not yet napped):
  - When a script filters a backlog's template row, match the template's exact line, not a
    substring such as `YYYY`; compare the count against the SessionStart count.
  - tooling: when replaying a transcript-reading PreToolUse hook, cut the transcript at the call
    first; the guard reads only the last 4 MB.
  - When counting classifier shadow rows for a verdict, deduplicate by (transcript, message text)
    first: a rescanned subagent transcript is logged again.
  - When dispatching blind judges or any review-shaped agent, pass `effort: medium` with
    `model: opus`.
  - tooling: ci_wait needs `--timeout 2400` or more here; this repo's CI ran about 35 minutes today.
  - tooling: switching a classifier knob to a mode a newer plugin adds leaves older sessions on the
    old behaviour with no log; queued against meta-memory-settings.
  - When you are working IN the repo that owns a bitranox tool and find it broken, fix it in its
    own worktree; the queue-the-symptom rule covers only a tool met while working elsewhere.
  - When a backlog item waits on the user, re-measure its premise before asking.
  - When a GitHub head_sha-filtered run listing goes empty mid-wait, the runs still exist: read
    them by id.
  - tooling: the question-premises gate refuses the first AskUserQuestion each time; mark
    unmeasured premises "unverified" in the option text before the first send.
  - When reusing an earlier round's workflow script, re-check its model and effort pins first.
  - When a review subagent's "Skill gaps" names a count in a lead-in, check whether your own edit
    changed what it counts.
  - When `factedit check` is the validator, read its advisories, not its exit code.
  - When measuring a subagent's output by effort, use the notification's subagent_tokens minus the
    transcript input.
  - When a /goal's pre-registered threshold misses but the arms do not overlap, decide on what the
    plan rests on, and record the weaker reading and the miss.
  - When a user answers an AskUserQuestion without reading it and asks again, the superseding
    answer governs; log both.
  - tooling: `repo-gate.py --mirrors` counts a tool repo's linked worktrees as UNLISTED twins.
  - tooling: the auto-mode classifier refused a subagent's Bash edit of plugin.json; keep version
    bumps in the controller.
  - When a rule depends on what an OMITTED subagent field inherits, read `~/.claude/settings.json`
    first and probe the override.
  - When an OPEN-WORK line carries several dated segments, the latest segment's "next:" is current.
  - When a handover's next action names counts, recount them from the cited data first.
  - When a mirrored skill's text carries a package version floor, check every pin of that floor
    (`jev_shadow.py` JEV_JUDGE_FLOOR); run `repo-gate.py --ci` before pushing.
  - tooling: bmk's floor-pin reconcile drops a hand-written `exclude-newer-package` timestamp once
    the floor is older than the cooldown.
  - When a PreToolUse gate refuses a git command, stage or fetch in a separate earlier command.

## The exact next action

[23] is the top-ranked open item; its next step is Phase 3 batch 4: open
`~/.claude/plans/curried-mapping-dolphin.md`, pick the next lower level group after the
bitranox-skills/KI levels, classify its FOLD rows read-only (reach + skeptic lens, as batch 3 did
in `.plan/fold-23/batch3/`), and put the batch to the user before folding anything. A tree dream
(due per the SessionStart nudge) would also add a dream-placement run for [96].

## Files that matter

- `plugins/bitranox/hooks/block-git-semicolon-chain.py` - `git_after_script`, its docstring figures.
- `plugins/bitranox/hooks/jig-repetition-nudge.py` - `shadow_request`, `_shadow`.
- `plugins/bitranox/hooks/classifier.py` - `jig_repetition_questions`, `SITES`, `SITE_THRESHOLDS`.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `summarize_jig_repetition`.
- `OPEN-WORK.md` lines [23], [28], [96], [680], [690].

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- Both releases on origin: `git merge-base --is-ancestor 7bce5e8b origin/master`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD --timeout 2700`
  (bitranox:compuse-toolbox).
- Site B data, once 9.15.0 runs: `python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report`
  and read the `jig_repetition` block.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
