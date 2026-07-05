# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-07-06, roster review wave 2)

- [x] Change: corrected the enum doctrine: StrEnum/str,Enum for string-on-the-wire values (the skill's own example fed 'active' strings into IntEnum(1/0) fields, which Pydantic cannot parse), IntEnum reserved for integer wire values - 4 coherent edits; STEP D's crude final grep replaced with judge-each-candidate guidance (the old ZERO-matches loop could never terminate). Deferred: structural dedup trim, rationalization table + red flags (needs baseline test), When-NOT-to-use section.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 5/5 (changed descriptions) 
- [x] Security scan: prose/frontmatter/table edits, no secrets/paths/PII
