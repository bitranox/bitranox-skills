---
name: coding-python-enforce-data-architecture-strict
description: Use when refactoring or reviewing Python code to enforce a strict data architecture - Pydantic models at every external boundary, typed models (never raw dicts) inside the app, Enums/IntEnum for all fixed string values, and minimal input-to-output conversions. Use when asked to eliminate dict parameters, stringly-typed status/mode values, Model->dict->Model conversion chains, or compatibility shims, or to make a Python data flow type-safe end to end.
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
4. **Enums for Constants**: All string literals representing categories, statuses, modes, or fixed values must be Enums. For values that cross an external boundary as strings, use `StrEnum` (Python 3.11+) or `class X(str, Enum)` so Pydantic parses and serializes them without changing the wire format; reserve `IntEnum` for values that are genuinely integers on the wire.
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
```

---

## Instructions

1. **Create a Todo List** with the following Definition of Done (DoD) items to track refactoring progress:

   **Input/Output Boundaries:**
   - [ ] Parse all external inputs into Pydantic models at system boundaries
   - [ ] Produce all outputs through Pydantic export methods (`.model_dump()`, `.model_dump_json()`)

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

2. **Analyze the Code** and identify violations:
   - Functions accepting `dict` parameters instead of typed models
   - Raw dict key access (`data["key"]`) instead of field access (`data.key`)
   - String literals used as identifiers, modes, or status values
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
     * **Enum usage**: Use `StrEnum`/`str, Enum` for string-valued fields and `IntEnum` only for integer-valued ones. Avoid unnecessary `.value` access or conversions - use the enum member directly in comparisons and assignments. Remove compatibility shims for enums (no wrapper methods, aliases, or backward-compatibility layers)

3. **Refactor the Code** following these rules:
   - Import external data immediately into Pydantic models with validation
   - Export data using Pydantic's built-in dump methods
   - **Prefer Pydantic over dataclass** - only use `@dataclass` when there's a clear benefit and no Pydantic conversion needed
   - If you see Pydantic -> dataclass -> Pydantic, eliminate the dataclass and use Pydantic throughout
   - Never create or handle internal dict structures
   - Convert dict inputs to dataclasses as early as possible
   - All functions must operate on dataclasses or Pydantic fields
   - **Minimize total conversions** - count them, ideal is ONE at input boundary, ONE at output boundary
   - Replace fixed string sets with `Enum` classes

4. **Mark Todo Items Complete** as each DoD criterion is satisfied.

## Workflow

**CRITICAL: This is an iterative process. You MUST loop until ZERO violations remain. Do NOT stop early.**

**State is tracked in `.data_arch_violations.json` - always read before and write after each phase.**

```
INITIALIZATION:
  1. Read all target files
  2. Read pyproject.toml (if exists) to identify configured tools
  3. Use TodoWrite to create checklist with one item per file
  4. Create state file `.data_arch_violations.json`:
     {
       "pass": 0,
       "total_violations": 0,
       "files": {
         "path/to/file.py": {
           "violations": [],
           "status": "pending"  // pending | in_progress | clean
         }
       }
     }

================================================================================
|  MAIN LOOP - REPEAT STEPS A->B UNTIL total_violations == 0                    |
================================================================================

  STEP A - PARALLEL ANALYSIS (use subagents):
     - Read `.data_arch_violations.json`
     - Increment "pass" counter
     - Launch subagents (Task tool, subagent_type="Explore", model="sonnet") in PARALLEL for each file
       (pin the tier; per-file scanning is bounded sonnet work - see "Concrete tiers" in
       bitranox:process-agents-subagent-driven-development)
     - Each subagent prompt MUST include:
       * The file path to analyze
       * The violation patterns to search for (from Architecture Rules above)
       * Instruction to return JSON: {"file": "path", "violations": [{"line": N, "type": "...", "description": "..."}]}
     - Collect all subagent results
     - Update `.data_arch_violations.json` with violations from each subagent
     - Calculate total_violations = sum of all violations across files

     >>> If total_violations == 0: EXIT LOOP, GOTO STEP C
     >>> If total_violations > 0: CONTINUE TO STEP B

  STEP B - PARALLEL REFACTORING (use subagents):
     - Read `.data_arch_violations.json`
     - For files with violations, launch subagents (Task tool, subagent_type="general-purpose", model="sonnet") in PARALLEL
       (per-file refactor is bounded sonnet work; pin the tier)
     - Each subagent prompt MUST include:
       * The full Architecture Rules section (copy from this document)
       * The specific violations for that file (from state file)
       * The state file path: `.data_arch_violations.json`
       * Instruction to fix ALL violations
       * Instruction to UPDATE the state file after fixing:
         - Set file status to "in_progress"
         - Clear the violations array for that file
         - Decrement total_violations by number of fixed violations
       * Instruction to return: {"file": "path", "fixed": ["violation1", ...], "remaining": [...]}
     - After all subagents complete: Read state file and verify updates

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

  >>> DO NOT proceed to STEP D until all tests/linters pass

STEP D - FINAL VERIFICATION:
  - Read `.data_arch_violations.json` and confirm total_violations == 0
  - Grep only to surface candidates: `-> dict`, `: dict` in signatures. A hit is a lead, not
    proof - a bare `== "..."` matches legitimate string comparisons and the permitted small
    local dicts. Judge each hit against the Exceptions rule; do NOT auto-loop on raw match count.
  - If a real violation is found: GOTO STEP A
  - If clean:
    * Update state file: all files status = "clean"
    * Delete `.data_arch_violations.json`
    * Mark todos complete
    * Report: "[OK] Complete after {pass} passes - all violations fixed - tests passing"
```

**IMPORTANT RULES:**
1. ALWAYS read state file before each step
2. ALWAYS write state file after each step
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

Analysis subagent:
```
Analyze {file_path} for data architecture violations:
- dict parameters (`: dict`, `-> dict`)
- dict key access (`["key"]`, `['key']`)
- string literals for statuses/modes (`== "..."`, `!= "..."`)
- missing Pydantic at boundaries
- unnecessary Model->dict->Model conversions

Return JSON only: {"file": "{file_path}", "violations": [{"line": N, "type": "...", "description": "..."}]}
```

Refactoring subagent:
```
Fix these violations in {file_path}:
{violations_list}

Rules: [paste Architecture Rules section]

After fixing:
1. Read `.data_arch_violations.json`
2. Update the entry for {file_path}:
   - Set "status": "in_progress"
   - Set "violations": [] (or list remaining if any)
3. Recalculate "total_violations" as sum of all violations arrays
4. Write updated state back to `.data_arch_violations.json`

Fix ALL violations. Return JSON: {"file": "{file_path}", "fixed": [...], "remaining": [...]}
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

## Rationalizations (pressure-tested; these do not fly)

Forced-choice pressure runs (deadline + sunk cost + green suite + a reviewer's LGTM) produced
exactly these excuses - two baseline subjects shipped incomplete conversions using them:

| Excuse                                                              | Reality                                                                                                                                                 |
|----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| "The remaining dict params are internal helpers - do not gold-plate" | An internal helper with multiple callers is where an untyped dict is riskiest (shape drift = runtime KeyError). "Internal" names the call site, not an exemption; only a small single-function local dict is exempt. |
| "The reviewer's LGTM overrode the definition of done"               | A reviewer comment does not rewrite the mandate you were invoked under. Reframing the unfinished 5/23 as "an explicit, reviewed scope decision" is the capitulation itself, dressed as governance. |
| "I'm basically done - the last functions do not matter"             | Sunk cost makes "basically done" feel true regardless of whether the remainder matters. The DoD was every function; the last mile is mechanical because the hard work is already verified.       |
| "Shipping verified-green beats an unverified conversion"            | The conversion is mechanical and re-verified by the same suite in minutes. This excuse converts a 15-minute completion into a permanent gap.            |
| "Converting under deadline pressure is riskier - ship the gap, finish next release" | Maybe - but that trade is the HUMAN's to make, not yours. Surface the DoD-vs-deadline conflict explicitly and ASK ("ship 18/23 now, or slip the window?"); a unilateral "ship partial, track the rest" is silent downscoping of the mandate you were invoked under. |
| "A StrEnum on the wire is risky - keep a shim accepting both"       | StrEnum members ARE str: the wire bytes are identical. The shim adds no safety, silently swallows stray raw strings, and becomes permanent. Pin the wire value with a test instead.              |
| "Enum internally, but DB/API stay raw strings - feels safer"        | That leaves the write path and response body - where a status typo causes the incident - unprotected. Backwards.                                        |
| "Tests pass, so the conversion chain does not matter"               | The defect is architectural, not behavioral - "tests pass" was never in question. Green tests do not make Model->dict->Model round-trips acceptable.    |
| "TODO + follow-up ticket, clean it after the demo"                  | A TODO on shipped code has no forcing function. If a genuine freeze (a live demo in minutes) blocks the fix, do it immediately AFTER in the SAME working session - never a ticket.               |

Catch yourself forming these phrases mid-run - "basically done", "internal helpers are fine",
"tests are green so it's correct", "feels safer to accept both", "we'll get it later", "the
reviewer signed off" - and treat the phrase itself as the signal to continue the loop instead
of stopping.

## Execution Summary

```
1. INIT: Read files, read pyproject.toml, create todos, create .data_arch_violations.json
2. LOOP: Parallel analyze (subagents) -> Update state -> Parallel fix (subagents) -> Re-analyze
3. TEST: Run make test OR pyproject.toml tools (loop until all pass)
4. VERIFY: Final grep check, confirm state file shows 0 violations
5. DONE: Delete state file, report "[OK] Complete after N passes"
```

**DO NOT STOP** until:
- `.data_arch_violations.json` shows total_violations == 0
- All tests/linters pass
- Final verification grep finds nothing

**Start now:**
1. Read the target files
2. Create `.data_arch_violations.json` with initial state
3. Launch parallel analysis subagents for STEP A
