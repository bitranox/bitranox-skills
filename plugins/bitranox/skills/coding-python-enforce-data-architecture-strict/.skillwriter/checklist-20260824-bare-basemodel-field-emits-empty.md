# skill-writer checklist - coding-python-enforce-data-architecture-strict (a bare BaseModel field serializes as {})

Change: one new subsection between the `str, Enum` version-fallback section and
`### Anti-Patterns to Eliminate`. Pydantic serializes by the DECLARED type, so a field annotated as
the bare `BaseModel` emits `{}` for every real subclass instance. Two fixes, and the union widening
that looks like a safe fallback and is not.

## PLAN

- [x] Skill type: prescriptive workflow skill with reference-style trap subsections. Test approach:
      measure the real behaviour against real Pydantic, then a coverage check with the shipped jig,
      matching the shape of the two trap sections already in this file.
- [x] Scope: one subsection. No frontmatter change - the description already covers Pydantic models
      at boundaries and export.

## RED

- [x] Measured rather than asserted, in an isolated PEP 723 script run with `uv run`, pydantic
      2.13.4. A field annotated bare `BaseModel` dumps `{'payload': {}}` through both `model_dump()`
      and `model_dump_json()` while the stored instance really holds `name='widget' count=3`.
- [x] Both fixes measured, not assumed: `SerializeAsAny[BaseModel]` recovers the real fields, and
      keeping the field a mapping with an explicit `model_dump()` in the emit function recovers them
      too.
- [x] The danger demonstrated in the two directions that matter: the field is fully and validly
      annotated, so a type checker has nothing to say, and a test asserting only the outer envelope
      keys passes while the payload is empty.
- [x] Coverage checked with `claim_check.py` (home: `skills/compuse-toolbox/scripts/`) rather than a
      bare grep, over all 100 `skills/*/SKILL.md` and `skills/*/references/*.md`: ABSENT, control
      matched 55 times across 100 files, so the files were read. `coding-python-clean-architecture`
      and `coding-input-sanitization` were checked separately: both discuss Pydantic at boundaries
      in general, neither mentions this trap.
- [x] `redcheck.py --corpus-cascade` reported STRONG inherited coverage, traced to this machine's
      private memory store rather than to any shipped file. That confirms the lesson is real and
      independently arrived at twice, and confirms the marketplace text still lacks it - a private
      fact ships to nobody. Route taken, per this skill family's own rule: text check of the file.

## GREEN

- [x] The claim in the shipped text is the one that was measured, not the one that was queued. The
      union widening raises `TypeError: 'MockValSer' object is not an instance of 'SchemaSerializer'`,
      and only when the runtime value is a raw dict that smart-union validates into the bare
      `BaseModel` arm; with a genuine model instance the same annotation builds and dumps fine. The
      recorded claim that it raises `PydanticSerializationError` did not reproduce on 2.13.4, so the
      text states the measured exception and the memory fact carrying the older wording is corrected
      in the same change.
- [x] One runnable example rather than three sketches, with the two fixes as prose carrying one
      concrete dumped result each.
- [x] The subsection states which fix to prefer and why: export at the boundary when the envelope
      exists only to be dumped, which is Rule 5 applied to the payload; `SerializeAsAny` when the
      envelope stays a live typed object past the dump call.

## REFACTOR

- [x] Placed as a `###` trap subsection matching the shape of the `str, Enum` section directly above
      it, rather than as a new top-level rule, because it is a serialization trap under the existing
      export rule rather than a rule of its own.
- [x] Nothing removed or reworded: the edit is a pure insertion between two existing headings, and
      both survive unchanged.
- [x] The preference between the two fixes is a judgement, stated as such in the text by giving the
      condition that selects each rather than declaring one universally correct.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Matches the file's voice: a `###` heading, one fenced example, prose bullets.
- [x] `old_string` verified unique by exact substring count before applying.

## Deliverables

- [x] One subsection in `SKILL.md`, applied.
- [x] The memory fact recording the wrong exception type corrected against this measurement, so the
      store and the shipped skill agree.
