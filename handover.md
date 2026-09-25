# STALE - read 2026-09-26, work continued

## In flight

Nothing running. The independent review of the 7.24.0-7.24.1 fix groups (OPEN-WORK rank 8) is
finished: 17 reviewers, all reported, no code changed. Rank 8 stays OPEN because its findings are
not fixed yet; the line in `OPEN-WORK.md` carries the counts, the three HIGH findings and the next
step.

## Committed, or not

- **In git and pushed:** this handover and the rank-8 update in `OPEN-WORK.md`, on top of
  `c27198fc`. No code changed this session. CI on `68414a2c` (7.25.2) is green on every workflow,
  re-checked live with ci_wait.
- **Not in git, by design (gitignored, main checkout):**
  `.plan/rank8-review-2026-09-26/REVIEW.txt` (all 17 reviews condensed, one section per group,
  every finding with file:line, severity, CONFIRMED or SUSPECTED) and `review-brief.txt` (the
  brief every reviewer worked from).
- **Not durable:** each reviewer's probe scripts and outputs sit in this session's scratchpad
  (`/tmp/claude-1000/...jev-roster/b0234229-.../scratchpad/review-<group>/`). Re-derive a probe
  from REVIEW.txt's description rather than counting on those files surviving.

## Decided, and why - do not reopen

- **One reviewer per group commit plus one CALLERS reviewer**, on opus, each re-running its
  verdicts' arm and control at HEAD and required to show an executed failing input for anything
  called CONFIRMED. The group commits were already self-tested by their fixers, so a reviewer who
  read the diff without running it would have added nothing.
- **Reviewers judged HEAD, not the group commit**, because 7.25.0-7.25.2 touched many of the same
  files; each checked `git log <group-commit>..HEAD -- <file>` before reporting.
- **The coordinator re-ran nothing yet.** Every finding in REVIEW.txt is a reviewer's executed
  claim. Re-running the HIGH and MED arms is the first step of the fix work, not a formality.

## Decided against, and why

- Fixing any finding in this session: the session was past the handover threshold, and the
  findings need a coordinator re-run before they become fix briefs.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 8 (USER): the review's findings - 3 HIGH, about 25 MED, about 85 LOW.
- Rank 175 (FOUND): the user's two decided implementations (schematic below threshold exits 1;
  repo-gate's padding-only waiver) - fold (a) into the rank-8 D1 batch.
- Rank 160 (FOUND): finished worktrees, including this `jev-roster` one; wtclean them from the
  main checkout, never `rm -rf`.

## Lessons for the next nap

- When a read-only reviewer runs probes, tell it to cd into its scratch dir: a probe run with the
  checkout as cwd and a relative redirect (`> o 2> e`) wrote untracked files into the checkout
  twice this session.
- When a brief forbids the network, say how a probe that fakes a tool must fail closed: a fake-PATH
  probe that dropped the fake fell back to the real /usr/bin gh and npm, which made 3 real API
  calls and wrote an npm log under ~/.npm.
- When a fix makes a detector more permissive or a refusal broader, expect the regression beside
  it: most of the review's new findings were a fix widening or narrowing past the case it named
  (winlog parity, ci_triage keywords, detectors.js extent, find_cache_candidates purity).
- tooling: factedit apply without --stage-dir leaks a /tmp/factedit-* dir per call, and its tests
  never pass one (1627 such dirs on this machine; in REVIEW.txt under M2).

## The exact next action

Rank 8 is the top open USER item. Read `.plan/rank8-review-2026-09-26/REVIEW.txt` in the main
checkout, then re-run the arm and control of each of the three HIGH findings yourself against HEAD
(T6 winlog NUL padding, T3 fleet_ssh inner "Host key verification failed", W1 detectors.js scroll
containers). The ones that reproduce become the first fix batch, TDD, one release.

## Files that matter

- `.plan/rank8-review-2026-09-26/REVIEW.txt` and `review-brief.txt` (main checkout, gitignored).
- `.plan/rank10-skillscript-2026-09-25/adj/<group>/verdicts.txt` - what each group was asked to fix.
- `OPEN-WORK.md` rank 8 - the summary and the next step.

## How to verify this still stands

- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.25.2.
- `grep -c '^## ' .plan/rank8-review-2026-09-26/REVIEW.txt` in the main checkout prints 17.
- `git status --porcelain` in this worktree is empty.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
