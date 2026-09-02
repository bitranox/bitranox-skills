# skill-writer checklist - meta-dream-tree (2026-09-02, the gate answers promotion, not misplacement)

Change: references/dream-core.md now states that the >=2-distinct-projects gate answers a PROMOTION
question and not a MISPLACEMENT one, with a two-row table giving the test.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Pre-change, a grep for `misplacement` and
      `re-home` over dream-core.md returned 0 hits.
- [x] The failure mode is stated as the reason the text is needed: the gate returns `hold`
      CORRECTLY by its own rule, so a careful reader honours it and preserves the never-fires
      defect. A rule that only fails when you are careless would not need writing down.
- [x] The test is mechanical (hook names the project? PLACE-HERE covers it?) rather than a
      judgement about how general a fact feels.
- [x] The re-home row still records the sighting, so the two paths do not diverge in what they
      leave behind for a later run.
- [x] Scope: shared - describes the shipped gate's semantics, not one store's contents.
- [x] Security scan: prose only; no paths, hosts or credentials.
- [x] CSO description: unchanged; dream-core is a reference file, not a routed skill.
- [x] Token budget: reference file, one section plus a two-row table.
