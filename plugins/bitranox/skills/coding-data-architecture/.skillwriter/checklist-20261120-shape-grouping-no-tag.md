# checklist - shape grouping and the no-tag baseline

One queued contribution with two parts: STEP B groups findings by shape across files before
partitioning (one shared record type, one owning fixer per shape), and the STEP C error-surface
diff uses the state file's `base` when the repo has no release tag.

Decisions: d-20261120-7c35a007, d-20261120-d44e37f1

## RED

- [x] Skill decisions read first: none rejected or removed.
- [x] Text check of the pre-edit file: the key phrases of the added rules had 0 hits at HEAD
      (listed in the run's notes).

## GREEN

- [x] Quote-back probe (haiku) on the added text: every question answered with a quote of the
      new lines; no NONE. The opus probe was skipped for this batch to keep the run inside its
      time budget; the haiku probe is the weaker reader, so a pass there is the harder bar.

## REFACTOR

- [x] Declined (haiku): where the shared module lives - the owning fixer decides it within the
      project's layer rules.
- [x] Width, fence and ASCII checks on the added lines clean.
