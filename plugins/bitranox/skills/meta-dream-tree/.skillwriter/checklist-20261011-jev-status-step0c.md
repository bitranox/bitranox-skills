# meta-dream-tree: Jev shadow status check in step 0c

Change: step 0c now runs `jev_shadow.py status` once and names the three shadow sites that need
the session's own per-fact verdicts during steps 5-7; the step 5/6/7 shadow bullets refer back to
the step 0c result instead of re-running the check. Skill type: technique. Test approach:
retrieval scenario, text-only probes pinned to haiku and sonnet.

## Verification

- [x] Defect confirmed on the unchanged text: `jev_shadow.py status` appeared only in the step 5, 6
      and 7 shadow bullets; step 0c did not mention it.
- [x] RED, haiku (step headings plus the old step 0c text): "(1) ... NOT STATED. The procedure text
      never mentions `jev_shadow.py`." "(2) ... NOT STATED. No step is described as collecting data
      for a Jev shadow report."
- [x] RED, sonnet (same input): "(1) ... NOT STATED. The text given ... never names
      `jev_shadow.py`" and "(2) ... NOT STATED. Nothing in the visible text says any step collects
      data for a Jev shadow report."
- [x] Inherited-coverage check: the RED arms answered NOT STATED, so no cascade or memory text
      supplied the answer; the arms are text-only (inert probe type, no file access).
- [x] GREEN, haiku (new step 0c text): "First run: step 0c. The text says to run
      `jev_shadow.py status` "HERE, once"" and "Step 5 (PLACEMENT): `dream-placement` verdict for
      each fact. Step 6 ... `dream-firing` ... Step 7 ... `dream-prune`".
- [x] GREEN, sonnet: "(1) ... step 0c ("Read the toolbox inventory"). The text says to run it
      "HERE, once"" and the three sites listed as `dream-placement` (step 5), `dream-firing`
      (step 6), `dream-prune` (step 7), "I record each verdict as I judge the fact, while the pass
      is under way."
- [x] RED vs GREEN diffed both ways: nothing the RED arms answered was lost (they had answered
      NOT STATED throughout).
- [x] Unfed-site wording is not new: step 11 already defines the forms `off (<reason>)`,
      `no items`, `error <message>` and the counts `run` printed; step 0c only points to
      `off (<reason>)`.

## Skill gaps reported by GREEN, each decided

- [x] Shadow bullet format, verdict values, where verdicts are stored: DECLINED here. The probes
      saw only the first line of steps 5-7. The format is fully defined in each step's shadow
      bullet (`{"id": ..., "verdict": {...}}` written to `$D/verdicts.jsonl`) and step 0c points
      to it.
- [x] `<plugin>` path: DECLINED. The same placeholder convention is used by every other script
      home in this skill.
- [x] Reason string for `off (<reason>)`: DECLINED. Defined once in meta-self-improve
      `references/jev-shadow.md`, "The report line", which step 11 cites.
- [x] Whether a verdict is needed for a fact left untouched: DECLINED. Steps 5-7 already say
      "every fact"; a closed question of OPEN-WORK [430] (sample versus full) is not decided here.
- [x] Whether status runs again at step 11: CLOSED by the text "once ... keep the result for the
      whole run".
- [x] Apparent clash between "may end with" (probe background) and the step 0c check: DECLINED;
      the background sentence was probe scaffolding, not skill text.

## Quality checks

- [x] ASCII only in the SKILL.md change and this file.
- [x] No new addresses, hostnames or private paths; no session narrative.
- [x] Frontmatter and description untouched; body change adds no routing keyword.
