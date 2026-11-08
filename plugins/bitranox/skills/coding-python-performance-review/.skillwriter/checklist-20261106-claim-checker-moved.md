# skill-writer checklist - coding-python-performance-review (2026-11-06, claim checker moved)

`validate_perf_claims.py` moved to the generic skill `coding-performance-review` (with its test
file and the three claim tests from `tests/test_perf_scripts.py`). The change here is two path
mentions: the Reference Files row now names `../coding-performance-review/validate_perf_claims.py`,
and the review-pipeline bullet reads "`python3 ../coding-performance-review/validate_perf_claims.py
<diff_file>` (path relative to this skill's directory)". No rule changed.

Decisions: none - the claim checker moved to the generic skill; no rule changed

- [x] Receipt fresh; Step 0b `show coding-python-performance-review --kind rejected,removed
      --full` and `show coding-python-performance-review` printed nothing (no ledger).
- [x] Not mirrored: `coding-python-performance-review` ships only from this marketplace.
- [x] RED: `tests/test_claim_checker_location.py` written first and run before the move: 2 failed
      (SKILL.md lacked `../coding-performance-review/validate_perf_claims.py`; the script still sat
      in this skill). On the pre-edit text a reader is sent to `validate_perf_claims.py` in this
      skill's directory, a file the move deletes.
- [x] GREEN: the same test passes after the move and the two edits (it asserts the path is in
      SKILL.md and resolves to a real file, and that no copy is left here). Retrieval probe on the
      edited excerpt (haiku, skill directory given as /opt/skills/coding-python-performance-review):
      it resolved the path to "/opt/skills/coding-performance-review/validate_perf_claims.py",
      quoting the Reference Files row. Its skill gaps were about the absent example files only.
- [x] Table re-aligned by the table formatter, not by hand; ASCII only; width and fence check
      over the added lines printed nothing.
- [x] Tests: this skill's suite plus the generic skill's pass with CI's dependency set;
      `test_perf_scripts.py` no longer imports `validate_perf_claims`.
