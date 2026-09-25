# STALE - read 2026-09-25, work continued

## In flight

Nothing running. The skill-script slice (79 targets) is fully swept and every finding adjudicated;
no fix has been started. The next step is a question to the user, not code.

## Committed, or not

- **In git:** this handover and the OPEN-WORK.md rank-10 update. No plugin change, so no version
  bump. Its first push (9b1bfe0) went RED on macOS from a flaky timing test, not from this change:
  OPEN-WORK rank 45 has the numbers and the fix. Expect every push to be at risk until it is fixed.
- **Not in git, by design (gitignored, main checkout):** `.plan/rank10-skillscript-2026-09-25/`,
  the whole record: `TRIAGE.md` (tally, batches A-F, every HIGH/MED line), `reports/` (79 plus
  6 `.recovered`), `adj/<group>/verdicts.txt` (16 files, copied verbatim from the agent
  transcripts), `adjudicate-brief.md`, `sweep.log`, `list.txt`. Byte-verified against the scratch
  copies.
- **Scratch only, will be swept:** the adjudicators' fixtures and repro scripts. Each verdict line
  carries its arm and control command, so a fixer rebuilds the fixture from the line.

## Decided, and why - do not reopen

- **Adjudicate everything before asking which batch goes first.** Matches slice 1; 0 REFUTED
  across 628 blocks says the reviewers' repros are reliable, but the PARTIAL verdicts narrowed
  several claims and a fixer should work from the adjudicated wording, not the raw report.
- **The six clobbered reports were recovered, not re-reviewed.** Each reviewer transcript is
  identified by the target path in its FIRST prompt; a group R adjudicator then covered them.
- **Severity is by what a user suffers**, per the brief; HIGH means data loss, a leak, a guard that
  passes what it exists to stop, or a confident wrong answer.

## Decided against, and why

- **Handing over before adjudication finished** (offered, user chose to finish first): it would have
  left 7 in-flight agents reporting into a dead session.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): pick a batch from TRIAGE.md A-F, fix it; then the last 5 targets.
- Rank 12 (USER): Jev router decision, blocked on >= 40 eligible choice-v1 rows.
- Rank 150 / 160 (FOUND): main-checkout TODO-JEV.md + fast-forward; wtclean of 17+ worktrees,
  including this one (jev-roster).
- Rank 170-178 (FOUND): earlier leftovers, unchanged this session.

## Lessons for the next nap

- When checking audit_skills reports for completeness, search for the literal "REPORT MISSING", never for a FINDING: count: the marker line itself contains "FINDING: REPORT-MISSING" and count_findings tallies it as 2, so 6 of 79 clobbered reports read as "2 finding(s)" and passed my check.
- When recovering a clobbered reviewer report from transcripts, identify the transcript by the target path in its FIRST user prompt: matching any mention picked another reviewer's transcript that merely named the file.
- When an adjudicator must run a tool that writes state, point HOME and XDG_STATE_HOME into its scratch dir in the harness, not only in the brief: a verb that ignored its --snapshot-dir flag wrote into the real ~/.local/state.
- When a session is isolated in a worktree, write multi-step shell work as a scratchpad script and run it with bash; inline commands with variables or `cd` get refused.
- tooling: audit_skills reviewers still inherit user Stop hooks (6 of 79 clobbered this slice); count_findings and the REPORT-MISSING wording are TRIAGE batch F.

## The exact next action

Rank 10 is the top open USER item that can move (rank 12 is blocked on data). Read
`.plan/rank10-skillscript-2026-09-25/TRIAGE.md` in the main checkout, put batches A-F to the user
with a recommendation (A first: guards that delete or leak data), and wait for their pick. Fold the
rank-45 timing-test fix into the first batch release: it is small, and until it lands a red macOS
cell can hide a real failure in that release.

## Files that matter

- `.plan/rank10-skillscript-2026-09-25/TRIAGE.md` and `adj/*/verdicts.txt` (main checkout).
- `plugins/bitranox/skills/meta-prune-plugin-cache/scripts/pluginprune.py`,
  `plugins/bitranox/skills/net-firewall-pfsense/scripts/pfsense.py`,
  `plugins/bitranox/skills/meta-skill-audit/scripts/audit_skills.py`,
  `plugins/bitranox/skills/compuse-toolbox/scripts/` (fleet_ssh, procsig, pushcheck, ...),
  `plugins/bitranox/hooks/recall-memory.py` with
  `plugins/bitranox/skills/meta-collect-knowledge/gather_scan.py`.

## How to verify this still stands

- `ls .plan/rank10-skillscript-2026-09-25/reports | wc -l` in the main checkout prints 85.
- `grep -c '^- ' .plan/rank10-skillscript-2026-09-25/TRIAGE.md` prints 224 (221 HIGH/MED lines).
- `git log --oneline origin/master -3` shows the handover commits on top of 858e712.

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
