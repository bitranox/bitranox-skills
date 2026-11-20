# checklist - what never goes to the ledger; the final review checks shipped behaviour

Two queued contributions from one run.

1. A finding or note that conflicts with a user decision goes to the human at once as a decision
   (it replaces "A Minor that contradicts a user decision goes to the final review flagged for the
   user"). A plan-mandated finding in security, layering or real-dependency test coverage is routed
   by the plan-mandated rule before the final review, whatever severity it was filed at; the final
   reviewer re-judges ledgered plan-mandated items at the rubric's severity.
2. Final review instruction 4 also checks the SHIPPED behaviour, defaults and pre-filled values
   included, against every recorded user answer.

Decisions: d-20261120-9a84982a, d-20261120-108e4e31, d-20261120-40e75e07

## RED

- [x] Skill decisions read first: two rejected headless entries, unrelated.
- [x] Text check at HEAD: "defaults and pre-filled values" and "Re-judge each item labeled
      plan-mandated" 0 hits; the old sentence routed a user-decision Minor to the final review.
- [x] The test-coverage class is NOT called Important: the reviewer rubric rates "coverage could be
      broader" Minor, so the text routes by the plan-mandated rule instead of re-rating it.

## GREEN

- [x] Quote-back probe (haiku): all four scenario questions answered by quotes (no ledger for the
      origin-check finding, controller dispatches the test-only fix, the user-decision note goes to
      the human at once, the final reviewer quotes the answer beside the shipped behaviour).

## REFACTOR

- [x] Width of the edited paragraphs kept to the file's; ASCII check clean.
