---
name: coding-data-architecture
description: Use when refactoring or reviewing code in any language for a strict data architecture - dict or map parameters, raw JSON values passed around inside the app, stringly-typed status or mode values, Model->dict->Model conversion chains, fixed-shape records returned as bare tuples, compatibility shims accepting old formats, or making a data flow type-safe end to end. Routes Python to coding-python-data-architecture and Rust to coding-rust-data-architecture.
---

# Data architecture enforcement (any language)

Typed models at every boundary, typed records inside, enums for every fixed category, one parse
in and one export out. This skill holds the rules, the definition of done and the
analyse-refactor-verify workflow; a language skill adds the mechanisms of its libraries and its
type checker on top.

> Parsing at the boundary is also the input-sanitization edge. What to validate there and
> per-sink output escaping (parametrized SQL, HTML autoescape, shell argv) are in
> `bitranox:coding-input-sanitization`.

## Route by language

| Code under review | Load as well                                                                                                                                              |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Python            | `bitranox:coding-python-data-architecture` (Pydantic, enums, datetimes, pyright facades; layered boundaries: `bitranox:coding-python-clean-architecture`) |
| Rust              | `bitranox:coding-rust-data-architecture` (newtypes, closed enums, serde and binary parsing)                                                               |
| anything else     | nothing: this skill alone                                                                                                                                 |

Where this text says "the language skill" (gate commands, candidate grep patterns, how a baseline
arm runs its own code) and no language skill exists, take each from the project itself: its own
test gate, its type checker in its strictest mode, and a grep for the map, untyped-JSON and tuple
types of that language.

---

## Architecture Rules

### Core Principles

1. **Typed model at every boundary**: all external data (API requests, file reads, environment
   variables, CLI arguments, queue messages) is parsed into a validated model immediately on entry
2. **Typed export**: all outputs (API responses, file writes, serialization) are produced by the
   model's own serializer. On a wire that already exists, a new serializer changes bytes and error
   types: byte-compare the old and new output, and the exceptions each raises, before swapping one
   (the language skill lists the known differences)
3. **No internal maps**: inside the application, never pass raw dicts, maps or untyped JSON values
   for structured data - always typed records. The two kinds listed under **Exceptions** in the
   Instructions checklist are exempt
4. **Enums for constants**: every literal standing for a category, status, mode or other fixed
   value is an enum. For a value that crosses a boundary as a string, use an enum whose wire form
   IS that string, so parsing and serializing do not change the wire; reserve integer enums for
   values that are integers on the wire. Check how your language renders a member when it is
   interpolated into a string: in some it is the value, in others the member name. A value
   someone else defines (a protocol code, a peer's field) may arrive in an open type that keeps
   unknown values; every decision is taken on a closed enum converted from it at the parse
   step, and the open value travels further only where it must be stored, forwarded or
   written back unchanged
5. **Minimize conversions**: ideal flow is ONE parse at input, ONE export at output - nothing in
   between. Decoding into a wire record and converting that once into the domain type, inside
   the boundary, counts as that one parse
6. **String-to-enum at edges only**: convert strings to enums only at system boundaries (input
   parsing). Every function and method accepts and uses the enum type - never convert
   string-to-enum inside business logic. This mirrors the model rule: parse once at entry, use
   typed values throughout
7. **No compatibility shims**: no wrapper methods, aliases or backward-compatibility layers that
   accept old formats; code uses the record fields and enums directly. One case is a boundary,
   not a shim: a wire format the system MUST still read (a peer's, data already persisted) gets
   its own versioned wire record, converted once into the domain type, and every old-format
   alias or default lives on that record only, never on the domain type. A format nothing reads
   any more is deleted, record and all

### Validated type or plain record

Use the VALIDATED model type (the one that parses, refuses and serializes) for anything that
crosses a boundary or needs validation. Inside the application, a plain typed record (a struct, a
dataclass, a record class) is enough where nothing is serialized or validated. Never convert a
validated model into a plain record and back again: keep the validated type throughout when it is
already there. A small fixed-shape value object (a coordinate, a host and zone pair) is a named
record type, not a bare tuple.

### Anti-Patterns to Eliminate

- A dict or map parameter or return value carrying structured data
- A string literal compared in logic for a status or mode (`status == "active"`)
- A Model -> map -> Model conversion chain
- Converting a model to a map just to read one field
- Validated model -> plain record -> validated model
- A fixed-shape record returned as a bare tuple across a function boundary (which slot is
  which?). Not this pattern: an OS address tuple the socket API takes and returns, a tuple that
  never leaves one function, and a variable-length sequence of one type
- A string parameter whose every caller passes one of a few literals. It is found by its CALLERS,
  not its signature: grep the call sites, and when every one passes a literal from a small fixed
  set, the parameter is an enum. Converting it changes the function's contract (validation moves
  to the boundary), so grep the function's tests first: a test asserting the function raises on an
  invalid value, or a raw string passed into an identity comparison, breaks
- A Model -> map -> Model round trip that exists only to RE-VALIDATE a copied-and-updated model.
  Replace it with the validation library's own revalidation, never with calls into its internals
  (the language skill names the setting)
- A refusal that interpolates the validation library's error text. It hands the caller the
  library's internal tags, versioned docs URLs and a slice of their own input. Emit your own
  sentence plus one `<dotted location>: <reason>` line per validation error, and keep the original
  exception as the cause

### Declare what the consumer must DISTINGUISH, not only what the old code read

When a typed model replaces a hand-rolled walk over external JSON (a chain of `.get()` calls, map
lookups), the old field list records what the old code looked at, not what it needed. For each
decision the consumer makes on the parsed data, ask what it must tell apart and whether the source
exposes a field for it that the walk dropped; declare that field and filter on it. A faithful
migration carries the latent bug forward. Example: a model of `uv python list --output-format
json` declaring only `version` and `version_parts` keeps an implementation-blind "newest installed
patch" pick: a PyPy build with a higher patch is reported as newest, and a free-threaded build of
the same patch cannot be told apart from the default one. The listing exposes both discriminators
(`implementation`, `variant`), so a migration that declares only what the old walk read drops
them.

### When the decision is "which X will tool T pick", ask T, do not re-derive T's choice

Declaring more discriminators and filtering T's listing re-implements T's selection rules and stays
wrong wherever T applies a rule the listing does not show. The `uv python list` pick above is that
case even with every discriminator declared: `uv venv --python X.Y` chooses by
`python-preference` (env, `uv.toml`, `[tool.uv]`) and discovery order, not by newest patch, so
under `UV_PYTHON_PREFERENCE=system` it built on the distro 3.14.4 while the listing's newest was
3.14.8, and a check comparing the venv with the listing rebuilt it on every run. The fix is to ask
uv: `uv python find --system --no-python-downloads --show-version 3.14` printed the version
`uv venv --python 3.14` built on in all six cells measured (uv 0.13.0, preference
unset/managed/system, with and without an active `VIRTUAL_ENV`); without `--system` it answers
with the current venv. Look for such a query command (`find`, `--dry-run`, `--print-*`,
`--show-*`) before modelling a listing.

---

## Define the types; never suppress or exclude the checker

The discipline that forbids stringly-typed values also forbids silencing the type checker or the
linter. When a strict checker flags your code - very often a gap in a third-party library's type
information, not a real defect - the completion path is to DEFINE the missing types, not to
suppress the diagnostic or exclude the file.

Order of preference:

1. Add the real annotation, type argument or type.
2. Wrap a partially-typed third-party symbol in a typed facade you define (an interface plus a
   checked conversion, a factory whose declared return type is that interface, or a local stub of
   the library's types) so every call site sees complete types.
3. Only if neither is feasible, a NARROW, rule-specific suppression on the one line, with a comment
   naming WHY and the condition for removing it. Never reach first for a rule switched off for a
   file or a project, an exclude entry, or a bare blanket suppression: those blind the same scope
   to real errors too, and rot silently.

The language skill has the checker's exact spellings and worked examples.

---

## Instructions

1. **Create a Todo List** with the following Definition of Done (DoD) items to track refactoring
   progress:

   **Input/Output Boundaries:**
   - [ ] Parse all external inputs into validated models at system boundaries
   - [ ] Produce all outputs through the model's own serializer
   - [ ] Each boundary model that replaced a `.get()` walk declares every field the consumer must
     distinguish, not only the fields the old code read (step 3), and a test feeds it an input
     where that field decides the answer
   - [ ] Your own new and rewritten code got the same adversarial read as the code you set out to
     fix: a faithful port passes every existing test while keeping the old bug

   **Internal Data Handling:**
   - [ ] Eliminate all internal map processing - no `data["key"]` access on structured data
   - [ ] All functions and methods use typed fields of models or records
   - [ ] A plain record is used only for pure internal logic with no serialization needs

   **Type Safety:**
   - [ ] Replace all string literals (statuses, modes, categories) with enums
   - [ ] Ensure all function signatures use typed models, not maps

   **Conversion Optimization:**
   - [ ] Remove redundant Model->map->Model chains
   - [ ] Eliminate validated-model -> plain-record -> validated-model conversions
   - [ ] Verify minimum conversions: ideally 1 at input, 1 at output

   **Exceptions:**
   - [ ] Small local maps (few items, single function scope) may remain - convert if used across
     functions or modules
   - [ ] A lookup table keyed by a closed enum may remain at any scope when ALL four hold: it is
     read-only; its key type is the enum itself; its value type is fully typed (no "any", no
     top type); and a test pins that every member has an entry (the table's key set equals the
     enum's member set). Read-only means the declared type is a read-only mapping, the value built
     is immutable so the type checker refuses a write through it, and nothing writes to it after it
     is built. Missing any one of the four, it is a violation: add the missing property or convert
     the table. A table keyed by string spellings of an enum's values is not this exception - key
     it by the enum

   **Verification:**
   - [ ] Run the project's full gate (the language skill names it) - fix all errors until passing
   - [ ] Verify the type checker passes and the boundary models validate and refuse as intended
   - [ ] If the refactor moved WHERE input is validated: every single-fault input the old code
     refused keeps its exception type, exit code and message, or each change is listed in the
     CHANGELOG (STEP C item 5)

2. **Analyze the Code** and identify violations:
   - Functions accepting map parameters instead of typed models
   - Raw map key access (`data["key"]`) instead of field access (`data.key`)
   - String literals used as identifiers, modes or status values
   - String parameters of a function called from another function or module whose call sites all
     pass literals from a small fixed set (grep the callers; the signature alone looks fine)
   - Fixed-shape records returned as bare tuples across a function boundary, with the exclusions
     under "Anti-Patterns to Eliminate"
   - Unnecessary conversions between maps and records
   - Missing validated models at input boundaries, missing model serializers at output boundaries
   - **Unnecessary data conversions** - AGGRESSIVELY detect and eliminate:
     * Model -> map -> Model chains (pass the model directly)
     * Several serializations of the same object
     * Converting to a map just to access fields
     * Redundant serialization/deserialization cycles
     * Intermediate map structures that serve no purpose
     * Validated model <-> plain record conversions: use the validated model throughout, and
       remove compatibility shims between the forms
     * Any conversion that does not add value - minimize total conversions
     * **Count total conversions** in the data flow - goal is the MINIMUM possible (ideally: 1 at
       input, 1 at output)
     * **Enum usage**: use the enum member directly in comparisons and assignments; avoid
       needless conversions to the raw value, except where the language skill says the raw value
       is required (string interpolation, for one)

3. **Refactor the Code** following these rules:
   - Import external data immediately into validated models
   - Export data through the model's own serializer
   - Never create or handle internal map structures; convert map inputs to models as early as
     possible
   - All functions operate on typed records or model fields
   - **Minimize total conversions** - count them, ideal is ONE at the input boundary, ONE at the
     output boundary
   - Replace fixed string sets with enums
   - Declare what the consumer must DISTINGUISH, and ask the tool rather than re-deriving its
     choice (both under "Architecture Rules")

4. **Mark Todo Items Complete** as each DoD criterion is satisfied.

## Workflow

**CRITICAL: This is an iterative process. You MUST loop until ZERO violations remain. Do NOT stop
early.**

**State is tracked in `.data_arch_violations.json` - always read before and write after each
phase.** The language skill supplies the gate commands, the candidate grep patterns, the tool
config to read at INITIALIZATION, and how to run a baseline's own code for the error-surface diff.

```
INITIALIZATION:
  1. Read all target files
  2. Read the project's tool configuration to identify configured tools (the language skill
     names the file)
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
         "path/to/file": {
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
       * The violation patterns to search for (from Architecture Rules above, plus the language
         skill's patterns)
       * The patterns that are NOT violations, spelled out - a small single-function local
         map, a free-form external JSON envelope, and DYNAMICALLY-keyed maps (queue index to
         count, metric name to value, MAC to address); for tuples, an OS address tuple, a local
         gather closure and a variable-length sequence; at the boundary, an open type for a
         value someone else defines (Core Principle 4), a wire record plus its one conversion
         into the domain type (Principle 5) and a versioned wire record for a format still read
         (Principle 7), plus the language skill's own list. Without this an analyser reports every
         string-keyed map it sees, and you spend the loop re-judging its false positives.
         Parameter ORDER is not a data-structure finding either: two positional parameters of
         the same type are a keyword-only style question, so keep the brief to records and
         values, or an analyser asked for "same-type pairs" reports function signatures.
       * The CALL-SITE SWEEP, named as a required step: for every string parameter of a function
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
     - Run your own CANDIDATE SWEEP beside the agents with the language skill's grep patterns over
       the target files, and hold each hit against the agents' verdicts. A file reported clean
       that holds an unjudged hit goes back to an analyser with the hit named. An all-clean
       verdict returned in seconds cannot be told from a blind one; the sweep tells them apart.
       Measured: 9 analysers called 46 of 49 modules clean, and a grep for tuple return
       annotations found 13 fixed-shape tuple records none of them had flagged.
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
       anything. This refactor is not per-file independent: an enum lives in one module and a
       model in another, so several agents will reach for the SAME shared file. Give each
       shared file exactly ONE owner (or edit it yourself first and let the others only
       import from it). Measured: three agents editing one checkout in parallel produced a
       transient test failure from a half-written sibling edit, and one agent had to re-read
       files before every write to avoid clobbering another's work.
     - Launch subagents (Task tool, subagent_type="general-purpose", model="opus") in PARALLEL,
       one per file SET (per-file refactor is bounded judgment, an `opus` job; pin the tier)
     - Each subagent prompt MUST include:
       * The full Architecture Rules section (copy from this document and the language skill)
       * The specific violations for that file (from state file)
       * The EXPLICIT list of files it may touch, and a statement that other agents are
         editing the rest of the repo concurrently so it must not edit anything outside that
         list. An agent that finds a needed fix in someone else's file REPORTS it instead of
         making it - that hand-off is how the last error gets found, not a failure.
       * Instruction not to delete a public name other modules may still read: it leaves an
         alias pointing at the new enum member and lists it under `hand_offs`. The coordinator
         greps the WHOLE repo for readers, moves them, then deletes the alias and any comment
         that introduced the alias block before STEP C (Core Principle 7: no code alias
         outlives the run; a wire-format alias on a versioned wire record is that principle's
         boundary case). A reader grep scoped to part of the tree misses a caller and fails
         collection.
       * When rows move onto a strict boundary model, instruction to validate only the rows that
         survive the skip/filter decision (type and size checks first, full parse after), with
         a test each way: a skipped row holding an unrepresentable value stays skipped, a kept
         one is refused. Validating every row first turns a row the old code skipped into an
         aborted load, and a live run on clean data cannot show it.
       * Instruction to fix ALL violations
       * Instruction NOT to read or write `.data_arch_violations.json`: the coordinator owns it
         and writes it from the returned JSON (below)
       * **Instruction to run the TYPE CHECKER as well as the tests, and to report the error
         count.** Tests alone cannot verify this refactor: an enum whose members compare and
         hash equal to their raw values, or a named record that compares equal to the tuple it
         replaced, keeps every call site still passing the raw value, and every assertion on it,
         green wherever the code compares by value rather than by identity, while the type
         checker errors on the changed signature. Measured: three agents each reported "731
         passed" while the type checker had 24 errors, all of them call sites still passing raw
         literals into newly enum-typed parameters.
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
       that turns a string parameter into an enum edits the enums module and every caller; with
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

  1-3. Run the project's full gate with the Bash tool - the language skill names the commands
       (a Makefile `test` target first, else the configured tools).

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
     - the exception TYPE, and through a CLI wrapper the EXIT CODE (an HTTP STATUS for a web
       endpoint) - the validation library's
       error, or the framework error you wrap it in, is not the error the old call raised;
     - the MESSAGE - the library adds its own error-type tags and docs links, and a model that
       redacts secret-bearing fields hides a value the old message quoted;
     - the ORDER - with several faults in one input, the setting the boundary checks first is
       now the one reported.
     Check it two ways:
     a. Read every doc that promises an error contract and hold the new code to it:
        `grep -rniE 'exit code|raises|refused' docs/ README*`
     b. Run ONE malformed value at a time through the real entry point of a baseline and of the
        working tree, and diff exception type / exit code / last error line per input. Use TWO
        baselines, HEAD and the LAST RELEASE tag: a change committed earlier in the same refactor
        is invisible against HEAD. Get each baseline's source without touching the checkout
        (`git archive <HEAD or tag> | tar -x -C <tmpdir>`), and prove each arm runs its OWN code
        before comparing (the language skill says how; an arm that silently imports the working
        tree reads "same" for every input). Feed wrong-TYPE values beside out-of-range ones (a
        boolean for a count, a string for a timeout, a float for an integer): a lenient parser
        accepts them silently. Mark one input whose result you changed on purpose as the LIVENESS
        CONTROL: if it does not show up as different, the harness is broken, not the code.
        Measured: a harness whose arms both imported the working tree reported 20 of 20 inputs
        "same", and only the control exposed it; the harness against the last release found a
        request model still accepting a boolean count and a string timeout after five analysis
        passes, and four behaviour changes the CHANGELOG did not list.
     Every single-fault input the old code refused keeps its type, exit code and message, or the
     change is listed in the CHANGELOG with the input, the old result and the new one. An input
     the old code ACCEPTED and the boundary now refuses (an unknown mode that used to fall through
     to a default branch) is such a change too, and is listed the same way. To keep
     it, re-raise the model's refusal as the old exception type carrying the validator's own text
     (one line per error when there are several), and run a check ahead of the model where the
     model would redact what the old message quoted. Multi-fault ORDER is inherent to parsing at
     the boundary: document it, do not fight it.

  >>> DO NOT proceed to STEP D until all tests/linters pass and the error-surface diff shows no
      unlisted change

STEP D - FINAL VERIFICATION:
  - Read `.data_arch_violations.json` and confirm total_violations == 0
  - Grep only to surface candidates, with the language skill's patterns (map-typed parameters and
    returns, tuple returns, module-level tables). A hit is a lead, not proof - the patterns also
    match the permitted small local maps and enum-keyed lookup tables (both under the Exceptions
    rule) and annotations that are not signatures at all. Judge each hit against the Exceptions
    rule, the exclusions under "Anti-Patterns to Eliminate" and the NOT-violations STEP A's
    brief carries (its own and the language skill's); do NOT auto-loop on raw match count.
  - Write one verdict line per hit, `<file:line> real|permitted - <reason>`, where a permitted
    hit names the exclusion it falls under. A hit that fits no named exclusion is real, whatever
    the analysers reported for its file: reaching STEP D means they already called every file
    clean, so their zero is not evidence about any hit you are looking at.
  - If a real violation is found: attribute it under STEP A's SCOPE rule. Out of scope, it joins
    `out_of_scope` and goes to the user. In scope, add it to `.data_arch_violations.json` as a
    violation of its file (status `in_progress`, the line and your reason as its description)
    and GOTO STEP B. Not STEP A: its analysers already passed that line as clean, and their fresh
    results would replace the entry you just wrote. STEP B's own loop back to STEP A re-checks
    the fix.
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
5. **ALWAYS run STEP C** - execute the project's full gate
6. Do NOT proceed to STEP D until all tests pass
7. Delete state file only after successful completion

**LOOP ENFORCEMENT:**
```
STEP A -> found violations? -> STEP B -> STEP A (again!)
STEP A -> no violations? -> STEP C (run the gate!) -> STEP D -> DONE
STEP D -> real violation in scope? -> recorded in the state file -> STEP B -> STEP A
```

**Subagent Prompt Templates:**

Analysis subagent (`model: "opus"`, `effort: "medium"` - review dispatch, see
bitranox:process-agents-subagent-driven-development "Review dispatches"):
```
Analyze {file_path} for data architecture violations:
- map/dict parameters and return values carrying structured data
- map key access on structured data (`["key"]`)
- string literals for statuses/modes compared in logic
- fixed-shape records returned as bare tuples; NOT an OS address tuple, a local gather
  closure, or a variable-length sequence
- missing validated models at boundaries
- unnecessary Model->map->Model conversions
{the language skill's patterns}

Call-site sweep (required): for every string parameter of a function called from another
function or module, grep its call sites across the repo; report it when every caller passes a
literal from a small fixed set.

Return JSON only: {"file": "{file_path}", "sweep": {"tuple_returns": N, "str_params": N,
"literal_only": N}, "violations": [{"line": N, "type": "...", "description": "..."}]}
```

Refactoring subagent:
```
Fix these violations in your file set ({file_set}):
{violations_list}

Rules: [paste the Architecture Rules sections of this skill and the language skill]

You may edit only: {file_set}. Other agents are editing the rest of the repo; report a needed
fix elsewhere as a hand-off instead of making it. Do not read or write
`.data_arch_violations.json` - the coordinator writes it from your reply.

Fix ALL violations, then run the type checker as well as the tests and report its error count.
Return JSON and nothing else, one "files" entry per file in your set:
{"files": {"<path>": {"fixed": [...], "remaining": [...]}},
 "hand_offs": [{"file": "...", "line": N, "description": "..."}], "type_errors": N}
```

---

## Rationalizations (pressure-tested; these do not fly)

Forced-choice pressure runs (deadline + sunk cost + green suite + a reviewer's LGTM) produced
exactly these excuses - two baseline subjects shipped incomplete conversions using them:

| Excuse                                                                              | Reality                                                                                                                                                                                                                                                             |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| "The remaining dict params are internal helpers - do not gold-plate"                | An internal helper with multiple callers is where an untyped map is riskiest (shape drift = runtime KeyError). "Internal" names the call site, not an exemption; only a small single-function local map is exempt.                                                  |
| "The reviewer's LGTM overrode the definition of done"                               | A reviewer comment does not rewrite the mandate you were invoked under. Reframing the unfinished 5/23 as "an explicit, reviewed scope decision" is the capitulation itself, dressed as governance.                                                                  |
| "I'm basically done - the last functions do not matter"                             | Sunk cost makes "basically done" feel true regardless of whether the remainder matters. The DoD was every function; the last mile is mechanical because the hard work is already verified.                                                                          |
| "Shipping verified-green beats an unverified conversion"                            | The conversion is mechanical and re-verified by the same suite in minutes. This excuse converts a 15-minute completion into a permanent gap.                                                                                                                        |
| "Converting under deadline pressure is riskier - ship the gap, finish next release" | Maybe - but that trade is the HUMAN's to make, not yours. Surface the DoD-vs-deadline conflict explicitly and ASK ("ship 18/23 now, or slip the window?"); a unilateral "ship partial, track the rest" is silent downscoping of the mandate you were invoked under. |
| "The enum conversion is code-only - no test churn"                                  | It changes the function's contract: validation moves to the boundary. Grep the function's tests first - a test asserting it raises on an invalid value, or a raw string passed into an identity comparison, breaks.                                                 |
| "Enum internally, but DB/API stay raw strings - feels safer"                        | That leaves the write path and response body - where a status typo causes the incident - unprotected. Backwards.                                                                                                                                                    |
| "Tests pass, so the conversion chain does not matter"                               | The defect is architectural, not behavioral - "tests pass" was never in question. Green tests do not make Model->map->Model round-trips acceptable.                                                                                                                 |
| "0 violations and the gate is green, so behaviour is unchanged"                     | The suite tests the NEW path. Moving validation into a model changes who raises: exception type, exit code, message wording and redaction - and no existing test pins those for the old entry point. Run the STEP C item 5 diff.                                    |
| "TODO + follow-up ticket, clean it after the demo"                                  | A TODO on shipped code has no forcing function. If a genuine freeze (a live demo in minutes) blocks the fix, do it immediately AFTER in the SAME working session - never a ticket.                                                                                  |

Catch yourself forming these phrases mid-run - "basically done", "internal helpers are fine",
"tests are green so it's correct", "feels safer to accept both", "we'll get it later", "the
reviewer signed off" - and treat the phrase itself as the signal to continue the loop instead
of stopping.

## Execution Summary

```
1. INIT: Read files, read the tool config, create todos, create .data_arch_violations.json
2. LOOP: Parallel analyze (subagents) -> Update state -> Parallel fix (subagents) -> Re-analyze
3. TEST: Run the project's full gate (loop until all pass); diff the error surface against HEAD
   and the last release when validation moved (STEP C item 5)
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
2. Read the project's tool configuration (if it exists) to identify configured tools
3. Use TodoWrite to add one item per target file to the DoD checklist from Instructions step 1
4. Create `.data_arch_violations.json` with initial state

Then enter the MAIN LOOP at STEP A, which begins by reading that state file and
incrementing the pass counter before it launches any subagent.
