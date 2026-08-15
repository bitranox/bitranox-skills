# meta-self-improve: drop the hook-shape clause from the unresolved-failure bullet

Scope: reword one bullet inside step 1 "Gather candidates" (the "An unresolved failure ..." bullet
added in the prior, separately-reviewed commit). No other section changes. A companion change in
`hooks/capture_constraints.py` (its module docstring item 2 and `_UNRESOLVED_ADVICE`) and in
`CHANGELOG.md` reword the same overclaim to match; the code itself is unchanged.

## The finding this fixes

The prior commit's bullet read "An unresolved failure written up as a procedure", and its closing
sentence claimed "the engine warns on both at write time" - implying the engine's warning is gated
on the hook reading as a procedure. It is not: `capture_constraints.advise()` fires
`_UNRESOLVED_ADVICE` off `UNRESOLVED_RX.search(body)` alone, with no check anywhere on hook shape.
The bullet described a two-part trigger the code does not implement. Fixed by wording, not by
adding a hook-shape check to the code (that heuristic already lost two prior review rounds in this
module - see `hooks/capture_constraints.py`'s own history).

## What the tests showed

- [x] Pre-edit PRESENT confirmed with the file genuinely read, not assumed: `claim_check.py
      --pattern 'unresolved failure written up as a procedure|writing them up as a workflow'
      --control 'Discard task state' plugins/bitranox/skills/meta-self-improve/SKILL.md`, run
      against `git show HEAD:...` (this branch's tip before this edit) -> PRESENT, 2 hits (the
      bullet heading and its closing clause), control matched (the file was read).
- [x] Post-edit ABSENT: same tool, same pattern, against the working-tree file -> ABSENT, control
      matched (the file was read, the old phrasing is gone).
- [x] Post-edit PRESENT for the new wording: `claim_check.py --pattern 'An unresolved failure\.\*\*
      If the session never' --control 'Discard task state'
      plugins/bitranox/skills/meta-self-improve/SKILL.md` -> PRESENT, 1 hit on the reworded bullet.
- [x] Behavioural pressure-test not run: this is a documentation-conformance fix (the wording now
      accurately describes an already-shipped, already-reviewed code trigger), not a new discipline
      rule whose phrasing needs pressure-testing against a subagent's rationalizations. The
      load-bearing check is textual accuracy against `capture_constraints.py`'s source, done above
      and in "Accuracy against the hook" below.

## Accuracy against the hook (read, not assumed)

- [x] `capture_constraints.py:79-82` (`advise()`): `if NEGATIVE_RX.search(hook): ...` gates on the
      HOOK; `if UNRESOLVED_RX.search(body): ...` gates on the BODY alone. No branch anywhere reads
      or classifies hook shape ("procedure" or otherwise) for the unresolved-failure advisory.
- [x] The reworded bullet ("An unresolved failure.") and its explanation ("capture the dead ends AS
      dead ends, explicitly labelled unsolved - an unlabelled write-up presents untested attempts
      as validated guidance") match this exactly: the trigger is the body content, and the remedy
      (label it unsolved) is what a body-only check can actually be satisfied by, regardless of how
      the hook reads.
- [x] The closing sentence ("The engine warns on both at write time...") was left unchanged - it
      claims only that the engine warns on both fact classes, which remains true, and (after this
      edit) neither bullet above it implies a second gating condition the code does not check.

## Coverage gap this task also closed

- [x] Added `test_unresolved_failure_is_flagged_even_when_the_hook_is_not_a_procedure` to
      `hooks/tests/test_capture_constraints.py`: an unresolved-failure body paired with a plainly
      non-procedure hook ("When investigating X, know that the usual suspects do not explain it.")
      still gets flagged. Before this task, every passing test paired the unresolved body with a
      procedure-shaped hook, so no test would have caught the code NOT requiring hook shape - this
      one does. Renamed the pre-existing case (was
      `test_unresolved_failure_written_as_procedure_is_flagged`, now
      `test_unresolved_failure_in_body_is_flagged`) since its old name implied the procedure shape
      was load-bearing for the flag, which it is not.
- [x] `uv run --quiet --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml
      --with httpx2 python -m pytest plugins/bitranox/hooks/tests/test_capture_constraints.py -q`
      -> `9 passed`.

## Scope declined

- [x] Did not touch `meta-using-bitranox-skills/SKILL.md` - out of scope, same reasoning as the
      prior commit's checklist (always-loaded context; a capture-time rule there costs every
      session tokens), and it does not carry this overclaim.
- [x] Did not edit the prior commit's checklists
      (`checklist-20260815-capture-constraints-authoring-side.md` /
      `-review-side.md`) even though one of them asserts "no wording change needed there" for this
      exact bullet - those are dated receipts of that review, not living documentation; the record
      of what was wrong belongs in this new checklist, not a retroactive edit of the old one.

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added; no renumbering of the existing steps.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (scanned the changed file for codepoints above 126: zero hits).
- [x] No `plugin.json` version bump in this change (5.202.0 already accounts for the paragraph this
      bullet lives in; this is a same-version wording correction, not a new capability).
- [x] `repo-gate.py --ci` passes on the full change set (see the paired commit's gate result,
      recorded in this task's own report).
