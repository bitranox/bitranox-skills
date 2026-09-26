# Handover - 2026-09-26, rank 8 MED batch shipped as 7.25.4 (+ a CI flake fix, 7.25.5); the LOW batch is next

## In flight

Nothing running and nothing part-done. 7.25.4 carries every MED finding of the rank-8 review,
and both workflows were green on it. The next push then failed macOS CI on the growth-ratio
meta-test in `test_secret_patterns.py` (sleep overshoot, not a code change); 7.25.5 moves that
meta-test onto a virtual clock. Check CI on the 7.25.5 commit before starting new work. The `OPEN-WORK.md` rank 8 line carries the state and the next
step.

## Committed, or not

- **In git and pushed:** 7.25.4, a handover commit, and 7.25.5 (this file plus the flake fix). Run
  `git log --oneline -3` for the shas; CI was confirmed on the release commit.
- **Not in git, by design (gitignored, main checkout):**
  `.plan/rank8-review-2026-09-26/REVIEW.txt` (every review finding, the LOWs still open) and
  `.plan/rank8-review-2026-09-26/MED-FOLLOWUPS.txt` (what the MED fixers found and left, rank 179).
- The 11 fixer worktrees still hold their changes UNCOMMITTED; the content is already in 7.25.4.
  They are listed under rank 160 for wtclean, to be discarded rather than merged.

## Decided, and why - do not reopen

- **The adopt license gate scopes its evidence to the skill's own folder plus the governing files
  of each ancestor folder.** A whole-tree scope stopped all 30 Apache skills of
  claude-plugins-official because a sibling plugin is proprietary. A symlinked folder, or a link
  out of the skill, stops the gate (copytree would ship the target unread).
- **task_brief ends a task at the next task heading or a HIGHER-level heading**, not at any
  same-level one. Across the 13 real plans only two briefs changed, both correctly. A same-level
  section after the last task now stays with that task (it reverses an earlier LOW fix).
- **A NEEDS_IMPROVEMENT verdict scoring at or above the threshold exits 0**, the literal reading of
  the user's exit-1 decision (below the threshold means exit 1). Flagged in rank 179 for a yes/no.
- **Jigs that run the caller's commands declare `LAUNCH_WITH = "python3"`** (gate, ci_triage,
  transfer, diffbehave), and toolbox-nudge reads the declaration. A test pins every nudged jig.

## Decided against, and why

- The LOW findings and the fixers' own follow-ups were kept out of 7.25.4: they are a separate
  pass by the rank-8 plan, and mixing them would have hidden which change fixed which MED.
- Deleting the 1704 `/tmp/factedit-*` dirs the old factedit leaked: not asked for, and some may
  belong to live sessions. The leak itself is fixed.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 8 (USER): the ~85 LOW findings of REVIEW.txt.
- Rank 175 (FOUND): decision (c), the table-padding waiver in repo-gate, still to implement.
- Rank 179 (FOUND): about 35 follow-ups the MED fixers left.
- Rank 160 (FOUND): 45 finished worktrees, including this one; wtclean from the main checkout.

## Lessons for the next nap

- When you hand a fixer's patch back to your own tree, apply its tests-only half first
  (`git apply --include='*/tests/*'`) and require RED on the old source, then the rest and require
  GREEN. It is a cheap independent check of the fixer's RED claim, and it caught nothing wrong this
  time only because each claim held.
- When a fixer's refusal widens a scope (a gate reading more files), measure it on the real
  corpus before landing: the license gate's whole-tree read looked conservative and blocked an
  entire marketplace.
- When a padded or recalled 40-char sha feeds ci_wait, it polls to "no runs" - derive it in the
  same command or copy it from `git rev-parse` output (recurred this session despite the memory
  rule and a nudge that fired).
- tooling: block-masked-gate-exit blocks a SINGLE backgrounded `ci_wait.py` call (queued in
  contrib_queue); the running 7.25.2 cache also still suggests `uv run gate.py`, fixed in 7.25.4.
- tooling: a worktree-isolated session refuses any Bash command whose TEXT contains a git
  subcommand phrase, even inside a Python string literal; use Edit or a scratchpad script.

## The exact next action

Rank 8's LOW batch is the top open USER item. Read `.plan/rank8-review-2026-09-26/REVIEW.txt` in
the main checkout, group its LOW lines by file owner, and fold in the rank 179 lines that overlap.
Then dispatch one fixer per group with the MED brief's rules: reproduce, RED test, fix. Land each
patch the same way, tests-only half RED first, then GREEN.

## Files that matter

- `.plan/rank8-review-2026-09-26/REVIEW.txt` and `MED-FOLLOWUPS.txt` (main checkout, gitignored).
- `OPEN-WORK.md` ranks 8, 175, 179 and 160.
- `CHANGELOG.md` `## [7.25.4]` - what the MED batch changed, per script.

## How to verify this still stands

- `grep '"version"' plugins/bitranox/.claude-plugin/plugin.json` prints 7.25.4.
- `python3 <plugin>/skills/compuse-toolbox/scripts/ci_wait.py --sha <full sha of the 7.25.4
  commit, from git log>` reports `workflow=success ci=success`.
- `grep -c '^## ' .plan/rank8-review-2026-09-26/REVIEW.txt` in the main checkout prints 17.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
