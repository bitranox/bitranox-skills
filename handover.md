# Handover - written 2026-08-31, nothing in flight

## In flight

Nothing. Every piece of this session's work is committed, pushed, released and CI-green.

## Committed, or not

`HEAD == origin/master == d091c17`, working tree clean. Plugin `5.297.5`, tagged, GitHub release
published, on PyPI. Nothing uncommitted anywhere.

## The change, in one paragraph, because the repo cannot tell you WHY

`handover.md` used to hold both the moment and the standing backlog. It is rewritten wholesale
every session, so the backlog was re-encoded from the writing session's memory once per session,
weighted by how recently each item was touched rather than by size or by who asked. Untouched items
lost one attribute per rewrite until they were a clause, then absent. Five real items went that way
in one day. The backlog now lives in `OPEN-WORK.md`, edited line by line and never rewritten, and
`session-start.py` prints its top ranks with their age at every session start.

## Decided, and why - do not reopen

- **Two files, not one.** They have opposite lifetimes: the moment must be replaced wholesale, the
  backlog must never be. That is the whole fix; merging them again reintroduces it.
- **Rank by ORIGIN before size.** A `USER:` item outranks every `FOUND:` one whatever the counts
  say. Ranking by size alone made a test arm put a 206-item internal sweep above the user's own
  88-target request, which is the same failure wearing different arithmetic.
- **Ranks go in tens.** Contiguous integers made every mid-list insertion renumber the tail.
- **Never infer a first-raised date.** `(2026-08-31?)` or `(unknown)`; both parse, and an undated
  item sorts last within its rank. A guessed date silently resets the only signal that makes a
  long-carried item conspicuous.
- **The shared-ceiling budget is computed from what the other blocks actually spent**, not a fixed
  share and not a guaranteed floor. A fixed share passed its fixture and overran production by 429
  bytes; a floor breached the ceiling it existed to respect, which hides the content it protects.
- **`handover.md`, `OPEN-WORK.md` tracked, not gitignored** (user decision). Check both for
  secrets, internal hostnames and private addresses before committing - this repo is public.
  `EXECUTION-USER-REVIEW.md` was removed for that reason and never entered git history.

## Decided against, and why

- **A gate enforcing the reconcile step.** It stays prose deliberately. The original failure needed
  BOTH halves to be invisible, and the read side is now covered mechanically. Recorded as
  `OPEN-WORK.md` item 135 so the assumption gets tested rather than assumed.

## Still open, untouched

Fifteen items in `OPEN-WORK.md`, ranked, with sizes and next actions. Read that file; a summary
here is the re-encoding this change exists to stop.

## The exact next action

**`OPEN-WORK.md` item 10, the top-ranked open item and the oldest** - the user's 2026-08-27
request, "review all skills and scripts one by one, each in its own subagent and ask when smth is
to change". 88 of 135 targets remain across 4 slices, and no decision has been recorded on it since
2026-08-28.

First step, before any reviewing: the prior work is in `/tmp/scriptwave-2026-08-28/TRIAGE.md`, and
`/tmp` does not survive a reboot. Copy that directory into the repo, then pick a slice.

If you do something else instead, say so in the next handover and why - recency is not a reason.

## Files that matter

- `OPEN-WORK.md` - the backlog. Its own header states the line format and the ranking rules.
- `plugins/bitranox/skills/meta-context-watcher/SKILL.md` - the procedure, including the reconcile
  step that must run BEFORE this file is overwritten.
- `plugins/bitranox/hooks/session-start.py` - `open_work_context`, `_parse_open_work`, and the
  remaining-budget arithmetic in `main()`.
- `plugins/bitranox/skills/meta-context-watcher/.skillwriter/checklist-20260831-open-work.md` -
  what was tested and what was declined, with the measurements.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

Expect `repo-gate: all checks passed`; it was 4135 passed / 13 skipped / 1 xfailed at `d091c17`.
To see what a new session will actually be shown, run the hook itself:

```bash
echo '{"cwd":"'"$PWD"'"}' | CLAUDE_PLUGIN_ROOT="$PWD/plugins/bitranox" \
  bash plugins/bitranox/hooks/run-python.sh plugins/bitranox/hooks/session-start.py
```

3239 bytes at `d091c17`, 7 of 15 items listed, remainder counted.

## One trap that cost an hour and is not in the repo

The Skill tool serves the INSTALLED plugin cache, which lags this checkout. Invoking
`bitranox:meta-context-watcher` here returned the 5.296.2 text - no reconcile step, and still
saying the handover must be gitignored. Read the repo copy when working on a skill in this repo.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
