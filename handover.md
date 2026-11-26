# Handover - 2026-11-26 15:55 CET (watcher checkpoint, session "skill-research")

## In flight (read first)

Working the Claude Code 2.1.33x research list, top item [55] (path-scoped `.claude/rules` for the
memory index). Work lives in the worktree `.claude/worktrees/research-cc-2-1-332` (branch
`research-cc-2-1-332`, pushed as `HEAD:master`).

- Pushed and CI green: "Record the Claude Code 2.1.33x context research and its backlog items"
  (research note `docs/plans/2026-11-26-claude-code-2-1-332-context-research.md`, items [55]-[85]).
- Push RUNNING in the background when this was written: "Probe how .claude/rules load: ancestor
  paths: rules fire on Read and Bash cat" (probe in `docs/plans/probes/2026-11-26-rules-loading/`,
  section 3.1 result table). Check with `git fetch && git log origin/master --oneline -3`.
- UNCOMMITTED in the worktree: the [55] line's sizing update in `OPEN-WORK.md` (keyword estimate:
  ~140 KB of 409 KB pointer index for this cwd chain could move behind `paths:`, Python 116 KB) and
  this `handover.md`. Commit both with the next change.
- Two private repos with skills of their own got their part of the research as backlog items
  and a note there, committed locally, NOT pushed (named in the session, not here: this file is
  public).

## Decided, and why

- The research note is split: this public repo holds sections 1-4; material about private
  projects stays in those private repos.
- [55]-[85] are USER items ranked after the existing USER items [45]-[50], biggest first.
- Probe evidence = captured request bodies via an ANTHROPIC_BASE_URL proxy, never the model's answer.

## Still open, untouched

- See `OPEN-WORK.md` [55]-[85] in this repo (and the two private repos' own backlogs).

## Exact next action

Both follow-up probes for [55] are done (re-send: once per session; compaction drops the rule,
next matching read re-attaches it; section 3.1 tables). Next: brainstorm the [55] engine design
with the user (bitranox:process-plan-brainstorming): which fact categories move behind `paths:`,
the rule-file layout per level, and how the move stays reversible.

## How to verify

- `python3 docs/plans/probes/2026-11-26-rules-loading/run_probe.py` (S0 shows TOKEN_PROJ_CLAUDEMD = live)
- CI: `python3 <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`

## Lessons for the next nap

- (captured already) When a claude -p probe tree sits under /tmp/claude-<uid>, no CLAUDE.md or rule loads.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
