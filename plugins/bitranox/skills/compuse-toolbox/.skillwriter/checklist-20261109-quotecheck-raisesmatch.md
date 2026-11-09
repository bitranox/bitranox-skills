# skill-writer checklist - compuse-toolbox (2026-11-09, quotecheck and raisesmatch)

- [x] Entries covered: the two queued toolbox contributions, quotecheck and raisesmatch.
- [x] Mechanism: both ran against this skill from their shipped path: `quotecheck text` gave OK for a sentence in the table and MISMATCH for an invented one, rc 1; `raisesmatch` over its own test file gave rc 0.
- [x] Tests: test_quotecheck.py and test_raisesmatch.py moved with the tools, 34 passed under the CI dependency set.
- [x] RED text check: `quotecheck` 0->1 and `raisesmatch` 0->1 table rows in the pre-edit HEAD versus the edited file.
- [x] GREEN text check: both rows sit beside `conflict_scan` in the tool table, every row of the table has the same width and all three cells.
- [x] Behavioural probes: none dispatched, so RED and GREEN are text checks; no "X does not happen" verdict is claimed.
- [x] ASCII only, no private path or host in either script or test (scanned).
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive tools from the queue, no recorded decision is reversed.
