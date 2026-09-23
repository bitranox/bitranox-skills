# STALE - read 2026-09-23, work continued

## Continued 2026-09-23: 7.11.0 is on origin/master, CI-green on 74358ef7

All three things the section below called "the exact next action" were done, in that order.

1. **The session-start gate defect is fixed in the question and NOT closed in the gate.** A router
   question is now built from the state the request carries, so it can no longer name a field that
   is absent. Measured live, interleaved: the old wording scored a first-prompt positive 0.65,
   0.68, 0.67 - under its own 0.7 threshold EVERY time, so it suppressed rather than coin-flipped,
   which is worse than the note below guessed. The new wording clears it 3 of 3 at 0.70-0.72 with
   the negative at 0.17-0.18, and mid-session is untouched. But asked beside the real roster
   instead of alone it scores 0.67-0.71, and 3 of 4 arms still fail that control, so `replay` now
   REFUSES to run. That refusal is deliberate: the gate is what every arm is measured through.
2. **The rerank is settled and it loses.** Re-thresholded to the 0.30 its own recipe uses, from
   scores already paid for: it names 5 picks and suppresses 5 of the wide pass's, and adjudication
   scored it 0 right against 11 misses. Do not revisit the two-request shape on the cookbook's
   authority again.
3. **The accuracy question is answered.** All 50 replayed prompts adjudicated blind by five
   judges, every pick classified rather than sampled. The numbers and the caveat live in
   `OPEN-WORK.md` rank 12; the short version is that `choice_full` wins on accuracy as well as
   cost (3 right, 7 defensible, 1 wrong, 6 missed) and the shipping KEYWORD matcher is the worst
   thing measured (0 right, 4 wrong, 10 of 11 missed).

The next action is no longer building or measuring shapes: it is choosing the two thresholds
against these labels, because the dominant failure is that the right answer scores just BELOW the
bar - 6 of 11 misses wanted `meta-context-watcher` for handover prompts, which the noul arm ranks
top at 0.58-0.73.

The adjudication inputs and labels are in this session's scratchpad and are NOT durable; the
replay logs were copied there from the previous session's and carry the per-arm scores.

---

# Handover - written 2026-09-23, nothing in flight

## In flight

Nothing. 7.10.0 is on `origin/master` and CI-green on `973292ab752174c9a40e5ae759607de5873d0d1a`.
The worktree is clean and level with `origin/master`.

## Committed, or not

- Everything is pushed. Work was done in `.claude/worktrees/jev-classifier`; it can be removed
  (`wtclean.py jev-classifier`) and the main checkout pulled.
- Machine config unchanged: `classifier_backend = jev`, all three sites `shadow`. Nothing shipped
  here changes what a live session sees.
- Two replay logs live in a session scratchpad and are NOT durable. The second one carries the
  per-arm scores, so it is the one worth keeping if anybody wants to re-threshold without paying:
  `replay-run2.jsonl`. Re-running costs about 1.6M input tokens, roughly $0.07.

## Decided, and why - do not reopen

- **A choice arm is NOT thresholded on its winner's probability.** A noul at 0.7 and a choice
  probability at 0.7 do not mean the same thing; the API guarantees no comparability between
  primitives. The `none_needed` option carries that judgement instead, which is what it is for.
- **The gate question stays byte-identical across arms.** It is the variable the comparison holds
  fixed, so an arm that also reworded it could attribute nothing.
- **`corpus_prompts` is its own jig, not a `--field prompt` mode on `guard_replay`.** A prompt has
  no gate, so guard_replay's precision column has nothing to read, and bolting them together would
  distort the one that works.
- **`<pasted_content` is NOT excluded from typed prompts, and must stay that way.** A person
  pasting a question wraps it in exactly that. This is why no blanket "opens with a tag" rule may
  be written; `<bash-input` and `<bash-stdout` are excluded individually.
- **The new jig has a `NO_COMMAND_SHAPE` exemption rather than a nudge rule**, on measured evidence
  over 84,968 Bash calls: the nearest candidate patterns either shadow `jsonl_grep --type user`
  (30 firings) or name the corpus WALK that `guard_replay` shares (56).

## Decided against, and why

- **Adopting the cookbook's two-request shape on its authority.** Measured here, the rerank stage
  does not pay for itself at any threshold or under either decision rule; the wide choice arm alone
  is the best shape so far. The recipe's own corpus and roster differ from ours.
- **Re-running the replay to answer the threshold question.** The scores are now recorded, so the
  0.3-to-0.8 sweep comes out of data already paid for.

## Still open, untouched

`OPEN-WORK.md` is the list. Ranks 115 and 117 were closed here; rank 12 was re-scoped and its
`next:` rewritten, because the instrument its old next action asked for now exists.

## Lessons for the next nap

- When an experiment's verdict depends on a threshold you chose, log the raw SCORES beside the verdict, or the first threshold you picked becomes the only one you ever measured.
- When a prompt template interpolates optional context, check the question text does not NAME a field the caller can omit - the model hedges near the threshold instead of erroring, so there is no failure to notice.
- When a control refuses a run, suspect the CONTROL's shape before the subject: one posed as production never poses it measures a question nobody asks.
- When a markdown table row renders short, count the BACKTICKS in it, not the pipes - an unbalanced code span swallows the next separator while the pipe count still reads correct.
- When you pad a short sha to full length, you have invented an identifier; derive it with `git rev-parse --verify -q HEAD` in the same command that uses it.
- When adding a routing row for a tool with a close sibling, test the DIFFERENTIATION, because two rows that sound equally plausible for one query is the failure that ships.
- tooling: `ci_wait` correctly refused a fabricated sha instead of polling to deadline - that refusal is worth keeping if anyone touches its validation.

## The exact next action

`OPEN-WORK.md` rank 10 is still top-ranked and still blocked on making `TRIAGE.md` durable; that
has not changed and it goes first if nothing else is asked for.

If the user picks up the Jev thread instead (rank 12, which this session advanced), the next action
there is NOT more building. It is the accuracy question no arm has answered: fix the session-start
gate defect first, since every measurement runs through that gate, then adjudicate a larger sample
adversarially, classifying every pick rather than sampling.

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `ARMS`, `run_arm`,
  `REPLAY_CONTROLS`, `check_controls`, `stratified_prompts`, `size_replay`, `load_skill_bodies`.
- `plugins/bitranox/skills/compuse-toolbox/scripts/corpus_prompts.py` - `extract_prompts`,
  `collect_prompts`, `diff_predicates`; predicate is called `f(text)`.
- `plugins/bitranox/hooks/classifier.py` - `skill_router_choice_questions`,
  `skill_router_rerank_questions`, `short_description`, `PICK_ID`, `NO_SKILL_KEY`.
- `plugins/bitranox/hooks/transcript_turns.py` - `NOT_TYPED_PREFIXES`, `NOT_TYPED_PATTERNS`,
  `looks_typed`.
- `plugins/bitranox/hooks/skill-router.py` - `_router_fields` is the seam the replay rebuilds
  state through, and the one the gate defect sits in.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
python3 plugins/bitranox/skills/meta-self-improve/classifier_eval.py size --limit 25
python3 plugins/bitranox/skills/compuse-toolbox/scripts/corpus_prompts.py --count
```

`repo-gate: all checks passed` with 5038 passed. `size` prices the four arms without calling the
API and puts the shipping `nouls` arm near 15,120 tokens a prompt. `--count` reports the typed
prompts the corpus holds; it was 1,301 after the harness-turn fix, against 1,409 before it.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
