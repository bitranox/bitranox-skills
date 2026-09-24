# Handover - written 2026-09-24, nothing in flight

## In flight

Nothing. The worktree is clean and level with `origin/master` at `120ba22`, CI confirmed green
(`workflow=success ci=success`).

## Committed, or not

Everything is committed and pushed. Nothing is uncommitted.

* **7.14.0** (`cc1be55`) - `classifier_eval.py replay --prompts LOG` pins a replay to an earlier
  run's exact prompts AND recorded state, reporting `state_drift`; the `skill_router` eval
  threshold 0.7 -> 0.5.
* **7.15.0** (`120ba22`) - the previous turn's reasoning rejected as a router input, pinned by a
  test; the held-out result recorded.

Machine config unchanged: `classifier_backend = jev`, all three sites still `shadow`. Nothing
shipped here changes what a live session sees - `SITE_THRESHOLDS` exists only in the eval tool and
`skill-router.py` has no threshold at all.

**The paid inputs are durable, byte-verified, gitignored.** Re-judging costs five opus agents and a
replay about $0.12, so do not let a `/tmp` sweep take them:

* `.plan/jev-replay-2026-09-23/` - panel-1 `labels.json`, `replay-run2.jsonl`
* `.plan/jev-replay-2026-09-24/` - `replay-run4.jsonl`, `labels2.json`, `verdicts2_0-4`
* `.plan/jev-heldout-2026-09-24/` - the held-out run and its labels (`h/`), the reasoning A/B
  (`stratum.jsonl`, `reasoning-ab.jsonl`), and every analysis script (`sweep.py`, `check_fit.py`,
  `ab_reasoning.py`, `build_stratum.py`, `build_heldout.py`)

## Decided, and why - do not reopen

- **The gate was the dominant failure, not the roster.** AUC about 0.71 on every arm, so 0.7 sat in
  the steep part of a shallow curve and kept 5 of 11. Every arm improves as the gate drops, and
  that REPLICATED on 50 held-out prompts, which is why this one is safe to build on.
- **0.5, not the better-scoring 0.3.** 0.5 is where the planted controls were actually run and
  passed on all six arms (positives 0.68-0.72, negatives 0.20-0.23). 0.3 leaves 0.07 over the
  negatives and has never been run.
- **The arm question is closed: `choice_full`.** `choice_router_text` led 9 right to 4 on the
  prompts its option text was authored from, and ties 7-7 on held-out prompts with the same wrong
  count, the same missed count and an identical 4-inside/3-outside split. Equal cost, and
  `choice_full` needs no hand-authored `router_criteria.json` kept in sync with the skills it
  describes. `nouls` is out (42 wrong at 0.3); the rerank is out (flat at 2 right).
- **The first-prompt control was never a wording defect.** Its 0.02 margin was the same shallow
  curve. At 0.5 all 24 control rows pass. The earlier "left FAILING on purpose" is superseded.
- **A pinned replay re-sends the RECORDED state.** Rebuilding from `source`+`line` reproduced
  `project` on only 39 of 50 - scope descriptors change, cwds stop resolving, and transcripts get
  swept (4 of the original 50 are already gone).

## Decided against, and why

- **Reasoning as a state field.** Structurally invisible today (a thinking block carries
  `{signature, thinking, type}`; `text_of` keeps only blocks with a `text` key) and present for
  about 12% of prompts. On a targeted stratum of 49 that DO carry it, the gate went LOWER on 139 of
  245 choice-arm cells against higher on 61, and the arms spoke LESS - the wrong direction when
  missing a needed skill is the dominant failure. Reverted; a test pins the rejection and
  `classifier._describing`'s docstring carries the numbers.
- **Keeping the experimental field as inert scaffolding.** Nothing populates it, so it would only
  invite a future reader to wire up a measured-negative input.

## Still open, untouched

`OPEN-WORK.md` is the list; read it before this file.

- Rank 10 (USER) - the skills-and-scripts review. Top-ranked and untouched.
- Rank 14 (USER) - the approved identifier guard. Small, self-contained.
- Rank 12 (USER) - two remainders of different kinds, detailed in the line itself.
- Rank 78 (FOUND) - the suite-ordering test leak.

## Lessons for the next nap

These three were already written to the store this session (the Stop gate required it), so the nap
should find them present rather than capture them again:

- When counting a structured field, parse the record and test the field - never grep the quoted key
  name, which also matches prose. (`feedback-count-a-structured-field-by-parsing-it-never-by-grepping-its-key-name`)
- When reusing a production helper's logic elsewhere, drop the quirks that exist only for ITS
  caller's constraint. (`feedback-a-helper-s-quirk-is-justified-by-its-own-caller-so-reusing-it-elsewhere-imports-a-bug`)
- Before A/B-ing an optional input measure its availability, and build a held-out set by excluding
  values rather than changing the seed. (`feedback-measure-an-optional-input-s-availability-and-build-a-held-out-set-by-excluding-values`)

Not yet captured, one line each:

- When a cheap proxy and a careful parser disagree about the same quantity, suspect the PROXY first
  - two rounds went into "fixing" a correct extractor.
- tooling: `build_packets2.py` matches prior labels by positional id (`p00`), so reusing it on a
  different prompt set reports a meaningless overlap count; it did not reach the judges, but the
  next reuse should key on prompt text.

## The exact next action

`OPEN-WORK.md` rank 10 is the top-ranked open item and goes first: the skills-and-scripts review,
one subagent each, asking before changing anything. It is a USER item and nobody has started it.
The Jev thread (rank 12) is NOT next despite being what this session worked on - recency is not a
reason, and its remaining halves are a decision for the user and an open research question.

## Files that matter

- `plugins/bitranox/skills/meta-self-improve/classifier_eval.py` - `prompts_from_log`,
  `state_drift`, `_replay_one`, `SITE_THRESHOLDS`, `REPLAY_CONTROLS`, `run_arm`, `ARMS` (six).
- `plugins/bitranox/hooks/classifier.py` - `_describing` (carries the reasoning rejection and its
  numbers), `skill_router_questions`, `_router_turn_text`, `short_description`.
- `plugins/bitranox/hooks/router_criteria.json` - the six authored entries whose contamination the
  held-out run measured.
- `plugins/bitranox/hooks/tests/test_classifier_sites.py` - the test pinning the rejection.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/jev-classifier
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
D=/media/srv-main-softdev/projects/public/KI/bitranox-skills/.plan/jev-heldout-2026-09-24
python3 "$D/hx/check_fit.py" plugins/bitranox/hooks/router_criteria.json
```

The gate prints `repo-gate: all checks passed` with 5069 passed. `check_fit.py` calls nothing and
reprints the held-out inside/outside split (4/3 for both arms) plus the two roster gaps.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
