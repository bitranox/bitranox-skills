# Handover - written 2026-09-01, nothing in flight

## In flight

Nothing. One commit, gated before the push.

## Committed, or not

Code and backlog are at `48b616b`, plugin `5.299.2`. This file and its companion backlog edit are
the only things after it.

## What was done, in one paragraph, because the repo cannot tell you WHY

`OPEN-WORK.md` item 10, continued: the six non-guard reports of the 2026-08-28 script wave, the
ones never mentioned anywhere in `TRIAGE.md`. All 22 claims were driven against the LIVE tree, not
read - a JSON event or an in-process call, each paired with a control that had to answer the
opposite. 15 confirmed, 6 refuted because they were already fixed (all of
`warn-inline-powershell`'s first five, which was rewritten after the report, plus the
`self-improve-audit` injection hole closed by `inert_snippet`), and 1 split. Of the 15, ten are
behavioural and five are untested-but-correct coverage gaps. The user chose one of four scoped
options: fix the two `session-start` decoy-check findings, together. That shipped as `5.299.2`.

## Decided, and why - do not reopen

- **The two decoy findings ship together or not at all.** The machine-wide stamp was what limited
  the `_anchor` bug to one firing per machine per day. Correcting the throttle alone would have
  made the destructive advice fire MORE often, not less. Anyone reopening either half needs to
  hold both.
- **`decoy_context` resolves its own anchor rather than borrowing `memory_engine._anchor`.**
  `_anchor` deliberately falls back to the project dir for bootstrap callers;
  `find_decoy_anchors` cannot accept that fallback. `retrieval_context` in the same file already
  had the correct shape, so this makes two neighbours agree rather than inventing a third rule.
- **The timing claim in `self-improve-audit` report finding 1 was not treated as urgent, and
  that verdict is deliberately scoped.** The double read is real. The claimed consequence does not
  reproduce HERE: worst 0.54 s across all 15 real transcripts over 9 MB, median 0.35 s, against
  the documented 1.5 s SessionEnd budget. But host speed was never controlled - the report's
  4.85 s came from its own room and I never ran its fixture on this host, so shape and machine
  speed stay confounded. Read it as "does not occur on this machine with real data", not as "the
  report was wrong". One pass would buy back about 15 percent, not the claimed half.

## Decided against, and why

- **Fixing the other eight confirmed behavioural findings.** Out of the scope the user chose. They
  are named on item 10 with their mechanisms, and in full in the wave's `TRIAGE.md`.
- **Chasing the five untested-but-correct coverage gaps now.** Every one behaves correctly today;
  they are regression exposure, not defects.

## Still open, untouched

Sixteen items in `OPEN-WORK.md`, ranked. Read that file; summarising it here is the re-encoding
that file exists to prevent.

## The exact next action

**`OPEN-WORK.md` item 10 again** - the eight remaining confirmed behavioural findings. The two
worth taking first, because both silently corrupt measurements rather than merely misinforming:

- `subagent-brief` injects 718 characters at the start of a clean-room dispatch whenever the
  agent_type is tool-capable, and emits the full envelope for an event whose `agent_type` it
  cannot identify at all. It fails OPEN against the fail-CLOSED asymmetry its own docstring states.
- `subagent-backstop-nudge` tells a named `baseline-probe` to call `SendMessage`, a tool its
  definition does not give it, and keys its background test on `name` when the live Agent tool
  schema says `isolation: "remote"` is what "always runs in background".

Three things that pass are worth carrying:

- Adjudicate against the LIVE tree, never the report. Six of 22 claims here were already fixed.
- Pair every probe with a control that must answer the opposite. One of mine fed the contribution
  queue IDENTICAL records, which deduped to a constant 601 chars and read exactly like a bounded
  function; distinct records showed 26,951.
- Ground truth this room has and the reviewers did not: real transcripts settle shape questions
  (list-form `tool_result.content` is 1101 of 38389, so that untested branch is a production
  path), and the Agent tool schema in the session prompt settles the backgrounding question.

If you do something else instead, say so in the next handover and why - recency is not a reason.

## Files that matter

- `OPEN-WORK.md` - the backlog; its header states the line format and ranking rules.
- `/media/srv-main-softdev/projects/public/KI/scriptwave-2026-08-28/TRIAGE.md` - the audit record.
  Its `NON-GUARD SLICE ADJUDICATED 2026-09-01` section holds all 22 verdicts with their evidence,
  so nothing here is re-derived. Beside the repo, not inside it: 19 MB, and this repo is public.
- `plugins/bitranox/hooks/session-start.py` - `decoy_context`, and `retrieval_context` above it
  for the anchor shape it now matches.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

`repo-gate: all checks passed`; 4213 passed / 13 skipped / 1 xfailed at `48b616b`.

## Three traps this session paid for

- **`meta-claude-hooks` is no longer exhaustive.** `hookdoc_stamp.py check` returns STRUCTURAL:
  upstream added `PreModelSwitch` and `PostModelSwitch` (31 to 33 events). Filed as item 95. Run
  that check before quoting the skill as authoritative.
- **A version bump needs BOTH `plugins/bitranox/.claude-plugin/plugin.json` AND `pyproject.toml`.**
- **Do not write a commit message file in the same Bash call as the commit.** The gate judges the
  whole command before any statement runs, so a block discards the prep with it. It did not fire
  this time; the nudge did.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
