# Checkpoint 2026-10-27 16:00: audit_candidate dropped (10.3.11), [870] harness tag (10.3.12)

## In flight

Nothing part-done in code. [28]'s second wave now has one shadow site left, `jig_repetition`.

## Committed, or not

- 10.3.11 carries: the `audit_candidate` site removed (classifier, self-improve-audit, defaults,
  settings and its skill row, classifier_eval, docs), the [28] line's 2026-10-27 state.
- 10.3.12 carries [870]: the audit note tags a user-role message `looks_typed` rejects as
  `[harness]` (user chose "Relabel as machine (Recommended)" 2026-10-27), the meta-self-improve
  audit section says so, [870] deleted, [860] holds the shapes the registry still misses.
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

- One question the user raised on 2026-10-27, answered with measurements, not decided: whether to
  re-test backlog_ask as "regex first, then Jev at >= 0.8" (8 right, 1 wrong on the judged set,
  but that threshold was fitted on it). I recommended leaving it regex-only.
- OPEN-WORK.md holds the backlog; [23] stays the top USER item.

## Exact next action

[860]: extend `transcript_turns` NOT_TYPED registry with the measured shapes in its line, after a
replay of the Stop gate and the router over real history (guard_replay) shows what changes.

## Lessons for the next nap

- When a backlog line sizes a defect from a sampled log, re-measure on the source before fixing:
  [870] said at least 34 of 159, the transcripts said 630 of 679 shown user-role candidates.
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
