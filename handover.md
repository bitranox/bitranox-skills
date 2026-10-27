# Checkpoint 2026-10-27 15:00: [28] backlog_ask dropped and regex widened (10.3.10); audit_candidate next

## In flight

[28] second wave of Jev sites. The backlog_ask part is finished in the commit that carries this
file (10.3.10, from worktree `.claude/worktrees/ow28`, branch `jev28/backlog-ask`). The next part
is audit_candidate.

## Committed, or not

- 10.3.10 carries: widened `prompt_text.asks_for_own_backlog`, the backlog_ask site removed
  (classifier, recall hook, defaults, settings and its skill row, classifier_eval, docs), new
  OPEN-WORK items [860] and [870], the [28] line's 2026-10-27 result.
- `classifier_backlog_ask` was switched to `off` on this machine before the removal.
- Measurement scripts and data, gitignored: `.plan/jev-28/review-2026-10-27/` (stats.py,
  replay_backlog.py, score_backlog.py, PREREG-backlog_ask-v2.md, judge files, key).

## Decided, and why

- User chose "Regex fix + one rewrite (Recommended)" for backlog_ask (2026-10-27).
- v2 passed [96] clauses 1-3 and failed the blind review (Jev wrong 35, regex wrong 11 of 46),
  so the pre-registered branch dropped the site. Details in the [28] line.

## Decided against, and why

- No second rewrite of backlog_ask: [96] allows one.
- Not keeping the site's code with the knob off: dead code nobody can promote.

## Still open, untouched

- OPEN-WORK.md holds the backlog; [23] stays the top USER item.

## Exact next action

Put the audit_candidate choice to the user (one question): it failed [96] clause 2 (band 49.5%);
the agreement clause cannot apply because the regex flags every candidate; [870] (harness
envelopes offered as role=user) inflates its user-role band. Options: one rewrite plus replay
(as for backlog_ask), drop the site, or fix [870] first and re-measure.

## Lessons for the next nap

- When an option in a user question claims a tool can do something (replay a site), run its --help first: classifier_eval replay covers only the skill router.
- When a measurement's figure goes into a durable record, compute it in the same command that writes it: a recalled 167 had to be corrected to the measured 137.
- When typing a non-ASCII character into Edit/Write, it lands literal: build it with chr() in a script.
- When a pre-registered rewrite passes the statistical clauses, still run the blind review before shipping: v2 passed band and agreement and then lost 35 to 11.
- tooling: ci_wait exits 2 when one gh call exceeds its 1 s limit (queued as a contribution).

## How to verify

- `env -u VIRTUAL_ENV uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/ -q`
- `git grep -n backlog_ask -- plugins docs ':!*/.skillwriter/*'` shows only the tests pinning the removal
- `python3 ~/.claude/plugins/cache/bitranox-skills/bitranox/<installed>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
