# STALE - read 2026-10-23, work continued

## In flight

- Nothing part-done. No subagent, workflow or background job of this session is running; the
  worktree `bitranox-skills-wt-ciwait` is merged (b231f04e) and removed. The worktree
  `bitranox-skills-wt-pwshpy16` (feat/pwshpy-1.6-skill-mirror) belongs to another session; leave it.
- The bmk-b3 session shipped 9.13.0 (afec058c, sibling-ledger.py) and handed over. Two memory-fact
  rewrites from that work wait on the user there, not here: the sibling-calls fact's hook
  (reference-hooks-read-same-message-sibling-calls-from-the-transcript-by-message-id) and one line
  in the wrong-repo fact naming the guard's live-miss cause (siblings not yet in the transcript).

## Committed, or not

- Pushed this session: fabd3b2b and 3916e8fc (backlog), b231f04e (9.13.1, ci_wait). CI on
  b231f04e passed (ci and both release workflows).
- The tree-top memory store (pushed): 5d5b04f rewrote the wrong-repo
  fact. About 44 other uncommitted fact files there belong to other sessions; leave them.
- This commit: this file and `OPEN-WORK.md` ([680] added).

## Decided, and why - do not reopen

- [570], user chose "Apply all (Recommended)": hits 12 and 16 failed in a call with NO cd of its
  own (transcripts 86506c66, e3f9c303); 4 parallel probe rounds with a leading absolute cd per call
  never crossed. A leading `cd /abs &&` is a valid target. A sibling project's contrib entry (never
  accept a leading cd) was dropped as disproven.
- [96], user chose "Wait for 3 runs": the >= 3 runs floor gates the rewrite-once branch too, so
  dream-placement (140 paired, 1 run) is not rewritten yet. Only meta-dream-tree step 5 adds runs.
- ci_wait: a run reading `queued` is not stuck while any of its jobs started or its jobs cannot be
  read; the job list is read only after the grace.

## Still open, untouched

- [23] batch 4, [28] question (B, C or D), [500] replay, [680] replay-priced guard docstrings, the
  rest: `OPEN-WORK.md`.

## Lessons for the next nap

- When a script filters a backlog's template row, match the template's exact line, not a
  substring such as `YYYY`: a real item quoting `jev-skill-shadow-YYYY-MM.jsonl` vanished from a
  summary twice (2026-10-22, 2026-10-23); compare the count against the SessionStart count.
  Queued against meta-context-watcher.
- tooling: when replaying a transcript-reading PreToolUse hook (transcript_siblings), cut the
  transcript at the call first (`head -n <line of the tool_use id>`): the guard reads only the last
  4 MB, so a grown transcript passes falsely; even a cut one shows siblings the live hook could
  not see before 9.13.0.
- When counting classifier shadow rows for a verdict, deduplicate by (transcript, message text)
  first: a rescanned subagent transcript is logged again.
- When dispatching blind judges or any review-shaped agent, pass `effort: medium` with
  `model: opus`; the gate warns only after the dispatch.
- tooling: ci_wait's 1500 s default is shorter than this repo's ci run (24 m 51 s on 6344b89d);
  pass `--timeout 2400` here until the queued fix lands.
- tooling: switching a classifier knob to a mode a newer plugin adds leaves older sessions on the
  old behaviour with no log; queued against meta-memory-settings.
- Carried from earlier handovers (not yet napped):
  - When you are working IN the repo that owns a bitranox tool and find it broken, fix it in its
    own worktree; the queue-the-symptom rule covers only a tool met while working elsewhere.
  - When a backlog item waits on the user, re-measure its premise before asking.
  - When a GitHub head_sha-filtered run listing goes empty mid-wait, the runs still exist: read
    them by id.
  - tooling: the question-premises gate refuses the first AskUserQuestion each time; mark
    unmeasured premises "unverified" in the option text before the first send.
  - When reusing an earlier round's workflow script, re-check its model and effort pins against
    the current rules first.
  - When a review subagent's "Skill gaps" names a count in a lead-in, check whether your own edit
    changed what it counts.
  - When `factedit check` is the validator, read its advisories, not its exit code.
  - When measuring a subagent's output by effort, use the notification's subagent_tokens minus the
    transcript input: transcript usage.output_tokens is the message_start partial.
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
in `.plan/fold-23/batch3/`), and put the batch to the user before folding anything. Ask [28]'s
question (B, C or D next) in a separate turn. A tree dream (due per the SessionStart nudge) would
also add a dream-placement run for [96].

## Files that matter

- `plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py` - `_stuck_queued`, `gh_run_started`.
- `plugins/bitranox/hooks/block-write-after-sibling-cd.py`,
  `plugins/bitranox/hooks/block-commit-beside-sibling-gate.py` - the docstring figures in [680].
- `OPEN-WORK.md` lines [23], [28], [96], [500], [680].

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- 9.13.1 on origin: `git merge-base --is-ancestor b231f04e origin/master`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD --timeout 2400`
  (bitranox:compuse-toolbox).
- [96] data: `python3 plugins/bitranox/skills/meta-self-improve/jev_shadow.py report`.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
