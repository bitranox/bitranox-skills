# Handover - 2026-10-06 08:25, wave D (rank 13, exit-code unification) shipped as 8.0.0

Working tree: the `jev-shadow` worktree (`.claude/worktrees/jev-shadow`, branch
`worktree-jev-shadow`) was the integration branch. Its gitignored `.plan/openwork-batch-2026-10-04/`
holds every batch record (DECISIONS-TAKEN.md, waveD/REPORTS.md, waveD/D-1/D-2/D-8-reply.json,
waveD/PARTITION.json, waveD/EXITCODES.md). It exists only in that worktree: copy the dir out before
removing the worktree.

## In flight

- Nothing is running. The contribution queue was closed against 8.0.0: 98 entries shipped or
  dropped with evidence, 19 remain open across 10 queues (#21, #58 -> OPEN-WORK [300], #77 ->
  [310], plus entries wave D never covered). `contrib_queue.py queues` (home
  `plugins/bitranox/skills/meta-self-improve/`) lists them; OPEN-WORK [200] is the item.

## Committed, or not

- On origin: 8.0.0 = cd960f03 (wave D, all 13 groups + D-7b, D-8b, D-14, D-win), CI green on every
  cell. 7.41.2 and 7.41.3 (Windows test fixes) and a concurrent session's 7.42.0 are below it.
- Committed with this handover: OPEN-WORK [360] (template repo's unpushed commits).
- Memory facts added this session: `reference-typesafe-jev-cost-and-latency-documented-and-measured`
  (KI level, closes C43) and `reference-a-background-subagent-survives-clear-and-reports-into-the-next-conversation`
  (bitranox-skills level).

## Decided, and why - do not reopen

- W-D1..W-D12 in `.plan/openwork-batch-2026-10-04/DECISIONS-TAKEN.md`, all as recommended: shim
  CLI exit 2; mirror gates judge what the change ships (index on commit, HEAD on push, the other repo
  at its published ref); migrate_memory writes .git/info/exclude; C99 closed with no guard; C35 and
  C27 stay advisory; C43 recorded as a fact; ci_wait default = every event except schedule; pfsense
  rm that removed nothing -> 2, partial multi-IP -> 1; same-command staging documented, not parsed;
  the four CLAUDE.md wordings applied (2bf51d4b); the release is 8.0.0 (MAJOR: exit codes and
  --json shapes changed for callers).

## Decided against, and why

- No deny/block for C86 (masked exit, <=15% real), C36 (sha literal, <=39% precision), D20 (PID
  literals, 1 of 189), C40 (md self-claims, 0 of 25) - priced by D-5 over the corpus.
- No post-read recall hook for C43, and no parser for same-command staging (W-D10).

## Still open, untouched

`OPEN-WORK.md` is the list. [17] (new USER item, the Claude Code module/behaviour feature) is the
top workable USER item; [12] and [14] wait on data; [18] is deferred by the user; [150]/[245] wait
on the user's housekeeping script; [300]-[360] are wave D's follow-ups.

## Lessons for the next nap

- When a partition gives fixers whole directories, a scope check must treat a directory entry as a
  prefix and diff each branch against ITS OWN base, or it flags owned files and every merged one.
- When a batch is green on Linux, run the whole suite on the Windows dev VM from a `git bundle` clone
  made with `-c core.autocrlf=false -c core.eol=lf` before the push: it found 6 defects the fixers'
  Linux runs missed, including Python 3.13's changed `ntpath.isabs('/r')`.
- When other sessions push to master during a long integration, MERGE origin/master into the
  integration branch rather than rebasing, so every fixer's base stays an ancestor.
- When a fixer cannot commit a file another group pins (a test asserting the old exit code), hand
  the callee to the test's owner with a byte-exact copy instead of leaving it uncommitted.

## The exact next action

Work OPEN-WORK [17]: find which Claude Code feature "write your own modules and change behaviour"
is (code.claude.com/docs raw .md pages and the changelog; `claude --version` for the installed CLI),
probe it on the installed CLI, then list concrete uses for bitranox-skills with a recommendation
each. Before that, merge nothing: master is clean at 8.0.0.

## Files that matter

- `OPEN-WORK.md`, `CHANGELOG.md` (8.0.0 Breaking section lists every moved exit code).
- `.plan/openwork-batch-2026-10-04/` in the jev-shadow worktree (see top).
- `plugins/bitranox/skills/compuse-toolbox/scripts/_cli_envelope.py` (the shared envelope helper).

## How to verify

- `git log --oneline -1 origin/master` shows cd960f03 or later.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci`
  ends with `repo-gate: all checks passed.`

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
