# Handover 2026-10-19: [23] Phase 3 batch 1 done but for install-gated archives, next batch 2

## In flight

- Nothing part-done, no subagents running. Batch 1 (provmm-umbrella level, 26 skeptic-checked
  rows) is recorded in full in the `[23]` line of `OPEN-WORK.md`; read that, not this summary.
- Waiting on the USER: install 9.7.1 or later here (a peer has since pushed 9.7.2; `/plugin marketplace update bitranox-skills`, then
  `/reload-plugins`). Only then archive the 4 marketplace-folded facts listed under "OPEN in batch
  1 (a)" in the `[23]` line - archiving before the install leaves the rule briefly in neither place.

## Committed, or not

- bitranox-skills 9.7.1 (`b3c46efb`, compuse-ssh + infra-windows-servicing): pushed; CI run
  39280166019 finished `success` (ci_wait itself timed out at poll 50 after a long queue).
- provmm_umbrella `c6fd58c` (8 skill folds) and `22a71ba` (CLAUDE.md re-points), provmm_proxmox
  review_gate.py docstring: pushed to Gitea. The peer `provmm-umbrella-42` was told about both.
- Memory store: 27 re-pointed facts + 21 archived facts committed and pushed. 5 untracked facts
  there belong to other sessions - leave them.
- This handover and the `[23]` update ride on branch `fold-23-batch1` (worktree
  `../bitranox-skills-wt-fold-23-b1`), pushed to master in the same step as this file.
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's two batch-1 decisions verbatim.

## Decided, and why - do not reopen

- `project-a-dependent-topic-cannot-build-standalone` is HELD, not archived: its body gained a
  measured section on 10-16 (a "runtime-only" dependency can be a test-time one) that no skill
  carries. Fold that section in batch 2 before archiving.
- The 4 DEAD rows of the level are not part of [23]; they go to the normal prune path.
- Stale fact premises were re-measured, not copied: the never-standalone reason now names the
  shim's integration-only flags (`--control-socket`, `--rtc-base`, ...), because `vnc_listen` is
  upstream now; the upgrade cost cites the skill's measured durations, not "about an hour".

## Still open, untouched

- `[23]` batch 2: provmm-umbrella's 57 FOLD-UNCHECKED rows need the reach + skeptic check first.
- `[28]` and the FOUND items in `OPEN-WORK.md` (incl. [620], [630], [640], [590] part 2).

## Lessons for the next nap

- When folding a memory fact into a skill, diff its body against the version the classification
  saw: 9 of 22 had changed since, one gained a measured section no skill held.
- When a fact justifies a rule by naming flags or APIs, re-check them against current source:
  the VNC flags it cited had moved upstream, though the rule still held for other flags.
- When a fold carries a duration or size from a fact, check the target skill's own measurement
  sections first: "about an hour" contradicted its measured 1 h to 5h18m.
- When grepping the softdev tree for citations, use one `grep -F -f patterns` pass and exclude
  linux-x64-source, qemu, provmm_openvmm, .venv and target: a per-slug walk ran past 5 minutes.
- tooling: `ci_wait.py --ref HEAD` exits 2 (timeout) while a queued-then-running run is still
  in progress; the run then succeeded. Read the run, not the waiter's exit.
- tooling: `factedit apply` normalises a double blank line after the frontmatter, so a ref-only
  body edit shows a blank-line delta; prove ref-only by reversing the substitution against HEAD.
- (carried, uncaptured) When writing a RED for a SKILL.md change whose companion reference was
  already edited, paste the PRE-change reference too.
- (carried, uncaptured) When an opus RED arm queues a skill fix, check whether it ALSO wrote a fact.
- (carried, uncaptured) tooling: block-masked-gate-exit refused a backgrounded
  `ci_wait ... > log; echo RC=$?`; background ci_wait alone.

## The exact next action

`[23]` is the top-ranked open item. If the user has installed 9.7.1 or later, archive the 4 facts in its
"OPEN in batch 1 (a)" list first (`ref_map.py` for inbound refs, then
`reconcile_memory_index.py --archive <slug> <provmm-umbrella level dir>`,
`--check-tree` TOTAL 0, commit by pathspec). Then batch 2: run the reach + skeptic check on the
57 FOLD-UNCHECKED provmm-umbrella rows in `.plan/fold-23/rows.json` (main checkout) and put the
surviving batch to the user as ONE question before any edit.

## Files that matter

- `OPEN-WORK.md` (`[23]` line), `.plan/fold-23/rows.json`, `.plan/fold-23/skeptic-output.json`,
  `~/.claude/plans/curried-mapping-dolphin.md`
- provmm: `.claude/skills/provmm-test/.skillwriter/checklist-20261019-fold-23-batch1.md`
- marketplace: `plugins/bitranox/skills/{compuse-ssh,infra-windows-servicing}/.skillwriter/checklist-20261019-*.md`

## How to verify

- CI on HEAD: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`), and if it times out
  read `gh run list --commit <full sha>`; 9.7.1 was green on `b3c46efb`.
- Installed version: `ls ~/.claude/plugins/cache/bitranox-skills/bitranox/` shows `9.7.1` or later.
- Memory tree: `reconcile_memory_index.py --check-tree .` from any level reports TOTAL 0.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
