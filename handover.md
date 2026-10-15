# Handover - 2026-10-15 17:45, [22] skill text shipped in 8.24.0; next is approving the 115-fact proposal

## In flight

- [22] stale-version facts. The tooling and the skill text are SHIPPED in 8.24.0 (ce8bfe63, `ci`
  green; the release `workflow` run was still in progress at writing). What remains is the cleanup
  itself: four read-only agents re-checked all 115 `versionrot.py` candidates against the current
  releases. Their proposal is in the gitignored `.plan/versionrot-proposal-20261015-batch1.md` ..
  `batch4.md`, one block per fact (outcome, evidence line, exact old/new text, new hook). Totals:
  49 KEEP, 59 REWORD, 2 DROP-LINE, 4 ARCHIVE, 1 MERGE pair, 0 UNSURE. Nothing in the memory store
  has been changed by it yet - dream mode is `propose`, so the user approves first.
- Facts that now state FALSE current behaviour, to apply first: batch 2's head (three bmk hooks
  saying "TEXT is silently ignored", the shfmt gitignore claim, the run-python.sh exit-0 claim,
  the factedit --type pinned claim, the tfbpr 8b contradiction) and batch 1's head
  (remote-powershell-file-not-inline, the jsonl_grep exit code in the missing-mechanism fact).

## Committed, or not

- Pushed: 8.24.0 (`20a7a993` code, `ce8bfe63` skill text). Fact amendments to
  forgetting-is-usage-based-only and feedback-keep-status-out-of-memory-entries are written to the
  store through factedit (the store's own git is committed by the next dream).
- This handover and the OPEN-WORK edits ([22] updated, [430] closed, new USER item [25]) are
  committed and pushed together with this file.
- Worktree `.claude/worktrees/recall-threshold-09` (branch `stale-version-pass`) is fully on
  origin now: remove it with wtclean.

## Decided, and why - do not reopen

- [25] (CI matrix, user's words in OPEN-WORK) is ranked right after the other USER items and
  needs one question first: the ci.yml comment says 3.11 is the supported floor that the matrix
  verifies, so the user's list (ubuntu 3.14/3.15, windows/macos 3.15) drops floor coverage.
- The `--jev-skip` example in meta-dream-tree step 11 is NOT a jev-judge timeout: a timeout after
  asking still logs rows (the site counts as fed, reported `error <message>`).
- A version given only as evidence or provenance inside a still-true general lesson is KEEP, not
  reword - 49 facts stay as they are on that rule.

## Still open, untouched

- [12] waits for decide rows (earliest about 2026-10-18). Everything else: `OPEN-WORK.md`.

## Lessons for the next nap

- When printing a listing's head and tail in one command, put a marker between them: the spliced
  output credited a tail line to the head's last header, and a subagent brief inherited the error.
- When you push from a worktree and then run a NEW script by its main-checkout path, fast-forward
  the main checkout first; it lacked the script and the call failed.
- When the repo's pre-push hook already runs the full gate (bitranox-skills: repo-gate --pre-push,
  about 4.5 min), the push IS the gate; do not run `repo-gate.py --ci` separately first.
- When a background CI wait is piped through `| tail`, its output file stays empty until it ends;
  run it unpiped so progress can be read.
- When an AskUserQuestion option carries an estimate or a premise, mark it "unverified" in the
  option text; the premise gate refuses the first ask otherwise.

## The exact next action

[12] is blocked on time, so the top live item is [22]: read the four `.plan/versionrot-proposal-
20261015-batch*.md` files, show the user a short summary (counts, the false-claim facts, the 4
archives, the merge, the 3 slug renames flagged), ask one approval question, then apply via
`plugins/bitranox/skills/meta-dream-tree/factedit.py apply --slug <s> --level <level>
--body-file <f> [--hook-file <f2>]`, `reconcile_memory_index.py --archive <slug> <level>`, and end
with `reconcile_memory_index.py --check-tree <memory tree top>` = 0 problems.

## Files that matter

- `.plan/versionrot-proposal-20261015-batch1.md` .. `batch4.md` (gitignored, this checkout only)
- `plugins/bitranox/skills/meta-dream-tree/versionrot.py`, `factedit.py`, `SKILL.md` step 7
- `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py`

## How to verify

- `python3 plugins/bitranox/skills/meta-dream-tree/versionrot.py scan --tree <memory tree top>`
  exits 1 and lists 115 facts before the cleanup; the count drops by the rewords, drops and
  archives applied (KEEP facts stay listed - they are candidates the re-check kept).
- `gh run list --commit ce8bfe63a9e83afec4668774fd5de84d7842c361` shows `ci` success.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete it -
if this session ends badly it is the only record of where things stood.
