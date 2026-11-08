# STALE - read 2026-11-08, work continued

## In flight (read first)

- RUN `~/ab-runs-skillchores/sdd-final-review-r1` (OPEN-WORK [25], the user's go to launch: "you can launch the run+", 2026-11-08): launched by `launch.sh` 18:50 UTC. Arm C finished 20:08 UTC (wall 4377 s), arm V42 running since then (expect about 1.5 h, done around 21:40 UTC). Driver log `launch.log` in the run dir; the arms use the pinned plugin 10.19.2, so nothing pushed to master affects them. Monitor on `launch.log` expires every 30 min: re-arm with `tail -n 0 -F ~/ab-runs-skillchores/sdd-final-review-r1/launch.log | grep --line-buffered -E "RC=|STOP|cost=|error"`. The launch log prints no cost line; the end is the line `RUN RC=`.
- AFTER BOTH ARMS END: `python3 <pinned abtest.py> score <run dir> --json` (pinned = `~/.claude/plugins/cache/bitranox-skills/bitranox/10.19.2/skills/meta-skill-ab-test/scripts/abtest.py`), then a blind pairwise opus judge of the two diffs against the source design per the run's `PREREG.md` decision rule, BEFORE `prune-run`; then ship or drop the V42 section of `process-agents-subagent-driven-development` by that rule. Remember: prune-run now writes `branches.bundle` first (10.37.1).
- BACKGROUND: subagent a474cefbc2edfd623 (entries 7, 1, 2) is DONE; its work sits on branch `worktree-agent-a474cefbc2edfd623` in `.claude/worktrees/agent-a474cefbc2edfd623`, 4 commits (baee244b, ab81fb11, 2ae54d0c, e9a233f4 = 10.38.0), already reviewed: based on origin/master, no attribution, ASCII only, 423 skill tests passed per its report. TO DO: run the skill tests with CI's dep set there, `git push origin HEAD:master` from that worktree (gate about 7 min), watch CI (`ci_wait.py --ref HEAD`, foreground or background alone), then `contrib_queue.py ship --match "<text>" --note "10.38.0"` for the entries starting "run: take a lock on the run dir", "Document that an unattended arm may end its session", "Give the harness a way to make a gitignored build prerequisite", then remove the worktree and branch.
- Backstop wakeup was set for 21:36 CET (may have fired).

## Committed, or not

- Primary checkout (this repo, master): UNCOMMITTED `OPEN-WORK.md` ([25] and [27] open: fields rewritten, new [110] and [120]) and this `handover.md`. Commit them with the next push (no version bump needed for docs only).
- Pushed today: 10.37.1 (prune-run bundles all branches), 10.37.2 (score: subagent overlap, idea markers, suite outcome), the records merge. Nothing else pending except the branch above.

## Decided

- User 2026-11-08: "keep them at the moment" (the `~/ab-runs` run dirs and plugin-pin stay); "go ahead" on the free work of [25]; "you can launch the run+" (I launched it); approved the plan for entries 7, 1, 2 (plan file `~/.claude/plans/fluttering-dancing-moonbeam.md`).
- The best workpiece branches were restored in `provmm_openvmm` as `keep/vfix-r10..r16`, `keep/VN1b-plan-review-14`, `keep/C-12`; best score is `keep/vfix-r16` (bare + fix rounds, 19+1) and `keep/vfix-r12` (20 after round 3). All 62 abx branches are in `data/branches/abx-all.bundle` of the private research repo.
- Private research repo (local, not pushed, no remote): `/media/srv-main-softdev/rnprivat/presse/presse-agent-research`, 4 commits, everything archived (runs, raw streams as per-run tarballs, judge inputs, sources). The user did not say where to push it; ask before creating any remote.

## Still open, untouched

OPEN-WORK.md: [25] (running, see above), [27] (judge redesign, queue entries 4 and 5), [50], [96], [100], [110] (follow-up experiments, need the user's go), [120] (dream, EXECUTION-USER-REVIEW decisions, STRUCTURES.md). Queue entries still unclaimed: 4, 5 (judge design), 6 (final-review text, covered by the V42 run), 8 (RecursionError rule for process-test-design), plus a stray entry under queue_key f71f9074ebdd8454 (report acceptance count as completeness).

## Lessons for the next nap

- When an Explore agent reports what master contains, check it against `git fetch` and `git show origin/master:<path>`: it read the stale primary checkout and said abtrace.py did not exist after I had pushed it.
- When a repo gate refuses a SKILL.md change, expect three demands in sequence: a co-changed `.skillwriter/checklist-*.md`, all boxes ticked (test the unchecked claim instead of leaving it open), and a `- [x] Decisions: none - <reason>` line.
- When writing a regression test for a failure path that a fixture cannot trigger, make the run dir read-only with `chmod 555` after the dry run and skip if `os.access` still says writable (root).
- When a hook refuses a python heredoc followed by git add, put `&&` on the heredoc opener or run the script alone first.
- When archiving run dirs into a repo, exclude each run dir's own `.git` and keep its history as `git bundle create ... --all`, and bundle EVERY workpiece branch before prune-run (the per-arm bundle.git files held 45 of 62).

## Files that matter

`plugins/bitranox/skills/meta-skill-ab-test/` (scripts, tests, SKILL.md, .skillwriter), `~/ab-runs-skillchores/sdd-final-review-r1/` (PREREG.md, launch.log, journal.jsonl), `/media/srv-main-softdev/rnprivat/presse/presse-agent-research/`.

## How to verify

- Skill tests: `env -u VIRTUAL_ENV uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/meta-skill-ab-test/tests -q`
- CI for a pushed commit: `uv run ~/.claude/plugins/cache/bitranox-skills/bitranox/10.16.1/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`
- Run state: `tail -n 3 ~/ab-runs-skillchores/sdd-final-review-r1/launch.log`

## Exact next action

Push the finished branch: in `.claude/worktrees/agent-a474cefbc2edfd623` run the skill tests, then `git push origin HEAD:master`, watch CI, close the three queue entries (see In flight). Then wait for the run to end and score it.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it - if this session ends badly it is the only record of where things stood.
