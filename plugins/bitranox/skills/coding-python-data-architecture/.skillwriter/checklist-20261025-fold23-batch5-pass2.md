# skill-writer checklist - coding-python-enforce-data-architecture-strict (memory rules folded in)

- [x] Change: Define the types; never suppress or exclude the checker -> option 2 (amended) + new
      '### Worked example - a stub gap only the oldest-floor pyright cell sees' (after the
      recursive-alias example) - coding-python-enforce-data-architecture-strict/SKILL.md. RED on the
      pre-edit snapshot: partial. Verified: Probe in a scratch venv (filelock 4.2.4, pyright
      1.1.414, strict): `pyright --pythonversion 3.10` flagged the annotated local (probe.py:18) and
      the plain local (probe.py:35) with `Type of "acquire" is partially unknown ... ->
      AcquireReturnProxy[Unknown] (reportUnknownMemberType)`; the factory and the bare `with
      FileLock(...)` were clean; the default-version run reported `0 errors`. filelock source:
      `_api.py:60 if TYPE_CHECKING:`, `:92 from typing import Self`, `:1145 ->
      AcquireReturnProxy[Self]`. The inserted code block, extracted from SKILL.md, checks `0 errors`
      under pyright strict at 3.10 and 3.12. Option 2 reconciled with the skeptic's cast-vs-no-cast
      conflict: the factory is listed as the no-cast alternative.
- [x] Dropped as stale or unverified: The body's 'filelock 4.2.0, pyright 1.1.41x' is replaced by
      the re-measured 4.2.4 / 1.1.414. The private example location (repo and module path) is
      dropped.
- [x] Change: Architecture Rules -> new '### A datetime's wire form flips at the same 3.10 / 3.11
      line' (right after the `str, Enum` section) -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot:
      partial. Verified: Probe `uv run --python 3.10/3.11 --with pydantic` (pydantic 2.14.1): 3.10
      `fromiso Z: ValueError: Invalid isoformat string: '2026-01-01T00:00:00Z'`, 3.11 parses it to
      `2026-01-01 00:00:00+00:00`; on both versions the hand-built dict gave
      `'2026-01-01T00:00:00+00:00'`, plain `model_dump_json()` gave `"2026-01-01T00:00:00Z"`, and
      with the field_serializer `"2026-01-01T00:00:00+00:00"`. The inserted block, extracted from
      SKILL.md, ran on 3.10 and its output parsed back with `fromisoformat`. The enum half is
      already at SKILL.md lines 38-64 (f"{C.A}" 3.10 -> "capacity", 3.11+ -> "C.A"; interpolation
      takes `.value`), so it was left unchanged.
- [x] Dropped as stale or unverified: Nothing stale. The project name, the dated incident and the
      cross-link to another fact are dropped (public skill).
- [x] Change: Worked example - a RECURSIVE alias on a pre-3.12 floor (step 3 and the Measured
      paragraph corrected; no new rule added) -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot:
      partial. Verified: ALREADY claims checked one by one against SKILL.md: quote only the
      self-references (step 1), runtime imports and never TYPE_CHECKING (step 2), Mapping/Sequence
      and never dict/list (step 3), RUF036 None last: all present. Probe (pyright 1.1.414 strict,
      --pythonversion 3.10, unq.py): `d({"a": {"b": "c"}})` with an inline literal against the dict
      alias gives NO error; `x = {...}; d(x)` gives `Type parameter "_VT@dict" is invariant ...
      Consider switching from "dict" to "Mapping" which is covariant in the value type`; the Mapping
      alias accepts both. So the skill's old 'an ordinary nested literal is rejected' was inaccurate
      and is corrected. Fully-quoted alias `ConfigValue: TypeAlias = "str | int | bool | None |
      list[ConfigValue] | dict[str, ConfigValue]"`: 0 errors on pyright 1.1.380, 1.1.400, 1.1.408
      and 1.1.414 (also with `from __future__ import annotations` and with TYPE_CHECKING imports);
      reveal_type shows it resolving.
- [x] Dropped as stale or unverified: The body's signature for the fully-quoted alias ('Expected
      type but received a string literal', reportGeneralTypeIssues, 23 errors at consumers) is
      CONTRADICTED on four pyright releases, so it was not added. The body's 'run pyright with no
      path arguments, or tests are excluded' was not folded: it is about pyright invocation and
      depends on project config, not on the alias rule.
- [x] Change: Define the types -> new '### A burst of strict errors in files you did not touch: look
      upstream first' (after the filelock example) -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot: NONE.
      Verified: Probe kw.py (pyright 1.1.414 strict): a helper returning `dict[str, object]` spread
      into `Client(host: str, port: int, *, tls: bool)` gave 3 errors at the spread line, `Argument
      of type "object" cannot be assigned to parameter "host" of type "str" ...
      (reportArgumentType)` (likewise port and tls); the same helper returning `Mapping[str, Any]`
      gave 0 errors. The 'Any is a suppression wearing a type's clothes' line in the recursive-alias
      section is reconciled by the parenthetical: here the value is a pass-through, not a value type
      the code defines.
- [x] Dropped as stale or unverified: The body's 'thirty errors' figure (UNVERIFIED) is replaced by
      the mechanism (one error per parameter per spread). The cross-link to another fact is dropped.
- [x] Change: Architecture Rules -> new '### A union without a discriminator is decided by
      validation mode, not by fit' (after the discriminated-union section), first bullet plus the
      shared test paragraph - coding-python-enforce-data-architecture-strict/SKILL.md. RED on the
      pre-edit snapshot: NONE. Verified: Probe un.py (pydantic 2.14.1, Python 3.12), model_validate
      and model_validate_json: `Loose | Specific` and `Specific | Loose` (Loose = extra="allow")
      returned `Specific` for {'name':'x','count':3} and for {'count':'3'}; `dict[str, Any] |
      Specific` returned `dict` for both inputs; `Specific | dict[str, Any]` returned `Specific` for
      the exact input and `dict` for the lax input (py and json alike). The skeptic's CONTRADICTED
      finding on the extra=allow half and on the 'put it last' remedy holds, so both are corrected.
- [x] Dropped as stale or unverified: The body's claim that an `extra="allow"` model arm swallows
      its siblings is CONTRADICTED on pydantic 2.14.1; it is kept only as a dated measurement of the
      opposite. The body's remedy 'order the permissive arm LAST' is dropped, because a last dict
      arm still wins every lax input. The cross-link is dropped.
- [x] Change: ### A bare `BaseModel` field serializes as `{}` (paragraph appended at the end) -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot:
      partial. Verified: Core already in the skill at the old lines 66-107 (declared-type
      serialization, SerializeAsAny vs export at the boundary, the MockValSer TypeError, diff
      against a baseline). Probe (pydantic 2.14.1): `Env(data={"a": 1})` with `data:
      SerializeAsAny[BaseModel] | dict[str, Any]` gave data type `BaseModel`, and `model_dump()`
      raised TypeError (mro TypeError -> Exception), `isinstance(ex, PydanticSerializationError)`
      False, message `'MockValSer' object is not an instance of 'SchemaSerializer'`.
      `Env(data=Specific(...)).model_dump()` gave `{'data': {'name': 'w', 'count': 1}}`. A field
      named `schema` emits `UserWarning: Field name "schema" in "Bad" shadows an attribute in parent
      "BaseModel"`. `schema_: str = Field(serialization_alias="schema")` dumps `{'schema': 'v1'}`
      with by_alias=True and `{'schema_': 'v1'}` without.
- [x] Dropped as stale or unverified: The body's 'Re-measured on pydantic 2.13.4' is replaced by the
      2.14.1 probe. The project name is dropped. The skeptic's wording 'must be renamed to satisfy
      Pydantic' is sharpened: it is a UserWarning, not an error.
- [x] Change: ### A union without a discriminator is decided by validation mode, not by fit: second
      bullet, plus the shared 'Test what was BUILT' paragraph (quoted in the permissive-union row) -
      coding-python-enforce-data-architecture-strict/SKILL.md. RED on the pre-edit snapshot: NONE.
      Verified: Probe un.py (pydantic 2.14.1): `Mapping[str, str] | Mapping[LogLevel, str]` with
      input {LogLevel.INFO: 'green', 'error': 'red'} stored `('20', 'str')`; pure-member and
      pure-name inputs kept their key types; `Mapping[str | LogLevel, str]` and the three-arm union
      both kept `LogLevel.INFO` for the mixed input. Probe mk.py (pyright 1.1.414 strict, 3.10):
      `narrow(by_name)` and `narrow(by_level)` with typed dict variables both failed with `Type
      parameter "_KT@Mapping" is invariant, but "str" is not the same as "str | LogLevel"`;
      `narrow({"info": "green"})` (literal) passed; the three-arm union accepted both typed
      variables and the mixed literal.
- [x] Dropped as stale or unverified: The body's 'Measured on pydantic 2.14, lib_log_rich 6.4.2' is
      replaced by the re-measure, and the library and alias names are generalised (MyIntEnum, V).
- [x] GREEN gap fixed: recursive-alias step 1 now says a fully quoted alias also type-checks (0
      errors on pyright 1.1.380 to 1.1.414) but is a plain str at runtime; the source fact's
      "Expected type but received a string literal" signature is contradicted on four pyright
      releases and is not carried.
- [x] Gaps declined: the Mapping[str, Any] pass-through beside "Any is a suppression" (already
      scoped by a parenthetical in the same paragraph); migration advice for persisted enum keys
      (outside this rule); version drift of filelock and pyright beyond the dated measurement.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (9 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
