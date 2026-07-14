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
2. Run project tools → collect objective data
3. Score 0-10 with rubric
4. Re-assess accepted items vs ground truth (respect, or reconsider propose-first)
5. Present Issue N
   ├── yes → 6a. Implement fix ──┐
   └── no  → 6b. Save decline ──┤
                                  ▼
                           More issues?
                           ├── yes → back to 5
                           └── no  → 7. Re-score
```

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
| Testing         | 20%    | Coverage %, test quality, edge cases, isolation                |
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

**Scoring anchors (all dimensions):**

| Score | Meaning                                                  |
|-------|----------------------------------------------------------|
| 0-2   | Absent or fundamentally broken                           |
| 3-4   | Present but inconsistent, significant gaps               |
| 5-6   | Adequate, follows conventions most of the time           |
| 7-8   | Good, minor gaps only                                    |
| 9-10  | Excellent, best practices throughout, no meaningful gaps |

Present the scorecard as a table with per-dimension scores and the weighted total.

**Three always-on robustness checks** (score under Resource Safety and Security):
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

## Step 7: Re-score

After all issues processed, re-run the rubric. Present before/after scorecard.

## Common Mistakes

| Mistake                                                                | Fix                                                         |
|------------------------------------------------------------------------|-------------------------------------------------------------|
| Dump all issues at once                                                | Present ONE at a time, wait for response                    |
| Re-raise an accepted item with no new evidence (nagging)               | Respect it silently; re-open only on a ground-truth trigger |
| Vague suggested fixes ("improve this")                                 | Write specific, actionable instructions                     |
| Skip saving declined items                                             | ALWAYS append to project instructions file                  |
| Subjective scoring without rubric                                      | Use the weighted rubric table                               |
| Leaving the respect-or-reconsider call to a weak/literal session model | Delegate it to a pinned `sonnet` subagent                   |
| Present MINOR issues before SEVERE                                     | Sort by severity: SEVERE > MEDIUM > MINOR                   |
| Silently skip an accepted item ground truth now contradicts            | Re-open it as a propose-first "Reconsider" finding          |
