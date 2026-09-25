# Handover - 2026-09-26, rank 8 HIGH batch shipped as 7.25.3; the MED batch is next

## In flight

Nothing running and nothing part-done. Rank 8's three HIGH findings are fixed, released and
CI-green; its MED and LOW findings are untouched. The `OPEN-WORK.md` rank 8 line carries the
state and the next step.

## Committed, or not

- **In git and pushed:** 7.25.3 (`2087861b`) and this handover on top. Both workflows (`ci`,
  `workflow`) are green on `2087861b`.
- **Not in git, by design (gitignored, main checkout):**
  `.plan/rank8-review-2026-09-26/REVIEW.txt` (all 17 reviews, every finding with file:line,
  severity, CONFIRMED or SUSPECTED) and `review-brief.txt`.
- This worktree (`.claude/worktrees/jev-roster`) sits at origin/master with a clean tree; it is
  one of the rank 160 worktrees to wtclean from the main checkout when done.

## Decided, and why - do not reopen

- **fleet_ssh never re-runs a command.** Probed on OpenSSH 10.2 against localhost with a wrong-key
  known-hosts file: `StrictHostKeyChecking=no` prints the banner and proceeds (no "Host key
  verification failed"); `yes` and `accept-new` print the fatal line. Heal mode always sets `no`,
  so the old retry could fire only on a remote command's own inner ssh failure. The heal keys on
  ssh's `Offending <TYPE> key in <file>:<line>` naming the tool's own known-hosts file.
- **winlog treats a trailing NUL run as padding, not text**, keeping its first NUL only when it
  closes a UTF-16 code unit, decided by whether an earlier chunk is wide or the last chunk does
  not read as clean narrow text. The residual (a single-line pure-CJK UTF-16 file whose bytes
  are all printable ASCII, then padded) is accepted as byte-level ambiguous.
- **detectors.js stops descending at any element whose computed overflow-y is not `visible`**,
  and measures text per text node, because a Range over the body spans clipped boxes too.

## Decided against, and why

- Touching the winlog LOW "narrow line then a U+xx00 segment": a different code path, and the
  bytes are genuinely ambiguous without padding.
- Fixing the pre-existing ruff findings (I001, PLW1510, RUF022) in the touched files: ruff is not
  gated in this repo and those predate this change.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 8 (USER): about 25 MED and about 85 LOW findings from the review.
- Rank 175 (FOUND): the user's two decided implementations - fold (a) into the rank-8 D1 batch.
- Rank 160 (FOUND): finished worktrees, including this one; wtclean from the main checkout.

## Lessons for the next nap

- When a read-only reviewer runs probes, tell it to cd into its scratch dir: a probe run with the
  checkout as cwd and a relative redirect (`> o 2> e`) wrote untracked files into the checkout.
- When a brief forbids the network, say how a probe that fakes a tool must fail closed: a fake-PATH
  probe that dropped the fake fell back to the real gh and npm and made real calls.
- When a fix makes a detector more permissive or a refusal broader, expect the regression beside
  it: most of the review's new findings were a fix widening or narrowing past the case it named.
- When a retry or heal path is gated on how an external tool fails, probe the real tool under the
  exact options the code itself sets before trusting a fixture: fleet_ssh's retry was unreachable
  under its own StrictHostKeyChecking=no, and its tests modelled a refusal ssh never emits there.
- When reproducing a reviewer's HIGH, widen the arm beyond the case they named: the winlog finding
  was reported as parity-dependent and lost the marker at every padding length and line shape.
- When a stub harness replaces a browser API, make the stub faithful to the real API before
  reading RED: the first RED was the old code crashing on the stub's Range, not the defect.
- tooling: factedit apply without --stage-dir leaks a /tmp/factedit-* dir per call, and its tests
  never pass one (in REVIEW.txt under M2).
- tooling: the WRONG VENV nudge fires on commands that already start with `env -u VIRTUAL_ENV`.
- tooling: ci_wait under a foreground `timeout` dies with exit 143 and no output when CI outlasts
  the bound; `gh run list --commit <sha>` was needed to see the state.

## The exact next action

Rank 8 is the top open USER item. Read `.plan/rank8-review-2026-09-26/REVIEW.txt` in the main
checkout and re-run the arm and control of each MED finding against HEAD, one group at a time,
starting with the weightiest: R (pluginprune deletes an enabled plugin's only version beside a
symlinked sibling; ignores a quoted `"$HOME"/...` pin), T1 (ci_triage keyword and `--step` name
regressions), CALLERS (toolbox-nudge and block-masked-gate-exit tell agents `uv run gate.py`).
The ones that reproduce become fix batches by group, TDD, and ship as releases.

## Files that matter

- `.plan/rank8-review-2026-09-26/REVIEW.txt` (main checkout, gitignored) - every finding.
- `.plan/rank10-skillscript-2026-09-25/adj/<group>/verdicts.txt` - what each group was asked to fix.
- `OPEN-WORK.md` rank 8 - the summary and the next step.

## How to verify this still stands

- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.25.3.
- `gh run list --commit 2087861b092f5fe717b986f0f911d1a1174dd5a4` shows `ci` and `workflow` success.
- `grep -c '^## ' .plan/rank8-review-2026-09-26/REVIEW.txt` in the main checkout prints 17.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
