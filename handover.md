# Handover - 2026-11-26 17:11 CET (session "skill-research")

## In flight (read first)

Working the Claude Code 2.1.33x research list (`docs/plans/2026-11-26-claude-code-2-1-332-context-research.md`,
backlog items [60]-[85]). Work lives in the worktree `.claude/worktrees/research-cc-2-1-332`
(branch `research-cc-2-1-332`, pushed as `HEAD:master`).

- [55] (path-scoped `.claude/rules` for the memory index) is CLOSED by the user's decision: not
  built. The measurement and the reopen condition are in section 3.1 of the research note.
- The commit closing [55] is being pushed; check with `git fetch && git log origin/master --oneline -3`.
- A CI watch on the earlier probe commit may still report into this session; it needs no action
  unless it reports a failure.
- Two private repos with skills of their own got their part of the research as backlog items and
  a note there, committed locally, NOT pushed (named in the session, not here: this file is public).

## Decided, and why

- [55] not built (user, 2026-11-26): only 14-26% of recent project sessions touch no `.py` file,
  so the average saving is 4-7% of the index, against an engine change and a fact gap after every
  compaction.
- The research note is split: this public repo holds sections 1-4; material about private
  projects stays in those private repos.
- Probe evidence = captured request bodies via an ANTHROPIC_BASE_URL proxy, never the model's answer.

## Still open, untouched

- `OPEN-WORK.md` [60]-[85] in this repo (and the two private repos' own backlogs).

## Exact next action

Ask the user whether to start [60] (split oversized SKILL.md files into `references/`,
`compuse-toolbox` first, 409 KB). That skill is a mirrored or plain bitranox skill: check
`repo-gate.py --mirrors` and its decisions ledger (`hooks/skill_decisions.py show compuse-toolbox`)
before editing it.

## How to verify

- `python3 docs/plans/probes/2026-11-26-rules-loading/run_probe.py` (S0 shows TOKEN_PROJ_CLAUDEMD = live)
- CI: `python3 <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`

## Lessons for the next nap

- (captured already) When a claude -p probe tree sits under /tmp/claude-<uid>, no CLAUDE.md or rule loads.
- (queued for meta-context-watcher) When a checkpoint goes into a tracked file of a public repo, name no private repo, project or org.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
