# skill-writer checklist - write-humanize-en (2026-08-01, script and hook agree about code)

Change: `strip_typographic_tells.py` now skips inline-code spans and fenced blocks, using the same
definition of code as the tell-sweep hook. Ships with plugin 5.134.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] ROOT CAUSE, not the symptom. The audit finding was that this skill's prose claimed code spans
      protect examples from an accidental strip; measured, the script rewrote the em dash inside an
      inline span AND inside a fenced block. The first pass corrected the PROSE to match the script.
      The operator chose to fix the SCRIPT instead, which is the better end state: the claim the
      skill wanted to make is now true.
- [x] ONE implementation, not two. The fence/span scanner already existed in the shared `tell_chars`
      module but only as a DETECTOR (`find_tell_lines`). Added `transform_outside_code` beside it as
      the write-side twin, and pointed the script at it - so the detector and the rewriter cannot
      drift. Two implementations of "what is code" drifting apart is precisely what produced this
      defect.
- [x] TDD: 6 tests for the shared primitive (inline span, fenced block, tilde fences, several spans
      on one line, no trailing newline, empty/None) and 4 for the script, all observed failing
      first. One of the four failures was my own test being wrong rather than the code - the em
      dash maps to " - " and my input already had a following space, so the expectation
      double-counted it. Corrected the test, not the mapping.
- [x] The strongest test is the parity one: a source the HOOK reports clean must come back from
      `normalize` byte-identical. That is the invariant the whole change exists to hold.
- [x] Re-ran the original failing probe end to end: the inline span keeps its em dash, the fenced
      block keeps its em dash, and surrounding prose is still normalised.
- [x] The SKILL.md wording was updated a SECOND time in this session - the first correction said the
      script does not skip code, which the fix has now made false. A doc corrected to match a
      defect goes stale the moment the defect is fixed.
- [x] Suite after: 876 pass across the hook tests and this skill's tests.
- [x] No session narrative or private provenance added; no machine paths added.
