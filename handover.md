# STALE - read 2026-11-02, work continued

## In flight

Nothing in code. 10.10.0 ships `proxy_pool.py fetch` (issue #4): a chunked byte-range download
over the rotating pool. Built in the worktree `.claude/worktrees/chunked-fetch` from the plan
`docs/plans/2026-11-01-proxy-chunked-fetch.md`, then five review-fix rounds.

- Pending with the USER: whether to comment on or close GitHub issue #4. Ask; never post unasked.
- The worktree is removed once CI on the pushed release is green and its gitignored
  `EXECUTION-USER-REVIEW.md` is merged into the main checkout's copy.

## Decided

The decisions behind the fix rounds are in the main checkout's `EXECUTION-USER-REVIEW.md` (four
2026-11-02 entries): only a failed connect bans to `bad.txt`; odd answers evict for the run only;
no exit 2 from what proxies answer (exit 2 = local causes and a sha256 mismatch); a rerun trusts
its manifest over a fresh probe vote; a shortened part counts only the bytes it holds.

## Still open, untouched

- OPEN-WORK.md [30] (re-count on/after 2026-11-05), [50] (issue #4's geo-routing part, ask the
  user first), [96], [100] (`run`'s Ctrl-C), [110] (pre-existing ruff findings in proxy_pool.py).

## Next action

[30] once 2026-11-05 has passed; before that, ask the user about [50].

## How to verify

- `uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/net-rotating-proxies/ -q -W error`
- `ci_wait.py --ref HEAD` (bitranox:compuse-toolbox) on the release commit

## Lessons for the next nap

(none open; this session's were captured by its naps)

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
