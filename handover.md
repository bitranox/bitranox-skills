# Handover - 2026-10-29 13:10, [23] batch 8 done, next group to pick

## In flight

- Nothing running. [23] batch 8 is complete: pass 1 (10.3.28) and pass 2 (10.3.30, bmk twin
  3.32.2) shipped with CI green, installed, quote-checked, and the store is updated (pass-1
  archive 22ba62e, pass-2 hook cut 209c426).
- The next group is a question for the user. Census: `.plan/fold-23/census_next.py` (main
  checkout, gitignored) writes `census_next.json`: 58 live phase-1 FOLD/ALREADY rows no batch has
  handled (14 tree top, 20 soundtouch-zonemaster + -watchdog, 15 provmm-umbrella levels, 10
  projects/public and below); 29 more have no pointer left.

## Decided

- USER 2026-10-29 ("Fix and log narrow cases (Recommended)"): logged verbatim in the main
  checkout's EXECUTION-USER-REVIEW.md; shipped in 10.3.30.
- Declined (delta review N4): changing task-reviewer-prompt.md's "plan-mandated rubric defect is
  Important" grading; outside the user's decision, the skill defers to the template.

## Still open, untouched

- Everything else: `OPEN-WORK.md`.

## Next action

Ask the user which group [23] batch 9 takes (one decision), then run the batch 8 flow on it:
check pass (classify against the live skills), pass 1 archive rows, pass 2 cut rows.

## How to verify

- Census: `python3 .plan/fold-23/census_next.py` from the main checkout.
- Tree: `reconcile_memory_index.py --check-tree /media/srv-main-softdev` reports 0 problems.

## Lessons for the next nap

- When backing up the memory tree with store_manifest.py, write --out OUTSIDE the tree (the
  session scratchpad): a backup under the tree adds its copied CLAUDE.local.md files as duplicate
  levels, and --check-tree then reports one problem per pointer.
- When a peer session pushes a plugin version while yours is staged, restore only the shared
  files (CHANGELOG, plugin.json, pyproject) to HEAD, fast-forward, and re-insert your entry under
  the next number with an assert on the old one.
