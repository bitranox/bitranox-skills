# Handover - 2026-10-15 14:00, [12] step (6) done, recall decide at 0.9 shipped (8.23.0); next is the due dream, covering [22]

## In flight

- Nothing part-done. 8.23.0 (f3548893) is on origin/master, pre-push gate passed (12,477 tests),
  CI green (`ci` and `workflow` runs).

## Committed, or not

- This handover is committed from the worktree `.claude/worktrees/recall-threshold-09` (branch
  `worktree-recall-threshold-09`), which holds nothing else uncommitted. Remove it with
  git-worktrees' `wtclean.py recall-threshold-09 --apply` (after `landed.py`) once this is on
  origin.
- The MAIN checkout's `master` is behind origin, and its `handover.md` carries an uncommitted STALE
  first line written by this session. Discard that line (`git checkout -- handover.md` there) and
  fast-forward `master` before working in the main checkout.
- Machine-local, not in git: `~/.claude/.bitranox-memory.json` now has
  `classifier_recall_rerank = decide` (set 2026-10-15 11:14:21Z through meta-memory-settings).
- The panel record is gitignored: `.plan/jev-recall-2026-10-15/` in the MAIN checkout (PREREG.md,
  RESULTS.md, labels.json, judges/, build_packets.py, score.py). Its key is in this session's
  scratchpad, not in the repo.
- Open sessions keep old plugin text until `/plugin marketplace update` plus `/reload-plugins`.

## Decided, and why - do not reopen

- Recall decide had NEVER run: the config was last written 2026-10-02 and said `shadow`, with 0
  decide rows in the log; the 10-08 handover's "already set" was false. The user chose to run the
  step (6) panel on the 322 fresh shadow rows (shadow and decide build the same request in
  `_rerank_request`) and to set decide the same day. Logged in EXECUTION-USER-REVIEW.md.
- Panel (pre-registered, 10 opus judges, 8/8 controls, 88% unanimous, every Jev-kept pair
  judged): 47% relevant at 0.8, 65% at 0.9, keywords 7%. Branch 4 fired; the user chose 0.9.
- A new test pins each decide row's "at N or more" in meta-memory-settings SKILL.md to
  `SITE_THRESHOLDS`, so a retune cannot leave the doc on the old bar.

## Decided against, and why

- 0.85: 56% on these labels, still under the 60% bar, and chosen after seeing labels, so it would
  need its own panel.

## Still open, untouched

- [12]: its remaining step waits for decide rows (read `decide_path` for the fallback-deadline
  share in a few days, earliest about 2026-10-18).
- A memory consolidation is due (`bitranox:meta-dream-tree`); [22] is, in the user's words,
  "a dream job".
- Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a handover or doc says a config knob is set, read the config file and its mtime before
  building on it: a false "already set" made a step wait a week for rows that could not exist.
- When planning a panel or count on decide-mode rows, count the log's rows BY MODE first; rows
  without a mode field are shadow rows whatever the docs say.
- When a doc table restates a code constant (a threshold, a deadline), pin it with a test that
  reads the row and compares it with the constant.
- tooling: the repo-gate version check also needs `pyproject.toml` bumped beside `plugin.json`;
  the first `--ci` run failed on that alone.

## The exact next action

[12] is the top open item but is blocked on time (its decide-row read is earliest about
2026-10-18), and [18] is deferred by the user, so the next live USER item is [22]. Run
`bitranox:meta-dream-tree` (due), scoped to include [22]: find facts about superseded library or
tool versions (btx-lib-mail first, per the user) at every level, and fix or retire them.

## Files that matter

- `OPEN-WORK.md` ([12] line, its "step (6) DONE" note)
- `plugins/bitranox/hooks/classifier.py` (`SITE_THRESHOLDS`), `plugins/bitranox/hooks/recall-memory.py`
  (`_decide_recall`)
- `plugins/bitranox/skills/meta-memory-settings/tests/test_settings.py` (decide-row pin)

## How to verify

- `uv run <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --ref origin/master` exits 0 on the
  commit carrying this handover (and 8.23.0's CI, f3548893, is green).
- `grep -c '"recall_rerank": 0.9' plugins/bitranox/hooks/classifier.py` prints 1.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
