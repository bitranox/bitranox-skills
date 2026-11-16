# Review: a new key in a file earlier releases read with extra="forbid"

Change: new section "A new key in a file that earlier releases read with `extra="forbid"`" after
"On an existing wire, `model_dump_json()` is not a drop-in": write a new persisted key only while
it holds data (`model_dump_json(exclude={key})` otherwise), pin its absence in a test against a
copy of the earlier model, name the remaining downgrade window in the CHANGELOG.

Decisions: d-20261116-f7d64272

- [x] Ownership: Python/Pydantic mechanism (`extra="forbid"`, `model_dump_json(exclude=...)`), so
      it lives here; the language-neutral skill states no copy of it.
- [x] RED (text check of the pre-edit file, `git show HEAD:.../SKILL.md`): `grep -niE
      'forbid|downgrade'` hit only line 370 (Core Principle 7 shim note) and line 709 (a click
      downgrade note); no text on adding a key to a file earlier releases parse strictly.
- [x] Pydantic behaviour measured (pydantic 2.14.3, `uv run --no-project --with pydantic`): an
      `extra="forbid"` model refused `{"history":["a"],"pending":[]}` with `extra_forbidden` at
      `('pending',)`; it accepted the dump made with `exclude={"pending"}`; a non-empty field
      still writes the key and is refused (the remaining window); `exclude_unset=True` kept
      `"pending":[]` after a key loaded from the file was cleared; `exclude_defaults=True` dumped
      a default `State()` as `{}`.
- [x] The SKILL.md code block was extracted and executed, then asserted on: empty dump has no
      key and validates against the earlier model; non-empty dump is refused by it; the
      no-`exclude` mutation arm is refused (the pin test can fail).
- [x] GREEN quote-back, `opus` (effort medium) and `haiku`, 2 tiers x 2 questions (Q4 wrong use of
      `exclude_unset`, Q5 remaining window): both tiers rejected `exclude_unset`, named
      `exclude={"pending"}`, the absence test and the CHANGELOG window, each with verbatim quotes.
- [x] Skill gaps reported and decided:
      - version scope (measured on 2.14.3 only): declined, the measured version is stated in the
        text; a later pydantic change is a reason to re-measure, recorded in the ledger reopen_if.
      - other cases where an earlier reader still fails: declined, the text names the one case
        this pattern leaves (field holds data).
      - one CHANGELOG entry or two: declined, no contradiction between the two duties.
- [x] Width, fence and non-ASCII check over the added lines: no problems.
