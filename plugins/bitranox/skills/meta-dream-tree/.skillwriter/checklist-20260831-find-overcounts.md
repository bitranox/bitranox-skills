# skill-writer checklist - meta-dream-tree (2026-08-31, find OVER-counts levels)

Change: "Level enumeration" documented only the UNDER-count (a session `grep` honouring
`.gitignore`). It now documents the other direction: a plugin copy installed under a repo's own
`.venv` carries real pointer blocks, and `find` has no gitignore behaviour to skip it. The
prescribed command in both SKILL.md and references/dream-core.md gains the exclusion.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE. Pre-change the section names exactly one failure
      direction and the prescribed command has no exclusion, so an enumeration on any tree holding
      an installed plugin copy over-counts and the skill says nothing about it.
- [x] MEASURED: `find` returned 100 levels against `--check-tree`'s 98. The two extra were one
      vendored plugin copy under a repo's `.venv`.
- [x] The failure is recorded in the form it actually takes, which is the point: because the
      vendored blocks are REAL, the cross-check reports two slugs pointed at from two levels each,
      which reads as a tree-uniqueness VIOLATION in the store rather than as an artifact of the
      scan. The store was clean.
- [x] The `.venv` pattern is a PREFIX match on purpose (`*/.venv*`), so `.venv-win`, `.venv-3.12`
      and `.venv-bmk` are caught; a bare `*/.venv/*` misses all three, which is a recorded defect
      in its own right.
- [x] The cross-check instruction now names the second instrument and says to CHASE a disagreement
      rather than average it - a gap of 2 in 100 is the size that gets waved through, and the
      existing "a count in the hundreds" tell does not fire at it.
- [x] Scope: shared - any tree containing an installed plugin copy, which is the normal case.
- [x] Security scan: no absolute paths, hosts or credentials; the anchor stays `<anchor>`.
- [x] CSO description: unchanged; this is body detail under existing triggers.
- [x] Token budget: one paragraph plus a fenced command in the reference file, one line in SKILL.md.
