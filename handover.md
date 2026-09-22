# STALE - read 2026-09-22, work continued

## In flight

Nothing. 7.5.0 is pushed and CI-green (`ca9f609`). The shadow log then collected 81 rows under it,
which are analysed below; no code change followed that analysis.

## Committed, or not

- `bitranox-skills`: everything is on `origin/master`, plugin `7.5.0`, except this handover commit.
  Work was done in the worktree `.claude/worktrees/jev-classifier`; it can be removed
  (`wtclean.py jev-classifier`) and the main checkout pulled.
- `TODO-JEV.md` at the MAIN checkout root stays untracked on purpose (user's choice); its Progress
  section was NOT updated - the state is in the `OPEN-WORK.md` rank-5 and rank-12 lines.
- Machine config: `classifier_backend = jev`, all three sites `shadow`. Key: `~/.credentials/typesafe.key`.

## Decided, and why - do not reopen

- **The router's new-task gate earns its place.** Over 21 prompts it cut Jev's picks from 1.8 per
  prompt to 0.62, gated out every continuation, and on real new tasks picked the right skills. Do
  not go back to asking only "would this skill help?" per skill.
- **`endorsement` comes out of the Stop gate's firing set** (keep logging it): all 5 of its
  standalone firings were plain approvals. `self_admission` and `realization` stay - 10 of their
  firings were real misses the regex never caught.
- **Recall needs a higher threshold, not a different input.** The description view fixed the
  matched-word problem; at 0.5 it is simply too generous (165 relevant against 99 injected).
- **An assistant answer to Stop-hook feedback is not "the reply"** (prefix match, not `isMeta`).
- **Every changed input is tagged** (`note_view`, `context_view`, `router_view`), and the report
  groups by every `*_view` key, so old and new rows never pool.

## Decided against, and why

- Full conversation history as classifier context: irrelevant state lowers accuracy, and recall
  multiplies every token by 30 requests.
- Suggesting nothing on a `<task-notification>` as a PRINCIPLE: a failed preflight can genuinely
  warrant a skill. What is wrong is judging it from the envelope text, which is why rank 5 sends
  Jev the notification's own fields instead.

## Still open, untouched

Twenty items in `OPEN-WORK.md`; rank 5 is new and rank 12 carries the 7.5.0 measurements.

## Lessons for the next nap

- When a keyword matcher scores free text, strip paths, ids and tags first (captured as a fact this
  session; nothing to add).
- When a test fixture is built from how you THINK the transcript looks, run the code once on a real
  transcript too: the Stop-hook-answer defect passed every synthetic test and failed on the first real one.
- When a classifier answers "which of N labels applies", give it a way to answer "none": without
  the router's gate question every prompt, even "yes", got two skills.
- When judging a classifier's extra firings, adjudicate them by FAMILY: the same site was noise in
  one family and correct in two others, and a single per-site rate hid both.
- tooling: the self-improve Stop gate fires on a self-admission phrase the assistant QUOTES as data
  (queued in contrib_queue as `hook:self-improve-gate`).

## The exact next action

`OPEN-WORK.md` rank 5, which the user asked for as the first thing after this handover: in
`plugins/bitranox/hooks/skill-router.py`, skip prompts starting with the
`transcript_turns.NOT_TYPED_PREFIXES` shapes AND strip tags, paths, ids and hashes before `match()`,
with a test per class and a replay over real transcript prompts to show the firing rate falls
without losing real matches. Then rank 5's second half (option 4): send Jev a notification's
`status` and `summary` as their own fields, shadow only.

## Files that matter

- `plugins/bitranox/hooks/skill-router.py` - `match`, `_router_fields`, `_project_line`, the nudge and its once-per-session state file.
- `plugins/bitranox/hooks/transcript_turns.py` - `NOT_TYPED_PREFIXES`, turn reading, `recent_activity`, `skills_used`, `excerpt`.
- `plugins/bitranox/hooks/classifier.py` - port, questions (`NEW_TASK_ID`), `with_previous`.
- `plugins/bitranox/hooks/recall-memory.py` - `_note_view`; same machine-prompt input problem.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - the report, `_router_picks`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py report --threshold 0.7
```

`repo-gate: all checks passed` (4924 passed at 7.5.0); the report shows
`skill_router@prev-reply-v1+ctx-v1` beside the older `skill_router@prev-reply-v1` rows.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
