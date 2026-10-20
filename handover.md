# Handover 2026-10-20: [23] batch 3 folded (9.10.2) and its 22 facts archived, next the batch-3 leftovers

## In flight

- Nothing part-done. No subagent or workflow is running. The only background job at writing time
  was a `ci_wait` on the backlog commit `e0768644`; this handover's own commit runs CI again.
- No worktree is left: `.claude/worktrees/fold-23-batch3` and `jev-subagent-signal` were merged
  and removed.

## Committed, or not

- bitranox-skills 9.10.2 (`4180c701`, release `v9.10.2`) is on origin/master and installed here.
- Memory store `ced6658` (pushed): 22 facts archived as `R100` renames to `.archive/`, 5 citing
  facts re-pointed to the owning skill (one line each). The store still holds 16 uncommitted
  changes that belong to OTHER sessions; they were left alone on purpose.
- This commit carries `OPEN-WORK.md` ([440] note) and this file. Nothing else is uncommitted.
- Gitignored, kept: `.plan/fold-23/batch3/` (all batch-3 data, the three workflow scripts, the
  checker scripts, `backup-pre-archive-b3.tgz` one level up), and the batch-3 decision in
  `EXECUTION-USER-REVIEW.md`.

## Decided, and why - do not reopen

- [23] batch 3: the user chose "22 rows + skill fix (Recommended)": fold the 11 REACH-OK rows,
  archive the 11 SAFE ARCHIVE+REACH-OK rows, fix the stale effort line. The 4 SAFE
  ARCHIVE+REACH-PARTIAL rows and the 2 KEEP-SHORTENED rows were NOT touched, by that choice.
- Re-pointed citers name the skill as a code span (`` `bitranox:<skill>` (<section>) ``), never a
  `[[ref]]`: a skill is not a fact, so a ref to it would dangle.
- Files that mention an archived slug as history keep it: recall caches, jig ledgers, old
  `.skillwriter` checklists, the closed OPEN-WORK [95] line, `RESEARCH/` probe comments and
  handover, and the `semdex` / `RESEARCH` decision logs. An archived body stays recoverable.

## Decided against, and why

- Re-routing the 10 REACH-FAILS rows to the better owner the reach lens named: those rows were
  checked only against their ORIGINAL owner, so they need a fresh reach and skeptic pass first.

## Still open, untouched

- [23] batch-3 leftovers, batch-2 (2b)/(2c), batch-1 (c): see the `[23]` line in `OPEN-WORK.md`.
- [440]: the recurrence bump on `feedback-audit-what-a-number-counts-before-quoting-it-as-evidence`
  awaits the user's go-ahead (asked 2026-10-20).
- [28] and [335] wait on shadow data (11 of the 100 answered subagent messages [96] needs).
- Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When stripping a fact's frontmatter to feed `factedit apply --body-file`, strip the blank line
  after it too, or the body gains one: tooling: queued against meta-dream-tree (contrib queue).
- When checking that a commit recorded moves, read `git show --name-status` (R100), never grep
  `--stat` for `=>`: `--stat` abbreviates long paths and the arrow never appears.
- (recurrence of feedback-a-pass-measured-on-one-model-tier-is-not-a-pass) When a bold lead
  sentence sums up a scoped rule, quote-test it on haiku: a lead broader than its paragraph made
  haiku apply an Agent-tool-only restriction to every effort channel while opus read it right.
- (recurrence of feedback-audit-what-a-number-counts-before-quoting-it-as-evidence) When the
  question-premises gate refuses an AskUserQuestion, recount every number in the options from the
  data, not from memory: a per-skill count was wrong in both the question and the chat text.
- When a fold batch is built from a workflow, save its input builder beside the data in `.plan/`:
  batch 2's builder lived nowhere and batch 3 rebuilt it from `rows.json` by hand.
- Carried from the previous handover (not yet confirmed captured): when a backlog line says
  something was "never named" or "never done", grep the design docs before relaying it; when a
  replay counts a hook firing on every input, read the predicate's return contract first; redcheck
  can flag a RED as inherited on generic shared terms, so grep for the new name before trusting it;
  when CI is red on a shared repo, fetch origin first, a peer may have pushed the fix; tooling:
  settings.py accepts any value for a knob its choices table does not list.

## The exact next action

`[23]` is the top-ranked open item. Take the 9 REACH-FAILS rows of batch 3 that name a
`better_owner` (`.plan/fold-23/batch3/merged.json`, `reach == "REACH-FAILS"`), build a group file
per new owner with `owner_skill` set to that owner, and re-run
`.plan/fold-23/batch3/fold23-batch3-reach-skeptic-wf_b462525f-a2d.js` against them (adjust its `DIR`
and `GROUPS`). Then put the surviving batch, plus the 18 REACH-PARTIAL fold-with-pointer rows, to
the user as ONE question before any edit.

## Files that matter

- `OPEN-WORK.md` (`[23]`, `[440]`, `[28]`, `[335]` lines)
- `.plan/fold-23/batch3/merged.json` (41 FOLD rows, reach + skeptic), `safe17-merged.json`
  (17 SAFE rows), `quotecheck_installed.py`, `repoint.py`, `owners27.json`, the three
  `fold23-batch3-*.js` workflow scripts
- `.plan/fold-23/rows.json` (every level's phase-1 classification, for the next level group)

## How to verify

- CI on the head commit: `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox `scripts/`).
- Store integrity: `reconcile_memory_index.py --check-tree /media/srv-main-softdev`
  (meta-self-improve) should report `TOTAL tree problems: 2`, the pre-existing libs-level and
  machines-level sideways refs; and `git -C /media/srv-main-softdev/.claude-memory status -sb` shows `main` level
  with `origin/main`.
- Installed plugin: the plugin cache's `9.10.2/.claude-plugin/plugin.json` exists and reads 9.10.2.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
