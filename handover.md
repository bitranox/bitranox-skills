# Handover 2026-10-19: [26] closed (9.6.0, 9.7.0), next [23] Phase 3

## In flight

- Nothing part-done. No subagents or background jobs of this session are running; both worktrees
  (`skill-routed-capture`, `memory-skill-field`) are removed and their branches deleted.
- The peer `btx-skill-jev-judge-37` finished its deep memory dream (store commit `2c4dbea`). The
  store-edit block the previous handover named is lifted; it left one uncommitted fact there that
  belongs to session `virtual-35` - leave it.

## Committed, or not

- Pushed, CI green: `ef0bad0e` (9.6.0) and `e3687144` (9.7.0). The memory store is pushed.
- Plugin cache here is still 9.5.0 until `/plugin marketplace update bitranox-skills` plus
  `/reload-plugins`, so this session's own Stop gate still showed the old reason text.
- `EXECUTION-USER-REVIEW.md` (gitignored) holds today's "Skill field" decision verbatim.

## Decided, and why - do not reopen

- [26]: a lesson learned inside a loaded skill's domain, or one a never-loaded shipped skill
  covers, is queued against that skill with NO memory fact, unless the rule binds work outside the
  skill; then the fact carries `--skill <name>`. RED (haiku, opus) wrote facts; GREEN queued all.
- The `--skill` field is written with NO consumer: the user chose "Add an optional --skill field"
  over the dream-consumer option. Do not build a reader without a new ask.
- The Stop gate's old "highest-altitude store (.claude-bx-selflearning/...)" sentence was removed
  as stale: capture writes at one project level, the dream raises altitude.

## Still open, untouched

- [23] Phase 3, [28], and the FOUND items in `OPEN-WORK.md`; new today: [620] repo-gate LF check
  reads worktree bytes (peer report, unverified), [630] CLAUDE.md probe-order and duplicate
  paragraph (peer report, unverified), [640] `--proj`/queue cwd rule inside a worktree.
- The peer queued 15 contributions in the btx-skill-jev-judge queue (queue_key 114e718bde5eba4a).
- [590] part (2) only; unreviewed transcripts of this project: `dream_state.py session-review`.

## Lessons for the next nap

- When writing a RED for a SKILL.md change whose companion reference was already edited, paste the
  PRE-change reference too: a probe shown the new flag in the reference passed the RED.
- When an opus RED arm queues a skill fix, check whether it ALSO wrote a fact: the duplicate, not
  the missing queue entry, was the failure there.
- tooling: block-masked-gate-exit refused a backgrounded `ci_wait ... > log; echo RC=$?`; background
  ci_wait alone (its own exit is the task's), as gated-rc-from-log already says - a repeat.

## The exact next action

[23] is the top-ranked open item. Read its line in `OPEN-WORK.md` and the plan
`~/.claude/plans/curried-mapping-dolphin.md`, pick the first lower-level batch from
`.plan/fold-23/rows.json` (main checkout), and put it to the user as ONE question before any edit.

## Files that matter

- `OPEN-WORK.md`, `.plan/fold-23/`, `~/.claude/plans/curried-mapping-dolphin.md`
- `plugins/bitranox/skills/meta-self-improve/SKILL.md` (step 2), `plugins/bitranox/hooks/self-improve-gate.py`,
  `plugins/bitranox/hooks/memory_engine.py` (`--skill`)

## How to verify

- CI: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`); 9.7.0 was green on `e3687144`.
- `python3 plugins/bitranox/hooks/repo-gate.py --ci` reports all checks passed.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
