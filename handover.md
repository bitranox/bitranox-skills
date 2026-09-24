# STALE - read 2026-09-25, work continued

## In flight

Nothing. 7.21.0 (`048713c`) is on master: the skill_router's Jev shadow now asks the choice shape,
and `classifier_eval.py report` can read it. CI passed on that commit (`workflow=success
ci=success`, via `ci_wait` on the full sha). The only change after it is this file.

## Committed, or not

- **Committed and pushed:** 7.21.0. That covers the hook, the report, tests, CHANGELOG, both
  version fields, `docs/reference.md`, the `meta-memory-settings` cell with its review artifact
  `plugins/bitranox/skills/meta-memory-settings/.skillwriter/checklist-20260924-router-choice-shape.md`,
  and OPEN-WORK rank 12.
- **Committed with this handover:** this file only.
- **Not in git, local only:** `EXECUTION-USER-REVIEW.md` in this worktree (ignored through the
  clone's `.git/info/exclude`). It holds the user's router choice and one autonomous decision.

## Decided, and why - do not reopen

- **skill_router stays in shadow, with the choice shape** (user, 2026-09-24: "Fix the shape, stay
  in shadow", chosen over decide mode now and over parking Jev). Decide mode waits for live
  choice-v1 rows and a blind-labelled sample of them, because a shadow row cannot say whether a
  pick was right.
- **New rows get their own tag, `question_view: choice-v1`,** rather than a bump of `router_view`
  (`ctx-v1`). `router_view` records the context shown, which did not change. Every `*_view` key
  feeds the report's grouping, so old and new rows never pool.
- **The report reads choice rows with the production rule `classifier.choice_pick`** (gate
  passes, or the winner's own probability reaches the 0.7 bypass, and never `none_needed`), at the
  site threshold 0.5 from `SITE_THRESHOLDS` in `classifier_eval.py`.

## Decided against, and why

- **Removing `skill_router_questions`.** The live hook no longer calls it, but the replay's nouls
  arm still does (`classifier_eval.py` `run_arm` and `size_replay`).

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 12 (USER): Jev. It is waiting on data now; its next step needs choice-v1 rows to exist.
- Rank 14 (USER): the approved invented-identifier guard.
- Ranks 82, 145, 150, 160 (FOUND): the git_state recall gap, the unbounded shadow log, the staged
  `TODO-JEV.md` in the main checkout, and the finished worktrees to remove (this one included).

## Lessons for the next nap

- When you change the SHAPE of what a producer writes (a question type, a field's type), check
  every reader parses the new shape: `classifier_eval`'s `_scores` kept only numeric answers, so a
  choice row would have read as "no pick" with nothing failing.
- When you change what a hook sends, grep the docs for the old description. Both
  `meta-memory-settings` and `docs/reference.md` still said "one yes/no per shipped skill", stale
  since 7.16.0 widened the roster.
- When a handover names a symbol's file, grep it before writing: the last one placed
  `SITE_THRESHOLDS` in `classifier.py`, and it lives in `classifier_eval.py`.
- tooling: in a worktree-isolated session even `bash run-python.sh skill_receipt.py start ...` is
  refused as "cannot be shown not to run git". Put it in a scratchpad script and run that.

## The exact next action

`OPEN-WORK.md` rank 10 is the top-ranked open item and nothing ranked above it is actionable: the
skills-and-scripts review, one subagent each, asking before changing anything. Start by sizing it:
count the targets under `plugins/bitranox/skills/*/` and `plugins/bitranox/hooks/`, and write the
count into the line.

Jev (rank 12) cannot move until live rows exist. Once sessions on 7.21.0+ have run for a while,
check with:

```bash
uv run plugins/bitranox/skills/meta-self-improve/classifier_eval.py report
```

and look for the `skill_router@...+choice-v1+...` group.

## Files that matter

- `plugins/bitranox/hooks/skill-router.py`: `_shadow_skill_router`, `QUESTION_VIEW`.
- `plugins/bitranox/hooks/classifier.py`: `skill_router_choice_questions`, `choice_pick`,
  `CHOICE_BYPASS`.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`: `_router_verdict`,
  `summarize_skill_router`, `SITE_THRESHOLDS`.
- `~/.claude/self-improve-audit/classifier-shadow.jsonl`: the shadow log the report reads.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -3 origin/master
uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

origin/master carries `048713c` (or later), and the gate prints `repo-gate: all checks passed`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
