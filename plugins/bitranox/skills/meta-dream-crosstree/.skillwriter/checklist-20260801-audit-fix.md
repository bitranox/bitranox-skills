# skill-writer checklist - meta-dream-crosstree (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.128.0.

- [x] WRONG: the promotion gate says a model-inferred generalization promotes once seen in ">= 2
      distinct projects", but the mechanism it names counts SIGHTINGS PER DREAM -
      `note_promotion_candidate` increments once per call and the crosstree dream calls it once per
      slug per run. Two projects corroborating inside one run therefore count as one. The step now
      states what the counter measures and keeps the distinct-projects test as the reader's
      judgement with the dwell counter as the mechanical backstop.
- [x] The "one-time whole-store backup" reference is recorded as open: it names a real historical
      artefact rather than a procedure the reader runs.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every QUOTE checked against the real file; every behavioural claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths added.
