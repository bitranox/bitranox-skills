---
name: process-review-enhance-code-quality
description: Use when asked to rate, score, audit, or improve code quality of a project, when user wants a 0-10 quality assessment, or when asked what needs to change to reach perfect quality
---

# Enhance Code Quality

## Overview

Score a project 0-10, identify issues by severity, walk the user through fixes one-by-one, track decisions in the project instructions file so declined items are never re-raised.

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

**Scoring anchors (all dimensions):**

| Score | Meaning                                                  |
|-------|----------------------------------------------------------|
| 0-2   | Absent or fundamentally broken                           |
| 3-4   | Present but inconsistent, significant gaps               |
| 5-6   | Adequate, follows conventions most of the time           |
| 7-8   | Good, minor gaps only                                    |
| 9-10  | Excellent, best practices throughout, no meaningful gaps |

Present the scorecard as a table with per-dimension scores and the weighted total.

**Four always-on checks** (score under Resource Safety, Security and Documentation):
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

| Aspect             | Ask                                                                                     |
|--------------------|-----------------------------------------------------------------------------------------|
| Public API surface | Every exported name: signature, contract, error behaviour, docs                         |
| CLI surface        | Every subcommand x every output mode x a failing input; exit codes agree                |
| Concurrency        | Task/memory growth vs input size; ordering assumptions; cancellation                    |
| Resource lifetime  | Sockets, files, handles, registries: freed on every path including errors               |
| Unbounded input    | Big/append-only files, wide ranges, long lists - streamed or bounded                    |
| Algorithmic cost   | Loops nested over inputs; per-item work inside a per-item loop                          |
| Error contract     | One hierarchy, consistent types, nothing leaking a foreign exception                    |
| Cross-platform     | Each supported OS's branch, and the type check for each                                 |
| Packaging          | Builds, installs clean, entry points and marker files present in the wheel              |
| Tests              | Could they fail? Real seams not self-mocks, an e2e path, no filler; stable and isolated |
| Shipped skill      | Covers the whole API and CLI (see the always-on checks)                                 |
| Docs and changelog | Match the code as it is now, including what the current change added                    |

Report per sweep: which rows were walked, what each found, and the running total. That record is
what makes "no findings" credible.

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
