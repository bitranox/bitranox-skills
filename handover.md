# Handover - 2026-10-01 22:45, ranks 97/98/160 closed, rank 99 queued shape fixed (7.31.4)

## In flight

- Nothing running. 7.31.1 (rank 97, meta-claude-hooks refresh) and 7.31.4 (rank 99 queued
  prompts) are on origin/master with CI green on every job; the rank 160 and 98 closures are too.
- The installed plugin is 7.31.4 and complete (81 skills, 2,087 files, identical to the
  marketplace clone).

## Committed, or not

- Everything this session made is committed and pushed. This file and the OPEN-WORK.md lines for
  ranks 190/191 are one commit on top of 7.31.5 (a peer session's release); no plugin file, no bump.
- The MAIN checkout still has two things this session did not commit: `TODO-JEV.md` staged (rank
  150, the user's call) and `handover.md` modified - only the STALE marker on the 17:40 handover,
  which this file supersedes, so `git checkout -- handover.md` there before the fast-forward.
- `.claude/worktrees/` holds only `close-98`, which this session used for the closing commits; it
  has nothing that is not on origin/master once this commit is pushed.

## Decided, and why - do not reopen

- Rank 98 (Jev rate limits) closed as refuted: 0 HTTP 429 in 4,881 hook rows, including 1,252
  recall_rerank bursts of 20-30 requests on 8 workers; replays are serial and already retry 429.
- Rank 160: all 16 worktrees removed. Each was checked against origin/master before removal: added
  lines present and removed lines gone, or superseded/padding-only (the closing line names each).
- A typed queued prompt is the `queued_command` attachment with `origin.kind == "human"`; every
  queued prompt is `absorbed_mid_turn` and recorded once, so reading it cannot double-count.

## Decided against, and why

- No rate limiter or pooled Jev client: nothing measured needs it (rank 98 line has the numbers).
- The slash-command shape of rank 99 (`/goal do 3-7`, ~19 prompts) was NOT taught to human_text:
  `looks_typed` excludes every `<command-` record on purpose, so it is the user's decision.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 waits on about a day of Stop-gate decide rows (20 so far) and
its step 5 on the user; rank 14 on two weeks of notification rows; rank 18 is deferred by the user;
rank 99 now needs the user's slash-command decision; ranks 190 and 191 are new this session.

## Lessons for the next nap

- When a backlog item cites a drift snapshot or a rate figure, re-run the measurement first: rank 97
  had grown a fourth section since filing, and rank 98's 80 req/s premise never produced a 429.
- When estimating how many rows a fix will recover, split the shape by the record's OWN origin
  field first: the queued shape looked like ~560 rows and was 112, the rest subagent hand-backs.
- When a skill suddenly answers "Unknown skill" or the reload count drops, compare the installed
  cache version dir against the marketplace clone (skill dirs and file count) before anything else.
- When removing a worktree whose dirty files differ from master, check both directions per file -
  added lines present on master AND removed lines gone - then whitespace-normalise for padding-only.
- tooling: a worktree-isolated session refuses any Bash command whose text names git in a compound
  or inline-script form (python -c, heredoc, for loop, `git -C`); write the script to the
  scratchpad and run it, or use Edit, one plain git command per call.
- tooling: `ExitWorktree remove` counts a commit already on origin as "would be discarded" when
  local master is behind; check `git log origin/master..HEAD` is empty, then pass discard_changes.
- (carried, not yet napped) When a mode must act only on one input class, gate it on the POSITIVE
  predicate for that class, never on excluding one known negative.
- (carried) When a pre-registered A/B turns out unpowered on fresh data, widen to the question the
  data can answer and re-register before any label.
- (carried) When a panel's sample comes from a locate step, count what it could not locate and by
  shape.
- (carried) When a production rule is re-checked on fresh rows, report noise beside precision.
- (carried) tooling: the auto-mode classifier refused committing a handover's STALE marker as
  "Unrequested Commit", so the "mark it STALE in place" step leaves an uncommitted edit.
- (carried) When deriving keyword triggers from descriptions not written trigger-first, expect
  generic head words: 12 right of 140 nudges.
- (carried) When a classifier site moves from shadow to decide, check what the switch stops LOGGING.
- (carried) When describing which path handles an input class, check the matcher actually scores
  that class.
- (carried) tooling: `ci_wait.py` backgrounded with `> log; echo RC=$? >> log` is blocked by
  block-masked-gate-exit; background the gate alone.

## The exact next action

Rank 12 is the top open item; its step 4 reads the Stop-gate decide rows once about a day of them
exists (rows with `site == stop_signal` and `mode == decide` in
`~/.claude/self-improve-audit/classifier-shadow-*.jsonl`; 20 at 22:00 on 2026-10-01): tally
`decide_path`, `families` and `latency_ms`. If that day has not passed, ask the user the rank 99
slash-command question (should `/goal do 3-7` count as typed?), which is blocking that item.

## Files that matter

- `plugins/bitranox/hooks/transcript_turns.py` - `human_text`, `_queued_human_text`, `_scan`.
- `plugins/bitranox/hooks/tests/test_transcript_turns.py` - the queued-prompt tests.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `locate_prompt`,
  `_typed_spans`, `unlocated_reason` (rank 191).
- `plugins/bitranox/skills/meta-claude-hooks/references/` - refreshed against hooks.md 2026-10-01.

## How to verify

- `git log --oneline -6 origin/master` shows f4739943 (7.31.4) and 19d9ade5 (7.31.1).
- With CI's dependency set (see CLAUDE.md): `python -m pytest -q
  plugins/bitranox/hooks/tests/test_transcript_turns.py` - 39 passed.
- `uv run plugins/bitranox/skills/meta-claude-hooks/scripts/hookdoc_stamp.py check` - CURRENT
  unless upstream moved again.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
