# skill-writer checklist - process-review-enhance-code-quality (2026-07-21, echo "a type-checker suppression is not a Type Safety pass")

Change: add a note under the Type Safety rubric - a per-file reportX=false, an exclude that drops files
from the strict run, or a bare # type: ignore blinds the checker to real bugs and must be scored as a
gap; the recommended fix is to DEFINE the missing types (annotation, or a typed facade: a Protocol +
cast, or a local .pyi stub), with a narrow rule-specific # pyright: ignore[rule] (remove-when reason) as
the last resort. Cross-refs bitranox:coding-python-enforce-data-architecture-strict for the worked
example (kept DRY).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED/GREEN: the rule was TDD-validated in coding-python-enforce-data-architecture-strict this
      session (baseline suppresses under deadline; with the rule the agent defines the types and rejects
      the reviewer's per-file-rule-off push). This edit re-expresses it as a REVIEW criterion (flag a
      suppression, score it a gap) and cross-references the example - inherits that test.
- [x] Placed in the rubric where it bites: the Type Safety dimension, right after the per-language table
      whose Python 7-10 anchor already says "minimal type: ignore".
- [x] DRY: worked facade example referenced by skill name, not duplicated.
- [x] CSO description unchanged - trigger (rate/score/audit/improve code quality) already covers it.
- [x] Security scan: prose-only change, no secrets, hostnames, or private paths.
- [x] Docs describe current state: no legacy/migration narrative.
- [x] Version bumped: plugin.json 5.96.3 -> 5.96.4 (PATCH; shared with the clean-architecture echo).
