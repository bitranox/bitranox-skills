# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-09-12, enum discriminator)

One gap: the skill requires Enums over string literals, and is silent on the discriminated
union, which is exactly where the stringly-typed duplicate survives.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The claim is about library behaviour, so the test is a probe of the
      installed library plus a coverage check, not a pressure scenario.
- [x] Scope: one subsection added beside the existing Pydantic serialization subsection.

## RED
- [x] Behavioural RED not used: this lesson is already a pointer line in this machine's
      always-loaded memory index, so a dispatched agent inherits it. `redcheck --corpus-cascade`
      returned clean, which means NOT CAUGHT, not absent.
- [x] Coverage RED with a positive control: control `SerializeAsAny` 3 hits;
      `Literal[Enum.MEMBER]` 0 hits; discriminated-union wording 0 hits.

## GREEN
- [x] Same instrument after the edit: control 3, `Literal[Enum.MEMBER]` 3, discriminator 3.
- [x] Quote-back: the tag is written `Literal[MyEnum.MEMBER]`, it validates from the plain value
      string "in lax and strict mode alike and from `validate_python` and `validate_json`
      equally", and what it refuses is the member NAME.
- [x] The reason the duplicate survives is stated, since that is what keeps the anti-pattern
      alive: once there are two spellings of one tag, nothing makes them move together.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] Example uses invented domain names, no machine values.
- [x] Frontmatter untouched.
