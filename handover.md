# STALE - read 2026-09-04, work continued

## In flight

Nothing. Working tree clean in both repos, everything pushed and verified.

## Committed, or not

- `bitranox-skills`: `HEAD == origin/master == 74d6f5a`, plugin `5.300.4`, CI green on both runs.
  Three of this session's versions are mine (`5.299.2` `48b616b`, `5.299.3` `5066ed4`); `74d6f5a`
  is another session's docstring commit that was left unpushed, verified then pushed from here.
- Memory store `/media/srv-main-softdev/.claude-memory`: `HEAD == origin/main == 4248e3b`,
  0 unpushed, 0 dirty. It was 20 commits and 36 files behind at the start of the session.

## What was done, in one paragraph, because the repo cannot tell you WHY

`OPEN-WORK.md` item 10: the six non-guard reports of the 2026-08-28 script wave, the ones never
mentioned in `TRIAGE.md`. All 22 claims driven against the LIVE tree - a JSON event or an
in-process call, each paired with a control that had to answer the opposite. 15 confirmed, 6
refuted because already fixed, 1 split. Two were fixed and shipped; the other eight are still open.
Then a second, unrelated thread: the user settled two standing questions about where things may be
pushed, and both are now recorded in the memory store rather than in this file.

## Decided, and why - do not reopen

- **The two decoy-check fixes ship together or not at all.** The machine-wide stamp was what
  limited the `_anchor` bug to one firing per machine per day, so correcting the throttle alone
  would have made the destructive advice fire MORE often.
- **`decoy_context` resolves its own anchor rather than borrowing `memory_engine._anchor`.**
  `_anchor` deliberately falls back to the project dir for bootstrap callers;
  `find_decoy_anchors` cannot accept that fallback. `retrieval_context` beside it already had the
  right shape, so this makes two neighbours agree rather than inventing a third rule.
- **The `self-improve-audit` timing claim is scoped, not refuted.** Worst 0.54 s across all 15 real
  transcripts over 9 MB here, against a 1.5 s budget - but host speed was never controlled and the
  report's fixture was never run on this machine. It reads "does not occur here with real data",
  NOT "the report was wrong". The duplicated read is real either way.
- **Two standing questions about publishing destinations were settled by the user.** Both are
  recorded in the memory store, which is where they belong and where the next session already
  loads them; deliberately not restated in this public repo.

## Decided against, and why

- **Fixing the other eight confirmed behavioural findings.** Outside the scope the user chose. They
  are on item 10 with their mechanisms, and in full in the wave's `TRIAGE.md`.
- **Chasing the five untested-but-correct coverage gaps.** Every one behaves correctly today; they
  are regression exposure, not defects.
- **Re-levelling the memory fact named in item 15 on the spot.** It strands two outbound refs.
  Filed rather than half-done here.

## Still open, untouched

Eighteen items in `OPEN-WORK.md`, ranked. Read that file; summarising it here is the re-encoding
that file exists to prevent.

## The exact next action

**`OPEN-WORK.md` item 10** - still top-ranked, still the oldest, still the user's own directive.
The eight remaining confirmed behavioural findings. Take these two first, because both corrupt
MEASUREMENTS rather than merely misinforming a reader:

- `subagent-brief` injects 718 characters at the start of a clean-room dispatch whenever the
  `agent_type` is tool-capable, and emits the full 803-byte envelope for an event whose
  `agent_type` it cannot identify at all - failing OPEN against the fail-CLOSED asymmetry its own
  docstring states.
- `subagent-backstop-nudge` tells a named `baseline-probe` to call `SendMessage`, which its
  definition does not give it (`tools: ReportFindings, Skill`), and keys its background test on
  `name` when the live Agent tool schema says `isolation: "remote"` is what always runs in
  background.

Item 15 is smaller and newer, and it is genuinely a USER directive that is only half reaching
sessions - take it first only if you want a short task. Item 10 is what someone is waiting on.

Three things that pass are worth carrying:

- Adjudicate against the LIVE tree, never the report: 6 of 22 claims were already fixed.
- Pair every probe with a control that must answer the opposite. Mine fed the contribution queue
  IDENTICAL records, which deduped to a constant 601 chars and read exactly like a bounded
  function; distinct records showed 26,951.
- This room has ground truth the reviewers lacked: real transcripts settle shape questions
  (list-form `tool_result.content` is 1101 of 38389, so that untested branch is a production path),
  and the Agent tool schema in the session prompt settles the backgrounding question.

## Files that matter

- `OPEN-WORK.md` - the backlog; its header states the line format and the ranking rules.
- `/media/srv-main-softdev/projects/public/KI/scriptwave-2026-08-28/TRIAGE.md` - its
  `NON-GUARD SLICE ADJUDICATED 2026-09-01` section holds all 22 verdicts with their evidence.
  Beside the repo, not inside it: 19 MB, and this repo is public.
- `plugins/bitranox/hooks/session-start.py` - `decoy_context`, and `retrieval_context` above it for
  the anchor shape it now matches.
- `plugins/bitranox/hooks/subagent-brief.py`, `plugins/bitranox/hooks/subagent-backstop-nudge.py` -
  the next action's two targets.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

`repo-gate: all checks passed`; 4216 passed / 13 skipped / 1 xfailed at `74d6f5a`.

## Four traps this session paid for

- **`meta-claude-hooks` is no longer exhaustive.** `hookdoc_stamp.py check` returns STRUCTURAL:
  upstream added `PreModelSwitch` and `PostModelSwitch`, 31 to 33 events. Item 95. Run that check
  before quoting the skill as authoritative.
- **A wikilink may only point UP the level chain, and nothing warns at write time.** Writing one
  into a tree-top fact aimed at a lower level dangles; only `--check-tree` reports it. And the
  engine parses ANY double-bracket token as a live ref, so an illustrative one in a hook creates an
  orphan. Both happened here, minutes apart.
- **A version bump needs BOTH `plugins/bitranox/.claude-plugin/plugin.json` AND `pyproject.toml`.**
- **Do not write a commit-message file in the same Bash call as the commit.** The gate judges the
  whole command before any statement runs, so a block discards the prep with it.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
