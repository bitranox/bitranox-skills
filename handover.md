# STALE - read 2026-09-24, work continued

## In flight

Nothing. 7.20.0 (`e8258fc`, meta-context-watcher's description names "what next") is on master and
CI passed on it (`workflow=success ci=success`, checked with `ci_wait` on the full sha). The only
change after it is this file.

## Committed, or not

- **Committed and pushed:** 7.20.0. That covers the description, the review artifact
  `plugins/bitranox/skills/meta-context-watcher/.skillwriter/checklist-2026-09-24-what-next-trigger.md`,
  the CHANGELOG, `docs/skills.md`, both version fields, and OPEN-WORK rank 12.
- **Committed with this handover:** this file only.
- **Not in git, durable:** `.plan/jev-whatnext-2026-09-24/` in the MAIN checkout (gitignored). It
  holds PREREG.md, the 10-prompt what-next set, every A/B run including the cw1/cw2 re-runs, the
  wn and re-judge labels, the native haiku probe files, and every script.
- **Not in git, local only:** `EXECUTION-USER-REVIEW.md` in this worktree, ignored through the
  clone's `.git/info/exclude`. It records one decision, below.

## Decided, and why - do not reopen

- **Shipped v2 although it loses "whats open ?".** It lost that pick in 3 of 3 reps. The winner
  is still context-watcher, but its probability fell from 0.78-0.88 to 0.55-0.69, under the 0.7
  bypass. That is one pick against 13 to 14 of the same kind gained. Recovering it would need a
  wording fitted to prompts that have all been read now.
- **The cw2 "gate, push, then write the handover" loss is noise.** The OLD wording flips between
  context-watcher and `tfbpr` across runs.

## Decided against, and why

- **Claiming the native (Claude Code) routing arm as a win.** It was near ceiling already, 18/20
  with the old wording against 20/20 with the new. It shows no harm, and it is not evidence of a
  gain.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 12 (USER): Jev. Its next step is a question for the user: skill_router decide mode.
- Rank 14 (USER): the approved invented-identifier guard.
- Ranks 82, 150, 160 (FOUND): the git_state recall gap, the staged `TODO-JEV.md` in the main
  checkout, and the finished worktrees to remove (this one included, once nothing needs it).

## Lessons for the next nap

- When a previous session's subagent dispatches show "The user doesn't want to proceed with this
  tool use", read that as the user REJECTING that exact step, not as an unfinished step: ask before
  re-dispatching it.
- When an experiment lives only in an ended session's scratchpad, copy it somewhere durable and
  byte-verify the copy before running anything else on it.
- When a guard set runs once per arm, re-run any row the new arm lost before calling it a loss. Of
  the two lost rows here, one reproduced (3/3) and one was the OLD arm flipping by itself.
- When a lost pick keeps the same winner, look at the probability against the pick rule's cutoff:
  the loss can be a threshold effect, not a routing change.
- When a probe measures a channel that is already near ceiling with the old text, report it as
  "no harm", not as a gain for the new text.
- When a CI wait needs a full sha, paste the 40 characters a previous call PRINTED. The invented
  identifier rule recurred here (recurrence 5): a short sha was padded into a fake full one, and
  ci_wait's not-a-commit warning is what caught it. That is evidence for OPEN-WORK rank 14's guard.
- tooling: in a worktree-isolated session, `env -u VIRTUAL_ENV uv run ...` with long args and a
  heredoc-fed python are refused as too complex. Put the command in a scratchpad script and run it.

Carried from earlier handovers, capture status unknown:

- When experiment labels were produced by judges who saw the thing under test, read a falsifier hit
  as possible label contamination. Re-judge the disputed rows with a neutral view plus unrelated
  controls before concluding.
- When a router never offers a skill whose body covers the case, read its DESCRIPTION before tuning
  inputs or thresholds.
- When a replay reads skill descriptions from recorded transcripts, an edited SKILL.md never
  reaches it. Override the text explicitly and assert per row that the override applied.
- When scoring runs against labels, key them by row uuid, never by prompt text.
- When a helper lives in a script with module-level work, importing it re-runs that work. Put
  helpers where an import has no side effects.
- tooling: in a worktree-isolated session `--sha $(git rev-parse HEAD)` is refused as too complex.
  Derive the sha in a separate call and paste what it printed.
- When you put numbers into the options of a question to the user, check they come from the set and
  threshold the question is about.
- When a replay changes a rule, diff old against new verdicts call by call and read every changed
  one.
- When a test fakes a directory that production code walks upward from, put the fake inside a tree
  the test owns.
- tooling: toolbox-nudge fired on measurement work rather than chores (srccount, transcript_index,
  procsig, factedit). That is precision evidence for the next time its rules are priced.
- When a cheap proxy and a careful parser disagree about the same quantity, suspect the PROXY first.
- tooling: block-masked-gate-exit blocks a plain backgrounded `ci_wait.py`, so a CI wait must run in
  the foreground with `--timeout` under the 600 s tool cap.

## The exact next action

`OPEN-WORK.md` rank 10 is the top-ranked open item: the skills-and-scripts review, one subagent
each, asking before changing anything. Start by sizing it: count the targets under
`plugins/bitranox/skills/*/` and `plugins/bitranox/hooks/`, and write the count into the line.

The user has chosen Jev (rank 12) over rank 10 in each recent session. If they do again, the next
step is ONE question to them, the router first, with the recommendation to put skill_router into
decide mode:

- the arm is choice_full at gate 0.5 plus the 0.7 confidence bypass, falling back to keywords on a
  timeout or an error;
- the live hook must switch from `classifier.skill_router_questions` to
  `skill_router_choice_questions`, because it still asks the nouls shape.

stop_signal and recall_rerank follow, one at a time.

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py`: `replay`, `--description`,
  `--prompts`, `locate_prompt`.
- `plugins/bitranox/hooks/classifier.py`: `choice_pick`, `skill_router_choice_questions`,
  `SITE_THRESHOLDS`.
- `plugins/bitranox/hooks/skill-router.py`: `_shadow_skill_router`, which still asks the nouls
  shape.
- `plugins/bitranox/skills/meta-context-watcher/SKILL.md`: the description line.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -3 origin/master
uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

origin/master carries `e8258fc` (or later), and the gate prints `repo-gate: all checks passed`.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
