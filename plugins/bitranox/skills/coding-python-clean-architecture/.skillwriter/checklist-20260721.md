# skill-writer checklist - coding-python-clean-architecture (2026-07-21, echo "define types, do not suppress the checker")

Change: add one paragraph to the Data Modeling section - when the strict type checker flags your code
(often a third-party stub gap), DEFINE the missing types (annotation, or a typed facade: a Protocol +
cast, or a local .pyi stub) rather than a per-file reportX=false, an exclude, or a bare # type: ignore;
a narrow rule-specific # pyright: ignore[rule] with a remove-when reason is the last resort. Cross-refs
bitranox:coding-python-enforce-data-architecture-strict for the rich-click module-cast Protocol facade
example (kept DRY - the worked example lives in that one skill).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED/GREEN: the rule itself was TDD-validated in coding-python-enforce-data-architecture-strict
      this session (baseline agent under deadline falls back to a per-file suppression; the agent with
      the rule rejects a reviewer's "per-file rule-off is standard" push and defines the types). This
      edit echoes that validated rule into the Data Modeling context with a cross-reference, not a new
      claim - so it inherits that test rather than restating the full example.
- [x] DRY: the worked facade example is NOT duplicated here; it is referenced by skill name.
- [x] CSO description unchanged - the trigger (structuring layered Python, deciding where code belongs,
      data-modeling boundaries) already covers this; no workflow summary added.
- [x] Security scan: prose-only change, no secrets, hostnames, or private paths.
- [x] Docs describe current state: no legacy/migration narrative.
- [x] Version bumped: plugin.json 5.96.3 -> 5.96.4 (PATCH; one bump covers this + the review-skill echo).
