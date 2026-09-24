# Handover - written 2026-09-24 ~20:35, nothing in flight

## In flight

Nothing. 7.18.0 (`6f96b5b`) is pushed to master with CI passing (`workflow=success ci=success`,
checked with `ci_wait` on the full sha). This file and `OPEN-WORK.md` rank 160 are the only change
after it.

## Committed, or not

- **Committed and pushed:** 7.18.0 - `meta-context-watcher`'s description names reading a handover
  (the body already covered it), `classifier_eval.py replay --description SKILL=FILE`, tests,
  review artifact `plugins/bitranox/skills/meta-context-watcher/.skillwriter/checklist-2026-09-24-reading-trigger.md`,
  `OPEN-WORK.md` rank 12 updated.
- **Committed with this handover:** this file, and `OPEN-WORK.md` rank 160 (worktree cleanup).
- **Not in git, durable:** `.plan/jev-cw-desc-2026-09-24/` in the MAIN checkout (gitignored): the
  fresh 40-prompt set, every A/B run, both label sets, the re-judge, and every script. 32 files,
  byte-verified against their source.
- **Outside the repo:** the memory fact on invented identifiers was updated to recurrence 4, and a
  contrib_queue entry asks for a blind-adjudication packet/harvest pair in `classifier_eval.py`.

## Decided, and why - do not reopen

- **The context-watcher fix is the DESCRIPTION, not router option text.** The router sees only
  descriptions, the body already covered reading, and the description is also what Claude Code's
  own routing reads (haiku probes 0/8 -> 8/8 twice). Option text would have needed a second
  hand-kept file, which is why `choice_full` was preferred over `choice_router_text`.
- **The older panels' "no skill" labels on "read the handover" turns are superseded** by a blind
  re-judge that saw a neutral body summary: 11 of 11 rows unanimous right, 4 unrelated controls 0.
  Those panels had judged with the old description in view.

## Decided against, and why

- **Tuning the description further for "what next for <project>"** (context-watcher under 0.1
  there): the 40-prompt set is now read, so any change would be fitted to it.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 12 (USER): Jev. The next step is a question put to the user and not yet answered, see below.
- Rank 14 (USER): the approved invented-identifier guard; the rule hit recurrence 4 this session.
- Rank 82, 150, 160 (FOUND): git_state recall gap; staged `TODO-JEV.md` in the main checkout; two
  finished worktrees to remove.

## Lessons for the next nap

- When experiment labels were produced by judges who saw the thing under test (here the OLD skill
  description), read a falsifier hit as possible label contamination: re-judge the disputed rows
  with a neutral view plus unrelated controls before concluding.
- When a router never offers a skill whose body covers the case, read its DESCRIPTION before tuning
  inputs or thresholds: the router ranks descriptions, and a body section the description never
  names is invisible to it.
- When a replay reads skill descriptions from recorded transcripts, an edited SKILL.md never
  reaches it; override the text explicitly and assert per row that the override applied.
- When scoring runs against labels, key them by row uuid, never by prompt text: repeated prompts
  ("read handover") collapse and silently drop rows (47 and 41 of 50 matched).
- When a helper lives in a script with module-level work (a packet builder), importing it re-runs
  that work; put helpers where an import has no side effects.
- tooling: in a worktree-isolated session `--sha $(git rev-parse HEAD)` is refused as too complex,
  which is exactly when a hand-typed sha tempts; derive it in a separate call and paste what it
  printed.

Carried from the previous handover, capture status unknown:

- When you put numbers into the options of a question to the user, check they come from the set and
  threshold the question is about.
- When a replay changes a rule, diff old against new verdicts call by call and read every changed
  one; a class count undercounted the real change 30 against 166.
- When a test fakes a directory that production code walks upward from, put the fake inside a tree
  the test owns; one directly under `tmp_path` walks into pytest's shared root.
- tooling: toolbox-nudge fired on measurement work rather than chores (srccount, transcript_index,
  procsig, factedit); precision evidence for the next time its rules are priced.
- When a cheap proxy and a careful parser disagree about the same quantity, suspect the PROXY first.
- tooling: block-masked-gate-exit blocks a plain backgrounded `ci_wait.py`, so a CI wait must run in
  the foreground with `--timeout` under the 600 s tool cap.

## The exact next action

`OPEN-WORK.md` rank 10 is the top-ranked open item: the skills-and-scripts review, one subagent
each, asking before changing anything. Start by sizing it: count the targets under
`plugins/bitranox/skills/*/` and `plugins/bitranox/hooks/`, and write the count into the line.

If the user continues Jev instead (they chose it over rank 10 in the last two sessions), the
question left open for them is what comes next: put the skill router into decide mode
(recommended: the larger lever, `choice_full` at gate 0.5 is now backed on three labelled sets, but
it changes live behaviour and the hook must also switch from `skill_router_questions` to
`skill_router_choice_questions`), or chase the "what next" misses first (needs a new unseen prompt
set; smaller gain).

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `with_descriptions`,
  `description_override`, `roster_for`, `run_arm`
- `plugins/bitranox/skills/meta-context-watcher/SKILL.md` - the description line
- `plugins/bitranox/hooks/classifier.py` - `choice_pick`, `skill_router_choice_questions`
- `plugins/bitranox/hooks/skill-router.py` - `_shadow_skill_router` (still asks the nouls shape)

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -3 origin/master
uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

origin/master carries `6f96b5b` (or later), and the gate prints `repo-gate: all checks passed`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
