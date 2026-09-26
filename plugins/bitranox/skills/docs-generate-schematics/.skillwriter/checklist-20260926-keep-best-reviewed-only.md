# skill-writer checklist - docs-generate-schematics (2026-09-26, keep-best reviewed-only)

Scope: one factual correction to the SKILL.md exit-status paragraph, following a behaviour change
in `scripts/generate_schematic_ai.py`: when a retry's review fails and an earlier image WAS
reviewed, the best-scoring reviewed image is kept and the run is judged on its score (before, the
unreviewed retry was delivered with exit 1). The paragraph also states the existing rule that the
threshold is numeric, so a NEEDS_IMPROVEMENT verdict on a score at or above it exits 0. The
frontmatter `description` is unchanged, so no routing keyword moved and no derived artifact needs
regenerating.

Why a behavioural RED does not apply here: this is a FACTUAL correction to a reference skill that
is installed on this machine, so a subagent would answer from the installed wording rather than
the file under test. The evidence is the script's own test suite and a text check of the file.

- [x] RED (text check against the file): the question "v1 was reviewed at 6.0, v2's review
      failed - which image is kept and what is the exit code?" had no answer in the previous
      paragraph, which listed "an image whose review failed" as exit 1 unconditionally; a grep for
      `NEEDS_IMPROVEMENT|REVIEWED|fall back on` matched 0 lines.
- [x] GREEN (text check): the paragraph now says the kept image is the best-scoring REVIEWED one,
      that a failed review exits 1 only with no earlier reviewed image to fall back on, and that a
      NEEDS_IMPROVEMENT verdict at or above the threshold exits 0; the same grep matches.
- [x] Behaviour the paragraph states, verified by the script tests:
      `test_a_failed_retry_review_keeps_the_reviewed_first_image` (v1 kept, exit 1 below the
      threshold), `test_a_failed_retry_review_after_a_verdict_forced_retry_keeps_v1_and_exits_0`,
      `test_failed_review_never_claims_the_threshold_was_met` (no reviewed image: exit 1, NOT
      verified), `test_a_verdict_forced_retry_above_the_threshold_is_not_called_below_it`.
- [x] The script docstring and `--help` epilog say the same as the paragraph.
- [x] Description unchanged (not in the diff).
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] No session narrative or private provenance; no machine paths or addresses added.
- [x] ASCII only in both changed files.
