---
name: process-agents-dispatching-parallel
description: Use when facing 2+ independent tasks (failing test files, broken subsystems, separate bugs, audit or worklist items) that can be worked without shared state or sequential dependencies and you want to run them concurrently instead of one at a time. Keywords - parallel subagents, dispatch agents, fan-out, worklist, batching, concurrent investigation, one agent per domain.
---

# Dispatching Parallel Agents

> Adapted from the superpowers plugin (MIT).

## Overview

You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history  -  you construct exactly what they need. This also preserves your own context for coordination work.

When you have multiple unrelated failures (different test files, different subsystems, different bugs), investigating them sequentially wastes time. Each investigation is independent and can happen in parallel.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

```dot
digraph when_to_use {
    "Multiple failures?" [shape=diamond];
    "Are they independent?" [shape=diamond];
    "Single agent investigates all" [shape=box];
    "One agent per problem domain" [shape=box];
    "Can they work in parallel?" [shape=diamond];
    "Sequential agents" [shape=box];
    "Parallel dispatch" [shape=box];

    "Multiple failures?" -> "Are they independent?" [label="yes"];
    "Are they independent?" -> "Single agent investigates all" [label="no - related"];
    "Are they independent?" -> "Can they work in parallel?" [label="yes"];
    "Can they work in parallel?" -> "Parallel dispatch" [label="yes"];
    "Can they work in parallel?" -> "Sequential agents" [label="no - shared state"];
}
```

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other

## The Pattern

### 1. Identify Independent Domains

Group failures by what's broken:
- File A tests: Tool approval flow
- File B tests: Batch completion behavior
- File C tests: Abort functionality

Each domain is independent - fixing tool approval doesn't affect abort tests.

**Mostly-independent is the normal case, and it needs a PARTITION rather than a coin flip.**
"Shared state" under *When NOT to Use* is the all-or-nothing extreme; far more often the work
separates cleanly except for a handful of genuinely shared files - the enum module, the models
module, a registry every domain appends to. Do not abandon the fan-out over those, and do not hope
the agents happen to miss each other. Decide the split BEFORE dispatching:

- Assign every file to exactly ONE agent, and give each agent its allow-list explicitly.
- A file several domains must touch gets ONE owner - or edit it yourself first and let the others
  only read from it.
- Tell each agent that other agents are editing the rest of the tree concurrently, and that a
  needed change in someone else's file is to be REPORTED, not made. Say it in those words, or a
  helpful agent reaches across "just this once". The hand-off is a feature: in one measured run
  the last remaining error surfaced precisely because an agent refused to touch a file outside
  its set and named it instead.

Measured: three agents refactoring one checkout in parallel produced a transient test failure from
a half-written sibling edit, and one reported having to re-read every file before each write to
avoid clobbering another's work. Nothing warned them - the collision showed up only as a test that
failed once and passed on re-run.

### 2. Create Focused Agent Tasks

Each agent gets:
- **Specific scope:** One test file or subsystem
- **Clear goal:** Make these tests pass
- **Constraints:** Don't change other code
- **Expected output:** Summary of what you found and fixed. **If you must AGGREGATE the results -
  sum findings, merge scores, build one report - pin a machine-readable shape and say "reply with
  that object and NOTHING else: no preamble, no summary, no markdown fence."** A prose answer is a
  valid response to "expected output: summary", so an agent that writes *"Findings reported above:
  8 items across 4 files"* is obeying this skill while every finding is lost - the detail it refers
  to was never in what came back, and the count makes the loss read as a result. Re-run that agent;
  never reconstruct its numbers from the summary.
- **An explicit model tier:** pin `model` per agent (do not inherit the session model - it is often
  `opus`, the most expensive). Default fan-out to `sonnet`; use `haiku` for mechanical domains and
  `opus` only for a domain needing deep design judgment. Full mapping: see "Concrete tiers" in
  `bitranox:process-agents-subagent-driven-development`. Omitting `model` trips the PreToolUse
  `subagent-model-gate` hook: a warning normally, a DENY while a plan execution is armed (the
  `plan-execution` receipt). Dispatching a batch as part of a plan? The plan skill already armed
  the gate. Running a standalone batch you want gated the same way? Arm it yourself first
  (`skill_receipt.py start plan-execution` via run-python.sh) and `end` it after the batch.

### 3. Dispatch in Parallel

Issue all three subagent dispatches in the same response  -  they run in parallel:

```text
Subagent (general-purpose): "Fix agent-tool-abort.test.ts failures"
Subagent (general-purpose): "Fix batch-completion-behavior.test.ts failures"
Subagent (general-purpose): "Fix tool-approval-race-conditions.test.ts failures"
# All three run concurrently.
```

Multiple dispatch calls in one response = parallel execution. One per response = sequential.

### 4. Review and Integrate

When agents return:
- Read each summary
- Verify fixes don't conflict
- Run full test suite
- Integrate all changes

**Re-run the gate YOURSELF, and run the WHOLE gate.** An agent's green is not the gate's green,
for two separate reasons:

- It sampled while siblings were still writing, so its numbers describe a tree that no longer
  exists. The tell is that the agents disagree with each other: in one run three agents reported
  30, 1 and 5 type errors for the same checkout, minutes apart. None was wrong; none was current.
  Yours, run after they all finish, is the only authoritative one.
- Agents run the cheap check. Told to verify, they run the tests - which is one stage of a gate
  that also lints and type-checks. Measured on a refactor that changed function signatures to
  enums: three agents each truthfully reported "731 passed" while the type checker had 24 errors,
  because the enum members compared equal to the strings the old call sites still passed. Name the
  exact command they must run, including the type checker, and check it yourself afterwards.

## Agent Prompt Structure

Good agent prompts are:
1. **Focused** - One clear problem domain
2. **Self-contained** - All context needed to understand the problem
3. **Specific about output** - What should the agent return?

```markdown
Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:

1. "should abort tool with partial output capture" - expects 'interrupted at' in message
2. "should handle mixed completed and aborted tools" - fast tool aborted instead of completed
3. "should properly track pendingToolCount" - expects 3 results but gets 0

These are timing/race condition issues. Your task:

1. Read the test file and understand what each test verifies
2. Identify root cause - timing issues or actual bugs?
3. Fix by:
   - Replacing arbitrary timeouts with event-based waiting
   - Fixing bugs in abort implementation if found
   - Adjusting test expectations if testing changed behavior

Do NOT just increase timeouts - find the real issue.

Return: Summary of what you found and what you fixed.
```

## Common Mistakes

**NO Too broad:** "Fix all the tests" - agent gets lost
**OK Specific:** "Fix agent-tool-abort.test.ts" - focused scope

**NO No context:** "Fix the race condition" - agent doesn't know where
**OK Context:** Paste the error messages and test names

**NO No constraints:** Agent might refactor everything
**OK Constraints:** "Do NOT change production code" or "Fix tests only"

**NO Vague output:** "Fix it" - you don't know what changed
**OK Specific:** "Return summary of root cause and changes"

## When NOT to Use

**Related failures:** Fixing one might fix others - investigate together first
**Need full context:** Understanding requires seeing entire system
**Exploratory debugging:** You don't know what's broken yet
**Shared state:** Agents would interfere (editing same files, using same resources)

## Worked Example

**Scenario:** 6 test failures across 3 files after major refactoring

**Failures:**
- agent-tool-abort.test.ts: 3 failures (timing issues)
- batch-completion-behavior.test.ts: 2 failures (tools not executing)
- tool-approval-race-conditions.test.ts: 1 failure (execution count = 0)

**Decision:** Independent domains - abort logic separate from batch completion separate from race conditions

**Dispatch:**
```
Agent 1 -> Fix agent-tool-abort.test.ts
Agent 2 -> Fix batch-completion-behavior.test.ts
Agent 3 -> Fix tool-approval-race-conditions.test.ts
```

**Results:**
- Agent 1: Replaced timeouts with event-based waiting
- Agent 2: Fixed event structure bug (threadId in wrong place)
- Agent 3: Added wait for async tool execution to complete

**Integration:** All fixes independent, no conflicts, full suite green

## Key Benefits

1. **Parallelization** - Multiple investigations happen simultaneously
2. **Focus** - Each agent has narrow scope, less context to track
3. **Independence** - Agents don't interfere with each other
4. **Speed** - 3 problems solved in time of 1

## Verification

After agents return:
1. **Review each summary** - Understand what changed
2. **Check for conflicts** - Did agents edit same code?
3. **Run full suite** - Verify all fixes work together
4. **Spot check** - Agents can make systematic errors

