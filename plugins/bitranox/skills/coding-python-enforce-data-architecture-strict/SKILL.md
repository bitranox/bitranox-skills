---
name: coding-python-enforce-data-architecture-strict
description: Use when refactoring or reviewing Python code to enforce a strict data architecture - Pydantic models at every external boundary, typed models (never raw dicts) inside the app, Enums for all fixed categorical values, and minimal input-to-output conversions. Use when asked to eliminate dict parameters, stringly-typed status/mode values, Model->dict->Model conversion chains, or compatibility shims, or to make a Python data flow type-safe end to end.
---

# Data Architecture Enforcement

Refactor Python code to follow strict data architecture rules using Pydantic models and Enums.

> Pydantic-at-the-boundary is also the input-sanitization edge. For the full per-sink output escaping
> (parametrized SQL, HTML autoescape, shell argv) and the boundary-vs-internal-libs scope, see
> `bitranox:coding-input-sanitization`.

---

## Architecture Rules

### Core Principles

1. **Pydantic at Boundaries**: All external data (API requests, file reads, env vars, CLI args) must be parsed into Pydantic models immediately upon entry
2. **Pydantic for Export**: All outputs (API responses, file writes, serialization) must use Pydantic's `.model_dump()` or `.model_dump_json()`
3. **No Internal Dicts**: Inside the application, never use raw dicts for structured data - always typed models
4. **Enums for Constants**: All string literals representing categories, statuses, modes, or fixed values must be Enums. For values that cross an external boundary as strings, use `StrEnum` (Python 3.11+) or `class X(str, Enum)` so Pydantic parses and serializes them without changing the wire format; reserve `IntEnum` for values that are genuinely integers on the wire. **If your floor is 3.10 and you take the `class X(str, Enum)` fallback, its default string form is version-dependent** - read "The `str, Enum` fallback formats differently on 3.10 and 3.11+" below before you interpolate a member anywhere.
5. **Minimize Conversions**: Ideal flow is ONE parse at input, ONE dump at output - nothing in between
6. **String-to-Enum at Edges Only**: Convert strings to Enums only at system boundaries (input parsing). All functions and methods must accept and use the Enum type directly - never convert str->Enum inside business logic. This mirrors the class/Pydantic rule: parse once at entry, use typed objects throughout
7. **No Compatibility Shims**: Remove all compatibility shims - code must use dataclass fields and enums directly. No wrapper methods, aliases, or backward-compatibility layers that accept old formats

### What to Use When

| Scenario                                   | Use                          |
|--------------------------------------------|------------------------------|
| External input/output                      | Pydantic `BaseModel`         |
| Internal business logic (no serialization) | `@dataclass` or Pydantic     |
| Need validation                            | Pydantic `BaseModel`         |
| Fixed string values (string on the wire)   | `StrEnum` / `str, Enum`      |
| Simple value objects                       | `NamedTuple` or `@dataclass` |

### The `str, Enum` fallback formats differently on 3.10 and 3.11+

`enum.StrEnum` is safe: `str(member)`, `format(member)` and an f-string all give the VALUE on
every version that has it. The `class X(str, Enum)` fallback for a 3.10 floor is NOT:

```python
class C(str, Enum):
    A = "capacity"

f"{C.A}"      # 3.10 -> "capacity"      3.11+ -> "C.A"
format(C.A)   # 3.10 -> "capacity"      3.11+ -> "C.A"
str(C.A)      # "C.A" on EVERY version
C.A.value     # "capacity" on every version
```

Python 3.11 made `__format__` follow `__str__` for mixed-in enums. So a member interpolated into
a key, a filename, a log line or any hand-built payload silently changes shape across the version
matrix, and the 3.10 lane is the one that looks correct.

This is the one place the "avoid unnecessary `.value` access" guidance above does NOT apply.
Comparisons, assignments and Pydantic serialization take the member directly; **anything that
builds a string by interpolation takes `.value`.** Measured cost of getting it wrong: an alert-state
key built as `f"{pool}:{category}"` wrote `rpool:IssueCategory.CAPACITY` instead of `rpool:capacity`
on 3.11+, which orphans every previously-written state entry and re-fires every open alert.

Pin the wire form with a test that asserts the exact string, and run the whole declared version
range - a single-interpreter green cannot see this.

### A datetime's wire form flips at the same 3.10 / 3.11 line

`datetime.fromisoformat("2026-01-01T00:00:00Z")` raises `ValueError: Invalid isoformat string` on
3.10 and parses on 3.11+. Pydantic's `model_dump_json()` writes a UTC datetime with a trailing
`Z`, while a hand-built dict using `value.isoformat()` writes `+00:00`. So moving an output from a
hand-built dict onto a Pydantic model changes the wire format, and a 3.10 reader that parses it
back with `fromisoformat` breaks with no reader code changed. Wherever a datetime reaches a key, a
filename, a log line or a payload another component reads back, pin its form:

```python
class Report(BaseModel):
    checked_at: datetime

    @field_serializer("checked_at")
    def _wire_checked_at(self, value: datetime) -> str:
        return value.isoformat()  # "+00:00" on every version; 3.10 fromisoformat reads it
```

Then assert the exact string in a test and run the whole declared version range, as for the enum
above. Measured (pydantic 2.14.1, Python 3.10 and 3.11): without the serializer
`model_dump_json()` gives `"2026-01-01T00:00:00Z"`, with it `"2026-01-01T00:00:00+00:00"`.

### A bare `BaseModel` field serializes as `{}`

Pydantic serializes a field by its DECLARED type, not the runtime value it holds. A field annotated
as the bare `BaseModel` base class has no fields of its own, so `.model_dump()` and
`.model_dump_json()` silently emit `{}` for it no matter which real subclass instance you put there
- a type checker sees a fully-annotated field and passes, and a test that asserts only the OUTER
envelope keys exist stays green too, so nothing catches it short of reading the actual value:

```python
from pydantic import BaseModel, SerializeAsAny

class Payload(BaseModel):
    name: str
    count: int

class Envelope(BaseModel):
    kind: str
    payload: BaseModel  # BAD: declared type has no fields to dump

env = Envelope(kind="a", payload=Payload(name="widget", count=3))
env.model_dump()  # {'kind': 'a', 'payload': {}}  <- silently empty
```

Two fixes, and they are not interchangeable:

- **`SerializeAsAny[BaseModel]`** keeps the field typed for as long as the object lives - use it
  when the envelope is a live object other code still reads before the final dump. It tells
  Pydantic to serialize the RUNTIME type polymorphically: `env.model_dump()` now gives
  `{'kind': 'a', 'payload': {'name': 'widget', 'count': 3}}`.
- **Export at the boundary** - keep the field a plain mapping and call `.model_dump()` on the
  payload yourself in the function that emits the envelope - is the better default when the
  envelope exists only to be dumped (a CLI's `{ok, command, data, skipped}` response, an API
  reply). That is Rule 5's "one dump at output, nothing in between" applied to the payload too,
  and it needs no extra annotation.

Do not widen either fix into `SerializeAsAny[BaseModel] | dict` expecting a permissive fallback: a
raw dict validates against the bare `BaseModel` arm (an empty base model accepts any mapping), and
the instance you get back has no working serializer, so `.model_dump()` raises `TypeError:
'MockValSer' object is not an instance of 'SchemaSerializer'` instead of degrading gracefully. Type
the field for the concrete subclasses you actually expect, and diff the emitted JSON against a
pre-change baseline whichever fix you take - the wire format is the only thing that shows an empty
payload.

That union breaks only on a RAW DICT input; a model instance builds and dumps fine, so a test that
feeds only models stays green. The `MockValSer` failure is a plain `TypeError`, not
`PydanticSerializationError`, so a handler catching Pydantic's error class misses it. If a payload
field must be renamed because its natural name shadows a `BaseModel` attribute (`schema` emits a
`UserWarning`: *Field name "schema" ... shadows an attribute in parent "BaseModel"*), keep the
wire key as an alias of `schema_` and configure it as the next section says, so the default dump
emits `schema` too; passing `by_alias=True` at each call covers only the calls that remember it.

### A wire name that differs from the field name needs three settings

When a field's wire name differs from its Python name (a reserved word such as `not` becoming
`not_`, or `schema` becoming `schema_`), the model needs all three: the first so the DEFAULT dump
uses the wire name, the other two so the field name stays usable as the constructor keyword:

```python
from pydantic import BaseModel, ConfigDict, Field

class Not(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True, validate_by_name=True)

    not_: Condition = Field(validation_alias="not", serialization_alias="not")
```

- **`serialize_by_alias=True` in `model_config`** (pydantic 2.11 and later). Without it,
  `model_dump()` / `model_dump_json()` with no arguments emit the FIELD name (`not_`); only a call
  passing `by_alias=True` uses the alias. An explicit `by_alias=False` still overrides the config.
  The setting resolves PER MODEL: a nested model that sets it emits its alias inside a parent that
  does not, and a parent that sets it does not fix a nested model that lacks it.
- **The split pair `validation_alias=` plus `serialization_alias=`, never a plain `alias=`.** Under
  pyright strict a plain `alias="not"` makes the synthesized `__init__` accept only the alias, so
  `Not(not_=x)` fails with `No parameter named "not_"`, even with `validate_by_name=True`. The split
  pair keeps `not_` as the constructor keyword while the alias governs the wire both ways.
- **`validate_by_name=True`**, so `Not(not_=x)` also validates at RUNTIME: with a
  `validation_alias` and no such setting, construction by field name raises `Field required`. It
  is the 2.11+ name for this; the older `populate_by_name=True` does the same, but pydantic marks it
  not recommended and due for deprecation in v3.

Prove it by dumping with NO arguments and validating that output against the wire contract the
consumer reads (its JSON Schema or a recorded fixture). A round-trip test written with
`by_alias=True` passes whether or not the config is set, and the no-argument dump is the path a
persistence layer actually takes, so it is the one to test.

### A discriminated union tags on the Enum MEMBER, not a copy of its value

When a Pydantic 2 discriminated union switches on a StrEnum field, write the tag as
`Literal[MyEnum.MEMBER]`. A plain value string is validated INTO the member, in lax and strict
mode alike and from `validate_python` and `validate_json` equally, so JSON arriving over the wire
needs no duplicate string literal and no coercing before-validator:

```python
class Kind(StrEnum):
    WIDGET = "widget"
    GADGET = "gadget"

class Widget(BaseModel):
    kind: Literal[Kind.WIDGET]          # accepts the JSON value "widget"
    teeth: int

class Gadget(BaseModel):
    kind: Literal[Kind.GADGET]
    volts: float

Payload = Annotated[Widget | Gadget, Field(discriminator="kind")]
```

What it refuses is the member NAME (`"WIDGET"`), which is the right way round: the name is an
implementation detail of the Python side and was never the wire format.

The belief that an enum literal cannot validate from JSON is what keeps a stringly-typed
duplicate alive next to the enum - `Literal["widget"]` beside `Kind.WIDGET` - and once there are
two spellings of one tag, nothing makes them move together. Probe it rather than carrying the
fear: construct the union, call `validate_json` with the value string, and read the result back.

### A union without a discriminator is decided by validation mode, not by fit

Smart mode takes the arm that validates STRICTLY, and only falls back to lax coercion when none
does. Two traps follow, and in both the dump looks right while the parse was wrong:

- **A bare `dict`/`Mapping` arm swallows its model siblings.** A dict arm accepts any mapping
  strictly, so it wins whenever it comes first, and even LAST it wins for every input the model
  arm would only accept after lax coercion (`"3"` for an `int`, from Python and from JSON alike).
  The dict keeps every key, so `model_dump_json()` emits the input document unchanged and a
  round-trip test comparing documents passes, while the model's field types, refusals and
  defaults never ran. Give the union a discriminator (or drop the dict arm) rather than
  reordering it.
- **A union of single-kind mappings mangles a mixed-key input.** For
  `Mapping[str, V] | Mapping[MyIntEnum, V]`, an input holding both kinds matches no arm
  strictly, so the lax `str` arm turns the enum keys into value strings (`'20'`) and the refusal
  surfaces far downstream; pure-name and pure-member inputs pass, so single-kind tests stay green.
  Narrowing to `Mapping[str | MyIntEnum, V]` fixes the parse but breaks callers under pyright
  strict, because `Mapping`'s KEY type is invariant (*Type parameter "_KT@Mapping" is invariant*)
  and a caller's `dict[str, V]` or `dict[MyIntEnum, V]` is not assignable to it. Keep both
  single-kind arms and add the mixed one, named once as an alias:
  `Mapping[str, V] | Mapping[MyIntEnum, V] | Mapping[str | MyIntEnum, V]`.

Test what was BUILT, not what was dumped: assert `type(parsed) is Specific` (the arm you meant)
for each event shape, and for a mapping field feed a MIXED-key input and assert the stored key
types. Check a narrowed annotation with typed `dict` VARIABLES, never inline literals: a literal is
inferred against the parameter and hides the invariance. Measured (pydantic 2.14.1, pyright
1.1.414 strict): `dict | Specific` returned `dict` for every input, `Specific | dict` returned
`dict` for `{"count": "3"}`; the two-arm mapping union stored the key `'20'` as `str`, the
three-arm one kept `LogLevel.INFO`; the narrowed annotation rejected both typed variables and
accepted the literal. A model arm with `extra="allow"` did NOT swallow a stricter sibling on that
version (the specific arm won for exact and lax input, in either order) - the `type(parsed)`
assertion is what proves it on the version you run.

### `AwareDatetime` accepts values that have no UTC equivalent

`AwareDatetime` checks only that an offset is present. A value at the edge of the `datetime` range
whose offset carries it past that range - `0001-01-01T00:00:00+01:00`, `9999-12-31T23:59:59-01:00`
- parses cleanly, and the first `astimezone(timezone.utc)` downstream (a domain constructor that
normalises to UTC, a comparison against a UTC value) raises `OverflowError: date value out of
range`. That is neither `ValueError` nor `ValidationError`, so a loader that catches the boundary's
refusal lets it escape as a bare traceback. Normalise to UTC INSIDE the boundary model, and turn the
overflow into a `ValueError` there yourself: pydantic turns a `ValueError`, an `AssertionError` or
its own `PydanticCustomError` raised in a validator into a `ValidationError`, and passes an
`OverflowError` through unchanged.

```python
def _to_utc(value: datetime) -> datetime:
    try:
        return value.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("timestamp has no UTC equivalent inside the datetime range") from exc

UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]
```

Build the domain object from the parsed model inside the same `try` that turns `ValidationError`
into your refusal, so anything the constructor still raises is reported there rather than past it.
Test with both range edges. Measured (pydantic 2.14.2, Python 3.15): plain `AwareDatetime` accepted
both edge values and `astimezone` raised `OverflowError`; an `AfterValidator` calling `astimezone`
without the `try` let the `OverflowError` out of `model_validate_json`; with it, both edges came
back as a `ValidationError` of type `value_error` and in-range values were normalised to UTC.

### A strict `IntEnum` field accepts the bare integer from JSON

`strict=True` refuses a raw `20` for an `IntEnum` field from Python, but from JSON it accepts the
VALUE (`{"level": 20}` gives `Level.INFO`), refuses the member NAME (`"INFO"`), and words every
refusal in the internal integers (`Input should be 10 or 20`). When the wire format is the NAME,
parse it yourself in a `BeforeValidator` and dump it with a `field_serializer` returning
`value.name`. The validator must let enum MEMBERS through before refusing non-strings: an
`IntEnum` member IS an `int`, so a validator that refuses every non-`str` also refuses the model's
own construction from domain values (`Record(level=Level.INFO)`), and the write path breaks while
every JSON-parsing test stays green:

```python
def _level_by_name(value: object) -> object:
    if isinstance(value, Level):     # the write path passes members; IntEnum members are ints
        return value
    if not isinstance(value, str):
        raise ValueError("level must be a level name such as 'INFO'")
    try:
        return Level[value]
    except KeyError:
        raise ValueError(f"unknown level name {value!r}") from None
```

Test the round trip from a domain object, not only the parse from JSON. Measured (pydantic
2.14.2): the strict model accepted `{"level":20}` and refused `"INFO"` with *Input should be 10 or
20*; a validator refusing every non-`str` refused `{"level":20}` correctly but also
`Record(level=Level.INFO)`; with the member pass-through both directions held and the dump read
`{"level":"INFO"}`.

### Converting a `str` parameter to an Enum changes its contract: scope it with its tests

A proper conversion of `release(part: str)` to `release(part: ReleasePart)` moves validation to
the boundary (`ReleasePart(raw)` where the CLI parses), so the value is checked there and not
inside the function. That changes what its existing tests can do, so before you put the item in a
"code-only, no test changes" tier of a review or plan, run `grep -rn <func_name> tests/` and read
each hit:

- **A test asserting that an invalid value raises `ValueError` from the function breaks**: the
  raise now happens at the boundary, in `ReleasePart("bogus")`. Keeping a validating raise inside
  the function to save that test re-adds the shim this skill forbids (Core Principle 7).
- **A test passing a RAW STRING breaks where the function dispatches by identity**
  (`part is ReleasePart.MAJOR`). It keeps passing where the code compares with `==`, matches on
  the members (`case ReleasePart.MAJOR:`), or looks the value up in a dict or set keyed by them,
  because a `str, Enum` member equals and hashes as its value; there only the type checker flags
  the call site (see STEP B). Switching `is` to `==` saves the raw-string tests but never the
  raises-on-invalid one.

If either kind of test exists, the item belongs in the tier that touches tests. `str, Enum`
wire-compatibility saves construction and lookup tests, never identity-dispatch or
raises-on-invalid tests.

**Branch on a `StrEnum` (or `str, Enum`) PARAMETER with `==`, never `is`.** A member equals its
own string, so `"quiet" == Mode.QUIET` is True while `"quiet" is Mode.QUIET` is False. Under `is`,
a caller passing the raw value does not raise: it silently takes the OTHER branch and does
something plausible and wrong. The annotation stops such a caller only inside the type-checked
code, never a config value, a payload field or an untyped test. Do not fix it by raising inside
the function either: validation belongs at the boundary parse (above), and on a hot or
supervisory path an instrument must not take down the run it observes. Keep `is` only on a value a
`parse_*` returned as `Member | None`, where a string cannot arrive. Add a test that passes the RAW
string (`cast("Mode", "quiet")`) and asserts the branch it reached by something only that branch
produces (a test that accepts either branch's output stays green on the wrong one), and grep the
diff for `is <Enum>.` on anything reached from a parameter.

**Where the Enum lives decides where the helper can live.** Read `[tool.importlinter]` (or
`.importlinter`) before choosing the parameter type: when the Enum sits in a HIGHER layer than the
module holding the `str`-taking helper, the helper cannot import it, and an import under
`if TYPE_CHECKING:` breaks the layers contract too (import-linter counts it unless the project sets
`exclude_type_checking_imports`, which hides the break rather than fixing it). Either move the
Enum down to a layer the helper may import, or move the helper onto the Enum as a method - the
second only when no caller of the helper sits below the Enum's layer, since those callers would
then import upward. Re-run `lint-imports` after the move. Measured: a low-layer
`errors.refused(verb: str)` could not take the `models` layer's enum, and every caller sat above
`models`, so it became a method on that enum.

### Anti-Patterns to Eliminate

```python
# BAD: Dict parameter
def process(data: dict) -> dict:
    return {"name": data["name"]}

# BAD: String literals for status
if user.status == "active":

# BAD: Unnecessary conversion chain
model.model_dump()  # -> dict
SomeClass(**dict_data)  # -> back to model

# BAD: Converting just to access fields
d = model.model_dump()
name = d["name"]  # Just use model.name!

# BAD: Pydantic -> dataclass -> Pydantic
@dataclass
class Internal:
    ...
internal = Internal(**pydantic_model.model_dump())
output = OutputModel(**asdict(internal))

# BAD: Fixed-shape record returned as a bare tuple across a function boundary
def split_target(text: str) -> tuple[str, str | None]:  # which slot is which?
    ...

# BAD: str parameter whose every caller passes one of a few literals
def refused(verb: str) -> str: ...
refused("add"); refused("delete")
```

A fixed-shape tuple record becomes a `NamedTuple` (`class Target(NamedTuple): host: str;
zone: str | None`). It is still a tuple - unpacking, indexing, `==` against a plain tuple and
hashing all work unchanged - so the change breaks no caller. Not this pattern: an OS sockaddr tuple
(what `socket` and `getaddrinfo` take and return), a tuple that never leaves one function (a
local gather closure), and a variable-length `tuple[X, ...]`. A `str` parameter is found by its
CALLERS, not its signature: grep the call sites, and when every one passes a literal from a small
fixed set, the parameter is an Enum (see "Converting a `str` parameter to an Enum changes its
contract").

A refusal is a boundary output too: never interpolate `str(ValidationError)` into one, because it
hands the caller pydantic's union-arm tags, a versioned docs URL and a slice of their own input.
Emit your own sentence plus one `<dotted loc>: <reason>` line per `error.errors()` entry and keep
the exception as `__cause__`. When writing or reviewing any such refusal (including one whose
`ValidationError` arrives wrapped in a library's exception, or a union field that reports once per
arm), read `references/validation-error-messages.md`.

---

## Instructions

1. **Create a Todo List** with the following Definition of Done (DoD) items to track refactoring progress:

   **Input/Output Boundaries:**
   - [ ] Parse all external inputs into Pydantic models at system boundaries
   - [ ] Produce all outputs through Pydantic export methods (`.model_dump()`, `.model_dump_json()`)
   - [ ] Each boundary model that replaced a `.get()` walk declares every field the consumer must
     distinguish, not only the fields the old code read (step 3), and a test feeds it an input
     where that field decides the answer
   - [ ] Your own new and rewritten code got the same adversarial read as the code you set out to
     fix: a faithful port passes every existing test while keeping the old bug

   **Internal Data Handling:**
   - [ ] Eliminate all internal dict processing - no `data["key"]` access
   - [ ] All functions/methods use typed fields from Pydantic models or dataclasses
   - [ ] Use `@dataclass` only for pure internal logic with no serialization needs

   **Type Safety:**
   - [ ] Replace all string literals (statuses, modes, categories) with Enums
   - [ ] Ensure all function signatures use typed models, not `dict`

   **Conversion Optimization:**
   - [ ] Remove redundant Model->dict->Model chains
   - [ ] Eliminate Pydantic->dataclass->Pydantic conversions (use Pydantic throughout)
   - [ ] Verify minimum conversions: ideally 1 at input, 1 at output

   **Exceptions:**
   - [ ] Small local dicts (few items, single function scope) may remain - convert if used across functions/modules

   **Verification:**
   - [ ] Run `make test` OR pyproject.toml tools (pytest, ruff, mypy, etc.) - fix all errors until passing
   - [ ] Verify type checking passes and Pydantic validation works
   - [ ] If the refactor moved WHERE input is validated: every single-fault input the old code
     refused keeps its exception type, exit code and message, or each change is listed in the
     CHANGELOG (STEP C item 5)

2. **Analyze the Code** and identify violations:
   - Functions accepting `dict` parameters instead of typed models
   - Raw dict key access (`data["key"]`) instead of field access (`data.key`)
   - String literals used as identifiers, modes, or status values
   - `str` parameters of a function called from another function or module whose call sites all
     pass literals from a small fixed set (grep the callers; the signature alone looks fine)
   - Fixed-shape records returned as bare tuples across a function boundary
     (`-> tuple[str, str | None]`), with the exclusions under "Anti-Patterns to Eliminate"
   - Unnecessary conversions between dicts and dataclasses
   - Missing Pydantic validation at input boundaries
   - Missing Pydantic export methods at output boundaries
   - **Unnecessary data conversions** - AGGRESSIVELY detect and eliminate:
     * Model -> dict -> Model chains (pass the model directly)
     * Multiple `.model_dump()` calls on the same object
     * Converting to dict just to access fields
     * Redundant serialization/deserialization cycles
     * Intermediate dict structures that serve no purpose
     * **Pydantic <-> dataclass conversions**: If code converts Pydantic -> dataclass or dataclass -> Pydantic, refactor to use Pydantic throughout. Remove compatibility shims for dict/dataclasses/Pydantic (no wrapper methods, aliases, or backward-compatibility layers)
     * Unnecessary dataclass wrappers when Pydantic can be used directly
     * Any conversion that doesn't add value - minimize total conversions
     * **Count total conversions** in the data flow - goal is MINIMUM possible (ideally: 1 at input, 1 at output)
     * **Enum usage**: Use `StrEnum`/`str, Enum` for string-valued fields and `IntEnum` only for integer-valued ones. Avoid unnecessary `.value` access or conversions - use the enum member directly in comparisons and assignments. The exception is string INTERPOLATION under the `str, Enum` fallback, where `.value` is required and not optional (see "The `str, Enum` fallback formats differently on 3.10 and 3.11+"). Remove compatibility shims for enums (no wrapper methods, aliases, or backward-compatibility layers)

3. **Refactor the Code** following these rules:
   - Import external data immediately into Pydantic models with validation
   - Export data using Pydantic's built-in dump methods
   - **Prefer Pydantic over dataclass** - only use `@dataclass` when there's a clear benefit and no Pydantic conversion needed
   - If you see Pydantic -> dataclass -> Pydantic, eliminate the dataclass and use Pydantic throughout
   - Never create or handle internal dict structures
   - Convert dict inputs to Pydantic models as early as possible
   - All functions must operate on dataclasses or Pydantic fields
   - **Minimize total conversions** - count them, ideal is ONE at input boundary, ONE at output boundary
   - Replace fixed string sets with `Enum` classes
   - **Declare what the consumer must DISTINGUISH, not only what the old code read.** When a
     Pydantic model replaces a hand-rolled `.get()` walk over external JSON, the old field list
     records what the old code looked at, not what it needed. For each decision the consumer makes
     on the parsed data, ask what it must tell apart and whether the source exposes a field for it
     that the walk dropped; declare that field and filter on it. A faithful migration carries the
     latent bug forward. Example: a model of `uv python list --output-format json` declaring only
     `version` and `version_parts` keeps an implementation-blind "newest installed patch" pick.
     Several implementations (CPython, PyPy, ...) can be installed for one minor while
     `uv venv --python <minor>` provisions CPython, so a PyPy build with a higher patch is reported
     as newest, never matches the venv's interpreter, and the venv is rebuilt on every run. The fix
     is `implementation: str` plus an `entry.implementation == "cpython"` filter; a build variant
     (free-threaded vs default) is the same kind of discriminator when the consumer must pick the
     default build.

4. **Mark Todo Items Complete** as each DoD criterion is satisfied.

## Workflow

**CRITICAL: This is an iterative process. You MUST loop until ZERO violations remain. Do NOT stop early.**

**State is tracked in `.data_arch_violations.json` - always read before and write after each phase.**

```
INITIALIZATION:
  1. Read all target files
  2. Read pyproject.toml (if exists) to identify configured tools
  3. Use TodoWrite to add one item per target file to the DoD checklist from Instructions
     step 1 (one list, extended - not a second, competing list)
  4. Create state file `.data_arch_violations.json` (the `//` notes explain fields; leave them
     out of the file). `base` is the commit the request starts from: the tag or commit it names
     when it asks about a change set ("since v2.0.0", a branch), otherwise HEAD at
     INITIALIZATION:
     {
       "pass": 0,
       "base": "<commit or tag the request starts from>",
       "pass_start_rev": null,  // HEAD when the current STEP B began (STEP B sets it)
       "total_violations": 0,
       "files": {
         "path/to/file.py": {
           "violations": [],
           "out_of_scope": [],  // findings on lines not changed since "base" (STEP A, SCOPE)
           "status": "pending"  // pending (never analysed) | in_progress (open findings, or
                                // changed since its last analysis) | clean
         }
       }
     }

================================================================================
|  MAIN LOOP - REPEAT STEPS A->B UNTIL total_violations == 0                    |
================================================================================

  STEP A - PARALLEL ANALYSIS (use subagents):
     - Read `.data_arch_violations.json`
     - Increment "pass" counter
     - Launch subagents (Task tool, subagent_type="Explore", model="opus", effort="medium") in
       PARALLEL for each file whose status is `pending` or `in_progress` (pin both; per-file
       analysis judges code already written, a review dispatch - see "Concrete tiers" and
       "Review dispatches" in bitranox:process-agents-subagent-driven-development). A `clean`
       file is skipped, which is safe only because STEP B re-opens every file a fixer changed.
     - Each subagent prompt MUST include:
       * The file path to analyze
       * The violation patterns to search for (from Architecture Rules above)
       * The patterns that are NOT violations, spelled out - a small single-function local
         dict, a free-form external JSON envelope, and DYNAMICALLY-keyed maps (queue index to
         count, metric name to value, MAC to address); for tuples, an OS sockaddr, a local
         gather closure and a variable-length `tuple[X, ...]`. Without this an analyser reports
         every `dict[str, X]` it sees, and you spend the loop re-judging its false positives.
       * The CALL-SITE SWEEP, named as a required step: for every `str` parameter of a function
         called from another function or module, grep its call sites and report it when every
         caller passes a literal from a small fixed set. A per-file read never sees this, because
         the signature looks fine and the evidence is in other files.
       * Instruction to return JSON: {"file": "path", "sweep": {"tuple_returns": N, "str_params":
         N, "literal_only": N}, "violations": [{"line": N, "type": "...", "description": "..."}]}
         - the `sweep` counts are what the agent grepped, so a zero shows it looked
       * **"Reply with the JSON object and NOTHING else - no preamble, no summary, no markdown
         fence."** Say it explicitly. An analyser that answers in prose ("Findings reported
         above: 8 items across 4 files") loses every finding, because the detail it refers to
         was never in what you received - and the count it cites makes the loss look like a
         result. Re-run that agent; do not reconstruct its numbers.
     - Collect all subagent results
     - Run your own CANDIDATE SWEEP beside the agents: `grep -rnE -- '-> tuple\[|: dict|-> dict'`
       over the target files, and hold each hit against the agents' verdicts. A file reported
       clean that holds an unjudged hit goes back to an analyser with the hit named. An
       all-clean verdict returned in seconds cannot be told from a blind one; the sweep tells
       them apart. Measured: 9 analysers called 46 of 49 modules clean, and a grep for
       `-> tuple[` found 13 fixed-shape tuple records none of them had flagged.
     - SCOPE: on pass 1 of a request over whole files or a package, every finding counts. From
       pass 2 on, and on every pass of a change-set request, a finding counts only on a line
       changed since `base`. Rules such as "defined once" and "refuse impossible values" apply
       to a whole file, so later analysers widen into code no fix touched and the count stops
       converging. Attribute every finding before you count: `git blame <base>..HEAD -- <file>`
       prefixes each line NOT changed since `base` with `^`. Move findings on such lines to
       `out_of_scope`; they do not count toward total_violations. Put the collected list to the
       user ONCE, when the in-scope count reaches zero, instead of looping on it; a finding the
       user rules in scope moves back into `violations`. Measured: pass 4 found 73 and pass 5
       found 86 findings; 59 of the 86 sat on lines older than the base.
     - Update `.data_arch_violations.json` with violations from each subagent; a file with no
       in-scope violation becomes `clean`, any other `in_progress`
     - Calculate total_violations = sum of all in-scope violations across files

     >>> If total_violations == 0: put any `out_of_scope` list to the user (SCOPE); when
         nothing comes back in scope, EXIT LOOP, GOTO STEP C
     >>> If total_violations > 0: CONTINUE TO STEP B

  STEP B - PARALLEL REFACTORING (use subagents):
     - Read `.data_arch_violations.json`, set `pass_start_rev` to `git rev-parse HEAD` and write
       it back BEFORE launching any fixer (the re-open step at the end of STEP B diffs against it)
     - REPRODUCE every claimed runtime failure before it goes into a brief. When a finding says
       what happens at runtime (an uncaught exception, a crash, a wrong result), make one real
       call through the public entry point that should trigger it, and brief the fixer on the
       MEASURED behaviour, not the analyser's wording. Measured: an analyser said an oversized
       payload surfaced as an uncaught `OSError`; the call raised nothing and instead reported a
       live host as unreachable, so a fixer briefed from the claim would have added `OSError`
       handling and left the misreport.
     - PARTITION the work into NON-OVERLAPPING file sets, one per subagent, BEFORE launching
       anything. This refactor is not per-file independent: an Enum lives in `enums.py` and a
       model in `models.py`, so several agents will reach for the SAME shared file. Give each
       shared file exactly ONE owner (or edit it yourself first and let the others only
       import from it). Measured: three agents editing one checkout in parallel produced a
       transient test failure from a half-written sibling edit, and one agent had to re-read
       files before every write to avoid clobbering another's work.
     - Launch subagents (Task tool, subagent_type="general-purpose", model="opus") in PARALLEL,
       one per file SET (per-file refactor is bounded judgment, an `opus` job; pin the tier)
     - Each subagent prompt MUST include:
       * The full Architecture Rules section (copy from this document)
       * The specific violations for that file (from state file)
       * The EXPLICIT list of files it may touch, and a statement that other agents are
         editing the rest of the repo concurrently so it must not edit anything outside that
         list. An agent that finds a needed fix in someone else's file REPORTS it instead of
         making it - that hand-off is how the last error gets found, not a failure.
       * Instruction to fix ALL violations
       * Instruction NOT to read or write `.data_arch_violations.json`: the coordinator owns it
         and writes it from the returned JSON (below)
       * **Instruction to run the TYPE CHECKER as well as the tests, and to report the error
         count.** Tests alone cannot verify this refactor: a `StrEnum` member compares and
         hashes equal to its string value, so every call site still passing a raw string, and
         every assertion on it, stays green wherever the code compares by value (`==`, `match`
         on the members, a dict or set lookup) rather than by identity (`is`), while the type
         checker errors on the changed signature.
         Measured: three agents each reported "731 passed" while pyright had 24 errors, all
         of them call sites still passing raw literals into newly-Enum-typed parameters.
       * Instruction to return JSON and nothing else, one entry per file in its set:
         {"files": {"path": {"fixed": ["violation1", ...], "remaining": [...]}},
         "hand_offs": [{"file": "path", "line": N, "description": "..."}], "type_errors": N}
     - After all subagents complete, WRITE THE STATE FILE YOURSELF, once, from their returned
       JSON: each file's `violations` becomes its `remaining` list, each `hand_offs` file is set
       to `in_progress` with the hand-off named in that file's next analyser brief, and
       `total_violations` is recomputed as the sum. Never let parallel fixers update the shared
       file themselves: two agents that both read it before either writes each write back a
       copy missing the other's change, and recomputing the total instead of decrementing it
       does not help, because the arrays it sums were already clobbered. One writer after all
       fixers return has no race to lose.
     - RE-OPEN EVERY FILE THE PASS CHANGED, not only the briefed ones. A pass edits files
       outside the violation list - a shared enum or model, the call sites of a signature a
       fixer changed, a hand-off you applied yourself - and a file left `clean` is one the next
       STEP A skips. List `git diff --name-only <pass_start_rev>` plus
       `git ls-files --others --exclude-standard` (a new module is untracked, so the diff alone
       misses it) and set every listed target-language file to `in_progress`, adding it to
       `files` when absent. While the work stays uncommitted the diff also lists files earlier
       passes changed; re-analysing those once more is the safe direction. Example: a fixer
       that turns a `str` parameter into an Enum edits the enums module and every caller; with
       only its own file re-opened, all of those keep their `clean` status and the next pass
       never reads them. Measured: after one pass, 8 files the fixers had changed still read
       `clean`, found only by diffing the changed-file list against the state file by hand.
     - **Re-run the gate YOURSELF.** A subagent's green is not the gate's green: it may have
       sampled mid-flight while a sibling was still writing, and agents' reported counts will
       disagree with each other for exactly that reason. Yours is the only authoritative one.

     >>> GOTO STEP A (MANDATORY - must re-analyze to verify fixes and catch new issues)
     >>> DO NOT proceed to STEP C until analysis shows total_violations == 0

STEP C - RUN TESTS:
  **THIS STEP IS MANDATORY - DO NOT SKIP**

  Execute these commands using the Bash tool:

  1. First, check if Makefile exists with test target:
     ```bash
     test -f Makefile && grep -q "^test:" Makefile && echo "FOUND"
     ```

  2. If "FOUND": Execute `make test` now:
     ```bash
     make test
     ```

  3. If NO Makefile test target, read pyproject.toml and run configured tools:
     ```bash
     # Run each tool that has a [tool.X] section in pyproject.toml:
     pytest                        # if [tool.pytest] exists
     ruff check . && ruff format --check .  # if [tool.ruff] exists
     mypy .                        # if [tool.mypy] exists
     black --check .               # if [tool.black] exists
     isort --check .               # if [tool.isort] exists
     ```

  4. ON FAILURE:
     - Read the error output
     - Fix the code causing the failure
     - Re-run the failed command
     - REPEAT until all commands pass

  5. ERROR SURFACE - required whenever the refactor moved WHERE input is validated (a boundary
     model now refuses what a deeper call used to refuse). A green suite cannot see this: the
     tests assert on the new path, and a model's refusal changes what a caller observes.
     The test is whether any refusal now comes from a different place than before - a check
     moved into the model, or a model check added in front of one that still exists (the first
     one to refuse is the one the caller sees). A refactor that leaves every refusal where it
     was, such as renaming internal fields, does not need this item.
     What changes:
     - the exception TYPE, and through a CLI wrapper the EXIT CODE - a `ValidationError`, or the
       framework error you wrap it in, is not the `ValueError` the old call raised;
     - the MESSAGE - pydantic adds its own error-type tags and a versioned docs URL, and a model
       that redacts secret-bearing fields hides a value the old message quoted;
     - the ORDER - with several faults in one input, the setting the boundary checks first is
       now the one reported.
     Check it two ways:
     a. Read every doc that promises an error contract and hold the new code to it:
        `grep -rniE 'exit code|raises|refused' docs/ README*`
     b. Run ONE malformed value at a time through the real entry point of a baseline and of the
        working tree, and diff exception type / exit code / last error line per input. Use TWO
        baselines, HEAD and the LAST RELEASE tag: a change committed earlier in the same refactor
        is invisible against HEAD. Get each baseline's source without touching the checkout:
        `git archive <HEAD or tag> src | tar -x -C <tmpdir>`, then run with
        `PYTHONPATH=<tmpdir>/src`, never with `python -I` - isolated mode ignores PYTHONPATH, so
        both arms import the installed (editable) working tree and every case reads "same". Print
        each arm's `<package>.__file__` first and require it to sit under that arm's tree.
        Feed wrong-TYPE values beside out-of-range ones: `True` for a count, `"1"` for a
        timeout, `3.0` for an int. A lax-mode model accepts all three silently (`True` becomes
        `1`); only `strict=True` or a strict field type refuses them. Mark one input whose result
        you changed on purpose as the LIVENESS CONTROL: if it does not show up as different, the
        harness is broken, not the code. Measured: a run under `python -I` reported 20 of 20
        inputs "same", and only the control exposed it; the harness against the last release
        found a request model still accepting `times=True` and `timeout="1"` after five analysis
        passes, and four behaviour changes the CHANGELOG did not list.
     Every single-fault input the old code refused keeps its type, exit code and message, or the
     change is listed in the CHANGELOG with the input, the old result and the new one. To keep
     it, re-raise the model's refusal as the old exception type carrying the validator's own
     text (`item["msg"]`, or `str(item["ctx"]["error"])` for a `value_error` entry; never
     `str(exc)`; one line per
     entry when there are several - see `references/validation-error-messages.md`), and run a
     check ahead of the model where the model would redact what the old message quoted.
     Multi-fault ORDER is inherent to parsing at the boundary: document it, do not fight it.

  >>> DO NOT proceed to STEP D until all tests/linters pass and the error-surface diff shows no
      unlisted change

STEP D - FINAL VERIFICATION:
  - Read `.data_arch_violations.json` and confirm total_violations == 0
  - Grep only to surface candidates: `-> dict`, `: dict`, `-> tuple[` in signatures. A hit is a
    lead, not proof - `: dict` also matches the permitted small local dicts and annotations that
    are not signatures at all, and `-> tuple[` matches the tuple exclusions under "Anti-Patterns
    to Eliminate". Judge each hit against the Exceptions rule and those exclusions; do NOT
    auto-loop on raw match count.
  - If a real violation is found: GOTO STEP A
  - If clean:
    * Update state file: all files status = "clean"
    * Delete `.data_arch_violations.json`
    * Mark todos complete
    * Report: "[OK] Complete after {pass} passes - all violations fixed - tests passing"
```

**IMPORTANT RULES:**
1. ALWAYS read state file before each step
2. ALWAYS write state file after each step - the coordinator writes it; subagents never do
3. ALWAYS loop back to STEP A after STEP B - never skip re-analysis
4. Do NOT proceed to STEP C until total_violations == 0
5. **ALWAYS run STEP C** - execute `make test` or pyproject.toml tools
6. Do NOT proceed to STEP D until all tests pass
7. Delete state file only after successful completion

**LOOP ENFORCEMENT:**
```
STEP A -> found violations? -> STEP B -> STEP A (again!)
STEP A -> no violations? -> STEP C (run make test!) -> STEP D -> DONE
```

**Subagent Prompt Templates:**

Analysis subagent (`model: "opus"`, `effort: "medium"` - review dispatch, see
bitranox:process-agents-subagent-driven-development "Review dispatches"):
```
Analyze {file_path} for data architecture violations:
- dict parameters (`: dict`, `-> dict`)
- dict key access (`["key"]`, `['key']`)
- string literals for statuses/modes (`== "..."`, `!= "..."`)
- fixed-shape records returned as bare tuples (`-> tuple[str, str | None]`); NOT an OS
  sockaddr, a local gather closure, or a variable-length `tuple[X, ...]`
- missing Pydantic at boundaries
- unnecessary Model->dict->Model conversions

Call-site sweep (required): for every `str` parameter of a function called from another function
or module, grep its call sites across the repo; report it when every caller passes a literal from
a small fixed set.

Return JSON only: {"file": "{file_path}", "sweep": {"tuple_returns": N, "str_params": N,
"literal_only": N}, "violations": [{"line": N, "type": "...", "description": "..."}]}
```

Refactoring subagent:
```
Fix these violations in your file set ({file_set}):
{violations_list}

Rules: [paste Architecture Rules section]

You may edit only: {file_set}. Other agents are editing the rest of the repo; report a needed
fix elsewhere as a hand-off instead of making it. Do not read or write
`.data_arch_violations.json` - the coordinator writes it from your reply.

Fix ALL violations, then run the type checker as well as the tests and report its error count.
Return JSON and nothing else, one "files" entry per file in your set:
{"files": {"<path>": {"fixed": [...], "remaining": [...]}},
 "hand_offs": [{"file": "...", "line": N, "description": "..."}], "type_errors": N}
```

## Example Transformations

**Before (violation):**
```python
def process_user(data: dict) -> dict:
    if data["status"] == "active":
        return {"name": data["name"], "role": "member"}
```

**After (compliant):**
```python
from enum import StrEnum
from pydantic import BaseModel

class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class UserRole(StrEnum):
    MEMBER = "member"
    ADMIN = "admin"

class UserInput(BaseModel):
    name: str
    status: UserStatus

class UserOutput(BaseModel):
    name: str
    role: UserRole

def process_user(data: UserInput) -> UserOutput:
    if data.status == UserStatus.ACTIVE:
        return UserOutput(name=data.name, role=UserRole.MEMBER)
```

---

## Define the types; never suppress or exclude the checker

The discipline that forbids stringly-typed values also forbids silencing the type checker. When
pyright/mypy strict flags your code - very often a third-party stub gap, not a real defect - the
completion path is to DEFINE the missing types, not to suppress the diagnostic or exclude the file.

Order of preference:

1. Add the real annotation or generic argument.
2. Wrap a partially-typed third-party symbol in a typed facade you define - a `Protocol` plus a
   `cast`, a factory whose return type is the `Protocol` (no cast; see the filelock example), or
   a local `.pyi` stub on `stubPath` - so call sites see complete types.
3. Only if neither is feasible, a NARROW, rule-specific `# pyright: ignore[theRule]` with a comment
   naming WHY and the remove-when condition. Never reach first for `reportX = false`, a per-file
   rule-off, an `exclude` entry, or a bare `# type: ignore` - those blind the same scope to real
   errors too, and rot silently.

Worked example - rich-click's `option`/`argument`/`version_option` decorators have a
partially-unknown return type, so pyright strict reports `reportUnknownMemberType` at every
`@click.option(...)`. This is a stub gap, not a language rule: reproduced on rich-click 1.9.8
with pyright 1.1.411 (2026-08-28). Run pyright first - once rich-click ships complete stubs it
reports nothing, and the facade below would be solving a problem you no longer have; a rich-click
DOWNGRADE never gets you there (see the diagnosis note after the example). click's own decorators are fully typed, but they default the parameter class
to `click.Option` rather than rich-click's `RichOption` (which changes help rendering), so you
cannot just import them from click. Cast the MODULE to a `Protocol`: the `cast` is a runtime no-op,
so the wrappers forward to rich-click's own decorators (RichOption preserved) while pyright sees
complete types and no rule is silenced:

```python
from collections.abc import Callable
from typing import Any, Protocol, cast

import rich_click as click

_CommandDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]


class _RichClickDecorators(Protocol):
    option: Callable[..., _CommandDecorator]
    argument: Callable[..., _CommandDecorator]
    version_option: Callable[..., _CommandDecorator]


_click = cast("_RichClickDecorators", click)  # type-only; forwards to rich_click at runtime


def option(*param_decls: str, **attrs: Any) -> _CommandDecorator:
    return _click.option(*param_decls, **attrs)
```

Casting the FUNCTION, or `from rich_click import option`, still evaluates the partially-unknown
member access and stays flagged; only casting the MODULE onto a typed Protocol moves the access to
a typed surface.

The flood arrives with a PYRIGHT upgrade, not with your edit and not with a rich-click change: it
reproduces at an untouched HEAD once the lock carries a recent pyright, and downgrading rich-click
does not clear it, so do not bisect your own change or pin rich-click. Keep `@click.command` and
`@click.group` from rich-click (already fully typed) and route only the three decorators through
the facade. Then verify behaviour, not just the checker: an option declared through the facade is
still a `RichOption` (`cmd.params[0]`), and `--help` still renders through rich-click.

Second worked example - a lambda cannot satisfy a keyword-only `Protocol`. Two house defaults
collide and the diagnostic blames the wrong one. Ruff's `FBT` forbids a boolean POSITIONAL
argument, so a callable `Protocol` grows a keyword-only parameter; a lambda used where that
`Protocol` is expected then fails pyright strict, because a lambda parameter takes no annotation
and pyright will not back-infer one from the `Protocol`. Always `reportUnknownLambdaType` on the
parameter, plus one more that depends on where the lambda sits: `reportUnknownVariableType` when
it is assigned, `reportUnknownArgumentType` when it is passed as an argument. Both errors name the
LAMBDA, so it reads as a pyright quirk rather than a consequence of the `Protocol` change:

```python
class Formatter(Protocol):
    def __call__(self, value: str, *, verbose: bool) -> str: ...


# 2 errors: reportUnknownVariableType + reportUnknownLambdaType ("verbose" is unknown)
render: Formatter = lambda value, *, verbose: value.upper() if verbose else value


def render(value: str, *, verbose: bool) -> str:      # same body, fully typed, 0 errors
    return value.upper() if verbose else value
```

The fix is the typed nested `def`, not a suppression: it annotates what the lambda syntactically
cannot. A `def` is available anywhere a lambda is, including inside another function.

Rationalizations that do not fly here:

- "The lambda is a one-liner and the `Protocol` already states the types, so a
  `# pyright: ignore[reportUnknownLambdaType]` is proportionate" - the `Protocol` types the
  PARAMETER the callable is assigned to, never the lambda's own parameters, which is why the
  checker cannot see them; the ignore suppresses a real gap rather than closing it, and the `def`
  is the same number of lines.
- "Just a per-file `reportUnknownMemberType = false` (or scattered `# pyright: ignore`) for the CLI
  glue, plus a ticket" - a per-file rule-off blinds every future line in that file to real
  unknown-type bugs, and the ticket has no forcing function; the facade is written ONCE and every
  call site inherits it, which is fewer edits than scattering ignores.
- "It is a third-party stub gap, not my code, so suppressing is fair" - the gap is real, but the
  suppression is YOUR code's permanent blind spot; define the missing types instead, and reserve a
  narrow, commented, rule-specific ignore only for the case a facade genuinely cannot express.
- "Exclude the wiring files - they are just glue" - `exclude` kills strict checking for everything
  in those files; wiring is exactly where an untyped decorator or a wrong-typed option silently
  breaks the CLI. Keep them checked; type the surface.

### Worked example - a RECURSIVE alias on a pre-3.12 floor

The third shape a reader meets, after the stub gap and the lambda: a value type that contains
itself (a JSON document, a config tree, a nested record). The temptation is `Any`, which is a
suppression wearing a type's clothes. Each of the three traps below reports somewhere other than
its cause, so getting it wrong costs a gate cycle per attempt.

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

JsonValue: TypeAlias = (
    str | int | float | bool | Mapping[str, "JsonValue"] | Sequence["JsonValue"] | None
)
```

1. **Quote the SELF-references, not the alias.** `from __future__ import annotations` does not
   help: a `TypeAlias` VALUE is evaluated at runtime, so the name must already exist - it does not
   yet, on the line defining it. Quoting only the recursive uses is what makes the definition
   evaluate to a real union. Quoting the whole value (`JsonValue: TypeAlias = "str | ..."`) also
   type-checks (0 errors on pyright 1.1.380 to 1.1.414), but the alias is then a plain `str` at
   runtime, so anything that inspects it there (`typing.get_args`, a validator built from the
   alias) gets a string, not the union. `type JsonValue = ...` (PEP 695) is the 3.12+ spelling
   and is not available below it.
2. **Import every other name at RUNTIME, never under `TYPE_CHECKING`.** Same reason: the union is
   built when the module loads, so `Mapping` and `Sequence` must really be there. This one fails
   only when the module is imported, so a type-check-only run stays green.
3. **`Mapping`/`Sequence`, never `dict`/`list`.** `dict` is INVARIANT in its value type, so
   `dict[str, dict[str, str]]` is not a `dict[str, JsonValue]` and an ordinary nested value that a
   caller holds in a variable is rejected at a call site that looks plainly correct. `Mapping` is
   covariant in the value type and `Sequence` in its element type, so the same value is accepted.

Measured (pyright 1.1.414 strict, `pythonVersion` 3.10): the form above reports 0 errors. The
`dict`/`list` variant reports `reportArgumentType` when `{"a": {"b": "c"}}` is first bound to a
variable (inferred `dict[str, dict[str, str]]`) and then passed, with pyright naming the mechanism
itself - *Type parameter "_VT@dict" is invariant ... Consider switching from "dict" to "Mapping"
which is covariant in the value type*. The same literal written INLINE in the call is
inferred against the parameter and accepted, so a quick probe with an inline literal hides the
invariance: probe with a typed or inferred variable. Both forms import fine on 3.10, so the
runtime is not what separates them.

Ruff's `RUF036` requires `None` LAST in the union (`None` not at the end of the type union), which
is why the alias ends rather than begins with it.

### Worked example - a stub gap only the oldest-floor pyright cell sees

When only the pyright run with `--pythonversion 3.10` (the floor cell) reports
`reportUnknownMemberType` - *Type of "acquire" is partially unknown ... ->
AcquireReturnProxy[Unknown]* - on a filelock `FileLock`, while the default-version run is clean:
filelock imports `typing.Self` only under `TYPE_CHECKING`, and `typing.Self` does not exist on
3.10, so the return type degrades to `Unknown` on the floor only. A local default-version
run is a false green; reproduce with the floor's `--pythonversion`. Fix it with a `Protocol` for
exactly the part of the lock the code uses, returned from a factory:

```python
from pathlib import Path
from typing import Protocol

from filelock import FileLock


class _ExclusiveLock(Protocol):
    def acquire(self) -> object: ...
    def release(self) -> None: ...


def _exclusive_lock(path: Path) -> _ExclusiveLock:
    return FileLock(str(path), timeout=600)  # assignability is still checked: no cast needed


def rebuild(lock_path: Path) -> None:
    lock = _exclusive_lock(lock_path)
    lock.acquire()
    try:
        ...
    finally:
        lock.release()
```

Annotating the local instead (`lock: _ExclusiveLock = FileLock(...)`) does NOT help: pyright
narrows a declared local to the type of the value assigned, so `lock.acquire()` still resolves on
`FileLock` and stays flagged. The factory's return boundary is what hides the concrete type. A
bare `with FileLock(...):` (no `as`) is not flagged and needs no change. Before calling it done,
re-run pyright at the floor's `--pythonversion` AND at the default version, then the project's
full gate (`make test`): all three clean. Measured (filelock 4.2.4, pyright 1.1.414 strict): on
3.10 the annotated local and a plain `lock = FileLock(...)` are flagged, the factory and the bare
`with` are clean; at the default version all four are clean.

### A burst of strict errors in files you did not touch: look upstream first

When a small change makes pyright strict report many `reportArgumentType` errors - *Argument of
type "object" cannot be assigned to parameter "host" of type "str"* - at call sites in files you
never edited, each one spreading an options mapping into a typed callee (`Client(**opts)`), do
NOT add a cast or a conversion at each call site. Look upstream for a narrowing on the path they
share. The usual cause is a passthrough helper that takes `**kwargs` and re-types them as
`dict[str, object]`: it looks like the careful choice and the annotation itself type-checks, but
every forwarded value becomes `object`, and pyright reports each one where it is SPREAD, naming
the callee's parameter, so the errors read as a call-site problem. Casting at each site multiplies
the damage and buries the cause. Fix the one annotation: type the passthrough as the mapping the
producer actually returns, `Mapping[str, Any]` where the values genuinely vary (a pass-through,
not a value type the code defines), so each spread keeps whatever the callee declares. Measured
(pyright 1.1.414 strict): `Client(**opts)` with `opts: dict[str, object]` reports one
`reportArgumentType` per parameter, with `opts: Mapping[str, Any]` it reports none.

### Worked example - a mutable-state dataclass with `field(default_factory=...)`

When pyright strict reports "Type of x is partially unknown" on `x: set[str] =
field(default_factory=set)` (likewise `dict` or `list`), it inferred `set[Unknown]` from the bare
factory instead of the annotation, so adding the annotation again does nothing. For a class that is
pure mutable state (a registry, a session bucket) rather than a value object, convert it to a plain
class with a typed `__init__` (`self.x: set[str] = set()`), keeping the class and attribute names so
callers and tests are untouched; first confirm nothing uses it AS a dataclass
(`dataclasses.replace`, `asdict`, `fields`). Value objects with immutable defaults stay
dataclasses. Re-run pyright before converting after a pyright upgrade, since a newer release may
infer the type from the annotation.

---

## Rationalizations (pressure-tested; these do not fly)

Forced-choice pressure runs (deadline + sunk cost + green suite + a reviewer's LGTM) produced
exactly these excuses - two baseline subjects shipped incomplete conversions using them:

| Excuse                                                                              | Reality                                                                                                                                                                                                                                                                                                                        |
|-------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| "The remaining dict params are internal helpers - do not gold-plate"                | An internal helper with multiple callers is where an untyped dict is riskiest (shape drift = runtime KeyError). "Internal" names the call site, not an exemption; only a small single-function local dict is exempt.                                                                                                           |
| "The reviewer's LGTM overrode the definition of done"                               | A reviewer comment does not rewrite the mandate you were invoked under. Reframing the unfinished 5/23 as "an explicit, reviewed scope decision" is the capitulation itself, dressed as governance.                                                                                                                             |
| "I'm basically done - the last functions do not matter"                             | Sunk cost makes "basically done" feel true regardless of whether the remainder matters. The DoD was every function; the last mile is mechanical because the hard work is already verified.                                                                                                                                     |
| "Shipping verified-green beats an unverified conversion"                            | The conversion is mechanical and re-verified by the same suite in minutes. This excuse converts a 15-minute completion into a permanent gap.                                                                                                                                                                                   |
| "Converting under deadline pressure is riskier - ship the gap, finish next release" | Maybe - but that trade is the HUMAN's to make, not yours. Surface the DoD-vs-deadline conflict explicitly and ASK ("ship 18/23 now, or slip the window?"); a unilateral "ship partial, track the rest" is silent downscoping of the mandate you were invoked under.                                                            |
| "A StrEnum on the wire is risky - keep a shim accepting both"                       | StrEnum members ARE str: the wire bytes are identical. The shim adds no safety, silently swallows stray raw strings, and becomes permanent. Pin the wire value with a test instead. (True for `enum.StrEnum`. The `class X(str, Enum)` fallback formats as `C.A` on 3.11+ when interpolated - use `.value` there, not a shim.) |
| "The enum conversion is code-only - no test churn"                                  | It changes the function's contract: validation moves to the boundary. `grep -rn <func_name> tests/` first - a raises-`ValueError` test, or a raw-string call into an identity (`is`) dispatch, breaks. See "Converting a `str` parameter to an Enum changes its contract".                                                     |
| "Enum internally, but DB/API stay raw strings - feels safer"                        | That leaves the write path and response body - where a status typo causes the incident - unprotected. Backwards.                                                                                                                                                                                                               |
| "Tests pass, so the conversion chain does not matter"                               | The defect is architectural, not behavioral - "tests pass" was never in question. Green tests do not make Model->dict->Model round-trips acceptable.                                                                                                                                                                           |
| "0 violations and the gate is green, so behaviour is unchanged"                     | The suite tests the NEW path. Moving validation into a model changes who raises: exception type, exit code, message wording and redaction - and no existing test pins those for the old entry point. Run the STEP C item 5 diff.                                                                                               |
| "TODO + follow-up ticket, clean it after the demo"                                  | A TODO on shipped code has no forcing function. If a genuine freeze (a live demo in minutes) blocks the fix, do it immediately AFTER in the SAME working session - never a ticket.                                                                                                                                             |

Catch yourself forming these phrases mid-run - "basically done", "internal helpers are fine",
"tests are green so it's correct", "feels safer to accept both", "we'll get it later", "the
reviewer signed off" - and treat the phrase itself as the signal to continue the loop instead
of stopping.

## Execution Summary

```
1. INIT: Read files, read pyproject.toml, create todos, create .data_arch_violations.json
2. LOOP: Parallel analyze (subagents) -> Update state -> Parallel fix (subagents) -> Re-analyze
3. TEST: Run make test OR pyproject.toml tools (loop until all pass); diff the error surface
   against HEAD and the last release when validation moved (STEP C item 5)
4. VERIFY: Final grep check, confirm state file shows 0 violations
5. DONE: Delete state file, report "[OK] Complete after N passes"
```

**DO NOT STOP** until:
- `.data_arch_violations.json` shows total_violations == 0
- Every `out_of_scope` finding was put to the user once and ruled on (STEP A, SCOPE)
- All tests/linters pass
- The error-surface diff (STEP C item 5) shows no change that is not listed in the CHANGELOG,
  whenever the refactor moved where input is validated
- Final verification finds no remaining REAL violation - judge each grep hit as STEP D
  requires ("a hit is a lead, not proof"); a raw match count is not the gate

**Start now** (this is INITIALIZATION - do all four):
1. Read the target files
2. Read `pyproject.toml` (if it exists) to identify configured tools
3. Use TodoWrite to add one item per target file to the DoD checklist from Instructions step 1
4. Create `.data_arch_violations.json` with initial state

Then enter the MAIN LOOP at STEP A, which begins by reading that state file and
incrementing the pass counter before it launches any subagent.
