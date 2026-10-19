# Handover 2026-10-19: [23] step 3c done, nap done, next [23] Phase 3

## In flight

- Nothing part-done. No subagents or background jobs of this session are running; the
  provmm-umbrella worktree `fold23-3c` is removed and its branch deleted.
- A PEER session (`btx-skill-jev-judge-37`) is running a deep crosstree dream on the shared memory
  store. It committed the earlier fold work as store `83dfc19` and is rewording stale
  bitranox-skills-level facts. Do not edit memory facts until it is finished, or ask it first
  (SendMessage); it was told which slugs this session wrote.

## Committed, or not

- Pushed: provmm_umbrella `86f643a` (Gitea, provmm-benchmark skill + `.skillwriter/` checklist),
  provmm_proxmox `8c76172` (Gitea, quirks doc pointer), bitranox-skills `b3ac1ac4` (OPEN-WORK
  [23] 3c). No plugin version change today: nothing under `plugins/` moved.
- Memory store: committed path-scoped, NOT pushed - `7389120` (the shortened benchmark fact) and
  `3acec0f` (nap: one new fact, five body deltas). The peer's dream may push.
- 7 tooling defects queued in this repo's contrib_queue (repo-gate UNLISTED worktree, memory_engine
  blank line, factedit framed body, store_manifest --out, archive vs inbound refs, anchor_edit
  absolute paths, CLAUDE.md bump instructions vs pyproject.toml).
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's user decision verbatim.
- The provmm-umbrella main checkout belongs to a live peer session, has an uncommitted
  OPEN-WORK.md and is one commit behind origin; that session was told to `git pull --ff-only`.

## Decided, and why - do not reopen

- feedback-benchmark-fair-settings stays at the tree top, cut to the general rule (user, verbatim
  label "Keep it, shortened (Recommended)"): two tree-top facts cite it and the project skill does
  not load outside provmm-umbrella.
- The skill names the axes and the diff, never a fixed vCPU/RAM/cache target: the live matrix
  cells match none of the numbers the old fact carried.
- The nap left the 56 versionrot flags on the chain for the full dream: the [22] pass reviewed the
  version-flagged set on 2026-10-16, and the peer dream is editing the same store now.

## Still open, untouched

- [23] Phase 3, [26], [28] and the FOUND items: `OPEN-WORK.md`. [590] part (2) only.
- 38 other unreviewed transcripts of this project (listed by `dream_state.py session-review`).

## Lessons for the next nap

- When briefing nap readers with a "known, do not report" list, keep the handover's own lessons
  off it unless they are already in the store: known to the coordinator is not captured.
- When a doc points at a section of another file by name, check the section still exists when the
  rule moves: provmm_proxmox's quirks doc pointed at a CLAUDE.md section removed months earlier.

## The exact next action

[23] is the top-ranked open item; its next step is Phase 3. Read the [23] line in `OPEN-WORK.md`
and the plan `~/.claude/plans/curried-mapping-dolphin.md`, pick the first lower-level batch from
`.plan/fold-23/rows.json` (main checkout), and put it to the user as ONE question before any edit:
each batch needs its own approval.

## Files that matter

- `OPEN-WORK.md` ([23] carries the step state)
- `.plan/fold-23/` (main checkout: rows.json, backups)
- `~/.claude/plans/curried-mapping-dolphin.md`

## How to verify

- CI: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`).
- Memory tree: `reconcile_memory_index.py --check-tree <softdev-root>` (home
  `skills/meta-self-improve/`) reports TOTAL 0.
- Twins: `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` from inside this repo reports
  0 of 12 drifted.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
