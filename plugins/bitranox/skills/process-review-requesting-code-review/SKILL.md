---
name: process-review-requesting-code-review
description: Use when completing a task, finishing a major feature, before merging to main, when stuck, or after fixing a complex bug, and you want a code review of the changes
---

# Requesting Code Review

> Adapted from the superpowers plugin (MIT).

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation  -  never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code reviewer subagent:**

Dispatch a `general-purpose` subagent, filling the template at [code-reviewer.md](code-reviewer.md)

**Placeholders:**
- `[DESCRIPTION]` - Brief summary of what you built
- `[PLAN_OR_REQUIREMENTS]` - What it should do
- `[BASE_SHA]` - Starting commit
- `[HEAD_SHA]` - Ending commit

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

**Before merging:** scan the push range for leaked secrets, private infrastructure, or personal data (see `bitranox:compuse-git`) - a reviewer should flag these too.

## A gate is real only when the actor cannot satisfy it

A review is a gate, and every gate fails the same way: the actor whose work is checked also decides
whether the check passed. A gate is real only when that actor is STRUCTURALLY incapable of
satisfying it - not merely instructed not to. Ask what the actor would do to pass WITHOUT doing the
work; if the answer is "assert that it did", the gate is advice.

| Does not gate                                | Gates, because the actor cannot reach it       |
|----------------------------------------------|------------------------------------------------|
| a role name in a prompt ("act as a reviewer") | a state machine checked against an authenticated identity |
| an LLM grading a peer, or itself              | a separate job with its own permissions        |
| a regex over prose the agent writes           | a non-AI step returning an exit code           |

**An LLM reviewer FINDS; it does not AUTHORIZE.** Both are true at once: dispatching the reviewer
is worth doing - fresh context and no sunk cost let it see what you cannot - and it is still not
the gate. Keep the jobs apart. The review surfaces candidates; something with an exit code decides
whether the work proceeds. Separateness buys better FINDING, never gating, so reading a subagent's
verdict as permission is exactly what puts an LLM in the left-hand column.

This is why the reviewer here is a SEPARATE subagent that never saw your session, and why "I already
tested it" is a Red Flag below. Apply it to the findings too - but gate on the FIX, not the
FINDING: checking prose for a finding is the left-hand column again, whereas a reported fix is
a claim until a command exits non-zero on the old code and zero on the new.

Measured across five agent orchestrators: four shipped verification that could not refuse, and what
separated the fifth was purely WHERE the gate lived - not effort, not code quality.

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch code reviewer subagent]
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each task or at natural checkpoints
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

These thoughts mean STOP - you are rationalizing:

| Excuse                                   | Reality                                                          |
|------------------------------------------|------------------------------------------------------------------|
| "It's simple, it doesn't need review"    | Simple diffs ship the confident bugs. Size is not risk.          |
| "I already tested it"                    | Tests check what you thought of; review catches what you didn't. |
| "The reviewer will just nitpick"         | Then the nitpicks are cheap. Critical findings are not.          |
| "I'll request review after one more fix" | The fix is exactly what needs reviewing.                         |
| "I wrote it, I know it's right"          | Authorship is the reason you cannot see it.                      |

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: [code-reviewer.md](code-reviewer.md)
