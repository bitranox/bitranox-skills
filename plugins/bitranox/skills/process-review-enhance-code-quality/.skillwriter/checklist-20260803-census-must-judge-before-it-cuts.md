# checklist - the census must judge before it cuts

Edit to the interface-shape judgement bullets: find out what a parameter is FOR before
proposing to remove or relocate it; gather call-site evidence by parser; a high tramp rate
does not select the fix; a fix must beat the status quo on every rubric dimension; counting
something and leaving it is a finished result.

## RED

- [x] Baseline dispatched on the pre-change judgement text, sonnet, TypeScript scenario so the
      rule is exercised language-agnostically. Input: census counts only - `logger` 190 fns /
      178 forward-only (94%), `db` 73 / 70 (96%), `ctx` 140 / 68 (49%), three clump pairs, two
      long parameter lists.
- [x] RED result: recommended folding `logger` and `db` into `ctx` across ~157 signatures,
      called it "close to codemod-able", ranked it "**Do first**". It never asked what either
      parameter was for - no question about who supplies a non-default value, no mention of a
      test seam or a production override. Its own gaps list asked only for MORE COUNTS.
- [x] First baseline PASSED and was discarded as contaminated, not banked. That prompt stated
      "the test suite passes a FakeLogger explicitly at that parameter in 12 tests" and "no
      production call site passes anything else" - the conclusions of the investigation the
      rule is meant to prompt. Handed the answer, the agent declined the refactor correctly.
      Re-run with those two facts withheld produced the failure above. Same model, same counts.

## GREEN

- [x] Same scenario, same counts, only the judgement text changed.
- [x] The purpose rule fires: a "Before implementing" section leading with "Who supplies a
      non-default `logger`/`db`? Enumerate production call sites and tests that pass something
      other than the standard instance."
- [x] The delete-the-tramp option is now rejected on its own terms: "rejected without even
      scoring it against the rest of the rubric, because it fails the injection-seam check by
      construction - with 600 tests, some non-trivial number almost certainly substitute a test
      double at the `logger` or `db` parameter directly."
- [x] The wrapper-object option is rejected citing the near-zero-parameters-removed trap.
- [x] The parser rule fires as a stated assumption: "I assumed the census was gathered by
      parser/declaration, not text grep ... If it was grep-based, every ratio above would need
      re-deriving."
- [x] The exoneration rule fires: an "Accepted-as-is (counted, no action)" section for `ctx`.
- [x] Verdict language changed from "Do first" to "a hypothesis the counts support strongly,
      not a verified finding".

## REFACTOR

- [x] Every RED and GREEN dispatch asked for a `Skill gaps` section; both lists recorded.
- [x] GREEN's gaps are absence-of-input, not skill defects: no source access (the scenario
      supplied counts only, by design), and no tramp row for `requestId` or the remaining
      census axes. Declined - a reviewer with the codebase has what the scenario withheld.
- [x] GREEN diffed against RED in both directions. RED's explicit ranked-by-parameters-removed
      table is not reproduced as a table in GREEN, but the quantification survives per item
      ("Net parameters removed: up to 70, added: 0") plus an explicit "highest-value,
      lowest-line-cost" call. Not a lost result; no restructuring on one run.
- [x] Language-agnostic: scenario is TypeScript, the worked builtin-collision example names
      Python's `sorted(key=...)` and generalises to `value`, `id`, `name`, `type`, `index`,
      `data`, `compare`, `callback`, `handler` in any language with a standard library.
- [x] No session narrative, no operator instructions, no scratch paths, no machine-derived
      addresses or hostnames in the skill text or this artifact.
