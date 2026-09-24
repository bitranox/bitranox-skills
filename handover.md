# Handover - written 2026-09-24 ~18:05, nothing in flight

## In flight

Nothing. 7.16.0 (`f4ecd18`) and 7.17.0 (`0b81ce2`) are pushed to master with CI passing
(`workflow=success ci=success`, checked with `ci_wait` on each full sha). This file is the only
change after them.

## Committed, or not

- **Committed and pushed:** 7.16.0 (router offers the session's installed skills,
  `hooks/skill_roster.py`, `classifier_eval.py replay --roster installed --arm`) and 7.17.0
  (`classifier.choice_pick`, a choice winner at >= 0.7 overrules a failed gate). `OPEN-WORK.md`
  rank 12 was updated in both commits.
- **Committed with this handover:** this file only.
- **Not in git, durable:** `.plan/jev-roster-2026-09-24/` in the MAIN checkout (gitignored):
  roster-run.jsonl, panel3.json, cw-stratum.jsonl, cw-base.jsonl, cw-labels.json (five-judge
  majority), and every script that produced them. Byte-verified copies.
- **Worktrees to remove with `wtclean`** (both fully on master): `.claude/worktrees/jev-roster`
  (this session) and `.claude/worktrees/nudge-recall-fix` (the previous one).

## Decided, and why - do not reopen

- **The router's roster is the session's installed skills** (user chose "widen roster first").
  4 of the 6 never-proposed skills were absent from the option list, not misjudged.
- **Confidence bypass at 0.7** (user chose it over rewording the gate or adding option text).
  0.6 added noise on the held-out set; 0.7 added none on either labelled set.
- **The p28/p37 verdicts come from panel 3** (five judges, unanimous). They replace panel 2's
  for those two prompts in BOTH rosters' scoring, which also downgrades compuse-toolbox on p28.

## Decided against, and why

- **Rewording the gate for handover prompts:** special-cases one skill inside a generic question.
- **Option text for context-watcher now:** that pattern contaminated router_criteria.json before;
  it needs prompts it was not written from, and the 30-prompt stratum has now been read.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER): the skills-and-scripts review. Top-ranked, not started.
- Rank 12 (USER): Jev. Remaining: the 11 context-watcher misses where the choice answers
  none_needed, then the decide-mode question (which must also switch the hook from the nouls
  question shape to choice_full).
- Rank 14 (USER): the approved invented-identifier guard.
- Rank 82, 150 (FOUND): git_state recall gap; the staged `TODO-JEV.md` in the main checkout.

## Lessons for the next nap

Captured this session (the nap should find them present):
`reference-the-system-prompt-is-not-in-the-transcript-so-injected-context-cannot-be-mined-from-the-corpus`
(updated), `reference-harvest-a-subagent-s-structured-output-from-its-transcript-the-delivered-message-is-html-escaped`
(updated), `feedback-a-never-proposed-answer-check-it-was-on-offer-before-tuning-the-scorer`,
`reference-in-a-worktree-isolated-session-scratchpad-scripts-edit-then-cp`.

Not yet captured, one line each:

- When you put numbers into the options of a question to the user, check they come from the set and
  threshold the question is about: this session quoted held-out gate scores (0.48-0.63) as a gap
  that the same data showed was already caught at the shipping gate, and had to retract it.
- When a replay changes a rule, diff old against new verdicts call by call and read every changed
  one; a class count used to estimate a fix (about 30 pushes) undercounted the real change (166).
- When a test fakes a directory that production code walks upward from (`.parent.parent`), put the
  fake inside a tree the test owns; one directly under `tmp_path` walks into pytest's shared root.
- tooling: toolbox-nudge fired on measurement work rather than chores (srccount on `find | wc -l`
  over transcripts, transcript_index on a Write naming the path, procsig on test data, factedit on a
  `wc -l` of a fact); precision evidence for the next time its rules are priced.
- When a cheap proxy and a careful parser disagree about the same quantity, suspect the PROXY first.
- tooling: `build_packets2.py` matches prior labels by positional id (`p00`), so reusing it on a
  different prompt set reports a meaningless overlap; key on prompt text instead.
- tooling: block-masked-gate-exit blocks a plain backgrounded `ci_wait.py` (no compound), so a CI
  wait must run in the foreground with `--timeout` under the 600 s tool cap.

## The exact next action

`OPEN-WORK.md` rank 10, the top-ranked open item: the skills-and-scripts review, one subagent each,
asking before changing anything. Nobody has started it. Start by sizing it: count the targets under
`plugins/bitranox/skills/*/` and `plugins/bitranox/hooks/`, and write the count into the line. (If
the user asks for Jev instead, rank 12's `next:` names the none_needed half.)

## Files that matter

- `plugins/bitranox/hooks/skill_roster.py` - installed_skills, listing_from_transcript, the cache
- `plugins/bitranox/hooks/classifier.py` - `CHOICE_BYPASS`, `choice_pick`, `skill_router_choice_questions`
- `plugins/bitranox/hooks/skill-router.py` - `_shadow_skill_router` (still asks the nouls shape)
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `run_arm`, `roster_for`, `--roster`, `--arm`

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
git fetch origin && git log --oneline -3 origin/master
uv run --no-project --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
```

origin/master carries `0b81ce2` (or later), and the gate prints `repo-gate: all checks passed`.
The main checkout was 32+ commits behind origin at the start of this session; fast-forward it only
after settling rank 150.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
delete it - if this session ends badly it is the only record of where things stood.
