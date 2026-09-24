# Handover - written 2026-09-24, nothing in flight

## In flight

Nothing. 7.15.0 is committed and pushed; the worktree is clean and level with `origin/master`.

## Committed, or not

Two releases this session, both CI-green:

* **7.14.0** - `classifier_eval.py replay --prompts LOG` (pin a replay to an earlier run's exact
  prompts AND recorded state, with a `state_drift` report), and the `skill_router` eval threshold
  0.7 -> 0.5.
* **7.15.0** - the previous turn's reasoning rejected as a router input, with the rejection pinned
  by a test, plus the held-out result recorded.

Machine config unchanged: `classifier_backend = jev`, all three sites still `shadow`. Nothing here
changes what a live session sees - `SITE_THRESHOLDS` exists only in the eval tool and
`skill-router.py` has no threshold at all.

**Paid inputs, all durable and byte-verified, all gitignored:**

* `.plan/jev-replay-2026-09-23/` - panel-1 `labels.json`, `replay-run2.jsonl`
* `.plan/jev-replay-2026-09-24/` - `replay-run4.jsonl`, `labels2.json`, `verdicts2_0-4`
* `.plan/jev-heldout-2026-09-24/` - the held-out run and its labels (`h/`), the reasoning A/B
  (`stratum.jsonl`, `reasoning-ab.jsonl`), and every analysis script

## Decided, and why - do not reopen

- **The gate was the dominant failure, not the roster.** AUC about 0.71 on every arm, so 0.7 sat
  in the steep part of a shallow curve and kept 5 of 11. Every arm improves as the gate drops, and
  that REPLICATED on 50 held-out prompts, which is why it is safe to build on.
- **0.5, not the better-scoring 0.3.** 0.5 is where the controls were actually run and passed on
  all six arms (positives 0.68-0.72, negatives 0.20-0.23). 0.3 leaves 0.07 over the negatives and
  has never been run.
- **The arm question is closed: `choice_full`.** `choice_router_text` led 9 right to 4 on the
  prompts its option text was authored from, and ties 7-7 on held-out prompts with the same wrong
  count, same missed count and an identical 4-inside/3-outside split. Equal cost, and `choice_full`
  needs no hand-authored `router_criteria.json` kept in sync. `nouls` is out (42 wrong at 0.3);
  the rerank is out (flat at 2 right).
- **Reasoning as a state field is rejected.** Invisible today by structure, present for about 12%
  of prompts, and on a targeted stratum of 49 that DO have it the gate went LOWER on 139 of 245
  cells against higher on 61 and the arms spoke LESS. Wrong direction. `_describing`'s docstring
  carries the numbers; a test pins it.
- **A pinned replay re-sends the RECORDED state.** Rebuilding from `source`+`line` reproduced
  `project` on only 39 of 50 - descriptor files change, cwds stop resolving, transcripts get swept
  (4 of the original 50 are already gone).

## Still open

`OPEN-WORK.md` is the list. Rank 10 (a USER item) is still top-ranked and untouched; it is not the
Jev thread, and recency is not a reason to prefer the Jev thread. Rank 14 (the approved identifier
guard) is still small and self-contained. Rank 78 is still open.

Inside rank 12, two things remain and they are different in kind:

1. **Whether any site leaves shadow.** No shadow log can answer this by itself - it is a decision,
   not a measurement.
2. **The roster gap.** Skills that NO arm proposes at any threshold: 4 of 13 on the first set
   (`meta-self-improve`, `meta-context-watcher`, `typesafe-ai`, `soundtouch-decloud`) and 2 of 11
   on the held-out set (`provmm-build`, `update-config`). A recall/coverage problem, not a gate
   one. Reasoning was the candidate input for it and is now ruled out, so it needs a different
   idea.

## Lessons for the next nap

- A grep for a literal token is not a structural check: searching `"thinking"` said 29 of 50
  transcripts carried reasoning, counting real blocks said 1 of 46, and I nearly "fixed" a correct
  extractor because the bad proxy disagreed with it.
- Mirroring a production helper can import a bug its caller does not have: `last_reply`'s two-slot
  fallback exists for a live race, and copying it into a historical extractor silently attached an
  earlier turn's reasoning to a later prompt. The tell was two unrelated prompts with identical text.
- A different seed does not give a disjoint sample when the population repeats: every seed tried
  overlapped the original 50 on 13-23 rows because continuations repeat verbatim. Exclude by value.
- Interleave by building the pairs into the input, not by running two passes - each prompt twice
  and adjacent needs no code change and cannot confound arm with clock.

## The exact next action

Rank 10 goes first unless the user says otherwise. If they pick Jev again, it is the roster gap -
and the first step there is deciding what evidence would even identify a skill nobody proposed,
since by construction it is absent from every arm's output.

## How to verify this still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/jev-classifier
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --ci
D=/media/srv-main-softdev/projects/public/KI/bitranox-skills/.plan/jev-heldout-2026-09-24
python3 "$D/hx/check_fit.py" plugins/bitranox/hooks/router_criteria.json
```

The gate prints `repo-gate: all checks passed`. `check_fit.py` reprints the held-out
inside/outside split (4/3 for both arms) and the two roster gaps, calling nothing.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
