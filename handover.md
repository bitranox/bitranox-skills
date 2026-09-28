# Handover - 2026-09-28 23:55, ranks 91/93 closed, 160 down to 14, three bose containers deployed

## In flight

- Nothing running. Everything this session made is committed and pushed.

## Committed, or not

- bitranox-skills: 7.30.1 (`f39f7e17`) shipped and green on every CI cell; backlog commits up to
  this handover on origin/master. This machine still RUNS plugin 7.30.0 until the user types
  `/plugin marketplace update bitranox-skills` then `/reload-plugins`.
- kct-bose `12ebef3`, rct-bose `2051c12`, wct-bose `23cefae`: pushed AND deployed (see rank 91).
- Tree-top memory store: `9f25c66` pushed; since then 4 more uncommitted changes have appeared in
  it (not from this session's work) - the next dream commits them.
- NOT committed, by design: the main checkout still has `TODO-JEV.md` and `PLAN-JEV-SKILL.md`
  staged plus a one-line STALE-marker edit to `handover.md`, and sits behind origin (rank 150).

## Decided, and why - do not reopen

- Rank 91 container route is a plain git clone at `/opt/soundtouch-decloud`, kept current by each
  machine's deploy hook, NOT the Claude Code plugin (user decision in the decision review): the
  containers should not need Claude Code to run a Python script. `SOUNDTOUCH_DECLOUD_DIR` overrides
  the path on a dev box.
- The three bose machines are kept identical (user: "they should work the same with the latest
  version"): same shim blob in all three; the clone step is bash in kct-bose, Python in rct/wct.
- A dirty worktree counts as landed when every dirty file's blob is SOME version of that path in
  origin/master's history, not only the current one (user confirmed). Checker:
  `.plan/wt_landed_check.py` in the main checkout (gitignored, read-only).
- `PLAN-JEV-SKILL.md` is kept (moved to `.plan/`), not deleted, when rank 150 is done: a 1,114-line
  plan for an unstarted `compuse-jev-judge` skill that no backlog line records.
- pytest/httpx2/PyYAML/lxml/defusedxml/ruamel.yaml installed into the Python 3.14 user site (user
  choice), so the repo-gate commit hook works in a session launched without a venv.

## Decided against, and why

- Running the rank-150 discard and the rank-160 `--discard-uncommitted` removals past an auto-mode
  refusal: the refusals said to stop and let the user decide. The user later asked for the 25
  landed worktrees to go, which is the only reason those were removed.
- Deleting the 14 worktrees whose content never reached master: nothing proves it landed.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on a day of 7.30.0 router rows (7.30.0 shipped 13:41
today). Rank 18 is deferred by the user. Rank 150 waits on the user running its four commands
(in its line). Rank 160 has 14 worktrees to read with the user one at a time. Ranks 175/177/178
are user decisions.

## Lessons for the next nap

- When a /goal's remaining step is refused by the auto-mode classifier, say so once and ask the
  user to clear or unblock it: the goal Stop hook re-blocks every turn and cannot be satisfied.
- When a doc says a script runs inside a container, check the container has what the script needs
  before fixing a path: CT 11000 had neither the plugin the fix assumed nor `uv` on the
  `pct exec` PATH (`/sbin:/bin:/usr/sbin:/usr/bin`).
- When the user asks whether sibling machines got the same change, search the sibling REPOS by
  machine name, not the changed file name: a find for `bose_onboard.py` missed that rct/wct share
  the runbook and lacked the capability entirely.
- When judging whether a dirty worktree's content landed, compare each file's blob to every
  version of that path in master's history, not to current master: 25 of 39 had landed and been
  superseded, and a current-master diff called all 39 unlanded.
- When RED-running tests against an old version of code that calls `os.execv`, expect the test
  process to be REPLACED mid-run: the log truncates and reads like a crash.
- tooling: the message file for `git commit -F` was again written in the same command as the
  commit; the gate blocked both and the file never existed (recurrence of
  feedback-repo-gate-pre-evaluates-the-pending-commit-command).
- (carried) When a prompt-time hook filters turns the person did not type, test the text the HOOK
  receives, not the transcript's stored form: the transcript wraps a subagent hand-back as
  "Another Claude session sent a message:", while UserPromptSubmit gets the bare `<agent-message`
  envelope.
- (carried) When quoting a rate from live router rows, first count how many locate to a typed
  prompt: of 230 answered rows only 57 did (89 hand-backs, 43 isMeta scheduled prompts, 40 gone
  transcripts).
- (carried) When running compuse-toolbox mutation_arm in bitranox-skills, launch it with system
  `python3`: the repo's `.venv` has no pytest, and the arm then reads `inconclusive` with
  `failure: null`.
- (carried) When ruff reports dozens of findings in a repo with no ruff config, compare against the
  file at HEAD with `--select E,F,W,B` before treating any as yours: ruff 0.16's default set flags
  this repo's %-format house style everywhere.
- (carried) tooling: the worktree-isolation guard refuses `env -u VIRTUAL_ENV uv run ...` and a
  `git push ... > file; echo RC` chain; put the first in a scratchpad script and run the push bare.
- (carried) When a test builds a shell command around a filesystem path, write the path
  double-quoted in forward-slash form: unquoted, Windows backslashes are eaten by bash and by the
  tokenizer alike, so the test silently exercises a fallback on the Windows cell.
- (carried) When a hook must judge the repository a Bash command acts on, resolve it from the
  event cwd plus the command's own `cd`/`git -C` (`shell_text.git_verb_dir`), never from the
  hook's working directory, which is where the session sits.
- (carried) When a design note justifies a trigger as "early beats never", measure how early
  before keeping it: the decision-review block on a running goal was early in 13 of 16 sessions,
  by up to 583 min.

## The exact next action

Rank 97 is the top-ranked item that is not waiting on data, a deferral or the user (12, 18 are
ahead of it and cannot move). Start with:

```
python3 plugins/bitranox/skills/meta-claude-hooks/scripts/hookdoc_stamp.py check
```

then read the three new upstream H4 sections in code.claude.com/docs/en/hooks.md, update
`plugins/bitranox/skills/meta-claude-hooks/references/configuration.md` (and `events.md` for the
dropped SessionStart field) through bitranox:meta-skill-writer's checklist, run `coverage`, then
`stamp --write`. If the user is present first, settle rank 150 (their four commands) and rank 175
(three decisions) with them.

## Files that matter

- `OPEN-WORK.md` - the backlog; ranks 91, 150, 160 carry today's detail.
- `plugins/bitranox/skills/meta-claude-hooks/references/` - rank 97's target.
- the three bose machine repos in the private tree (`kct-bose`, `rct-bose`, `wct-bose`):
  `bose_onboard.py` and `upd_posthook_local.{sh,py}` - rank 91's shipped change.
- `.plan/wt_landed_check.py` (main checkout, gitignored) - rank 160's checker.

## How to verify

- `git -C <repo> log --oneline -1` on the three bose repos: 12ebef3 / 2051c12 / 23cefae.
- `python3 .plan/wt_landed_check.py` from the main checkout: 14 worktrees, each with a non-empty
  list of unlanded files.
- `git worktree list | wc -l` in the main checkout: 16 (main, openwork-upstream, the 14).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
