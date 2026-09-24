# Handover - written 2026-09-24 ~16:45, nothing in flight

## In flight

Nothing. 7.15.1 is pushed (`a8fedd3`) with CI passing (`workflow=success ci=success`, checked
with `ci_wait` on the full sha). This file and the `OPEN-WORK.md` edits below are the only
changes after it.

## Committed, or not

- **Committed and pushed:** 7.15.1. It fixes toolbox-nudge `pushcheck` (a push on a later line,
  behind `VAR=`/`env -u`, behind `git -C`/`-c`) and `backstop` (a polling loop with a short
  sleep, and `ps | grep || echo FINISHED`). It also fixes the order-dependent test failure
  (rank 78).
- **Committed with this handover:** `OPEN-WORK.md` gains the unanswered Jev recommendation
  appended to rank 12, and a new rank 150 (a staged `TODO-JEV.md` in the main checkout).
- The worktree `.claude/worktrees/nudge-recall-fix` stays in place. Remove it with `wtclean`
  once this handover is on master.

## Decided, and why - do not reopen

- **Jev has no role for the compuse-toolbox jigs.** The router's option list holds one entry per
  `skills/*/SKILL.md`, so all 29 jigs share the single `compuse-toolbox` option. A jig is needed
  when a command is about to be typed, not when a prompt arrives, and the command-time channel
  (`hooks/toolbox-nudge.py`) is the right one. Replaying it for misses found regex gaps, not a
  problem that needs a model.
- **The measured miss rate is about 0.2%** (roughly 130-150 real misses in 79k calls). The first,
  wide pass said 8%; that was the oracle's own breadth, and reading the rows is what brought it
  down.
- **git_state was deliberately left out of 7.15.1.** Half of its candidate loops run over refs or
  files inside one repo, not over repos. It is rank 82, with the approach in its `next:`.
- **Rank 78's recorded diagnosis was wrong.** There was no registry leak: the fake shipped dir sat
  two levels under pytest's shared temp root. The closed line records the real cause.

## Decided against, and why

- **Jev behind the toolbox nudge:** PreToolUse runs on every tool call, and ~0.8-1.2 s per call
  is too costly for recall that regexes already reach.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 14 (USER): the approved invented-identifier guard.
- Rank 12 (USER): Jev. The per-site decide recommendation is waiting on the user; see the line.
- Rank 82 (FOUND): the git_state recall gap.
- Rank 150 (FOUND): the staged `TODO-JEV.md` in the main checkout.

## Lessons for the next nap

Already captured this session, so the nap should find it present:
`feedback-measure-a-guard-s-misses-with-an-independent-wider-oracle-then-read-narrow-classes`.

Not yet captured, one line each:

- When a replay changes a rule, diff old against new verdicts call by call and read every
  changed one; the class count used to estimate the fix (about 30 pushes) undercounted the real
  change (166), because the biggest group (`git -c credential.helper=... push`) was outside the
  class regex.
- When a test fakes a directory that production code walks upward from (`.parent.parent`), put
  the fake inside a tree the test owns; a fake directly under `tmp_path` walks out into pytest's
  shared temp root and sees every other test's files.
- When a worktree-isolated session refuses a Bash call as "too complex", move the logic into a
  script file with literal paths (or split out the `git` part); inline test strings naming `git`,
  `env -u` or computed `python3 $G` arguments are what trip it.
- tooling: toolbox-nudge fired falsely four times in this session, on measurement work rather
  than chores: `srccount` on `find | wc -l` over transcripts, `transcript_index` on a Write naming
  the path, `procsig` on a test-data file, `factedit` on a `wc -l` of a fact. That is precision
  evidence for the next time its rules are priced.
- (carried over, not yet captured) When a cheap proxy and a careful parser disagree about the same
  quantity, suspect the PROXY first.
- (carried over) tooling: `build_packets2.py` matches prior labels by positional id (`p00`), so
  reusing it on a different prompt set reports a meaningless overlap; key on prompt text instead.

## The exact next action

`OPEN-WORK.md` rank 10, the top-ranked open item: the skills-and-scripts review, one subagent
each, asking before changing anything. It is a USER item and nobody has started it. Start by
sizing it: count the targets under `plugins/bitranox/skills/*/` and `plugins/bitranox/hooks/`,
and write the count into the line.

## Files that matter

- `plugins/bitranox/hooks/toolbox-nudge.py` - `_SHELL_ONLY_RULES` (pushcheck, backstop),
  `_sibling_skill_script`
- `plugins/bitranox/hooks/tests/test_toolbox_nudge.py` - `_no_shipped_tree`, and the recall tests
  after `test_a_ci_poll_loop_routes_to_ci_wait_not_backstop`
- `plugins/bitranox/skills/compuse-toolbox/scripts/guard_replay.py` - the replay the measurement
  wraps

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/nudge-recall-fix
uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
uv run --no-project --with pytest python -m pytest -q -p no:randomly \
  plugins/bitranox/skills/meta-self-improve/tests/test_jig_probe.py \
  plugins/bitranox/hooks/tests/test_toolbox_nudge.py
```

The gate prints `repo-gate: all checks passed`. The second run is the ordering that used to fail
rank 78, and it must pass.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
