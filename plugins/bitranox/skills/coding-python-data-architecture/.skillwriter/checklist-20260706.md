# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-07-06, roster review wave 2)

- [x] Change: corrected the enum doctrine: StrEnum/str,Enum for string-on-the-wire values (the skill's own example fed 'active' strings into IntEnum(1/0) fields, which Pydantic cannot parse), IntEnum reserved for integer wire values - 4 coherent edits; STEP D's crude final grep replaced with judge-each-candidate guidance (the old ZERO-matches loop could never terminate). Deferred: structural dedup trim, rationalization table + red flags (needs baseline test), When-NOT-to-use section.
- [x] Receipt held (skill_receipt.py, this session)
- [x] Review: read-only opus subagent audit, verified against the files by the applier
- [x] Discovery test: fable subagent wave 5/5 (changed descriptions) 
- [x] Security scan: prose/frontmatter/table edits, no secrets/paths/PII

# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-07-06, emoji policy + rationalization tables)

- [x] Change: rationalization table added from TWO RED rounds (first round's design leaks disclosed by its own runner; corrected forced-choice round produced genuine 2/2 capitulation - 'reviewed scope decision', 'sequencing not skipping'); GREEN passed for the demo-freeze carve-out; REFACTOR added the ask-the-human row after a fresh deadline-risk loophole appeared, retest then chose surface-and-ask.
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED/GREEN evidence per the Iron Law where behavior changed (see Change line)
- [x] Suites green: hooks 532, humanize 54+54, SDD 16
- [x] Security scan: prose/table/marker edits, no secrets/paths/PII
