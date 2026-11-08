# Checkpoint 2026-11-08 16:50 CET (A/B experiment [26] finished: all paid runs done, data archived, pruned)

## In flight (read first)

- Nothing paid is running. r5, r6, r20 and r21 are done and judged; results are in OPEN-WORK.md [24] and [31].
- All data is archived in the private repo `rnprivat/presse/presse-agent-research` (local, 3+ commits, not pushed):
  runs, raw streams and transcripts, judge inputs and diffs, every abx branch as `data/branches/abx-all.bundle`.
- The workpiece branches were removed with `prune-run` for r1..r21 after that bundle was verified (62 heads).
  Run dirs under `~/ab-runs` are still there (110 GB, plugin-pin included).

## Decided

- User 2026-11-08: "lets continue with the cleanup now that everything is saved so far" (my reading: covers prune-run).
- Next paid step is the user's call: fix rounds on VN1b (and Vpar for a like-for-like), about 50 USD per arm; the
  weaknesses list (one run, one judge, nothing code-checked) is in the research repo METHOD.md.

## Committed, or not

- OPEN-WORK.md and this file: commit and merge origin/master (peers landed 10.20.0 and 10.22.1).

## Still open, untouched

OPEN-WORK.md: [24], [25], [26], [27], [28], [29], [30] overdue, [31], [40], [50], [95]-[100]. Also: full dream (about 21 MB of
transcripts unreviewed), EXECUTION-USER-REVIEW.md needs the r5-r21 decisions, remove `~/ab-runs/*/plugin-pin` and the run dirs
only on the user's word, fix rounds only on the user's word.

## Lessons for the next nap

- When pruning a workpiece after an experiment, bundle EVERY branch first (`git bundle create ... <all refs>`): the per-arm bundle.git files missed 17 branches (attempts, killed arms).
- When copying run dirs into an archive repo, exclude each run dir's own .git (it becomes an embedded repo and loses its content), keep it as a bundle instead.
