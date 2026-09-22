# Handover - written 2026-09-22, nothing in flight

## In flight

Nothing. The Jev shadow work shipped as 7.2.0, 7.3.0 and 7.4.0 (CI green on `059f884`, `61f2f6e`,
`114b748`). The shadow log was deleted after 7.4.0 was loaded, so it is filling with current-input
rows only.

## Committed, or not

- `bitranox-skills`: everything is on `origin/master`, plugin `7.4.0`, except this handover commit.
  Work was done in the worktree `.claude/worktrees/jev-classifier`; once this commit is pushed it can
  be removed (`wtclean.py jev-classifier`) and the main checkout pulled.
- `TODO-JEV.md` at the MAIN checkout root stays untracked on purpose (user's choice); its Progress
  section was NOT updated this session - the state is in the `OPEN-WORK.md` rank-12 line.
- Machine config: `classifier_backend = jev`, all three sites `shadow`. Key: `~/.credentials/typesafe.key`.

## Decided, and why - do not reopen

- **The Stop gate's own verdict is unchanged by 7.4.0.** Transcript reading moved to
  `hooks/transcript_turns.py`; the gate still judges the newest assistant text, only the classifier
  gets the reply before the prompt.
- **An assistant answer to Stop-hook feedback is not "the reply".** Measured on this session's
  transcript: without the rule, the context for "yes" was the one-line hook answer. Matched on the
  `Stop hook feedback:` prefix, never `isMeta` alone, because skill bodies are `isMeta` too.
- **Every changed input is tagged in the log** (`note_view`, `context_view`), and the report groups
  by every `*_view` key, so old and new rows are never pooled.
- The user chose to delete old shadow logs after each input change rather than keep them.

## Decided against, and why

- More conversation history than one trimmed previous reply: TypeSafe's guidance is that irrelevant
  state lowers accuracy, and recall multiplies every token by 30 requests.

## Still open, untouched

Nineteen items in `OPEN-WORK.md`; rank 12 (Jev) was updated this session.

## Lessons for the next nap

- When a reranker judges a keyword shortlist, show it each candidate's own summary, not the window
  centred on the matched word (already captured as a fact this session; nothing to add).
- When a test fixture is built from how you THINK the transcript looks, run the code once on a real
  transcript too: the Stop-hook-answer defect passed every synthetic test and showed on the first real one.
- When judging Jev-only firings, read the actual turn text before calling them noise: in the 7.3.0
  rows all three were real lessons the regex missed.
- tooling: the self-improve Stop gate fires on a self-admission phrase the assistant QUOTES as data
  (queued in contrib_queue as `hook:self-improve-gate`).

## The exact next action

`OPEN-WORK.md` item 10, the top-ranked USER item: copy `TRIAGE.md` out of the ZFS snapshot named in
that line to somewhere durable, then ask the user which bucket goes next. Rank 12 (Jev) follows once
the shadow log has a few sessions of 7.4.0 rows: `classifier_eval.py report` at 0.5/0.7/0.9.

## Files that matter

- `plugins/bitranox/hooks/classifier.py` - port, questions, `with_previous`, `CONTEXT_VIEW`.
- `plugins/bitranox/hooks/transcript_turns.py` - prompt / reply / reply-before-prompt, `excerpt`.
- `plugins/bitranox/hooks/recall-memory.py` - `_note_view`, `_shadow_recall`.
- `plugins/bitranox/hooks/skill-router.py`, `plugins/bitranox/hooks/self-improve-gate.py` - the other two sites.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - the report.
- Tests: `plugins/bitranox/hooks/tests/test_transcript_turns.py`, `test_classifier_sites.py`,
  `test_recall_memory.py`; `plugins/bitranox/skills/meta-self-improve/tests/test_classifier_eval.py`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report
```

`repo-gate: all checks passed` (4916 passed at `114b748`); the report groups rows as
`<site>@prev-reply-v1...`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
