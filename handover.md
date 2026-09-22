# Handover - written 2026-09-22, nothing in flight

## In flight

Nothing. The Jev shadow work shipped as 7.2.0 to 7.5.0. 7.5.0 (the router's context and gate
question) is committed with this handover; check its CI result if the push below is not green.

## Committed, or not

- `bitranox-skills`: everything is on `origin/master` with this commit, plugin `7.5.0`. Work was
  done in the worktree `.claude/worktrees/jev-classifier`; it can be removed
  (`wtclean.py jev-classifier`) and the main checkout pulled.
- The running plugin needs `/plugin marketplace update bitranox-skills` and `/reload-plugins` to
  pick up 7.5.0.
- `TODO-JEV.md` at the MAIN checkout root stays untracked on purpose (user's choice); its Progress
  section was NOT updated - the state is in the `OPEN-WORK.md` rank-12 line.
- Machine config: `classifier_backend = jev`, all three sites `shadow`. Key: `~/.credentials/typesafe.key`.

## Decided, and why - do not reopen

- **Router context (user chose options 1-4):** a `_new_task` gate question, `project` (scope WHAT
  line), `recent_activity` (last 6 tool calls; Bash named by its description, never its command),
  `skills_already_used` (invoked plus already nudged). The eval suggests nothing when the gate is
  below threshold. Option 5 (pre-filter to the keyword shortlist) is the fallback if this fails.
- **The Stop gate's own verdict is unchanged**; only the classifier gets the reply before the
  prompt. An assistant answer to Stop-hook feedback is not "the reply" (prefix match, not `isMeta`).
- **Every changed input is tagged** (`note_view`, `context_view`, `router_view`); the report groups
  by every `*_view` key, so old and new rows never pool.
- The user deletes old shadow logs after input changes when they want a clean slate.

## Decided against, and why

- Full conversation history as context: irrelevant state lowers accuracy (TypeSafe guidance), and
  recall multiplies every token by 30 requests.

## Still open, untouched

Nineteen items in `OPEN-WORK.md`; rank 12 (Jev) was updated this session.

## Lessons for the next nap

- When a test fixture is built from how you THINK the transcript looks, run the code once on a real
  transcript too: the Stop-hook-answer defect passed every synthetic test and showed on the first real one.
- When judging Jev-only firings, read the actual turn text before calling them noise: in the 7.3.0
  rows all three were real lessons the regex missed.
- When a classifier answers "which of N labels applies", give it a way to answer "none": without the
  router's gate question every prompt, even "yes", got two skills.
- tooling: the self-improve Stop gate fires on a self-admission phrase the assistant QUOTES as data
  (queued in contrib_queue as `hook:self-improve-gate`).

## The exact next action

`OPEN-WORK.md` item 10, the top-ranked USER item: copy `TRIAGE.md` out of the ZFS snapshot named in
that line to somewhere durable, then ask the user which bucket goes next. Rank 12 (Jev) follows once
the shadow log has a few sessions of 7.5.0 rows: `classifier_eval.py report` at 0.5/0.7/0.9 and
read the `--disagreements` rows.

## Files that matter

- `plugins/bitranox/hooks/classifier.py` - port, questions (`NEW_TASK_ID`), `with_previous`.
- `plugins/bitranox/hooks/transcript_turns.py` - turn, `last_reply`, `recent_activity`, `skills_used`, `excerpt`.
- `plugins/bitranox/hooks/skill-router.py` - `_router_fields`, `_project_line`.
- `plugins/bitranox/hooks/recall-memory.py`, `plugins/bitranox/hooks/self-improve-gate.py` - the other two sites.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - the report, `_router_picks`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report
```

`repo-gate: all checks passed` (4924 passed); router rows appear as
`skill_router@prev-reply-v1+ctx-v1`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
