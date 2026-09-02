# skill-writer checklist - process-test-design (2026-09-02, injecting a callable as a seam)

Change: one section. Annotate an injected stdlib callable with your OWN contract or pyright strict
rejects the double, and read the test file's wall clock after adding a wait to a shared path.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Pre-change, a grep for `Callable[`,
      `SupportsFloat` and `wall clock` over SKILL.md returned 0 hits.
- [x] MEASURED with both arms under `typeCheckingMode: strict`, not reasoned about. A class holding
      a bare `self._sleep = time.sleep` REJECTS a double declared `(_seconds: float) -> None`:
      "Type "(_seconds: float) -> None" is not assignable to type
      "(seconds: _SupportsFloatOrIndex, /) -> None"". The annotated arm
      (`self._sleep: Callable[[float], None]`) ACCEPTS the same double.
- [x] The control is what makes it a finding: both arms are in one file, so the difference is the
      annotation and nothing else. A single failing arm would not have shown that.
- [x] The section says where the error LANDS (on the test), because that is why it reads as a bad
      double rather than as a missing annotation.
- [x] Scope: shared - generic to any pyright-strict project injecting a stdlib callable; the
      example is `time.sleep`.
- [x] Security scan: stdlib names and a timing figure only.
- [x] CSO description: unchanged; the section sits under existing mock/seam triggers.
- [x] Token budget: one section.
