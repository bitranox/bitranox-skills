# Handover - 2026-10-29 15:40, [23] batch 9 (tree top) complete

## In flight

- Nothing. [23] batch 9 shipped as 10.4.1 (marketplace 237b6aab, bmk 3.32.3 a2195a8, btx_lib_mail
  4.6.3 143795c), CI green on all three, installed and quote-checked; store 1a03525 archived 9
  facts, cut 4 hooks and re-pointed 6 citing facts.
- The `lib_layered_config` peer rebased and pushed its change as 10.4.2 (33da9706).

## Decided

- USER 2026-10-29 chose "Tree top (Recommended)" for batch 9 (verbatim in the main checkout's
  EXECUTION-USER-REVIEW.md); one fold round for archive and cut rows (autonomous, logged there).
- feedback-public-push-review-and-humanize stays a fact (5 inbound refs).
- Declined review items: the venv lock timeout (already stated in devops-bmk), a second envelope
  from the Makefile regeneration (its pre-steps run no pipeline), restoring devops-bmk's
  cross-plugin pointer (the bmk twin installs alone).

## Still open, untouched

- Everything else: `OPEN-WORK.md`.

## Next action

[23]: propose the next group to the user (OPEN-WORK.md line for [23], "after batch 9": 20
soundtouch, 15 provmm-umbrella, 10 projects/public and below), then run the batch 9 flow on it.

## How to verify

- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (devops-bmk and send-mail in sync).
- `reconcile_memory_index.py --check-tree /media/srv-main-softdev` reports 0 problems.

## Lessons for the next nap

- When backing up the memory tree with store_manifest.py, write --out OUTSIDE the tree (the
  session scratchpad): a backup under the tree adds its copied CLAUDE.local.md files as duplicate
  levels, and --check-tree then reports one problem per pointer.
- When a peer session pushes a plugin version while yours is staged, restore only the shared
  files (CHANGELOG, plugin.json, pyproject) to HEAD, fast-forward, and re-insert your entry under
  the next number with an assert on the old one.
- When a peer COMMITS a version bump on the main checkout without pushing, it is invisible to a
  fetch of origin: check `git log master` in the main checkout before picking a number.
- tooling: the SessionStart hook after a compaction creates empty CLAUDE.md/CLAUDE.local.md in a
  gitignored scratch dir under .plan (contrib queued).
