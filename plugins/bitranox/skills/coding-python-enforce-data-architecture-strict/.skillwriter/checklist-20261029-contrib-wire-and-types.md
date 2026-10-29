# skill-writer checklist - coding-python-enforce-data-architecture-strict (wire bytes, NamedTuple, revalidation, factories, ask the tool)

- [x] Changes: new section "On an existing wire, `model_dump_json()` is not a drop-in for the old
      serializer call" plus a pointer from Core Principle 2; the NamedTuple paragraph says
      equality hides unmigrated callers; the fixer brief adds the NamedTuple twin of the StrEnum
      warning; the analyser brief scopes out parameter order; a worked paragraph for re-validating
      `model_copy(update=...)`; the DISTINGUISH example is corrected and gains "ask T, do not
      re-derive T's choice"; the default_factory worked example offers the parametrised factory
      first.
- [x] RED (text check): `grep -rnE "revalidate|default_factory=(list|set|dict)\[|separators|
      drop-in|64-bit|surrogate|uv python find"` over SKILL.md and references/ found nothing; the
      NamedTuple paragraph said "the change breaks no caller"; the DISTINGUISH example's fix was
      an `implementation == "cpython"` filter.
- [x] Every claim run:
      - pydantic 2.14.2, orjson 3.13.0: `model_dump_json()` compact vs `json.dumps` spaced; a
        2**70 int written by `model_dump_json` and `json.dumps`, `orjson` raises
        `JSONEncodeError` (a TypeError); a surrogateescape-decoded str: `PydanticSerializationError`
        (ValueError) / orjson `JSONEncodeError` / `json.dumps` writes `\udce9`; non-UTF-8 bytes in
        `Any`: `PydanticSerializationError` / `UnicodeDecodeError`; NaN: null / null / NaN; -0.0
        and non-ASCII identical; a float field given 30 dumps 30.0 where the dataclass printed 30.
      - pyright 1.1.414 strict: a plain tuple passed to a `Target` (NamedTuple) parameter reports
        reportArgumentType; `Target("a", None) == ("a", None)` is True; a plain tuple raises
        AttributeError on `.host`. `field(default_factory=list)` reports "partially unknown",
        `field(default_factory=list[str])`, `set[str]`, `dict[str, int]` report 0 errors and run
        on Python 3.10 and 3.14 returning plain containers.
      - pydantic 2.14.2: `model_copy(update=...)` alone and `model_validate(copy)` /
        `from_attributes=True` without the setting pass an over-long value; with
        `revalidate_instances="always"` `model_validate(copy)` raises the same errors as the dict
        round trip (`errors()` equal); a `model_construct` instance passed into another model now
        raises; a field validator runs again when the instance enters an outer model.
      - uv 0.13.0: `uv python find --system --no-python-downloads --show-version 3.14` matched
        `uv venv --python 3.14` in 6/6 cells; under system preference uv built 3.14.4 while the
        listing's newest was 3.14.8; the listing carries `implementation` and `variant`.
- [x] GREEN quote-back: "keep the existing serializer call, with a comment saying why, unless a
      byte-identity test passes first"; "That same equality hides the callers you did NOT
      migrate"; "The public fix is two parts: `model_config =
      ConfigDict(revalidate_instances=\"always\")` ... and `Model.model_validate(...)`"; "Try the
      one-word fix first: pass the PARAMETRISED type as the factory"; "When the decision is
      \"which X will tool T pick\", ask T".
- [x] Description: unchanged.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
