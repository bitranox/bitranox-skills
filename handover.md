# Handover - written 2026-09-23, nothing in flight

## In flight

Nothing. 7.13.0 is on `origin/master`, CI-green on `fb3330bd1ad7088658dda3716342906364ca87e2`.
The worktree is clean and level with `origin/master`.

## Committed, or not

Everything is pushed: 7.11.0 (`74358ef7`), 7.12.0 (`baaffb2f`), 7.13.0 (`fb3330bd`), all CI-green.
Machine config unchanged - `classifier_backend = jev`, all three sites still `shadow`. Nothing
shipped here changes what a live session sees.

**Not durable and not re-derivable for free.** The five judges' blind labels for all 50 prompts
(`labels.json`) and the scored replay logs (`replay-run2.jsonl`, per-arm scores) sit in this
session's scratchpad. Re-judging costs five opus agents; re-running the replay costs a paid run.
Paths are under "Files that matter"; `OPEN-WORK.md` rank 12 carries them too. Copy them somewhere
durable before `/tmp` is swept.

## Decided, and why - do not reopen

- **The option catalogue belongs in the question's `criteria`, never in `state`.** Checked against
  the live docs when the split was questioned: state is "the content you ask a System One model to
  evaluate", every worked routing example puts candidates in `criteria`, and nothing documents
  `state` as cached or persisted. The placement was right and had never been a decision; it is
  now checked, so do not re-litigate it.
- **There is no prefix cache to unlock, so the request's field order stays as it is.** An
  interleaved 3-arm, 18-call probe: reordered is not faster than shipping, the broken-prefix
  control is indistinguishable from both, 9,400 input tokens charged on every call. Excludes the
  5-6x a published replica reports; cannot exclude a subtle effect.
- **Cost is not a deciding axis.** The whole spread across six arms is $1.33 to $6.43 per TEN
  THOUSAND prompts, and latency is ~36 ms per 1k tokens against a 15 s shadow deadline. Choose the
  arm on accuracy.
- **The rerank is settled and loses**, on two independent grounds: 0 right / 11 missed when
  adjudicated, and the vendor's own "give the model the full list rather than a shortlist".
- **The first-prompt control is left FAILING on purpose.** `controls` fails it on 3 of 4 arms at
  0.67-0.71 and that blocks `replay`. The gate is what every arm is measured through; the refusal
  is the instrument working, not a bug to route around.

## Decided against, and why

- **Moving the catalogue into `state`** - contradicts the documented purpose of `state`, no
  example does it, and the caching benefit that would have justified it was measured absent.
- **Reordering the request body to `{model, questions, state}`** - correct in theory, measured
  worthless, so it would be a cosmetic edit justified by a mechanism nobody observed.
- **Sending full skill bodies** - 1,469,460 chars over 81 skills is ~367k tokens a prompt and $154
  per 10,000; `compuse-toolbox` alone is 104,951 chars. Out on SIZE, not on caching.
- **Naming the absence in the gate question** ("no earlier reply yet") - measured and rejected: it
  inverted the gate, positive 0.24 against negative 0.34.

## Still open, untouched

`OPEN-WORK.md` is the list. Rank 10 (a USER item) is still top-ranked and untouched. Rank 14 was
added this session for the guard the user approved. Rank 78 was raised this session.

## Lessons for the next nap

- When a command uses an identifier you did not derive in that same command, you may have invented it - PADDING a short sha to 40 characters is inventing, not completing. (recurrence 3; captured, and the guard is rank 14)
- When a worktree session needs an untracked or gitignored file, resolve it against the MAIN checkout - a worktree brings the committed tree only, and the read just fails.
- When a judge or router ranks candidates, do not cut every candidate's text to the same width: a uniform cap spends equal characters on unequal text, so a trigger-LIST description loses everything past its first clause.
- When an early-exit gate sits in front of a scored question, record what was already paid for BEFORE the exit, or an offline re-threshold can only remove picks and a flat curve reads as insensitivity.
- When verifying a fix to one question in a multi-question request, re-check it inside the REAL request: asked alone it scored 0.70-0.72, asked beside its 81 siblings 0.67-0.71, which flipped the verdict.
- When optimising within your own shape, read the vendor's guidance for the primitive first - three documented practices had been missed for the whole life of this site.
- tooling: the "every arm sends a different sequence" test caught two arms shipping INERT (choice_body, choice_router_text), both because a missing text source falls back to descriptions. Keep that test.

## The exact next action

`OPEN-WORK.md` rank 10 is still the top-ranked item and goes first unless the user says otherwise:
the skills-and-scripts review, one subagent each, asking before changing anything. It is not the
Jev thread, and recency is not a reason to prefer the Jev thread.

If the user picks up Jev (rank 12) instead, the next action is the GATE, because it blocks
everything else: `classifier_eval.py controls` fails the first-prompt positive on 3 of 4 arms at
0.67-0.71, and until it passes `replay` refuses to run, so neither `choice_body` nor
`choice_router_text` can be scored against the labels already paid for.

Rank 14 (the approved guard) is small and self-contained, and was ranked rather than started only
because it was approved at ~530k context.

## Files that matter

- `plugins/bitranox/hooks/classifier.py` - `load_router_criteria`, `_router_turn_text`,
  `_pick_question`, `skill_router_questions`, `load_skill_descriptions`, `short_description`.
- `plugins/bitranox/hooks/router_criteria.json` - six structured entries; every other skill falls
  back to its description. This is the file to extend.
- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `ARMS` (six), `_roster`,
  `run_arm`, `run_controls`, `REPLAY_CONTROLS`, `size_replay`.
- The grader, NOT durable:
  `/tmp/claude-1000/-media-srv-main-softdev-projects-public-KI-bitranox-skills--claude-worktrees-jev-classifier/45b97af6-13f7-4877-8a62-0b1cf1242f33/scratchpad/`
  holds `labels.json`, `replay-run2.jsonl`, `packets.json`, `score.py`, `rethreshold.py`.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/jev-classifier
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py size --limit 25
```

`repo-gate: all checks passed` with 5063 passed. `size` prices all six arms without calling the
API: `choice_router_text` 36,112 chars a prompt against `choice_full` 36,245.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
