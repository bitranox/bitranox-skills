# Handover 2026-10-19: [23] Phase 3 batch 2 folded and archived, next the KI-level group

## In flight

- Nothing part-done. No subagent or workflow is running.
- `[23]`'s line in `OPEN-WORK.md` records batch 1 and batch 2 in full, with their open sub-steps
  (batch 1 (c), batch 2 (2b) and (2c)). Read that line, not this summary.

## Committed, or not

- Everything this session changed is committed and pushed:
  - provmm_umbrella `7b0d558` (test-time dependency) and `c19a144` (20 rules), on Gitea main;
  - bitranox-skills 9.8.1 (`f7979fe4`, 5 rules); CI finished `success` on that sha;
  - memory store `c6b8162`, `da637b9` (nap), `78419d5` (20 archived, 10 re-pointed),
    `0f96701` (5 archived).
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's batch-2 decision verbatim.
- 9.8.2 and 9.8.3 on origin are other sessions' releases; the installed 9.8.2 carries 9.8.1.

## Decided, and why - do not reopen

- Only the 25 REACH-OK rows were folded, on the user's choice "25 reach-OK rows (Recommended)".
  The 30 REACH-PARTIAL rows stay facts: their rule also fires where the owning skill is not loaded,
  so folding them would leave two copies to drift.
- `feedback-no-qemu-comparison` and `feedback-no-private-paths-in-public` stay facts:
  `review_gate.py load-facts` (provmm_proxmox) prints their bodies by slug.
- Folds used the second reviewer's amended text, re-verified per row, never the first
  classifier's hint: 15 of the 57 bodies held a claim false today.

## Still open, untouched

- `[23]` (2b), (2c) and batch 1 (c): see the `[23]` line.
- `[28]` and the FOUND items: see `OPEN-WORK.md`.

## Lessons for the next nap

- When a fold batch is drawn from facts classified days earlier, expect about one body in four to
  hold a claim false today (measured 15 of 57): give the editor the skeptic's amended text plus a
  re-verify step, never the classifier's hint.
- When checking that an editor's inserted text or a GREEN quote is in a skill file, normalise
  whitespace AND strip backticks/bold before matching: a plain substring match called two present
  rules missing.
- (recurrence of feedback-audit-what-a-number-counts) When writing a count into a backlog line or
  a review checklist, compute it from the data in the same command: three counts written from
  memory this session (11/9 RED, 9 stale bodies, 8+) were all wrong and had to be corrected.
- tooling: a Workflow task's output file is a JSON object whose `result` holds the return value;
  scanning the text for the first `[` decodes an unrelated empty list.
- tooling: interactive `grep` here is ugrep; given explicit file arguments plus `--include` it
  warns and matches nothing, so a "no hits" from it is not evidence - use `bash -c "grep ..."`.

## The exact next action

`[23]` is the top-ranked open item. Start Phase 3's next level group: take the FOLD-UNCHECKED rows
of the bitranox-skills and KI levels from `.plan/fold-23/rows.json` (main checkout), copy the
batch-2 workflows (reach + skeptic, then scenario/RED/edit/GREEN) and their input builders, run the
reach + skeptic workflow, and put the surviving batch to the user as ONE question before any edit.

## Files that matter

- `OPEN-WORK.md` (`[23]` line), `.plan/fold-23/rows.json`, `.plan/fold-23/batch2/merged.json`
  (both lenses per row, incl. `skeptic.stale` for (2b)), `.plan/fold-23/batch2/cites.txt`
- `~/.claude/plans/curried-mapping-dolphin.md` (the [23] plan)
- batch-2 workflow scripts:
  `~/.claude/projects/-media-srv-main-softdev-projects-public-KI-bitranox-skills/a03de64b-f570-4dce-96b1-bdc8920fc6df/workflows/scripts/`
- review artifacts: provmm_umbrella `.claude/skills/provmm-pr/.skillwriter/checklist-20261019-fold-23-batch2.md`,
  marketplace `plugins/bitranox/skills/{infra-windows-servicing,meta-context-watcher,meta-skill-audit}/.skillwriter/checklist-20261019-*.md`

## How to verify

- Memory tree: `reconcile_memory_index.py --check-tree .` (home: `<plugin>/skills/meta-self-improve/`)
  reports TOTAL 1, the rotek rpyc sideways ref from another session's nap (`d44b62b`), nothing else.
- None of the 25 batch-2 slugs keeps a pointer:
  `grep -c 'mem:<slug>)' /media/srv-main-softdev/bitranox-systems/provmm-umbrella/CLAUDE.local.md` is 0.
- CI on HEAD: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`); 9.8.1 was green on
  `f7979fe4`.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
