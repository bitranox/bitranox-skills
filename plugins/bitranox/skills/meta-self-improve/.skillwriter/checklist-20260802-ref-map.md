# skill-writer checklist - meta-self-improve (add the `ref_map` tool + its section)

Change: ship `ref_map.py` and a short SKILL.md section telling a placement decision to map a fact's
refs in BOTH directions before moving it. Reference/procedure edit, not a technique rewrite.

## PLAN
- [x] Skill type identified: procedure with a tool (the capture loop + its scripts).
- [x] Scope decided: one new script, one new SKILL.md section placed immediately before "When to
      run", so it is read before any engine call. No change to the capture procedure itself.
- [x] Trigger for the addition is EVIDENCE from a real run, not a guess: the crosstree-deep dream on
      2026-08-02 needed exactly this map twice, and there was no tool for it (hand-rolled as a
      scratch `refmap.py` and thrown away). It predicted both of the engine's two `move` refusals.

## RED / motivation
- [x] The gap is a real asymmetry in the engine, not a documentation preference: `move` REFUSES a
      down-move that would dangle an INBOUND ref, and never inspects the OUTBOUND refs the fact
      makes. Measured previously at a cost of one tree going from 2 to 14 `--check-tree` problems
      after a promotion round.
- [x] Tests written first and confirmed failing (`ModuleNotFoundError: No module named 'ref_map'`).

## GREEN
- [x] 10 tests, each pinning one behaviour: level lookup, inbound (what blocks a down-move),
      outbound (what `move` does not guard), the JSON envelope carrying levels for both directions,
      an unknown slug exiting 1 rather than printing an empty map, JSON still parseable on the
      failure path, a dangling outbound ref reported as dangling, `_`/`-` treated as one slug, a
      missing root as an error not an empty map, warnings on stderr.
- [x] The unknown-slug test exists because "no refs" and "no such fact" would otherwise print the
      same thing, which is the vacuous-answer failure this store already records twice.
- [x] The underscore test exists because a scanner in this same dream reported
      `[[project_ttrpc_construction_site_ownership]]` as a dead link; it is not, the engine's
      `_canon` folds `_` to `-`. A tool that did not copy that rule would ship that false positive.
- [x] CLI contract per `every-cli-needs-a-machine-readable-mode`: `--json` envelope
      `{ok, command, data, skipped}`, JSON on the failure path too, warnings on stderr, exit codes
      format-independent (0 clean / 1 unknown-or-dangling / 2 cannot build the map).
- [x] Validated against the REAL store, not only the fixture: it reproduced both refusals the
      engine had already given this run, with the same referencing slugs and levels
      (`feedback-benchmark-fair-settings` 4 inbound, `project-forward-port-subset-recipe` 1).
- [x] Script referenced in the SKILL.md with its home path and the `run-python.sh` launch at point
      of use, per the cross-skill-script-references rule.
- [x] Section says how to READ the output (which half blocks what), not merely that the tool exists.

## REFACTOR
- [x] No rule restated from references/memory-backend.md; the section points at the behaviour and
      gives the operator action.
- [x] `_canon` duplicated rather than imported from `reconcile_memory_index`: the tool is a
      standalone script launched through the shim, and the rule is three tokens. Noted here so a
      future consolidation has the reason rather than guessing.

## Deliverables
- [x] `ref_map.py`, `tests/test_ref_map.py` (10 tests, green), SKILL.md section.
- [x] `plugin.json` version bumped so installs see the change.
