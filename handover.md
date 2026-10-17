# Handover 2026-10-17: [23] steps 1-3 (bmk group) done, 9.2.4 and bmk 3.21.4 shipped

## In flight

- Nothing part-done. No subagents or background jobs are running. Both temporary worktrees
  (`bitranox-skills-wt-fold23-bmk`, `bmk-wt-fold23`) and their branches are removed.

## Committed, or not

- Pushed, CI green: bitranox-skills 9.2.3 (`ac494793`) and 9.2.4 (`ea6b8170`); bmk 3.21.3
  (`9ecf0fa`) and 3.21.4 (`8006727`). bmk was pushed, NOT released (no tag, no PyPI), the same as
  3.17.1, its earlier skill-only bump.
- Memory store (`<softdev-root>/.claude-memory`): still uncommitted. Besides the prior sessions'
  changes it now holds three shortened pointers (`remote-powershell-file-not-inline`,
  `memory-store-local-git-durability`,
  `feedback-a-recorded-review-verdict-goes-stale-when-the-reviewer-posts-again`; hooks and titles
  only, bodies untouched). The next dream commits it, staging deliberately.
- This handover and `OPEN-WORK.md` are committed together.

## Decided, and why - do not reopen

- User 2026-10-17, verbatim label "bmk first (Recommended)": only bitranox/bmk this round; pwshpy
  and btx_lib_mail were NOT to be pushed (logged in `EXECUTION-USER-REVIEW.md`).
- `devops-bmk` folds were checked against bmk's source, not the fact bodies. Three body claims were
  stale or wrong, and the skill follows the source: the "gave up" line comes from `bmk_toollock`'s
  skipped upgrade (`--on-timeout skip`), so the target continues; `make testintegration` exits 2
  (make) with bmk's `exit code: 5` line; bmk's `-m integration` is fixed, so an uncollected
  integration suite is diagnosed with `pytest --collect-only -m integration`.
- "Serialize all bmk-local commands across repos" was NOT folded: the tool-env lock and the
  per-venv provisioning lock make it obsolete, and the skill already says a caller-side lock is
  worse.
- A mirrored-skill change on both sides is committed with the twin text temporarily copied into
  the OTHER repo's main checkout working tree, and pushed after a `git merge --ff-only <branch>` in
  the tool repo's main checkout: the push gate reads that checkout's HEAD, never a worktree branch.

## Still open, untouched

- [23] step 3a, the next action below; 3b (pwshpy, btx_lib_mail) needs a new approval; 3c
  provmm-benchmark (private Gitea). [12] waits for decide rows (earliest ~2026-10-18). [26] and
  the rest: `OPEN-WORK.md`.

## Lessons for the next nap

- When folding a memory rule into a skill, grep the user's local commands and skills
  (`~/.claude/commands/`, `~/.claude/skills/`) for the same topic first: `tfbpr.md` already held
  the measured make-exits-2 detail that the fold got wrong and shipped once.
- When a fact body describes a tool's behaviour, re-check it against the tool's CURRENT source
  before folding it: 3 of 6 bmk bodies were stale (lock message, exit code, marker expression).
- When a verifier reports a gap you are about to decline, check the claim against the source first:
  the declined "tests exist but none collected" case was a real defect in the text.
- tooling: `repo-gate --mirrors` lists a tool repo's own linked worktree as an UNLISTED twin;
  harmless, but it reads like a missing `MIRRORED_SKILLS` entry.
- Carried over, not napped yet: the five lessons in `git show 6cdee6d3:handover.md`, and the
  ones that file itself carries over (`2d056f71`, `6c1370ea`).

## The exact next action

[12] is blocked until ~2026-10-18, so [23] step 3a. The user first runs
`/plugin marketplace update bitranox-skills` and `/reload-plugins` so 9.2.4 is installed. Then:

1. Quote-check each of the 6 bmk rules against the INSTALLED
   `~/.claude/plugins/cache/bitranox-skills/bitranox/9.2.4/skills/devops-bmk/SKILL.md`
   (substring-checked quotes).
2. Re-point the 14 citing facts: in each, replace `[[<one of the 6 slugs>]]` with
   `bitranox:devops-bmk` through `factedit.py apply --body-file` (strip leading newlines, see the
   tooling lesson in `6cdee6d3`); each body diff must be the ref lines only. Find them with
   `find <softdev-root>/.claude-memory/facts -name '*.md' -print0 | xargs -0 grep -l -F '[[<slug>]]'`.
3. Archive the 6 with `reconcile_memory_index.py --archive <slug> <softdev-root>` (home
   `skills/meta-self-improve/`), after a backup tgz.

The 6 slugs: `reference-bmk-make-test-can-lie-via-a-concurrent-uv-reinstall-race-on-bmks-shared-tool-venv`,
`reference-bmk-deps-fails-push-on-an-outdated-floor-and-hides-why`,
`project-a-stale-project-venv-makes-the-bmk-gate-lie`,
`reference-multi-repo-bmk-release-serialize-local-gates-overlap-remote-ci-watches`,
`reference-bmk-test-lanes-marker-model-cross-version-coverage-and-the-project-venv`,
`reference-bmk-make-release-can-succeed-after-printing-that-it-gave-up-on-the-lock`.
`project-tfbpr-local-run-gotchas` and `reference-ghrunner-linux-tools-...` cite the multi-repo one,
which also covers the tfbpr test-lane order (`~/.claude/commands/tfbpr.md` holds it).

## Files that matter

- `OPEN-WORK.md` ([23] carries step-by-step state and the 3a/3b/3c split)
- `plugins/bitranox/skills/devops-bmk/SKILL.md`, its `.skillwriter/checklist-20261017-fold23.md`
- `.plan/fold-23/` (rows, reach, step-6 evidence, backups)
- `EXECUTION-USER-REVIEW.md` (the "Step 3 push" decision)

## How to verify

- CI: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`) here and in
  `projects/public/apps/utils/bmk`.
- Twins: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` reports 0 drifted.
- Memory tree: `reconcile_memory_index.py --check-tree <softdev-root>` reports TOTAL 1 (the known
  rct-bose sideways ref, [590]).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
