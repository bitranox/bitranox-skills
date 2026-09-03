# skill-writer checklist - meta-dream-tree (2026-09-03, statusrot pending triage)

Change: the `statusrot.py` entry in the Reference files paragraph gains a clause saying its
UNEXAMINED list is split into RE-SURFACED / WRITTEN SINCE the sweep / NEVER CHECKED, and that only
the last is a backlog - read that group's count, never the total. One body line becomes three. No
frontmatter change.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: REFERENCE. The paragraph is an index entry, so the tests that apply are whether
      what it SAYS is true and whether it aids retrieval - not whether it changes a decision.
- [x] Its claim is true of the shipped tool, checked against behaviour rather than intent: a live
      `scan --chain` over the softdev tree prints exactly those three labelled groups and they sum
      to the stated total (7 + 10 + 5 = 22).
- [x] RED/GREEN run as a clean A/B: identical scenario and identical tool output in both arms, the
      SKILL.md clause the ONLY difference. Both arms answered **4**, the NEVER CHECKED count.
      **The RED did not flip, and the reason is a property of the implementation, not a failed
      test:** the labels ship with a gloss INSIDE the tool's output ("the real backlog",
      "freshness, not rot"), so a reader holding a scan does not need the SKILL.md to interpret it.
      The RED arm said so unprompted - that the taxonomy "only exists in the tool's own output".
      Recorded rather than escalated; inventing a harder scenario until something failed would be
      manufacturing a RED, not finding one.
- [x] The clause is kept despite the non-flip, because the population it serves is the one that
      has no scan in front of it: a reader deciding whether to RUN statusrot, or sizing a dream
      pass from the skill alone. That is where the miss this change answers actually happened - a
      flat count was copied into a backlog as "39 of 40 candidates unexamined" and a day of work
      was ranked on it.
- [x] Gaps reported by the test arms, each closed or declined:
      - DECLINED, fixture artifact: both arms flagged that the category counts in the scenario did
        not sum to the stated total. Real category groups legitimately overlap - one slug can be
        both SHIPPED and ID_REF - so the total is a DISTINCT count and is smaller than the sum.
        Pre-existing, accurate as printed, and untouched by this change. Worth a future word
        ("distinct") in the summary line; not smuggled into this one.
      - DECLINED, deliberate: both arms noted NEVER CHECKED bundles "predates the sweep" with "age
        unanswerable" and gives no split. Both demand the same action - adjudicate it - and the
        tie-break routes an unanswerable age here ON PURPOSE. A fourth group would invite treating
        those as a lesser class, which is the failure the tie-break exists to prevent.
      - NOTED, correct by design: both arms said they relayed the tool's bucketing without opening
        the slugs. That is what the report is for; adjudication against owners is the reader's step.
- [x] No frontmatter change: the committed diff for this file touches one body line only, no
      `name:` and no `description:`, so no routing keyword moved.
      `build_skill_triggers.py --check` reports the map in sync (82 skills).
- [x] Scripts ship with tests that pass. `tests/test_statusrot_pending_triage.py` is new and covers
      each bucket, the fail-toward-more-work fallback for an unanswerable age, a non-git store, an
      exact partition of the pending list with no entry in two buckets, a known-negative control
      proving one input yields two different buckets, and the omit-empty-group rendering choice.
      RED verified at 8 of 8 failing before any implementation. Suite green at 140;
      `repo-gate.py --ci` green at 4669 passed.
- [x] Present tense, no session narrative, no machine-specific address or path added.
