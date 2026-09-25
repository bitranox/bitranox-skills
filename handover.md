# STALE - read 2026-09-25, work continued (ranks 7, 12, 14 dispatched to subagents)

## In flight

Nothing running. All seven fix batches (A-G) are on origin/master and CI-green (7.22.9, `c1a357b`,
plus a docs commit on top). They were coordinated from a session past 500k tokens of context, so
the user wants them reviewed before anything else - that is rank 7 in `OPEN-WORK.md`.

## Committed, or not

- **Pushed:** 7.22.1 (A) through 7.22.9 (G2 and its Windows test-helper fix), range
  `4fb3348..c1a357b`. This handover plus OPEN-WORK.md go in one commit on top.
- **Not in git, by design (gitignored, main checkout's `.plan/`):**
  `.plan/rank10-review-2026-08-28/` (rescued old TRIAGE.md + 53 reports),
  `.plan/rank10-hooklib-2026-09-25/` (TRIAGE.md with batches A-G, reports/, adjudication/g1..g5,
  FOLLOWUPS.md with 12 open follow-ups). The adjudication files are what a reviewer checks each
  batch diff against.
- **Local only:** `EXECUTION-USER-REVIEW.md` in this worktree (this session's user decisions).
  Copy it to the main checkout before `wtclean` removes this worktree.

## Decided, and why - do not reopen

- **User chose the never-reviewed-scripts sweep, slice 1 = 22 hook-libs; then /goal "all batches
  in order A to G" and "use subagents to keep main agent clean".** Implementers ran in parallel
  worktrees and landed strictly in order.
- **Provisional version bump on every branch** (the commit gate refuses a plugins/ change at
  origin's version), renumbered at landing.
- **Secret redactor rule:** a secret word ANYWHERE in a name counts unless the LAST word is a
  non-secret tail (ID, FILE, PATH, COUNT, ...). A last-word-only draft silently dropped
  `SECRET_KEY_BASE=`; fixed before landing. A reviewer should re-check this rule hardest.
- **Reviewer shadow rows are not excluded at the source**: filter choice-v1 rows whose
  transcript_path contains `scratchpad-sweep` (turning the classifier off would drop every
  concurrent session's rows).

## Decided against, and why

- **Rewriting the two stale memory facts in this session**: rewriting an existing entry is
  propose-first, so they are lessons below for the nap.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 7 (USER): review the 7.22.1-7.22.9 batch diffs.
- Rank 10 (USER): next sweep slice, skill-script (79 targets).
- Rank 12 (USER): Jev - judge the router only on choice-v1 rows from 7.22.5+ sessions.
- Rank 14 (USER): the approved invented-identifier guard.
- Rank 150 / 160 (FOUND): main-checkout TODO-JEV.md and fast-forward; wtclean 10 worktrees.
- Rank 170 (FOUND): 12 follow-ups in FOLLOWUPS.md.

## Lessons for the next nap

- When parallel implementers must commit under a gate that demands a version bump, give them one provisional bump and renumber each branch at landing, in order.
- When a subagent changes a secret redactor, require a replay listing every span the OLD code redacted and the new does not, adjudicated in full - a narrowing rule dropped SECRET_KEY_BASE silently.
- When a replay measures a guard that decides on the event's cwd, pass the recorded cwd - a command-only replay read block-partial-typecheck as 0 firings while it had blocked 88 real calls.
- When a subagent's post-push `git rev-parse` is refused by the auto-mode classifier, the coordinator resolves the sha from origin/master and runs ci_wait itself.
- When a coordinator session ships many subagent batches from a very full context, schedule an independent review of the landed diffs as the next session's first job.
- The fact reference-the-skill-edit-guard-s-receipt-is-machine-global-for-8h-not-session-scoped is STALE since 7.22.4 (receipts are per skill and session) - rewrite it via the engine.
- The fact reference-a-clobbered-audit-report-is-reported-clean-so-verify-every-clean-against-the-transcript is partly stale: audit_skills now flags a clobbered report REPORT-MISSING instead of clean (recovery from the transcript still applies).
- tooling: audit_skills reviewers inherit every user hook (the self-improve Stop gate clobbered a report; reviewers write Jev shadow rows) - queued in contrib_queue.
- tooling: decision-review-nudge fired "a /goal objective was met" while the goal was unmet - queued.

## The exact next action

Open the next session in the MAIN checkout (`/media/srv-main-softdev/projects/public/KI/bitranox-skills`),
fast-forward it, then take rank 7: invoke `bitranox:process-review-requesting-code-review` over
`4fb3348..c1a357b`, one reviewer per batch commit (`git log --oneline 4fb3348..c1a357b` lists
them), each given its batch's adjudication file from
`.plan/rank10-hooklib-2026-09-25/adjudication/` and told to demand a failing input per finding.
Look hardest at `secret_patterns.py`, `shell_text.py`, `memory_engine.py` / `uuid_store.py` and
`skill_receipt.py`. Verify each reviewer finding yourself before fixing; fix confirmed defects TDD.

## Files that matter

- `plugins/bitranox/hooks/secret_patterns.py`, `shell_text.py`, `memory_engine.py`,
  `uuid_store.py`, `skill_receipt.py`, `skill_roster.py`, `skill_frontmatter.py`.
- `.plan/rank10-hooklib-2026-09-25/TRIAGE.md`, `adjudication/g1..g5`, `FOLLOWUPS.md` (main checkout).
- `CHANGELOG.md` entries 7.22.1-7.22.9 - each batch's own description of what it changed.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline 4fb3348..origin/master
uv run ~/.claude/plugins/cache/bitranox-skills/bitranox/7.22.0/skills/compuse-toolbox/scripts/ci_wait.py --sha "$(git rev-parse --verify origin/master)" --repo bitranox/bitranox-skills
```

The log lists the batch commits up to `c1a357b` (plus later docs commits), and ci_wait prints
`workflow=success ci=success`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
