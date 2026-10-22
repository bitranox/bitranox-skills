# Handover 2026-10-22 (evening): seven waiting items settled; 9.11.5 ci_wait fix, 9.11.6 dispatch-restriction rule

## In flight

- Nothing part-done. No subagent, workflow or background job is running. The two fix worktrees
  (`fix/ci-wait-vanished-runs`, `fix/sdd-dispatch-prohibition`) are merged into origin/master and
  removed. `bitranox-skills-wt-pwshpy16` (feat/pwshpy-1.6-skill-mirror) belongs to another
  session; leave it alone.
- The user has not yet installed 9.11.5/9.11.6 here: `/plugin marketplace update bitranox-skills`
  plus `/reload-plugins`.

## Committed, or not

- Pushed to origin/master this session: 9c88c053 (OPEN-WORK decisions, CLAUDE.md probe order),
  a07f0942 (9.11.5 ci_wait), 7c94630a (9.11.6 subagent-driven-development rule). bmk-e3's 9.11.4
  devops-bmk sync sits between them; it was theirs.
- Memory store (pushed): grep-shim fact, number-audit recurrence 11, table-pipe fact rewrite.
  The store also holds OTHER sessions' uncommitted edits (among them hit 16 in the wrong-repo
  fact); this session did not touch or commit them.
- Outside any repo: `~/.bashrc` gained `alias claude='claude --allowedTools Grep,Glob'` (backup
  `~/.bashrc.bak-2026-10-22`), user decision.
- This commit: this file only.

## Decided, and why - do not reopen

- [440] [460] [575] [610] [630] are closed in `OPEN-WORK.md`, each with the user's chosen option
  and a measured/argued tag; [500] and [570] carry the chosen next step in their lines.
- The grep shim's root switch is the launch flag `--allowedTools Grep,Glob`; `EMBEDDED_SEARCH_TOOLS`
  does nothing (probed 0/false/1) and a settings.json allow rule does not either (docs).
- The queued "scope the pathfinder queue rule" contribution was DROPPED, not fixed: the rule
  already limits queue-not-fix to a tool misbehaving while working on another project; queuing
  the ci_wait defect from inside bitranox-skills was a misapplication.
- ci_wait's fallback re-reads a vanished run by id (`gh run view`), not the unfiltered runs API:
  the by-id read cannot be pushed out of a `--limit` window, and a deleted run (404) is retried
  then reported, never silently dropped.

## Still open, untouched

- [23] batch 4, [500] corpus replay, [570] hit-16 adjudication, the rest: `OPEN-WORK.md`.
- [28], [335], [96]: blocked on Jev shadow data.

## Lessons for the next nap

- When you are working IN the repo that owns a bitranox tool and find it broken, fix it in its own
  worktree; the queue-the-symptom rule covers only a tool met while working on another project.
- When a backlog item waits on the user, re-measure its premise before asking: four of seven
  waiting items had moved (a guard shipped, a recurrence count stale, a contradicting incident
  appeared) since their lines were written.
- When a GitHub head_sha-filtered run listing goes empty mid-wait, the runs still exist: `gh run
  view <id>` and the unfiltered runs API had the completed run while `--commit` answered [].
- tooling: the question-premises gate refuses the first AskUserQuestion each time; mark unmeasured
  premises "unverified" in the option text before the first send to save the round.
- Carried from earlier handovers (not yet napped):
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
  - When an OPEN-WORK line carries several dated segments, the latest segment's "Next:" is current.
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
in `.plan/fold-23/batch3/`), and put the batch to the user before folding anything. If the user
prefers the two items they sent to further work first: [500] (write the predicate, replay with
guard_replay, bring the firing rate and a sample) or [570] (adjudicate hit 16 against its
transcript, wait for the peer's store edit to be committed).

## Files that matter

- `OPEN-WORK.md` lines [23], [500], [570] - the next steps, with what was measured.
- `plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py` - `keep_seen_runs`, `gh_run`.
- `plugins/bitranox/skills/process-agents-subagent-driven-development/SKILL.md` - File Handoffs,
  "A restriction you add beyond the brief"; its review artifact
  `.skillwriter/checklist-20261022-dispatch-restriction.md`.

## How to verify

- `git status --porcelain` in the repo: empty after this commit except gitignored files.
- Both fixes on origin: `git merge-base --is-ancestor 7c94630a origin/master`.
- CI for the commit carrying this file: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox).
- Grep shim off after a fresh interactive start from a shell: `declare -F grep` prints nothing.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
