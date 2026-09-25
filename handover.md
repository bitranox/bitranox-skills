# Handover - 2026-09-25, rank 10 hook-lib slice fixed and shipped (7.22.1 - 7.22.9)

## In flight

Nothing. All seven fix batches (A-G) are on origin/master and CI-green; master is `c1a357b`
(7.22.9). No agent is running.

## Committed, or not

- **Pushed:** 7.22.1 (A) through 7.22.9 (G2 plus its Windows test-helper fix), each landed by
  its own implementer subagent in order, CI confirmed by the coordinator on every sha.
- **This handover and OPEN-WORK.md** go in one commit after this file.
- **Not in git, by design (gitignored, main checkout's `.plan/`):**
  `.plan/rank10-review-2026-08-28/` (rescued TRIAGE.md + 53 reports from the ZFS snapshot),
  `.plan/rank10-hooklib-2026-09-25/` (TRIAGE.md with batches A-G, reports/, adjudication/ g1-g5,
  FOLLOWUPS.md with the 12 open follow-ups).
- **Local only:** `EXECUTION-USER-REVIEW.md` in this worktree (user decisions of this session).
  Copy it to the main checkout before `wtclean` removes this worktree.

## Decided, and why - do not reopen

- **User: sweep the never-reviewed scripts first** (over the stale 2026-08-28 buckets); slice 1 =
  22 hook-libs. **User: /goal "do all batches in order A to G"** and "use subagents to keep main
  agent clean" - implementers worked in parallel worktrees, landed strictly in order.
- **Provisional version bump on every branch** (the PreToolUse commit gate refuses a plugins/
  change at origin's version); renumbered at landing.
- **Secret redactor: a secret word ANYWHERE in a name counts, unless the LAST word is a
  non-secret tail** (ID, FILE, PATH, COUNT, ...). The first draft keyed on the last word only and
  silently stopped redacting `SECRET_KEY_BASE=`; fixed before landing, every old-redacted/new-not
  span (244, then 550 after G1) adjudicated as a non-secret.
- **Reviewer shadow rows are NOT excluded at the source**: filter rows whose transcript_path
  contains `scratchpad-sweep` when evaluating choice-v1 (switching the classifier off would drop
  every concurrent session's rows).

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): next slice, skill-script (79 targets); old buckets need re-checking against 7.22.9.
- Rank 12 (USER): Jev - judge the router only on choice-v1 rows from sessions on 7.22.5+ (clean roster).
- Rank 14 (USER): the approved invented-identifier guard.
- Rank 150 / 160 (FOUND): main-checkout TODO-JEV.md + fast-forward; wtclean 10 worktrees.
- Rank 170 (FOUND): the 12 follow-ups in FOLLOWUPS.md.

## Lessons for the next nap

- When parallel implementers must commit under a gate that demands a version bump, give them one provisional bump and renumber each branch at landing, in order.
- When a subagent changes a secret redactor, require a replay listing every span the OLD code redacted and the new does not, adjudicated in full - a narrowing rule dropped SECRET_KEY_BASE silently.
- When a replay measures a guard that decides on the event's cwd, pass the recorded cwd - a command-only replay read block-partial-typecheck as 0 firings while it had blocked 88 real calls.
- The fact reference-the-skill-edit-guard-s-receipt-is-machine-global-for-8h-not-session-scoped is STALE since 7.22.4 (receipts are per skill and session) - rewrite it via the engine.
- The fact reference-a-clobbered-audit-report-is-reported-clean-so-verify-every-clean-against-the-transcript is partly stale: audit_skills now flags a clobbered report REPORT-MISSING instead of clean (the recovery-from-transcript step still applies).
- When a subagent's post-push `git rev-parse` is refused by the auto-mode classifier, the coordinator resolves the sha from origin/master and runs ci_wait itself.
- tooling: audit_skills reviewers inherit every user hook (self-improve Stop gate clobbered a report; reviewers write Jev shadow rows) - queued in contrib_queue.
- tooling: decision-review-nudge fired "a /goal objective was met" while the goal was unmet - queued.

## The exact next action

Open the next session in the MAIN checkout (`/media/srv-main-softdev/projects/public/KI/bitranox-skills`).
Rank 10 is top-ranked: sweep the skill-script slice -
`python3 plugins/bitranox/skills/meta-skill-audit/scripts/audit_skills.py --plugin plugins/bitranox --room <scratchpad dir> --scripts --kind skill-script --list`
first to size it, then wall recall (`settings.py set cross_tree_search false`, restore after),
run it, recover any REPORT-MISSING target from its transcript, and adjudicate every claim with
controls before asking which batch goes first. Ranks 150/160 are FOUND and rank below it.

## Files that matter

- `.plan/rank10-hooklib-2026-09-25/TRIAGE.md`, `FOLLOWUPS.md`, `adjudication/g1..g5` (main checkout).
- `plugins/bitranox/skills/meta-skill-audit/scripts/audit_skills.py` - the sweep harness.
- `plugins/bitranox/hooks/secret_patterns.py`, `shell_text.py`, `skill_frontmatter.py`,
  `skill_receipt.py`, `skill_roster.py` - the most-changed modules.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -1 origin/master
uv run ~/.claude/plugins/cache/bitranox-skills/bitranox/7.22.0/skills/compuse-toolbox/scripts/ci_wait.py --sha "$(git rev-parse --verify origin/master)" --repo bitranox/bitranox-skills
```

origin/master carries `c1a357b` (7.22.9) or later, and ci_wait prints `workflow=success ci=success`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
