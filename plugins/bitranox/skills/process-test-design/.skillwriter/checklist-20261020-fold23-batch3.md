# skill-writer checklist - process-test-design (2026-10-20, fold23 batch 3)

- [x] Change: "Injecting a callable as a seam" grows from two traps to three - a double must have
      the seam's SHAPE, or a fail-open caller goes inert (run once against the real callable,
      build the double from the signature, pin the call's keywords against
      `inspect.signature(seam).parameters`).
- [x] Change: new paragraph "A consistency test pays on the code it did not grow up with, so it
      enumerates every entry" (iterate every declared entry, assert how many were read, expect the
      first run to fail on old code and fix that in its own commit).
- [x] Change: "Five mechanics" becomes "Six mechanics"; the new bullet says a fixture built to make
      code FAIL can run the success path (`Path.rglob()`/`glob()` over a file or a missing path
      yields nothing), so the failure comes from a collaborator injected at a seam, adding one when
      the code has none. Ground truth: run on Python 3.10 and 3.14 - `list(Path(<file>).rglob('*'))`,
      `list(Path(<missing>).rglob('*'))` and `list(Path(<file>).glob('*'))` all return `[]`.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); the editing agent
      loaded the skill through the Skill tool before its first SKILL.md edit.
- [x] RED (text check of the artifact, quote-back on the pre-edit snapshot): wrong-shape double -
      partial (the two annotation traps only); failure fixture - partial (general precondition
      checks only); registration test - NONE. Behavioural RED replaced on purpose: the rules are in
      the always-loaded memory index of the authoring machine (inherited coverage).
- [x] GREEN quote-back on haiku and opus, every quote substring-checked against the edited file
      (0 unmatched): SKILL.md:116 "A double must have the seam's SHAPE, or a fail-open caller goes
      inert."; :334 "A consistency test pays on the code it did not grow up with, so it enumerates
      every entry."; :380 "A fixture built to make code FAIL can run the success path instead."
- [x] GREEN diffed against RED both ways: the RED partial quotes (annotation traps, precondition
      checks) are still present; nothing lost.
- [x] Gaps closed or declined: closed - no seam in the code under test ("add one when the code has
      none", re-tested by quote-back on haiku and opus, both quoted it); declined - which tier the
      one real-callable run belongs in (the tier rule earlier in the file already answers it);
      whether a registration test may land red while the old defect waits (the paragraph says to
      fix that defect in its own commit).
- [x] Description measured: unchanged
- [x] Security scan: prose only, no secrets, hostnames, private paths or PII
