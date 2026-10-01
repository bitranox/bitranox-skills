# Handover - 2026-10-01 14:50, rank 4 measured and closed (7.30.8), notifications shadowed in decide mode (7.30.9)

## In flight

- Nothing running. Everything this session made is committed and pushed; CI is green on both
  releases (`50fb6599` 7.30.8, `5338ce82` 7.30.9).

## Committed, or not

- bitranox-skills 7.30.8 and 7.30.9 are on origin/master. This machine still RUNS plugin 7.30.0
  until the user types `/plugin marketplace update bitranox-skills` then `/reload-plugins`; until
  then neither the 7.30.9 notification logging nor anything since 7.30.0 is live here.
- The backlog edits (ranks 4, 14, 98, 150) and this file were committed from the
  `.claude/worktrees/openwork-upstream` worktree, which tracks origin/master.
- NOT committed, by design: the main checkout still has `TODO-JEV.md` staged (`AM`), rank 150.
- Outside this repo: `KI/btx-skill-jev/PLAN-JEV-SKILL.md` got a "Packaging" section; that directory
  is not a git repo yet, and the btx-skill-jev session owns it now.

## Decided, and why - do not reopen

- The Jev judgment skill will NEVER ship in bitranox-skills: not mirrored, not listed in
  marketplace.json (user decision 2026-10-01, relayed by the btx-skill-jev session; it superseded
  this session's earlier "standalone now, listed later"). It lives in `KI/btx-skill-jev`.
- The keyword skill router keeps a map of this plugin's skills only (rank 4, user chose option 1):
  keywords derived from other plugins' descriptions were 12 right of 140 nudges on 1,317 typed
  prompts, about 5 of 37 with prompt-common words dropped. The reason is in the skill-router.py
  docstring.
- In decide mode a task notification is shadowed, never nudged (user chose option 1 of 4 on
  2026-10-01): too few rows to decide it, and decide had stopped the log from growing.

## Decided against, and why

- Routing notifications through Jev now: about 20 of 42 picks plausibly right, and the one strong
  kind (failed background commands, 12 of 12) is 12 rows from 9 sessions. Rank 14 holds the
  re-measurement.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 12 is no longer waiting on data (7.30.0 router rows exist since
2026-09-28). Rank 14 waits on the plugin update plus about two weeks of notification rows. Rank 18
is deferred by the user. Rank 98 (Jev client rate limits) is new and unmeasured. Rank 150 needs the
user or a session the classifier lets run git in the main checkout.

## Lessons for the next nap

- When deriving keyword triggers from descriptions not written trigger-first (another plugin's
  skills), expect generic head words: measured 12 right of 140 nudges, so measure on real prompts
  before building any keyword matcher over such text.
- When a classifier site moves from shadow to decide, check what the switch stops LOGGING: decide
  turned the shadow off for notifications it never acted on, so their evidence silently stopped.
- When describing which path handles an input class, check the matcher actually scores that class:
  "a notification goes to the keyword router" was true and inert, since it scores machine turns as
  nothing (0 of 505).
- When an earlier backstop wakeup fires after its work is done, answer it in one line: two stale
  re-fires restated finished steps here.
- tooling: right after a user-approved `git merge --ff-only` in the main checkout, the auto-mode
  classifier refused plain `git status` and `repo-gate.py --mirrors` as "Irreversible Local
  Destruction"; seen once, cause unknown.
- tooling: `ci_wait.py` backgrounded with `> log; echo RC=$? >> log` is blocked by
  block-masked-gate-exit; backgrounding the gate alone worked.

## The exact next action

Rank 12 is the top-ranked open item and is no longer blocked: 7.30.0+ router rows exist since
2026-09-28. Its step (2) is a blind panel over decide rows from sessions on 7.30.0 or later:

```
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py packet --help
```

then build packets from the decide rows since 2026-09-28 13:41 (the `packet` verb drops rows it
cannot locate to a typed prompt and reports why), dispatch the judges, and `harvest`. Rank 4,
ranked above it, is closed.

## Files that matter

- `OPEN-WORK.md` - ranks 12, 14, 98 and 150 carry today's detail.
- `plugins/bitranox/hooks/skill-router.py` - `_shadows`, the decide-mode notification shadow.
- `plugins/bitranox/hooks/tests/test_skill_router_decide.py` - the two notification tests.
- `plugins/bitranox/skills/meta-memory-settings/SKILL.md`, `docs/reference.md` - the
  `classifier_skill_router` row.
- `~/.claude/self-improve-audit/classifier-shadow-*.jsonl` - the router rows; notification rows
  carry `regex.notify_view`.

## How to verify

- `git log --oneline -3 origin/master`: 5338ce82 (7.30.9) on top of 50fb6599 (7.30.8).
- `python3 -m pytest -q plugins/bitranox/hooks/tests/test_skill_router_decide.py` with CI's
  dependency set (see CLAUDE.md): 22 passed.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
