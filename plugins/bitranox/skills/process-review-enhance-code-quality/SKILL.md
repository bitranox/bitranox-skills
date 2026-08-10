---
name: process-review-enhance-code-quality
description: Use when asked to rate, score, audit, or improve code quality of a project, when user wants a 0-10 quality assessment, or when asked what needs to change to reach perfect quality
---

# Enhance Code Quality

## Overview

Score a project 0-10, identify issues by severity, walk the user through fixes one-by-one, track decisions in the project instructions file so a declined item is not re-raised while its
reason still holds.

> **Project instructions file** depends on your CLI tool:
> **Claude Code** → `CLAUDE.md` | **Codex** → `AGENTS.md` | **Kilo Code / Windsurf** → equivalent config file.
> This skill uses "CLAUDE.md" as shorthand  -  substitute the correct filename for your environment.

**Core principle:** Respect prior decisions by default, but re-assess them against ground truth. A documented acceptance whose premise no longer holds is surfaced as a propose-first "reconsider" item - never silently skipped, never silently changed. Check before suggesting. Ask before changing.

**Pathfinder:** leave each file better than you found it and accept no technical debt - fix adjacent rot
you can verify, flag (do not silently pass) anything wrong, and route an out-of-scope fix to its own
worktree. See `bitranox:meta-self-improve` ("Pathfinder discipline").

## Workflow

```
1. Read CLAUDE.md / AGENTS.md → collect accepted items
   ┌───────────────────────────────────────────────────────── SWEEP ─────────┐
   │ 2. Run project tools → collect objective data                           │
   │ 3. Score 0-10 with rubric                                               │
   │ 4. Re-assess accepted items vs ground truth                             │
   │ 4b. Walk the aspect checklist - every row, every sweep                  │
   │ 5. Present Issue N                                                      │
   │    ├── yes → 6a. Implement fix ──┐                                      │
   │    └── no  → 6b. Save decline ──┤                                       │
   │                                   ▼                                     │
   │                            More issues in THIS sweep?                   │
   │                            ├── yes → back to 5                          │
   │                            └── no  → end of sweep                       │
   └────────────────────────────┬────────────────────────────────────────────┘
                                ▼
                   Did this sweep find anything, or fix anything?
                   ├── yes → SWEEP AGAIN from 2 (fixes create findings)
                   └── no  → 7. Re-score and report
```

**The outer loop is the point.** One sweep is not a review. Keep sweeping until a sweep that
walked the whole checklist finds nothing and changes nothing; that clean sweep is the exit
condition, not "I presented the issues I noticed".

## Step 1: Read Project Instructions File First

**Before any analysis**, read the **entire** project instructions file (CLAUDE.md / AGENTS.md / equivalent).

**If no project instructions file exists:** Note it and proceed to Step 2 with an empty accepted-items list. After scoring, recommend creating one as a MEDIUM issue if the project would benefit from it.

Collect deliberately accepted items from **all** of these sources:
- The `# Code Quality` section (explicit accepted items list)
- Any phrase like "by design", "intentional", "deliberately", "do not move/change"
- Architecture decisions with documented rationale (e.g., "This design is intentional")
- Dependency decisions (e.g., "Do not move X to optional-dependencies")
- Test scope decisions (e.g., "minimal test coverage by design")

**Read the entire file, not just one section.** Intentional decisions are often documented inline near the relevant architecture description, not only in the "Code Quality" section.

**Respect these by default - do not casually re-litigate a settled decision.** But they are NOT frozen forever: each is RE-ASSESSED against current ground truth in Step 4. Re-open one only when concrete evidence shows its premise no longer holds; absent that, respect it silently (do not re-raise). Never silently CHANGE a documented decision, and never silently SKIP one that ground truth now contradicts.

## Step 2: Run Project Quality Tools

**Before manual scoring**, run whatever quality tooling the project already has. Check for:

- `Makefile` targets: `make test`, `make lint`, or similar
- Project instructions file (CLAUDE.md / AGENTS.md) for test/lint commands.
- Common tools: `ruff check`, `pyright`, `shellcheck`, `eslint`, `pytest`, etc.
- CI config (`.github/workflows/`) for the project's own quality gates

Record tool output (pass/fail, coverage %, lint warnings). Use this objective data to inform Step 3 scoring.

## Step 3: Score With Rubric

For a large project, FAN OUT: dispatch one **`sonnet`** subagent per rubric dimension (each returns its
0-10 score + concrete evidence) in parallel, then one **`opus`** pass to synthesize the weighted total
and adversarially sanity-check the score. Small project: score inline. If that synthesis runs inline on
the main agent and the session is not on `opus`, offer switch-model-or-continue per "The session model
is fixed" in `bitranox:process-agents-subagent-driven-development` (the main agent cannot self-switch its
model). (Tiers: see "Concrete tiers" in the same skill; fan-out pattern: `bitranox:process-agents-dispatching-parallel`.)

Use this rubric to score the project. Each dimension is 0-10, final score is the weighted average.

| Dimension       | Weight | What to Check                                                  |
|-----------------|--------|----------------------------------------------------------------|
| Architecture    | 16%    | Layer separation, dependency direction, SOLID principles       |
| Type Safety     | 15%    | See language-specific criteria below                           |
| Testing         | 20%    | See "Testing is not the coverage number" below                 |
| Error Handling  | 8%     | Consistency, domain exceptions, exit codes                     |
| Security        | 15%    | Input validation/sanitization, secrets handling, dep audit     |
| Resource Safety | 10%    | Bounded memory on large data (stream/chunk, no unbounded load) |
| Documentation   | 8%     | Docstrings/comments, README, inline docs where needed          |
| Maintainability | 8%     | DRY, naming, complexity, readability                           |

**Type Safety by language:**

| Language   | 0-3                                         | 4-6                                        | 7-10                                                     |
|------------|---------------------------------------------|--------------------------------------------|----------------------------------------------------------|
| Python     | No type hints                               | Partial hints, no strict checking          | Full hints, pyright strict, minimal `type: ignore`       |
| Bash       | No input validation, no `set -euo pipefail` | Some validation, inconsistent quoting      | `set -euo pipefail`, all vars quoted, `shellcheck` clean |
| TypeScript | `any` everywhere, no strict                 | Partial strict, some `any`                 | Strict mode, no `any`, proper generics                   |
| JavaScript | No JSDoc, no validation                     | Some JSDoc or TypeScript migration started | Full JSDoc with types, or migrated to TypeScript         |

**A type-checker suppression is not a Type Safety pass - flag it.** A per-file `reportX = false`, an `exclude` entry that drops files from the strict run, or a bare `# type: ignore` blinds the checker to real bugs in that scope; score it as a gap and recommend the fix: DEFINE the missing types (the real annotation, or a typed facade - a `Protocol` plus a `cast`, or a local `.pyi` stub), reserving a narrow rule-specific `# pyright: ignore[rule]` (with a remove-when reason) as the last resort. Pattern and worked example: **bitranox:coding-python-enforce-data-architecture-strict**.

**Testing is not the coverage number - audit the test DESIGN.** Testing carries the heaviest weight
here, and a green suite at high coverage is the single easiest thing to mistake for a pass. Coverage
says which lines RAN, never whether anything would have FAILED. Score the design, using
**bitranox:process-test-design** as the criteria (mock-vs-real, adversarial inputs, determinism,
pruning) - load it for this dimension rather than judging "test quality" ad hoc. Cap Testing at 5
when any of these holds, however green the run:

| Test-design gap            | What it looks like                                                                                                                 |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| Self-mocked internals      | The suite patches the code under test's own methods/module rather than injecting a collaborator at a seam. Fix: make it injectable |
| No integration / e2e proof | Nothing exercises the real DB, HTTP, broker, or filesystem, so the contract is unproven and the mocked path can be flatly broken   |
| Tests that cannot fail     | Asserts nothing, restates the implementation, or asserts on the mock; a call-order assertion over private methods is this          |
| Filler                     | Tests the language, the framework, or a constructor storing its arguments - deletable with nothing lost                            |
| Flaky or order-dependent   | Needs a re-run, a real `sleep`, or a specific execution order; shared mutable state between tests                                  |

**Recommend DELETING low-value tests, do not preserve them.** A test that cannot fail is negative
value: it costs maintenance and buys false confidence. Never propose a type-checker or lint
suppression to keep one alive - that is two gaps, not a fix. Deletions belong in the findings list
like any other change, with the count and the reason.

**The tell that this matters:** in the baseline that motivated this section, a service's record-to-database
step was patched out in every test. The suite was 10/10 green; the real code inserted into a table
nothing ever created, so the function failed on the first real call. A coverage-led read scored that
suite adequate. Ask of any mocked-out path: if the mock were removed, would this still work?

**Interface shape - COUNT it, do not read for it.** Score under Architecture (the seams) and
Maintainability (the churn). This is the shapes units pass BETWEEN each other, and it is the gap
a review most reliably walks past, because every individual signature looks reasonable. It only
appears in aggregate, so the method is a census, not a read. Language-agnostic - parameters,
returns and call edges exist everywhere: use a parser where one exists, `grep` over signature
lines where it does not.

| Signal                           | Count                                                                            | Worth a finding when                                                                            |
|----------------------------------|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| **Data clump**                   | For each pair/triple of parameter NAMES, how many signatures contain all of them | The same group in 3+ functions. That group is an unnamed object                                 |
| **Long parameter list**          | Parameters per function, descending                                              | More than 4-5, especially two functions sharing most of a long list                             |
| **Anonymous multi-value return** | Returns that are a tuple/pair/array/out-param/bare map, bucketed by shape        | Any shape returned by 3+ functions. A shape that dominates the codebase is a missing named type |
| **Parameter tramp**              | Parameters used ONLY as an argument to a forwarded call, never read              | Any; threaded 3+ levels deep is the strongest evidence an object belongs there                  |
| **Receiver re-parse**            | Call sites that immediately split/parse/cast a callee's return                   | Any. The callee had the structured value and discarded it                                       |
| **Boolean/stringly parameter**   | Flag parameters, and strings compared against literals                           | Any that selects behaviour. It wants an enum, which often already exists                        |

**The counting is HALF the row. The other half is QUOTED EVIDENCE - not a verdict.** For the
DOMINANT shape, PASTE the actual source line that produces the "true"/success value at each site:

> - `check_battery.chargeCheck` -> `return [true, \`charge ${pct}%\`]`
> - `check_controller.degradedModeCheck` -> `return [true, "controller is running in degraded mode"]`

Then state the conclusion UNDER the quotes. Do not state it instead of them.

**Cap it when the sites are many.** Above roughly 15, quote every site whose message text and
boolean disagree in sentiment - a `true` beside wording that describes a fault, a `false` beside
wording that describes health - and give the number you skipped: "quoted 6 of 26 sites; the other
20 read `[false, <fault text>]` / `[true, <healthy text>]`." A capped-but-honest sample beats a
complete-sounding summary.

**Why quotes and not a verdict.** A verdict is an assertion ABOUT the work; a quote is a
BYPRODUCT of it. Measured twice on the same fixture. First: a reviewer counted 26 instances
correctly and simply stopped, losing a planted inverted check it had found before the census
existed. So the check was made a required output line - and the reviewer then wrote
"read 13 of 13 sites ... Inverted: none" about a file it had cited in two other findings, where
`degradedModeCheck` returns `true` for "degraded" - and wrote 13 where there were 26, having
summarised the FILE count without ever enumerating sites. The demand for a verdict did not
produce the reading; it produced a confident false all-clear, which is worse than the silence it
replaced. You cannot paste that `return [true, "...degraded mode"]` line and still write
"inverted: none".

The count is not the answer. It is what tells you which lines to quote.

The rest of the judgement, applied to what the counts turned up:

- **A shared NAME is not a shared concept.** Two functions taking `key` where one means an ssh
  key path and the other a lookup key are not a clump; merging them is a new bug, not a fix.
- **Before proposing to remove or relocate a parameter, find out WHAT IT IS FOR - go and look.**
  A tramp count says the parameter is not used HERE. It cannot see why it is threaded, and the
  reasons are precisely the ones that make removing it a regression: a TEST SEAM (the suite
  substitutes a double at that parameter), a PRODUCTION OVERRIDE (one caller, maybe one
  deployment, passes something else), or a deliberate VARIATION POINT not yet exercised. So
  before recommending anything, enumerate WHO SUPPLIES A NON-DEFAULT VALUE, across production
  call sites AND tests, and say what you found. A parameter whose only non-default supplier is
  the test suite is an injection seam: deleting it does not remove plumbing, it forces those
  tests onto patching a global, which is a worse design and a LOWER Testing score.
  This is the step a census cannot prompt you to take, so take it explicitly. Measured: given
  only the counts, a review recommended folding two 94%-and-96%-forward-only parameters into an
  existing object across ~157 signatures, called it "close to codemod-able", ranked it "do
  first" - and never asked what either parameter was for. The same review handed the purpose up
  front declined the same refactor. The counts were identical; only the investigation differed.
- **Gather the call-site evidence by PARSER, never by text match, because the commonest
  parameter names collide with the language's own.** Searching call sites for `key=` in Python
  returns `sorted(key=lambda ...)` and `max(key=len)`; the same trap waits on `value`, `id`,
  `name`, `type`, `index`, `data`, `compare`, `callback`, `handler` in any language with a
  standard library. Resolve each hit against its DECLARATION - type, defining scope - and drop
  the builtin or framework call that merely shares the spelling. Measured: a `key=` grep
  returned 20 call sites, and every one inside the project's own code was the language's sort
  key. The count was real; the thing it counted was not the parameter under review.
- **Ask what would catch a positional mistake.** A type checker catches a swap between different
  types and catches NOTHING between two same-typed fields, which is where the expensive bugs are.
- **Prefer the named type that already exists** - extending one usually beats adding a sibling.
- **A high tramp rate says the parameter does not belong in those signatures. It does NOT say
  which fix.** There are three - introduce the object, DELETE the parameter and resolve it at
  the edge, or leave it - and the census implies none of them. Note especially that bundling a
  near-pure tramp into an object threads the SAME value through the SAME functions inside a new
  wrapper: same ceremony, same call sites touched, close to zero parameters actually removed.
- **A fix must beat the status quo on EVERY rubric dimension, not just the one that found it.**
  Score the candidate against the rest of the rubric before proposing it, and say so. A
  structural win that costs a testability loss is not a win.
- **Rank by parameters removed per line changed**, and say which findings are NOT worth doing.
- **Counting nothing is a real result. So is counting something and leaving it.** If the counts
  come back clean, say so with the numbers. If they come back loud and no available fix improves
  the code, that is equally a finished result - record it as an accepted item WITH the counts and
  the reason each candidate fix was rejected, so the next review does not re-derive the same
  numbers and reach a different answer. The census must be able to exonerate a codebase, or it
  will start inventing work.

**The tell that this matters.** Measured, not assumed. A package whose gate was fully green
(formatter, linter, strict type checker, import contracts, 650 tests) carried 43 of 568 annotated
returns in one anonymous 2-tuple, two 11-parameter functions, one parameter group across 20
signatures, and 8 receiver re-parses. Three structural reviews read that code and rated the tuple
cosmetic. Then a purpose-built fixture with 26 instances of one pair-return and one silently
inverted check was reviewed twice: the weaker model missed the shape entirely, the stronger found
it and ranked it MINOR, tenth of eleven findings - and missed the inversion that the weaker one
caught. Neither counted. That is the failure this section exists to prevent: not blindness, but
local judgement of a global pattern.

Worth doing on its own once a named type exists: tighten the CONTAINER annotations too
(`list[pair]` -> `list[Named]`). A named tuple is assignable to the anonymous one but not the
reverse, so tightening makes the type checker surface every remaining raw construction - eight of
them, in the measured case, none reachable from a green test run.

**Scoring anchors (all dimensions):**

| Score | Meaning                                                  |
|-------|----------------------------------------------------------|
| 0-2   | Absent or fundamentally broken                           |
| 3-4   | Present but inconsistent, significant gaps               |
| 5-6   | Adequate, follows conventions most of the time           |
| 7-8   | Good, minor gaps only                                    |
| 9-10  | Excellent, best practices throughout, no meaningful gaps |

Present the scorecard as a table with per-dimension scores and the weighted total.

**A CLI must be drivable by a machine, not only by a person.** Score under Error Handling and
Documentation. Applies to anything with subcommands and an exit code, in any language. Check all
five, and check them by RUNNING the tool - ask for the structured mode on a command that FAILS,
and read the exit code:

| Requirement                                           | What to look for                                                                                                                                        |
|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| A structured mode exists at all                       | `--json` (or equivalent) on every subcommand, not just the one that was easiest                                                                         |
| An envelope that reports completeness                 | `{ok, command, data, skipped}` - a reader must be able to tell a complete answer from a partial one                                                     |
| A bare mode that stays parseable on failure           | `--json-bare` for `jq`; on error it emits `{type, message}`, never a traceback into a pipeline expecting data                                           |
| Typed errors, not prose                               | An error CLASS name a caller can branch on, rather than a string to regex                                                                               |
| Diagnostics on stderr, exit codes that mean something | Warnings and progress never enter the parsed stream; exit codes fixed and format-independent (0 success, 1 the question answered "no", 2 could not run) |

The distinction that carries the weight is **"it ran and the answer is no" versus "it could not
run"**. A human-formatted table plus exit 0 collapses those into one observation, and the caller
proceeds on nothing.

**On this row, OVER-report rather than under-report.** The costs are asymmetric. Flagging a tool
that turns out not to need a structured mode costs someone a small, additive, backward-compatible
change that breaks no human caller. Missing one costs an agent that drives the tool and silently
acts on the wrong answer, and nothing in the output says so. When unsure whether a CLI is
machine-driven today, raise it anyway and let the owner decline - that decline is a one-line
accepted item, and it is recorded rather than re-derived every review.

This asymmetry is specific to THIS row. Do not carry it to the interface-shape census, where
over-reporting means churning working code and the clean "counted, found nothing" answer is the
valuable one.

Do NOT assume the existing checklist row covers this. "Every subcommand x every output mode x a
failing input" audits the modes that EXIST and never asks whether a machine-readable one exists.
Measured: given a CLI with no structured mode, warnings on stdout, and exit 0 on a failed
inspection, four independent reviews across two models flagged the inconsistent exception handling
and the missing tests, and not one raised any of the five rows above. One review explicitly noted
the exit codes were "inconsistent" without observing that a failure reported success.

**Five always-on checks** (score under Resource Safety, Security, Documentation and Testing):
- **Bounded memory on large/unbounded data.** Reading big files, huge database result sets, or
  huge log files must stream/iterate/chunk/paginate - never load the whole thing into memory or
  accumulate unbounded. Materialize only when the dataset is provably and safely bounded.
- **Sanitized, bounded input.** External input is length-bounded (guard overflow/underflow),
  type-validated, and encoding-safe - non-ASCII, emoji, CJK, control characters, and binary data
  are rejected/normalized/escaped, never trusted raw - and the handling is tested with adversarial
  and edge inputs. Check input validation AND per-sink output escaping (parametrized SQL, HTML
  autoescape, shell argv) per `bitranox:coding-input-sanitization` - at the boundary, not internal
  libs; do not flag internal library calls for "missing input sanitization".
- **Validated structured input.** Structured data passed in (a dict, JSON, an API/IPC payload, a
  deserialized object) is parsed into a typed model before use - never trusted to have the right
  keys, types, or shape. Exception: items the project instructions deliberately accept.
- **A shipped skill covers the whole surface.** If the repo ships a Claude Code skill (a
  `skills/<name>/SKILL.md`, usually alongside `.claude-plugin/`), check it against the code by
  SCRIPT, not by reading. Three sets must appear in it, and they are not the same as "everything
  exported": every CLI subcommand from the tool's own `--help`; every public CALLABLE; and every
  type a caller has to WRITE - the enums passed as arguments, and the exception types caught.
  Score under Documentation.

  Payload and result types are deliberately out. A caller reads `result.reached` without ever
  naming `ResponseObject`, so listing it is noise, while omitting the enum a `family=` argument
  takes is a real gap. Draw the line at "would the user have to type this name", not at the export
  list - a rule that demands every exported symbol makes the skill a duplicate of the API
  reference, and one nobody keeps current.

  This is not pedantry about completeness. A usage skill is what an agent consults to decide what
  the tool can do, so anything it omits is a capability that does not get used, and anything it
  states in the past tense - "no X surface yet" - actively steers an agent away from a feature that
  now exists. Both failures have shipped in practice: a skill that named eight of thirty callables,
  and one that asserted a whole subsystem did not exist two releases after it did.

  Flag as MEDIUM, or SEVERE where the skill makes a claim the code contradicts. The fix is to name
  the missing surface; leave per-flag detail to `--help`, which cannot go stale. A check worth
  keeping in the repo:

  ```python
  named = pathlib.Path("skills/<name>/SKILL.md").read_text()
  missing_cmd = [c for c in commands_from_help() if c not in named]
  missing_api = [n for n in package.__all__ if n not in named]
  ```

  **Coverage is the easy half. Also check what it ASSERTS.** A skill can name every symbol and
  still describe them wrongly, and that passes any coverage check. Two kinds of statement rot
  toward actively misleading an agent, so re-verify each against the code every review:

  - **Absence claims** - "no X yet", "not supported", "does not", "cannot", "only on Linux". These
    are true when written and become false the moment the feature lands, and unlike an omission
    they do not merely fail to help: they steer an agent away from something that now works. Grep
    the skill for the negation and check each hit against the code.
  - **Contract claims** - "never raises", "always returns", "needs no privileges", exit codes.
    An agent writes error handling against these. Where one is load-bearing, the honest check is
    whether a test pins it; if nothing does, that is a finding in its own right.

  Neither is mechanically decidable, so this one is read-and-verify rather than a script. Budget
  for it: it is a handful of greps, and it is the half that produces the SEVERE findings.
- **Every documented invariant is enforced by a test that fails without it.** The project
  instructions file and the design docs state rules in must/never terms - "an unread end is never
  a capable end", "the time base is always the device clock". Each one is an unverified CLAIM
  until something fails when it is broken, and each one is REPORTABLE in its own right: a rule the
  code breaks is a finding whether or not it maps onto any other check on this list. Walk the set
  and report the walk as a table - the invariant, the test that owns it, the paths it covers, the
  verdict - because a reader cannot tell "checked, holds" from "never looked" in prose. Score
  under Testing.

  Three things separate this from reading the test file:

  - **Enumerate the paths the INVARIANT covers, not the ones the test covers.** A passing test
    that names the rule proves it holds on ONE path. Where the same idea has several
    implementations, list them all and check each; the violation lives in the one nobody wrote a
    test for, and the named test on the neighbouring path is exactly what makes it look covered.
  - **The evidence is a mutation, not a reading.** Break the invariant in the code and require the
    suite to go RED. A surviving mutant is a FINDING, not a pass. Reading tells you what a test is
    NAMED; only the mutation tells you what it HOLDS. Where the code defends in layers, a
    single-layer mutation gets absorbed and reads green, so mutate the whole stack before you
    believe it (`bitranox:process-review-verification-before-completion`).
  - **Drift is a finding in either direction.** Where the code and a documented rule disagree, one
    of the two is wrong and neither is self-evidently the one to change. Report the disagreement
    and let the user pick; never quietly rewrite the rule to match the code, and never read the
    rule as evidence the code is fine.

  An unenforced invariant is MEDIUM; one the code VIOLATES is SEVERE. This is not Step 4 in
  advance: Step 4 asks whether a deliberate decision still holds, this asks whether a stated rule
  is true of the code at all.

## Step 4: Re-assess Deliberately Accepted Items (respect, or reconsider)

Cross-reference your findings against **all** deliberately accepted items from Step 1 (the "Code Quality" section AND inline "by design" notes throughout the file). For each match, choose an outcome - do NOT just delete it:

**RESPECT (default).** Keep it accepted and do not present it. This is the outcome unless a re-open trigger fires. Respecting is silent - you do not re-litigate a settled decision.

**RECONSIDER (only on a ground-truth trigger).** Re-open an item ONLY when concrete ground truth shows its stated premise no longer holds - any of:
- the code or context the acceptance was based on has CHANGED (an "internal-only" input is now reachable from an untrusted boundary; a "handful of rows" table now holds millions);
- ground truth now CONTRADICTS the stated reason (read/measure it - do not assume);
- it now causes a REAL problem (security hole, data-loss, correctness bug, OOM) or rests on a rule since invalidated.

Verify against ground truth (read the code / data / measurements). If you cannot establish whether the acceptance still holds, do NOT silently keep or drop it - include it and ASK the user (a hand-written instructions file can rot; never silently prefer either side - see `bitranox:meta-self-improve`).

**Re-assess with a capable model, not whatever the session happens to run.** Judging "does this premise still hold?" is bounded judgment a weaker/literal model gets wrong - it honors a stale premise and silently misses a live issue. Dispatch a **`sonnet`** subagent (pin the tier per dispatch; **`opus`** for a high-stakes security / data-loss call) to evaluate each accepted item against ground truth and return a respect-or-reconsider verdict with evidence. The main agent cannot self-switch its model (see "The session model is fixed" in `bitranox:process-agents-subagent-driven-development`); on a small project already on a known-capable session model, inline is fine.

**Externally-enforced off-limits** (a `.github/` tree or vendored files "managed by an external template"): "propose a change" means FLAG it for the user to take up at the SOURCE (the template / owner) - do not edit the managed file directly.

**Still-accepted summary.** After presenting findings, emit a compact read-only list of the accepted items you RESPECTED this run, each with a one-line "still holds" note (and, for any you re-opened, a pointer to its Reconsider finding). This makes what was set aside visible without re-litigating it.

**If unsure whether something is deliberately accepted:** include it but note "This may be intentional per the project instructions - please confirm."

## Step 5: Format and Present One-by-One

Every finding MUST use this exact format:

```markdown
## Issue N: [Short Title]
**Severity**: SEVERE | MEDIUM | MINOR
**Affected files**: [list of files]
**Description**: [what's wrong]
**Suggested fix**: [specific actionable fix instructions]
```

**A re-opened acceptance uses this variant** (propose-first - present it one at a time like any other issue and let the user decide):

```markdown
## Reconsider accepted item N: [Short Title]
**Severity**: SEVERE | MEDIUM | MINOR
**Affected files**: [list]
**Originally accepted because**: [the documented rationale]
**What changed (ground truth)**: [the concrete evidence the premise no longer holds]
**Proposal**: [re-affirm as-is, or the specific change - your call]
```

**Severity guidelines:**
- **SEVERE**: Security issues, data loss risks, critical bugs, architectural violations
- **MEDIUM**: Performance issues, code quality problems, missing tests, unclear code, documentation gaps
- **MINOR**: Pure style issues (formatting, naming conventions that don't affect readability)

**Every issue MUST have a specific, actionable suggested fix.** Not "improve this"  -  actual instructions.

**Number issues sequentially.** Present in severity order: SEVERE first, then MEDIUM, then MINOR.

**Do NOT dump all issues at once.** Present ONE issue at a time. After presenting, ask:

> "Do you want to implement this fix? Or skip it? If skipping, what's the reason?"

Wait for the user's response before presenting the next issue.

## Step 6a: Implement Accepted Fixes

Implement the change, verify it works (run relevant tests/lints), show the user what changed, move to next issue.

## Step 6b: Save Declined Items to Project Instructions File

**Mandatory for every decline.** Append to `# Code Quality` section in CLAUDE.md / AGENTS.md:

```markdown
Deliberately accepted items  -  do not flag in future reviews:

- **[Short Title]**: [User's reason]. [Brief description so future reviewers understand.]
```

If the section exists, append. Do not duplicate entries. If the section does not exist, create it at the end of the project instructions file. If no project instructions file exists, create one (CLAUDE.md / AGENTS.md) with the `# Code Quality` section.

**When you re-opened an accepted item (a Reconsider finding):**
- If the user RE-AFFIRMS it, refresh its acceptance note in place - rewrite the rationale to the current ground truth and date it - so the record reflects reality (replace the stale wording; do not append a "superseded" note).
- If the user CHANGES it, implement the fix (Step 6a) and update or remove the acceptance note accordingly.

## Step 7: Sweep again, and only then re-score

**Do not stop after one sweep.** Go back to Step 2 and sweep again whenever the sweep just
finished found ANY issue or applied ANY fix. Stop only when a full sweep - one that walked every
row of the aspect checklist - produces no findings and no changes. Then re-run the rubric and
present the before/after scorecard, with the per-sweep finding counts.

Two independent reasons, both observed rather than theorised:

**A fix creates findings.** It changes code that was not previously reviewed, and it is written
under the momentum of having just understood the problem, which is when the adjacent case gets
missed. Real examples from one project: replacing a `gather` with a worker pool made results
arrive out of order, so the existing zip-by-position silently paired results with the wrong hosts;
a typed facade written for one platform module was then re-derived as a bare import in a sibling,
breaking the same type check the facade existed to fix; and a fix landed alongside a test whose
fixture wrote platform-translated newlines, reddening CI on a file the fix never touched.

**One sweep does not see everything.** Attention goes where the last thing led. Measured on that
same project, four invocations found 4, 2, 1, then 0 issues - and the later sweeps were not
picking up scraps. Sweep 2 found a correctness bug that silently produced wrong results under
concurrency; sweep 3 found a quadratic loop costing about eighteen minutes on a wide input. Both
had been present, and reachable, during sweep 1. Nothing about them was subtle; they were simply
in parts of the code that sweep had not looked at.

The user should not have to invoke the skill four times to get four sweeps.

### The aspect checklist

Walk EVERY row each sweep, and say which rows you walked. A sweep that reports "no findings"
without naming its coverage is a sweep that stopped looking, and it is indistinguishable in the
transcript from a thorough one.

| Aspect             | Ask                                                                                                                                                   |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| Public API surface | Every exported name: signature, contract, error behaviour, docs                                                                                       |
| CLI surface        | Every subcommand x every output mode x a failing input; exit codes agree                                                                              |
| Concurrency        | Task/memory growth vs input size; ordering assumptions; cancellation                                                                                  |
| Resource lifetime  | Sockets, files, handles, registries: freed on every path including errors                                                                             |
| Unbounded input    | Big/append-only files, wide ranges, long lists - streamed or bounded                                                                                  |
| Algorithmic cost   | Loops nested over inputs; per-item work inside a per-item loop                                                                                        |
| Error contract     | One hierarchy, consistent types, nothing leaking a foreign exception                                                                                  |
| Cross-platform     | Each supported OS's branch, and the type check for each                                                                                               |
| Packaging          | Builds, installs clean, entry points and marker files present in the wheel                                                                            |
| Tests              | Could they fail? Real seams not self-mocks, an e2e path, no filler; stable and isolated                                                               |
| Shipped skill      | Covers the whole API and CLI (see the always-on checks)                                                                                               |
| Docs and changelog | Match the code as it is now, including what the current change added                                                                                  |
| Interface shape    | COUNT (clumps, long lists, anonymous returns, tramps, re-parses, flags) THEN the meaning check on the dominant shape - both, or the row is not walked |
| Machine-drivable   | Structured mode exists per subcommand; typed errors; stderr diagnostics; exit codes                                                                   |

Report per sweep: which rows were walked, what each found, and the running total. That record is
what makes "no findings" credible.

Two of these rows are COUNTED, not read, and a sweep that reports "no findings" on them without
naming the counts did not walk them. State the numbers: how many functions share the dominant
return shape, the largest parameter group and how many signatures carry it, how many subcommands
offer the structured mode out of how many exist.

Interface shape needs one thing more, because counting is the half that gets done: the row is
walked only once the dominant shape's success-value lines are QUOTED (capped and counted when
there are many). A verdict does not count - "inverted: none" was reported in testing about a file
containing `return [true, "...degraded mode"]`. Paste the lines; the conclusion goes under them.

## Common Mistakes

| Mistake                                                                | Fix                                                                                                                                    |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| Dump all issues at once                                                | Present ONE at a time, wait for response                                                                                               |
| Re-raise an accepted item with no new evidence (nagging)               | Respect it silently; re-open only on a ground-truth trigger                                                                            |
| Vague suggested fixes ("improve this")                                 | Write specific, actionable instructions                                                                                                |
| Skip saving declined items                                             | ALWAYS append to project instructions file                                                                                             |
| Subjective scoring without rubric                                      | Use the weighted rubric table                                                                                                          |
| Leaving the respect-or-reconsider call to a weak/literal session model | Delegate it to a pinned `sonnet` subagent                                                                                              |
| Present MINOR issues before SEVERE                                     | Sort by severity: SEVERE > MEDIUM > MINOR                                                                                              |
| Silently skip an accepted item ground truth now contradicts            | Re-open it as a propose-first "Reconsider" finding                                                                                     |
| Review only the one code path in front of you                          | Walk the full input/variant/caller matrix (types, sizes, states, callers) of the changed code, one check per branch, on the FIRST pass |
| Stop after one sweep because its issue list is empty                   | The list being empty means THIS sweep is done. Sweep again from Step 2; stop only when a full checklist walk finds and changes nothing |
| Report "no findings" without saying what was examined                  | Name the checklist rows walked. An unqualified "nothing found" reads identically whether you looked or not                             |
| Leave the user to re-invoke the skill for another pass                 | The loop is the skill's job. Four invocations to reach zero findings is three invocations too many                                     |
| Score Testing from coverage % and a green run                          | Coverage says which lines RAN, not whether anything could FAIL. Audit the design per `bitranox:process-test-design`                    |
| Treat a mocked-out path as covered                                     | Ask whether it would still work with the mock removed. A self-mocked step can be flatly broken and the suite stays green               |
| Only ever ADD tests                                                    | Deleting a test that cannot fail is a finding too. Filler is negative value - propose the deletion, never a suppression to preserve it |
