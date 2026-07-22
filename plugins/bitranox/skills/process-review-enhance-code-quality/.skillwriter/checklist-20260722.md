# skill-writer checklist - process-review-enhance-code-quality (2026-07-22, codepath-coverage-matrix)

Change: added a Common-Mistakes row - do not review only the one code path in front of you; walk
the full input/variant/caller matrix (types, sizes, states, callers) of the changed code, one
check per branch, on the FIRST pass.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: a real observed failure - a review PR caught three matrix gaps across two rounds
      (a fixup gated on one flag missed another; a header parse ignored the extension chain; a
      test covered only one family), and a follow-up review was still cursory until the user
      pushed twice (fact feedback-codepath-coverage-matrix). Without the rule, reviews validate
      only the shown path and miss real defects on sibling inputs/callers.
- [x] GREEN: row names the failure (single-path review) and the fix (walk the full
      input/variant/caller matrix on the first pass), generalized beyond the network example.
- [x] Scope: universal review-discipline item; the network specifics were dropped as generic.
- [x] Security scan: prose only, no secrets/hosts/paths/private repo names.
- [x] CSO description: unchanged (a Common-Mistakes row; existing triggers cover retrieval).
- [x] Token budget: one table row.
