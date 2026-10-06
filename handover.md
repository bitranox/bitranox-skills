# Handover - 2026-10-06 12:40, stop_signal live adjudication done, 8.0.1 shipped

Working tree: the `jev-shadow` worktree (`.claude/worktrees/jev-shadow`, branch
`worktree-jev-shadow`), level with origin/master after the handover commit. Its gitignored
`.plan/` holds two records that exist nowhere else: `.plan/openwork-batch-2026-10-04/` (wave D)
and `.plan/jev-stop-2026-10-06/` (this session). Copy both out before removing the worktree.

## In flight

- Nothing is running. 8.0.1 is on origin (d63beefd), CI green on every workflow.

## Committed, or not

- On origin: 8.0.1 = d63beefd (`classifier.MIN_PROMPT_CHARS = {"correction": 40}`, tests, CHANGELOG,
  `docs/reference.md`, meta-memory-settings row + its `.skillwriter` checklist).
- Committed with this handover: OPEN-WORK [12] updated with step (4) and the 8.0.1 decision.

## Decided, and why - do not reopen

- stop_signal decide mode STAYS at 0.8: a pre-registered blind panel (ten opus judges, 8/8 planted
  controls right) found 67 of 92 live Jev blocks to be real lessons (73%, bar 60%). Record:
  `.plan/jev-stop-2026-10-06/` (PREREG.md, RESULTS.md, labels.json, key.json, judges/, scripts).
- `correction` kept (user's choice over dropping it) but counted only after a typed prompt of at
  least 40 characters. The user asked about 60: measured worse (4 real lessons lost against 2, no
  extra false block removed). 30 scored one item better on the same 14 blocks; left at 40.
- No lowering to 0.7: quiet turns scored 0.7-0.8 were only 31% real lessons.

## Decided against, and why

- A prompt-length rule for EVERY family: it lost 43 of 67 real lessons, because most admissions
  and root causes follow a bare "yes" or "continue".

## Still open, untouched

`OPEN-WORK.md` is the list. [12] next step is recall_rerank (count its eligible rows first; the
user said it waits for much more data); [14] waits on notification rows; [17] is the top workable
USER item after that; [18] deferred by the user; [150]/[245] need the main checkout.

## Lessons for the next nap

- When a gate or filter is keyed on one field (prompt length), measure where the positives'
  evidence actually lives before applying it to every class: most Stop-gate lessons sit in the
  assistant reply after a short prompt, so a prompt-length gate removed 43 of 67 of them.
- When a blind panel needs more items than one judge can read, split them into halves with their
  own five judges and their own planted controls per half, and dry-run the scorer on all-true
  labels first so the control check is proven able to fire.
- When a classifier shadow log grows during the analysis, freeze the data with a timestamp cutoff
  written into the pre-registration, or the strata counts drift between inventory and build.
- tooling: in a worktree-isolated session, a command that runs python with `$VAR` or `$(...)`
  arguments is refused; write the script to the scratchpad and pass literal paths.

## The exact next action

Work OPEN-WORK [10] (added at the end of this session, the user's "fix that"): ask the user which
fix they chose for the recall hook injecting other projects' handover notes on "read handover and
continue" (recommended: session-management words as filler), then TDD it with a firing-rate replay.
After that, [12] step (5): count the recall_rerank shadow rows on plugin >= 7.31.0, and put to the
user whether that is "much more data" yet; if not, move to [17].

## Files that matter

- `plugins/bitranox/hooks/classifier.py` (`MIN_PROMPT_CHARS`, `stop_signal_firings`)
- `plugins/bitranox/hooks/self-improve-gate.py` (`_decide_stop_signal`)
- `plugins/bitranox/hooks/tests/test_self_improve_gate_decide.py`
- `.plan/jev-stop-2026-10-06/` in the jev-shadow worktree (gitignored)

## How to verify

- `git log --oneline -1 origin/master` shows the handover commit on top of d63beefd.
- `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/test_self_improve_gate_decide.py -q`
  passes (25 tests).

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
