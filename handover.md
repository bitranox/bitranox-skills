# Handover - 2026-10-01 17:40, rank 12 steps 2 and 3 done: gate stays 0.5, Stop gate decide at 0.8 (7.31.0)

## In flight

- Nothing running. 7.30.10 (`03d4bc87`), the rank 12/99 backlog commit (`694707be`) and 7.31.0
  (`96ead362`) are on origin/master, CI green on all three.

## Committed, or not

- Everything this session made is committed and pushed. This file and the OPEN-WORK.md rank 12
  update are one commit on top of 7.31.0; it touches no plugin file, so no version bump.
- This machine's config now has `classifier_stop_signal = decide` (set 2026-10-01 on the user's
  word). It takes effect only once the installed plugin reaches 7.31.0: the user must type
  `/plugin marketplace update bitranox-skills` then `/reload-plugins`. Until then 7.30.9 logs no
  Stop-gate shadow rows (it treats decide as not-shadow) and still blocks on keywords as before.
- NOT committed, by design: `.plan/jev-gate-2026-10-01/` in the main checkout (PREREG, RESULTS,
  labels, scripts); `.plan/` is untracked, like every earlier panel record. The main checkout still
  has `TODO-JEV.md` staged (rank 150).

## Decided, and why - do not reopen

- skill_router gate stays at 0.5 (pre-registered blind panel, 22 gate-suppressed winners from rows
  the 09-27 panel never saw: 5 right, 9 defensible, 8 wrong; no threshold met 0.7 precision with
  noise <= 0.25; 10/10 planted controls wrong). The 09-27 "0.3 looked better" did not replicate.
- Stop gate decide = keywords OR Jev at 0.8 (user chose option 2 of 3 on 2026-10-01). Jev is not
  asked when the keywords already block; endorsement never fires; Jev silent = keyword verdict.
- Decide mode in skill-router acts on typed prompts only (`prompt_text.typed_by_a_person`), and
  `<cross-session-message` is in the not-typed registry (7.30.10).

## Decided against, and why

- Testing gate 0.3 vs 0.5 alone: only 6 fresh prompts lie in [0.3, 0.5), too few for a verdict.
  The panel judged every suppressed winner instead.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12's next is step (4), the first read of 7.31.0 Stop-gate decide
rows, after about a day of them. Rank 14 waits on the plugin update plus about two weeks of
notification rows. Rank 18 is deferred by the user. Rank 98 (Jev client rate limits) and rank 99
(locate_prompt misses mid-turn and slash-command prompts) are unmeasured. Rank 150 needs the user.

## Lessons for the next nap

- When a mode must act only on one input class, gate it on the POSITIVE predicate for that class
  (looks_typed), never on excluding one known negative (not a notification): every other machine
  turn leaks through. Measured: 278 hand-back and cross-session turns asked of Jev, 25 nudged.
- When a pre-registered A/B comparison turns out unpowered on the fresh data, widen to the question
  the data can answer (judge every item the knob changes, across all bands) and re-register before
  any label, rather than running the narrow test anyway.
- When a panel's sample comes from a locate step, count what it could not locate and by shape:
  145 of 400 rows were unlocatable, which silently restricted the panel to turn-boundary prompts.
- When a production rule is re-checked on fresh rows, report noise (picks on turns needing no
  skill) beside precision: precision held at 28/30 while noise rose from 1/19 to 10/30.
- tooling: the auto-mode classifier refused committing a handover's STALE marker as "Unrequested
  Commit", so meta-context-watcher's "mark it STALE in place" step leaves an uncommitted edit.
- (carried from the previous handover, not yet napped) When deriving keyword triggers from
  descriptions not written trigger-first, expect generic head words: 12 right of 140 nudges.
- (carried) When a classifier site moves from shadow to decide, check what the switch stops LOGGING.
- (carried) When describing which path handles an input class, check the matcher actually scores
  that class: "a notification goes to the keyword router" was true and inert (0 of 505).
- (carried) When an earlier backstop wakeup fires after its work is done, answer it in one line.
- (carried) tooling: right after a user-approved `git merge --ff-only` in the main checkout, the
  auto-mode classifier refused plain `git status` as "Irreversible Local Destruction"; seen once.
- (carried) tooling: `ci_wait.py` backgrounded with `> log; echo RC=$? >> log` is blocked by
  block-masked-gate-exit; backgrounding the gate alone worked.

## The exact next action

Rank 12 is the top open item. Its step (4) needs about a day of Stop-gate decide rows, which only
exist once the user has updated to 7.31.0. If they exist (rows with `site == stop_signal` and
`mode == decide` in `~/.claude/self-improve-audit/classifier-shadow-*.jsonl`), tally `decide_path`,
`families` and `latency_ms` per row; if not, ask the user to run the plugin update first. Rank 12
step (5), recall_rerank, waits on the user.

## Files that matter

- `plugins/bitranox/hooks/self-improve-gate.py` - `_regex_verdict`, `_request`, `_decide_stop_signal`.
- `plugins/bitranox/hooks/classifier.py` - `SITE_THRESHOLDS`, `NON_FIRING_FAMILIES`,
  `stop_signal_firings`, `decided_row`.
- `plugins/bitranox/hooks/tests/test_self_improve_gate_decide.py` - the decide contract.
- `plugins/bitranox/hooks/skill-router.py` - the typed-prompt gate at `main`.
- `.plan/jev-gate-2026-10-01/RESULTS.md` (main checkout) - the gate panel.

## How to verify

- `git log --oneline -3 origin/master`: 96ead362 (7.31.0) above 694707be and 03d4bc87.
- With CI's dependency set (see CLAUDE.md): `python -m pytest -q
  plugins/bitranox/hooks/tests/test_self_improve_gate_decide.py
  plugins/bitranox/hooks/tests/test_skill_router_decide.py` - 14 and 25 passed.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
