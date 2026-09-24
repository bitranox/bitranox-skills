# Handover - 2026-09-25, 7.22.0 shipped, stop_signal adjudicated, design doc committed

## In flight

Nothing. Everything below is committed, pushed and CI-green on master (`602b271`).

## Committed, or not

- **Committed and pushed:** 7.22.0 (`f819820`, shadow log bounded), and `602b271`
  (`docs/jev-design.md`, OPEN-WORK ranks 12/150/160 updated). This handover goes in its own commit.
- **Not in git, by design:** `.plan/jev-stop-2026-09-25/` (PREREG, RESULTS, labels, key, scripts).
  It is gitignored and lives in BOTH this worktree and the main checkout's `.plan/`
  (`diff -r` identical), so removing this worktree loses nothing.
- **Local only:** `EXECUTION-USER-REVIEW.md` in this worktree (clone-local exclude). It holds this
  session's user decisions and the day-file decision. Copy it to the main checkout before
  `wtclean` removes this worktree if you want to keep it.

## Decided, and why - do not reopen

- **Shadow log retention 30 days / 200 MB** (user, over the recommended 14 / 100).
- **One file per UTC day, pruned on each append, never rename rotation.** The writers are
  concurrent detached children. With rename rotation, two of them can both rotate, and the second
  rename silently overwrites the full `.1`. The current day's file is never deleted.
- **recall_rerank waits for much more data** (user: "2 we wait for much more data !").
- **TODO-JEV.md became `docs/jev-design.md`** (user chose "commit as design doc"), corrected to the
  current code, with a pointer to rank 12 instead of a progress log.
- **The stop_signal recommendation ("regex OR Jev at 0.7") is held until the skill_router decision**,
  so the user gets one decision at a time. It met the pre-registered bar: 70% precision on the
  Jev-only turns.

## Decided against, and why

- **ExitWorktree to lift the isolation:** this session did not enter the worktree via EnterWorktree,
  so the tool is a no-op here, and it is for user requests only.
- **Removing this worktree from inside itself:** it has to be done from the main checkout.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 12 (USER): Jev. Waiting on choice-v1 rows; stop_signal's result is recorded there.
- Rank 14 (USER): the approved invented-identifier guard.
- Rank 150 (FOUND): unstage and delete `TODO-JEV.md` in the main checkout, then fast-forward it.
- Rank 160 (FOUND): `wtclean` on this worktree and `nudge-recall-fix`, from the main checkout.

## Lessons for the next nap

- When a log has concurrent detached writers, bound it with one file per period plus deletion of old
  files, never rename rotation: two writers that both rotate let the second rename overwrite the
  full `.1` with no error.
- When harvesting a subagent's structured verdict from its transcript, look inside tool_use INPUTS as
  well as text blocks: the hand-back report is an escaped string inside a SubagentHandback tool_use.
- When a jig that mutates source files runs, send its output to a file and never pipe it into a
  consumer that can exit early: SIGPIPE can kill the jig mid-arm while a mutation is still applied.
- When a worktree-isolated session's task needs git in the main checkout (unstage, wtclean,
  fast-forward), plan those steps for a session opened in the main checkout, and copy gitignored
  `.plan/` artifacts out of the worktree first.
- When you change the SHAPE of what a producer writes (a question type, a field's type), check that
  every reader parses the new shape, because a reader that skips unknown shapes fails silently.
- When you change what a hook sends or where it writes, grep the docs for the old description: the
  settings skill and `docs/reference.md` both carried it.

## The exact next action

Open the next session in the MAIN checkout
(`/media/srv-main-softdev/projects/public/KI/bitranox-skills`), not this worktree.

Then take rank 10, the top-ranked open item: the skills-and-scripts review, one subagent per target,
asking before changing anything. Its line says the only record of its 17 unadjudicated claims and 5
coverage gaps is a `TRIAGE.md` in a ZFS snapshot, so the first step is to copy that file somewhere
durable. Then size the sweep by counting the targets under `plugins/bitranox/skills/*/` and
`plugins/bitranox/hooks/`.

Ranks 150 and 160 are FOUND items ranked below it. They are not a reason to start elsewhere.

## Files that matter

- `plugins/bitranox/hooks/classifier.py`: `shadow_log_path`, `shadow_log_files`,
  `prune_shadow_logs`, `_append_log`, `SHADOW_KEEP_DAYS`, `SHADOW_MAX_BYTES`.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`: `load_rows` (file or directory),
  `default_log`, `SITE_THRESHOLDS`, `NON_FIRING_FAMILIES`.
- `docs/jev-design.md`: the Jev design.
- `.plan/jev-stop-2026-09-25/` in the main checkout: `RESULTS.md`, `score.py`, `labels.json`,
  `key.json`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -3 origin/master
python3 .plan/jev-stop-2026-09-25/score.py .plan/jev-stop-2026-09-25/key.json
```

origin/master carries `602b271` (or later), and the score run prints `signals 51` with
`P(jev_only) 39/56 = 70%` at t=0.7.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
