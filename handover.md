# Checkpoint 2026-11-01 (compact mode): backlog [40] chunked proxy fetch

## In flight

Backlog [40] / issue #4: a `fetch` subcommand for net-rotating-proxies that downloads ONE large
file as byte-range chunks over the rotating pool. The session runs in the EnterWorktree worktree
`.claude/worktrees/chunked-fetch` (branch `worktree-chunked-fetch`, base origin/master b990191f =
v10.9.18 released).

- Design: `docs/plans/2026-11-01-proxy-chunked-fetch-design.md`, COMMITTED in the worktree
  (794fbd1c), not pushed. Approved by the user section by section.
- Plan: `docs/plans/2026-11-01-proxy-chunked-fetch.md`, UNCOMMITTED, being finalised. Already
  revised for: probe voting on every reply (exact `bytes 0-0/N` only), `pool.active()` in the
  port, Task 4 reduced to the whole-file fallback.
- Mid-edit: route the probe's "only one proxy answered" warning through a `warn` callable that
  defaults to stderr (it went to stdout via `log`, which broke the CLI warning test). Spots:
  plan lines ~166 (add `sys` import), ~457 (add `_stderr` helper beside `_client`), ~509
  (interface text), ~529/630/637/871 (tests: pass `warn=`), ~680/719 (probe signature and
  call), ~780-783 (fetch gains `warn=None`, passes it to probe). Also in the mixed-pool test read
  bad.txt with `pp._read(...)`, which tolerates a missing file.
- `OPEN-WORK.md` [40] rewritten to IN PROGRESS (uncommitted, in the worktree).

## Committed, or not

- Worktree: 794fbd1c (design) committed; plan, OPEN-WORK.md edit and this file uncommitted.
- Main checkout: `handover.md` carries an uncommitted STALE line; untracked `o` is a peer's.

## Decided

- User: work [40] now; approach "New fetch subcommand"; design sections 1-3 approved.
- Probe answers are votes (design refinement, to report to the user with the plan): decide when
  two distinct proxies agree or every active proxy answered; a single-voter decision is warned.
- `chunked_fetch.py` never imports `proxy_pool`; the pool is a parameter (acquire, mark_in_use,
  record, ban, active), so tests drive the real ProxyPool.
- 10.9.18's two commits shared one bump (the bump jig cannot stack a second unpushed bump).

## Still open, untouched

- OPEN-WORK.md [30] (re-count on/after 2026-11-05), [96] (needs more dream runs).

## Next action

Finish the `warn` edits listed above in the plan, self-review once more, commit the plan with the
OPEN-WORK.md line, tell the user about the voting refinement, then execute Task 1 (TDD) in the
worktree.

## How to verify

- `git log --oneline origin/master..HEAD` in the worktree
- `env -u VIRTUAL_ENV uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/net-rotating-proxies/ -q` (baseline 86 passed)

## Lessons for the next nap

- When a probe or first contact decides a value every later step trusts (size, identity), take it by agreement of two independent sources, not the first answer: one lying source otherwise poisons every honest one after it.
- tooling: bump_version.py refuses a second bump while an earlier bump is unpushed; for two commits in one push, share the first bump and extend its CHANGELOG section.
- When a session is worktree-isolated, a compound inline python/heredoc Bash call is refused: Write the script to the scratchpad, then run it plainly.

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
