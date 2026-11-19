# STALE - read 2026-11-19, work continued

## In flight

- Items the user handed over at 03:21: [25], [100], [120], [150], [180], [190], [195], [200], [210].
- Integration worktree `.claude/worktrees/sweep-1119`, branch `fix/sweep-1119` from origin/master
  d8e71019 (11.12.0). Holds 20 cherry-picked fixer commits (all wave-1 work; DROP-AT-INTEGRATION
  bump commits were NOT picked). UNCOMMITTED here: bump to 11.13.0 (plugin.json, pyproject.toml,
  CHANGELOG with the wave-1 notes) plus a scrub of the bare token for the private project family
  (replaced by "private") in 19 live files; and this handover.
- Wave 2, running as named background agents in prepared worktrees branched from the integration
  branch (each makes its own DROP-AT-INTEGRATION commit first; reports by SendMessage to main):
  - `w2-g1` in `.claude/worktrees/w2-g1` (branch wave2/g1-engine): [195] G1, memory_engine
    move/relocate/heal reports as typed records.
  - `w2-row` in `.claude/worktrees/w2-row` (branch wave2/toolbox-row): compuse-toolbox SKILL.md
    mutation_arm row is stale after the mutation_arm fix; dream-core `--to` offset wording.
  - `w2-regex` in `.claude/worktrees/w2-regex` (branch wave2/quadratic-regex): fix the 18
    confirmed quadratic regexes in shipped hooks and skill scripts (toolbox-nudge.py first).
- Results log of every report: scratchpad `RESULTS.txt` (volatile: scratchpad dies on reboot);
  the per-item outcome is also summarised below.
- Research repo commit b26340f ([120] STRUCTURES.md) is PUSHED; [120] decision log section is in
  the gitignored EXECUTION-USER-REVIEW.md at the main checkout root.

## Decided, and why

- User 03:31: the private project-family name stays private "at the moment". Scrub forward in every live tracked file (dated
  checklists and old CHANGELOG entries included, since they ship); git history stays.
- Contribution entry 4 (probe hand-backs to a named teammate) is premise-false: drop it from the
  queue citing ledger d-20261115-0a37a1d3; reopening that rejection is the user's call.
- [195] G4 FU-b (transcript_turns resume-from-offset cache): leave it - median transcript 1.9 MB
  (~2 ms), p90 29 MB (~30 ms); a cache adds stale-able state for outliers. Close that part.
- mutation_arm refuses when its state dir is unwritable (fail loud) rather than falling back.
- Plan-mode checkpoint goes into the plan file as `## Checkpoint` (implemented; option A).

## Still open, for OPEN-WORK.md at the end

- [100] KEEP: fixes ship in 11.13.0; re-measure after a week on >= 11.13.0 (scripts cycles2.py,
  bucket2.py, classify.py in scratchpad measure-100; copy them into .plan/compact-cycles/).
- [150] rewrite to the LEFT list (retitle race rm4, rehome default, empty-scope next step,
  crosstree per-promotion cost + "global" naming, _check_out other-anchor guard, unreadable second
  walk, dedup_scan duplicate, dup-pointer lock, ledger wording) plus the user question on
  dream_mode off for a manual crosstree run.
- [195] rewrite to: corpus_prompts, guard_replay, pfsense run_php, abscore/abtest (+ G1 if w2-g1
  leaves parts).
- [200] close; quadratic hits in tests (10, low) stay as a FOUND line if w2-regex leaves them.
- Close [25] (ship entries 1,2,3,5,6,7 with contrib_queue ship --match; drop 4), [120], [180],
  [190], [210]. Scrub the private token from OPEN-WORK.md lines too.
- User questions: dream_mode off (manual crosstree); bare `type:` clears kind?; Step 4b severity
  for quadratic on bounded non-hot input; [45] reviewer reads design?/4th arm.

## Next action

Wait for w2-g1, w2-row, w2-regex reports; cherry-pick their work commits (not their DROP commits)
into `fix/sweep-1119`; add their CHANGELOG bullets under 11.13.0; commit; then update OPEN-WORK.md,
run `python3 plugins/bitranox/hooks/repo-gate.py --ci`, push `HEAD:master`, watch CI with
`ci_wait.py --ref HEAD` (compuse-toolbox), run the contrib_queue closes, `skill_receipt.py end
meta-skill-writer`, remove the fixer worktrees.

## Lessons for the next nap

- When a measurement agent finds a regression in the item it measures, dispatch the fixer in the
  same sweep: the measurement brief should ask for the recommended fix with code lines.
- When fixers run in parallel on one file (memory_engine.py), confine each to named functions;
  the cherry-picks then merged clean.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
