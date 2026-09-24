# Handover - written 2026-09-24, nothing in flight

## In flight

Nothing. 7.14.0 is committed and pushed; the worktree is clean and level with `origin/master`.

## Committed, or not

7.14.0 carries `--prompts` on `classifier_eval.py` (pin a replay to an earlier run's exact prompts
AND recorded state, reporting `state_drift`), the `skill_router` eval threshold 0.7 -> 0.5, and
five new sibling tests. Machine config unchanged: `classifier_backend = jev`, all three sites still
`shadow`. Nothing shipped here changes what a live session sees - `SITE_THRESHOLDS` exists only in
the eval tool, and `skill-router.py` has no threshold at all.

**The paid inputs are durable now**, both byte-verified copies, both gitignored:

* `.plan/jev-replay-2026-09-23/` - panel-1 `labels.json`, `replay-run2.jsonl` (48 files)
* `.plan/jev-replay-2026-09-24/` - `replay-run4.jsonl`, `labels2.json`, `verdicts2_0-4.json`,
  `sweep.py`, `check_fit.py`, `merge_verdicts2.py` (24 files)

Re-judging costs five opus agents; a replay costs about $0.12. Do not let a `/tmp` sweep take them.

## Decided, and why - do not reopen

- **The gate, not the roster, was the dominant failure.** Its AUC is about 0.71 on every arm, so
  0.7 sat in the steep part of a shallow curve and kept 5 of 11 - reproducing the first
  adjudication's "missing 6" exactly. No rewording moves a curve like that.
- **The first-prompt control was never a wording defect.** Its 0.02 margin was that same steep
  curve. `controls --threshold 0.5` passes all 24 rows on all six arms (positives 0.68-0.72,
  negatives 0.20-0.23). The previous handover's "left FAILING on purpose" is superseded: the
  instrument was sound, the operating point was not.
- **0.5 and not 0.3**, though 0.3 scores better here: 0.5 is where the controls were actually run
  and clears both ways by about 0.2, where 0.3 leaves 0.07 over the negatives and has never been
  run.
- **A pinned replay re-sends the RECORDED state.** Rebuilding it from `source`+`line` was tried
  first and is unfaithful - `project` reproduced on 39 of 50, differed on 8 because a directory had
  since gained its own scope descriptor, 3 cwds unresolvable. Holding state fixed is also what
  makes this an A/B at all.
- **`nouls` is out.** 42 outright wrong picks at 0.3, because one number gates the turn AND sets
  its per-skill bar.
- **The rerank stays settled.** Flat at 2 right across the whole grid.

## Not established - do not repeat this as a result

**`choice_router_text`'s lead is contaminated.** It looks dominant (0.30: 9 right / 12 defensible /
1 wrong / 2 missed, against `choice_full` at 0.70 on 2/7/1/8). But 7 of those 9 right picks fall
inside the six entries in `router_criteria.json`, which 7.13.0 authored FROM the panel-1
adjudication over these same 50 prompts. Outside those six it scores 2 right - the same as
`choice_full`. It is fitted to this test set until a held-out run says otherwise.

What IS arm-independent, and therefore safe to build on: every arm improves as the gate drops.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 10 (a USER item) is still top-ranked and untouched - it is not
the Jev thread, and recency is not a reason to prefer the Jev thread. Rank 14 (the approved
identifier guard) is still small and self-contained. Rank 78 is still open.

A new one this session, inside rank 12: **4 of the 13 prompts that need a skill wanted one NO arm
proposed at any threshold** (p02 `meta-self-improve`, p05 `meta-context-watcher`, p28
`typesafe-ai`, p43 `soundtouch-decloud`). That is a roster/coverage gap. No threshold closes it and
it should not be folded into the gate work.

## The exact next action

If the user picks Jev (rank 12): the **held-out run**. Pin a FRESH 50 prompts with a seed the six
criteria were never authored against, replay at 0.5, adjudicate blind, and require
`choice_router_text` to beat `choice_full` OUTSIDE those six entries. About $0.12 plus five judges.
Only then decide per site whether anything leaves shadow.

Otherwise rank 10 goes first.

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `prompts_from_log`,
  `state_drift`, `_replay_one`, `SITE_THRESHOLDS`, `REPLAY_CONTROLS`, `run_arm`, `ARMS` (six).
- `plugins/bitranox/hooks/classifier.py` - `skill_router_questions`, `_router_turn_text`,
  `short_description`.
- `plugins/bitranox/hooks/router_criteria.json` - the six authored entries; everything else falls
  back to its description. This is the file whose contamination the held-out run tests.
- `.plan/jev-replay-2026-09-24/sweep.py` - re-derives any arm's picks at any threshold offline,
  per shape; `check_fit.py` - the contamination and roster-gap checks.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/jev-classifier
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
D=/media/srv-main-softdev/projects/public/KI/bitranox-skills/.plan/jev-replay-2026-09-24
python3 "$D/sweep.py" "$D/replay-run4.jsonl" "$D/labels2.json"
```

`repo-gate: all checks passed` with 5068 passed. The sweep calls nothing and reprints the table
above from the recorded run.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
