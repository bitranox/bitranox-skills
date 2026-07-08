# skill-writer checklist - meta-skill-writer (2026-07-08, script-reference home-path rule)

- [x] Change: "Cross-Referencing Other Skills" gains the script-reference counterpart rule - a script referenced from outside its owning skill states the home (skills/<owner>/<script>) + run-python.sh launch at point of use; families single-source homes in a "Script homes" section; bare names are fine only inside the owning skill's own SKILL.md (announced base dir)
- [x] Trigger/RED: observed in the wild - bare cross-skill script references made a 5.53.0 plugin audit falsely conclude dream_state.py / reconcile_memory_index.py are not shipped (fixed tree-wide in 5.54.1; this is the prevention leg)
- [x] Receipt held (skill_receipt.py, this session)
- [x] GREEN: fable author agent applied the rule 4/4 (cross-skill script ref, skill ref unchanged, family single-sourcing, own-dir bare name) from the text alone
- [x] Discovery: description unchanged (authoring-rule body addition)
- [x] Security scan: prose only, generic example names, no secrets/PII
