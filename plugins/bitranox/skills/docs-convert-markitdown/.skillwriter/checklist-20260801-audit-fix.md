# skill-writer checklist - docs-convert-markitdown (2026-08-01, isolated-audit fix)

Source: surfaced during the first clean-room sweep, though not by a reviewer's finding - a sweep
reviewer installed `markitdown` into the ambient environment while verifying this skill's claims,
which flipped these tests from skipping to running for the first time. Ships with plugin 5.126.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Two real defects in `scripts/convert_literature.py`, both in the pattern the function's own
      docstring advertises (`Author_Year_Title.pdf`):
      - the year regex used `\b(19|20)\d{2}\b`, but an underscore IS a word character, so `\b`
        never fires between `_` and a digit and the year was never extracted. Replaced with
        `(?<!\d)...(?!\d)` lookarounds, which do not depend on the separator's word-ness.
      - the year was then also left inside the title, so a caller got it twice.
- [x] The two tests DISAGREED with each other and neither had ever executed: the underscore case
      expected the year stripped from the title, the dash case expected it kept. Reconciled on
      stripping, since the caller already receives `year` as its own field, and the dash test's
      expectation and comment updated to match.
- [x] Root cause of the invisibility recorded: the tests `importorskip("markitdown")`, so in every
      environment without that dependency - including the documented CI dependency set - all seven
      skipped and reported green. A test that skips everywhere is not coverage.
- [x] Verified: 6 passed, 1 skipped with markitdown present; the whole gate re-run clean.
- [x] No session narrative or private provenance in the skill; no machine paths added.
