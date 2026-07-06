# skill-writer checklist - compuse-vnc (2026-07-06, roster review wave 1)

- [x] Change: folded the click-text OCR-failure pixel fallback into driving-loop step 4 (from the source-repo lineage); fixed the pre-rename H1. Reconciliation verdict: marketplace body is the base; merged body flows to the vnc-remote-control repo at sync (its copy keeps its own name and adopts this description).
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent, scenario picked this skill from a 12-candidate list (wave 6/6)
- [x] Security scan: prose/frontmatter edits, no secrets/paths/PII

# skill-writer checklist - compuse-vnc (2026-07-06, read-the-screen-before-retry gotcha)

- [x] Change: new Gotchas bullet "Nothing happened, or an error? READ the screen before re-sending input - ROOT-CAUSE it" (screenshot + ocr first; same-coordinates-different-control hazard; two-screenshots-apart rule before diagnosing dropped input; single retry with increased delays). Family-consistency change: compuse-bash/git already carry the never-wave-off rule, ssh/vnc lacked it
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED: sonnet baselines (choice-framed AND open-ended laggy-installer pressure) would not violate at this tier; retrieval gap was the failing test (prior text had no read-the-error-before-retry rule)
- [x] GREEN: fable retrieval test 5/5 with correct bullet/section citations
- [x] Discovery: description unchanged (no new trigger class; the gotcha is body content inside an already-triggered skill)
- [x] Security scan: prose edit only, no secrets/paths/PII
