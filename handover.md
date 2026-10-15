# Handover - 2026-10-15 16:20, [22] stale-version facts: code done on a branch, skill text next

## In flight

- [22] + [430], one change. CODE DONE and committed, NOT pushed: branch `stale-version-pass`,
  commit 1e937bba, in the worktree `.claude/worktrees/recall-threshold-09` (the worktree name is
  historical; do NOT wtclean it). Plugin bumped to 8.24.0 there with a CHANGELOG entry; 8.24.0 is
  not on origin.
  - `plugins/bitranox/skills/meta-dream-tree/versionrot.py` + `tests/test_versionrot.py` (37 tests)
  - `meta-self-improve/jev_shadow.py`: `items --sample N --seed`, `run --dream ID`, `receipt`
  - `meta-dream-tree/dream_state.py`: `done` now REQUIRES `--kind nap|tree`; tree takes
    `--dream ID [--jev-skip SITE=REASON]` and refuses (exit 1) while a switched-on site is unfed
  - `jev_sites/dream-prune.json`: third question `version_bound` (version 2)
  - `hooks/capture_constraints.py`: version-history advisory (21 of 1,602 real hooks fire)
- SKILL TEXT NOT WRITTEN YET. The skill-writer RED is done and recorded in
  `meta-dream-tree/.skillwriter/red-20261015-version-rot-and-jev-receipt.md` (committed); its
  "What GREEN must make true" section is the spec. Until the text lands, the shipped SKILL.md
  files still say plain `dream_state.py done`, which the new code REFUSES - so the branch must
  not be pushed without the text.

## Committed, or not

- Committed on the branch: everything above. Unpushed.
- This handover and the OPEN-WORK edits are committed from a separate worktree
  `.claude/worktrees/handover-1015` (branch `handover-1015`, from origin/master) and pushed to
  master. Remove that worktree after this is on origin.
- MAIN checkout: `master` is behind origin and its `handover.md` carries an uncommitted STALE
  line from an earlier session; auto mode refused discarding it. To fix, the user runs:
  `! git checkout -- handover.md && git merge --ff-only origin/master` (from the main checkout)
- Gitignored, main checkout: `EXECUTION-USER-REVIEW.md` has the 2026-10-15 13:47Z user decision.

## Decided, and why - do not reopen

- [430], the user's choice "Sample + receipt (Recommended)": about 40 facts per site per dream,
  the session's own verdicts, and `done` refuses until each switched-on site has rows for that
  dream or a stated reason. Full option text in EXECUTION-USER-REVIEW.md.
- [18] closed on the user's "delete 18" (cf0e1686); the file's header forbids dropping lines.
- "Deleted" stale facts go through the existing archive verb (`reconcile_memory_index.py
  --archive`), recoverable; no new delete verb.
- versionrot attribution: a version belongs to the word right before it; only a preposition
  (in, since, from, fixed...) lets the search pass an unknown word; a run ("8.4.2 -> 8.5.0",
  "from X to Y") keeps its first package. Before this rule, "click 8.2.1" in a lib_shopware6
  sentence was credited to lib_shopware6. `ahead` (named > local) means a stale local clone and is
  not flagged.
- The version advisory skips an explicit Python boundary ("before Python 3.14"): those facts stay
  true while the supported range spans them.

## Still open, untouched

- [12] waits for decide rows (earliest about 2026-10-18). Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When a handover or doc says a config knob is set, read the config file and its mtime before
  building on it: a false "already set" made a step wait a week for rows that could not exist.
- When planning a panel or count on decide-mode rows, count the log's rows BY MODE first; rows
  without a mode field are shadow rows whatever the docs say.
- When a doc table restates a code constant (a threshold, a deadline), pin it with a test that
  reads the row and compares it with the constant.
- When a `find` starting at `.` prunes `-name '.*'`, it prunes the start dir itself and prints
  nothing; add `-mindepth 1`.
- When checking that a push landed, read `git ls-remote origin refs/heads/<branch>`; a
  `git rev-parse --verify -q A B` with two refs exits 1 and reads like a failed push.
- When a number in prose must be tied to the package it versions, credit it to the word right
  before it unless a preposition intervenes; nearest-known-name lookback misattributes.
- tooling: the repo-gate version check also needs `pyproject.toml` bumped beside `plugin.json`,
  and it fires on COMMIT, not only on push.

## The exact next action

[12] is blocked on time and [18] is closed, so the top live item is [22] (with [430]). In the
worktree `.claude/worktrees/recall-threshold-09` on branch `stale-version-pass`: invoke
`bitranox:meta-skill-writer` (run its receipt `start`), then write the GREEN text per the RED
file's spec - meta-dream-tree SKILL.md steps 0c, 5, 6, 7 (third question fed by `versionrot.py
scan --tree <anchor> --json`, re-check against the current release, then reword / archive /
merge), 11 (`dream_state.py done --kind tree --dream <id>`, home and launch named), checklist
lines 400/436; meta-dream-nap step 5 (`versionrot.py scan --chain`) and step 6 (`done --kind
nap`); crosstree 4b and crosstree-deep 3b (sample + `jev_shadow.py receipt`);
`references/dream-passes.md` removal policy and `references/dream-core.md:255`;
`meta-self-improve/references/jev-shadow.md` (`dream_id` field, sample + receipt, dream-prune's
`version_bound` row). GREEN-probe with the same two scenarios, plus haiku. Then amend the facts
feedback-keep-status-out-of-memory-entries and forgetting-is-usage-based-only through the engine,
rebase on origin/master, `repo-gate.py --ci`, push `HEAD:master`, `ci_wait.py --ref HEAD`. Then
run the dream with versionrot, btx-lib-mail facts first.

## Files that matter

- `plugins/bitranox/skills/meta-dream-tree/versionrot.py`, `dream_state.py`, `SKILL.md`,
  `references/dream-passes.md`, `references/dream-core.md`
- `plugins/bitranox/skills/meta-self-improve/jev_shadow.py`, `references/jev-shadow.md`
- `plugins/bitranox/skills/meta-dream-nap/SKILL.md`, `meta-dream-crosstree/SKILL.md`,
  `meta-dream-crosstree-deep/SKILL.md`
- `~/.claude/plans/fancy-meandering-hejlsberg.md` (the approved plan)

## How to verify

- In the branch worktree: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml
  --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/ -q`
- `python3 plugins/bitranox/skills/meta-dream-tree/versionrot.py scan --tree
  <memory tree top> --json` exits 1 and reports about 115 superseded facts.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
