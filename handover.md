# Checkpoint 2026-10-27 15:30: [28] audit_candidate dropped (10.3.11); two user questions open

## In flight

Nothing part-done in code. [28]'s second wave now has one shadow site left, `jig_repetition`.

## Committed, or not

- 10.3.11 carries: the `audit_candidate` site removed (classifier, self-improve-audit, defaults,
  settings and its skill row, classifier_eval, docs), the [28] and [870] lines' 2026-10-27 state.
- `classifier_audit_candidate` was switched to `off` on this machine before the removal.
- Measurement scripts and data, gitignored: `.plan/jev-28/review-2026-10-27/`
  (PREREG-audit_candidate-v2.md, replay_audit.py, replay_audit.json, make_blind_audit.py - unused,
  clause 4 never ran).

## Decided, and why

- User replied "audit_candidate" to "one rewrite plus replay (my recommendation), or drop it";
  read as the recommended branch (EXECUTION-USER-REVIEW.md). v2 left 47.5% in band against a
  25% limit, so the pre-registered branch dropped the site.

## Decided against, and why

- No second rewrite: [96] allows one.
- The audit's candidate dicts no longer carry `text` and `uuid`: only the shadow read them.

## Still open, untouched

- Two questions the user raised on 2026-10-27, both answered with measurements, neither decided:
  [870] drop or relabel harness envelopes in the audit note; whether to re-test backlog_ask as
  "regex first, then Jev at >= 0.8" (8 right, 1 wrong on the judged set, but that threshold was
  fitted on it). Detail in the [870] and [28] lines of OPEN-WORK.md.
- OPEN-WORK.md holds the backlog; [23] stays the top USER item.

## Exact next action

Ask the user the [870] question (drop or relabel the harness envelopes the audit offers as
role=user), one AskUserQuestion with the measured 34-of-159 lower bound.

## Lessons for the next nap

- When an [96] site fails clause 1, check whether one role or one shape carries the band before
  proposing a fix upstream of it: tool-role alone was 40.2% in band, so fixing [870] could never
  have rescued audit_candidate.
- When a removed shadow site was the only reader of a field a hook builds, remove the field too:
  the audit kept carrying full message text and transcript ids for nobody.

## How to verify

- `env -u VIRTUAL_ENV uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/ -q`
- `git grep -n audit_candidate -- plugins docs ':!*/.skillwriter/*'` shows only the tests pinning the removal
- `python3 ~/.claude/plugins/cache/bitranox-skills/bitranox/<installed>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`

> Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
> delete it - if this session ends badly it is the only record of where things stood.
