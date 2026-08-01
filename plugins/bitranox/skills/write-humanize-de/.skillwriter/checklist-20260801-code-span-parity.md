# skill-writer checklist - write-humanize-de (2026-08-01, script and hook agree about code)

Change: this skill's `strip_typographic_tells.py` gets the same code-skipping fix as its English
twin, and the SKILL.md text names the shared definition. Ships with plugin 5.134.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] FOUND BY A TEST FAILURE, not by the audit. After fixing the English copy, the whole-plugin
      suite failed while this skill's tests passed in isolation: `strip_typographic_tells` is
      shipped TWICE under the same module name, and in a full run the DE copy - loaded first - is
      what the EN tests actually imported. So the English tests had been exercising the German
      script, and the fix looked absent.
- [x] The two files were BYTE-IDENTICAL before this change, so the defect was a straight duplicate
      and the fix applies verbatim. Verified after: `diff` of the two reports 0 differing lines.
- [x] This skill's SKILL.md already claimed the exact character "übersteht sowohl den Hook als auch
      einen versehentlichen Durchlauf". That claim was FALSE before the fix and is true now, so the
      text needed no correction - only the explanation of WHY, matching the English copy.
- [x] Recorded as an open observation rather than fixed here: two skills shipping the same script
      under one module name is both a duplication and a test-isolation hazard. A test in one skill
      can silently exercise the other's copy, which is exactly what happened. Consolidating them is
      a design change beyond this fix.
- [x] Suite after: 1448 pass ambient, 1442 pass with the CI dependency set.
- [x] No session narrative or private provenance added; no machine paths added.
