# RED: version-bound facts in the prune step, and the Jev shadow receipt

Skill type: technique (the dream's prune step, step 0c, step 11) plus the nap's step 5.
Probe: `bitranox:baseline-probe` on opus, given the CURRENT step text verbatim, asked to act and to
quote the governing text or answer NONE, ending with a `Skill gaps` section.

## Probe 1: prune, three version-bound facts (build tool fixed in 3.13.0, installed 3.21.1; a
## mail library fact naming 1.5.0, library now 4.3.0; a body line "tests PASS on 1.5.0")

- The two prune questions select none of the three. The probe reached the build-tool fact only by
  its own reading of the removal policy ("a resolved issue"), kept the mail-library fact without
  re-checking it against 4.3.0, and called the test snapshot task-state.
- Q2, how to find every such fact among 1,602: NONE. "the text gives no instruction or command to
  compare a fact's cited version against the installed one."
- Gaps reported: no detector for stale version gates; no rule that a version-bound claim is
  re-checked against the current release; no verb for dropping one stale line from a body that is
  otherwise valid; how to resolve a fact's owning level for `--archive`.

## Probe 2: Jev shadow at step 11, no per-fact verdicts recorded during steps 5-7

- Reports all three sites `off (per-fact verdicts not recorded ...)` and marks the dream done:
  "Nothing stops it. The text never makes the shadow verdicts a precondition for `done`."
- Gaps reported: no sampled or budgeted mode ("A site is either fed with every fact ... or
  `off`"); "every entry reviewed" (step 7 body) and "every fact" (shadow bullet) disagree; the
  home and launch of `dream_state.py` are missing at step 11; whether a deliberate skip reads
  differently from a site that could not run.

## What GREEN must make true

1. Step 7 names `versionrot.py` and its three outcomes (still true -> reword to current state;
   fixed bug, finished migration, test snapshot -> archive; siblings on one library -> merge),
   and says to re-check a superseded claim against the current release before acting.
2. Steps 0c/5/6/7 shadow a SAMPLE (`items --sample 40 --seed <dream id>`, `run --dream <id>`),
   and step 11 runs `dream_state.py done --kind tree --dream <id>` (home and launch named), which
   refuses until each site has rows or a `--jev-skip SITE=REASON`.
3. The nap runs `done --kind nap`, and its prune step runs `versionrot.py --chain`.
