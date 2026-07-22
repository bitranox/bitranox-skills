# skill-writer checklist - meta-skill-writer (2026-07-22, hermetic-red-green-fixture)

Change: added a Common-Mistakes entry to testing-skills-with-subagents.md - a RED/GREEN fixture
must be HERMETIC (no shared namespace with the live system) or the subagent routes around it and
the run proves nothing; verify a PASS against ground truth, never at face value.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: a real observed failure - the same skill-testing mistake recurred three times in real
      skill-authoring sessions (a fixture named a real repaired resource; a run symlinked the live
      tree instead of the fixture; a doc-test handed agents the real repo where the fix already
      sat), each producing a misleading PASS; sealed hermetic re-runs then FAILED correctly
      (fact feedback-a-red-green-fixture-must-be-hermetic-and-verify-ground-truth-before-believing-it).
- [x] GREEN: entry names the tell (a PASS via a path not in the prompt, an effort spike) and the
      fix (hermetic paths with no real counterpart, no live-repo access, verify PASS vs ground truth).
- [x] Scope: universal skill-testing methodology; specifics scrubbed to generic prose.
- [x] Security scan: prose only, no secrets/hosts/paths/private repo names.
- [x] CSO description: SKILL.md and its description unchanged (edit is in a reference file).
- [x] Token budget: one Common-Mistakes entry in a supporting reference file.
