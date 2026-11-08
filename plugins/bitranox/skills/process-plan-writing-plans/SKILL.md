---
name: process-plan-writing-plans
description: Use when you have a spec or requirements for a multi-step task and want an implementation plan before touching code
---

# Writing Plans

> Adapted from the superpowers plugin (MIT).

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the process-plan-writing-plans skill to create the implementation plan."

**Context:** If run after brainstorming you will already be in a worktree; otherwise create one with `bitranox:git-worktrees`.

**Save plans to:** `docs/plans/YYYY-MM-DD-<feature-name>.md` (user preferences for plan location override this default).

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans, one per subsystem. Each plan should produce working, testable software on its own.

## Plans Over a Day's Work: Three Altitudes

When the work spans more than a day, do not write one detailed plan: a plan written at task altitude is reviewed at task altitude, so scope, sequencing, prerequisites in other projects and adopt-versus-rebuild stay invisible. Instead:

1. **Freeze the inputs.** Snapshot the spec/design set into a staging dir and note the commit, so every plan references a fixed design.
2. **Run an elephants-in-the-room review** before planning: scope for one builder, riskiest assumptions ranked, over-engineering versus need, what existing thing already does 80 percent (adopt versus rebuild, costed), and whether it solves the actual problem.
3. **Write three plans top-down:** HIGH (milestones, MVP slice, what is cut, risks), then MID (components, interfaces, verification per milestone), then DETAILED (tasks, files, tests, in the format below). Check each lower plan against the one above it, never the reverse.
4. **Detail only to the next decision checkpoint** in the high plan, and say in the file that later milestones get their tasks once that checkpoint is decided: task-level code written for a choice not yet made is a stale brief waiting to be dispatched.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.

**Capability check.** Decomposing a spec into well-bounded units is capability-sensitive - a weaker
model produces a shallow or incoherent decomposition. If the session is on a lesser tier, delegate
the design/decomposition to a pinned `opus` subagent, or offer switch-model-or-continue
(the main agent cannot self-switch its model). The Self-Review below is NOT delegable at any tier -
it is a fresh-eyes pass over the plan YOU just wrote against the spec, and a subagent that never saw
the plan take shape cannot know what was considered and rejected. See `bitranox:process-agents-subagent-driven-development` ("The session model is fixed").
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure, but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.
- In an existing or template-derived repo, read its gate configuration before writing task code (type-checker include and exclude, lint per-file-ignores, selected rule families) and make every code block pass it. Test any glob-scope assumption on scratch files instead of reading the pattern.
- When a cross-cutting check (a lease, a lock gate, an audit hook) must cover a resource the code reaches through more than one path, plan a task that unifies the paths FIRST and put the check in the one remaining path. A per-path check doubles what must stay in sync and keeps behaviour the paths already differ on.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. When drawing task boundaries: fold setup, configuration, scaffolding, and documentation steps into the task whose deliverable needs them; split only where a reviewer could meaningfully reject one task while approving its neighbor. Each task ends with an independently testable deliverable.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

## Global Constraints

[The spec's project-wide requirements: version floors, dependency limits, naming and copy rules, platform requirements, one line each, with exact values copied verbatim from the spec. Every task's requirements implicitly include this section.]

---
```

**Every version floor or pin in Global Constraints names what sets it** (a measured candidate, a user decision). A floor picked as a "safe low" for comfort is a plan defect: check what the target environment can actually run, and ask when it is unknown.

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks - exact signatures]
- Produces: [what later tasks rely on - exact function names, parameter and return types.
  A task's implementer sees only their own task; this block is how they learn the names
  and types neighboring tasks use.]

**Out of scope** - do NOT touch, though they look related:
- `path/that/looks/related.py` - one line on WHY: what makes it different, or what breaks
  if it changes.

**STOP conditions** - stop and report rather than improvise, if:
- the code at the paths above does not match what this task describes;
- a step's verification fails twice after one reasonable fix attempt;
- the change turns out to need a file that is not listed in **Files:**;
- [the assumption this task rests on] turns out to be false.

- [ ] **Step 1: Write the failing test**

Name the seam it drives. A test that patches the module under test proves the patch works;
drive the real entry point and assert on what it produces (`bitranox:process-test-design`).

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

**Task ids start with a digit:** `### Task 3:`, `### Task 2.1:`, `### Task 2.1b:`. A milestone label
goes in the name after the colon (`### Task 2.1: M2 parser`), never in the id. `task_brief.py`
(bitranox:process-agents-subagent-driven-development) finds tasks by `Task <digits>`, so a plan
whose headings read `### Task M2.1:` is reported as having no task headings at all.

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures**, never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code, the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step: if a step changes code, show the code (not "add validation")
- Exact commands with expected output
- Reference relevant skills by name with a REQUIRED marker (e.g. `REQUIRED SUB-SKILL: bitranox:process-test-driven-development`)
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself, not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for the red flags from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug. Every helper a task's code calls from ANOTHER module must be public there: if it is private (`_name`), the plan makes it public in the earliest task that needs it (a word-boundary rename across callers, `sed` with `\b`), instead of leaving the implementer to duplicate it or to import a name a strict type checker reports.

**4. Absence checks:** A step that verifies a rename or removal with "`grep X` must print nothing" must not match what the plan itself leaves behind. A substring pattern still matches the NEW name (`grep '_reason'` hits `failure_reason`), so the step can never pass as written, and an executor following it literally stops or "fixes" correct code. Match whole identifiers (`grep -nw '_within\|_reason'`, or `\b` with `grep -E`), then dry-run each such check against the intended after-state, a scratch file holding the code the plan's own steps write: it must print nothing there, and print the line when each old name in turn is planted back. Measured: a plan checked `grep '_within\|_reason'` after renaming `_reason` to `failure_reason`, and the check matched the new name.

**5. Observable pass criteria:** Every pass criterion for a run on a real machine (a deploy, a hardware or VM test, an end-to-end run) names an observable the build actually produces - a log line, a JSON field, a file, an exit code - and where to read it. Grep the code for the line or field before you write the criterion. A criterion nothing records ("both node-side calls ran") cannot be checked after the run, so the result can only be reported as unobserved; either add the logging as a task or reword the criterion to something already recorded.

**6. Quoted user decisions:** When Global Constraints quotes a user decision verbatim, split the chosen option's text into its clauses and point each clause at the task that delivers it. A clause no task owns surfaces only as a reviewer finding mid-execution. Then check the tests those tasks prescribe assert the PROPERTY the decision promises, not an exact value it never stated: "the script gets the caller's whole PATH back" is tested by every caller entry being present in order, not by equality with the caller's PATH, which fails the first time a tool legitimately prepends an entry.

**7. Memory bound:** For every input whose size the caller controls, the plan states what the code holds per item, what grows with the count, and the peak, and the task that builds that path prescribes a test measuring peak memory at two input sizes, the larger not scaling with the input (Python's tracemalloc sees only Python objects, so measure the child's maximum RSS where a driver or native code allocates). A step that collects every item before acting, or bounds memory only with a count limit, is a defect: rewrite it to iterate (a check pass that discards each result, then an action pass, still checks everything before acting), give each item a byte limit, and keep anything that grows with the input (errors, findings, caches) to the first N plus a total. The one exception is an output that must be built in memory as one piece (a complete file that can be streamed does not qualify): there the plan holds it behind a byte limit with a typed refusal. Where items move to a temp-file spool, the test measures the spool's bytes per item too, since a `/tmp` on tmpfs is memory and a flat peak RSS hides it. If the design never answered the question, answer it now with bitranox:process-plan-brainstorming's data-flow rule before tasks build on the structure.

**8. Each task stands on its own:** Every task's code imports, collects and lints with only that task and the ones before it applied. A task adds only the imports its own code uses: an import block written in Task 1 for modules later tasks create needs placeholder modules, draws unused-import lint findings, and fails test collection. A new helper module under `tests/` is made importable in the task that creates it, the way the repo's pytest configuration needs (under `--import-mode=importlib` the `tests/` directory is not on `sys.path`, so a `conftest.py` that inserts it).

**9. Run the plan's code:** When the plan carries complete code and tests, extract each task's blocks into a scratch copy of the repo in task order and run that task's prescribed tests and lint, instead of only reading them. Where a task prescribes a mutation battery, run it against the extracted code too (bitranox:compuse-toolbox `mutation_arm.py --battery`): every arm must turn a test RED, and a surviving arm is either an equivalent mutant (drop the arm and the redundant line it mutated) or a test whose input passes under both the right and the wrong code (fix the input). Green tests on the extracted code tell neither apart. A test that asserts a substring of the output (a flag name, a word) must fail with the code it guards deleted: check that no other path in the same scenario prints that substring, and prescribe the exact message where one does. Measured: running extracted code found a wrong assertion that reading had missed; a plan whose battery was never run shipped an equivalent mutant and a length test that could not fail, two extra fix rounds; two substring tests passed with their guarded code deleted because another path always warned with the same flag name.

**10. Platforms:** Read the repo's CI OS matrix (the workflow file, or the config it is generated from) and make every platform claim in Global Constraints agree with it: each prescribed test passes on every OS there or skips with a stated reason. A test that isolates `HOME` also sets `USERPROFILE`, which `Path.home()` reads on Windows. Measured: a plan said "Linux only" while CI ran Windows and macOS, and a test that set only `HOME` passed locally and failed on Windows after the release.

**11. Code against the design text:** In a three-altitude plan, check each DETAILED step's code against every behavioural sentence the MID plan states for the same function (what happens at a limit, the order things are cut in, which fields a record carries). Implementers follow the brief's code, so a mismatch ships as the plan's intent, and only a reviewer who reads both documents catches it.

**12. Tests that can show what they claim:** A test for an ORDER or STATE constraint (arms interleaved, a resource held open during a step) makes that order observable: a fake clock with distinct increasing deltas (arm A gets d1, d3, d5 and arm B d2, d4, d6) or a wrapper recording state at each call; counts and lengths under a uniform clock assert nothing about it. A RED step that runs two test files at once stops at a collection error in one, so the other's RED never shows: give each file its own RED command or add `--continue-on-collection-errors`, and say which failure each shows. A test that a CLI option rejects a bad value asserts the option's own name in stderr (`argument --max-rows`), never only exit code 2: argparse also exits 2 on an option it does not know yet, so that RED passes before any code exists.

**13. Text replaced by a pointer:** When a task replaces a passage with a pointer to another file or skill, diff the removed text against the pointed-to text and keep or move every rule, remedy and threshold the target does not carry.

If you find issues, fix them inline. No need to re-review, just fix and move on. If you find a spec requirement with no task, add the task - except for a milestone past the next decision checkpoint of a three-altitude plan: there the file's note that its tasks come once that checkpoint is decided is the intended state, not a gap or a placeholder.

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Attended (this session or a new one)** - The tasks are executed without subagents, in batches, with a checkpoint for your review after each

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use bitranox:process-agents-subagent-driven-development
- Stay in this session
- Fresh subagent per task + two-stage review (each reviewer an `opus` subagent at effort `medium`,
  review dispatch, see bitranox:process-agents-subagent-driven-development "Review dispatches")

**If Attended chosen:**
- For a new session, guide them to open it in the worktree
- **REQUIRED SUB-SKILL:** The executing session uses bitranox:process-agents-subagent-driven-development, section "Attended Mode"
- Batch execution with checkpoints for review
