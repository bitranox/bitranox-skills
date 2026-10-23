# STALE - read 2026-10-23, work continued

## In flight

- Nothing part-done. No subagent, workflow or background job is running. The worktree
  `bitranox-skills-wt-subagent-decide` is merged and removed. `bitranox-skills-wt-pwshpy16`
  (feat/pwshpy-1.6-skill-mirror) belongs to another session; leave it alone.
- 9.12.0 is installed here (`/plugin marketplace update` + `/reload-plugins` done 2026-10-23).
  Other open sessions on an older plugin read `classifier_subagent_signal = decide` but have no
  decide path: they keep buffering on all patterns and log no row until they reload.

## Committed, or not

- Pushed this session: 6344b89d (9.12.0, subagent-capture decide mode); its ci and release runs
  passed; tag v9.12.0, GitHub release and PyPI 9.12.0 all present.
- This commit: this file and `OPEN-WORK.md` ([28] line).
- Not in any repo: `~/.claude/commands/tfbpr.md` Step 10 gained a stuck-runner branch
  (force-cancel endpoint, `rerun --failed`) and Step 12 a note that ci_wait has no `--workflow`
  flag; the file is untracked and live. The lsdsk queue entry for it is shipped.
- Gitignored evidence: `.plan/jev-28/clause5-2026-10-22/` (stats.py, score.py, key.json, the
  three judges' labels, the blind packets).

## Decided, and why - do not reopen

- [96]'s rule was applied to the subagent_signal site (written for the skill sites; the user said
  go ahead). All five clauses pass; clause 5 by a blind three-judge review of all 30
  disagreements: patterns wrong 24, Jev wrong 6.
- Decide design, user's choice "Build Jev decide (Recommended)" (EXECUTION-USER-REVIEW.md): Jev
  decides every answered message at 0.8 on either question; unanswered or capped messages fall
  back to the STRICT patterns only, never broad. A strict match Jev scores low is not buffered.
- Shadow rows are re-logged per transcript rescan: deduplicate by (transcript, text) before any
  count (992 of 7,698 rows were repeats).

## Still open, untouched

- [23] batch 4, [500] corpus replay, [570] hit-16 adjudication, the rest: `OPEN-WORK.md`.
- [28]: the next site (B, C or D) is a question for the user.

## Lessons for the next nap

- When a script filters a backlog's template row, match the template's exact line, not a
  substring such as `YYYY`: a real item quoting `jev-skill-shadow-YYYY-MM.jsonl` vanished from a
  summary; compare the count against the SessionStart count.
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
in `.plan/fold-23/batch3/`), and put the batch to the user before folding anything. [28]'s
question (B, C or D next) can be asked in the same turn, one decision at a time.

## Files that matter

- `plugins/bitranox/hooks/subagent-capture.py` - `_decide`, `_ask`, `_jev_families`, `_hit`.
- `plugins/bitranox/hooks/tests/test_subagent_capture_decide.py` - the decide contract.
- `plugins/bitranox/skills/meta-memory-settings/SKILL.md` - the `classifier_subagent_signal` row;
  review artifact `.skillwriter/checklist-20261022-subagent-signal-decide.md`.
- `OPEN-WORK.md` lines [23], [28], [500], [570].

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- The feature on origin: `git merge-base --is-ancestor 6344b89d origin/master`.
- Decide live: the newest `subagent_signal` rows in
  `~/.claude/self-improve-audit/classifier-shadow-<date>.jsonl` carry `"mode": "decide"`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD --timeout 2400`
  (bitranox:compuse-toolbox).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
