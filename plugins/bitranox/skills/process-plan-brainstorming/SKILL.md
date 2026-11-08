---
name: process-plan-brainstorming
description: Use when starting non-trivial feature, component, or behaviour-change work whose design or requirements are not yet settled, or when a request adds a setting, option or feature that reverses or undoes a decision the user made earlier. Not for trivial, mechanical, or fully-specified changes.
---

# Brainstorming Ideas Into Designs

> Adapted from the superpowers plugin (MIT).

## Overview

Help turn ideas into fully formed designs and specs through natural collaborative dialogue.

**When NOT to use:** trivial, mechanical, or fully-specified tasks where design and requirements are already settled.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in small sections (200-300 words), checking after each section whether it looks right so far.

## The Process

**Understanding the idea:**
- Check out the current project state first (files, docs, recent commits)
- **Ask WHETHER before any HOW question.** State whether the requested feature is worth having at
  all, with a recommendation: what already covers the need (a call site, an existing option, the
  default), what it costs to keep, and YAGNI. Every option of a scope or design question
  presupposes the feature, so once you ask one the user has no way left to say no to it. This
  matters most when the request reverses a decision the user made earlier (a setting to turn off
  something they just chose to have no setting for): name that decision and its reason, and
  recommend for or against reversing it before asking anything else.
- Ask questions one at a time to refine the idea
- Prefer multiple choice questions when possible, but open-ended is fine too
- Only one question per message - if a topic needs more exploration, break it into multiple questions
- Focus on understanding: purpose, constraints, success criteria

**Exploring approaches:**
- Propose 2-3 different approaches with trade-offs
- Present options conversationally with your recommendation and reasoning
- Lead with your recommended option and explain why

**Capability check.** Generating and weighing 2-3 genuinely different designs is capability-sensitive -
a weaker model produces shallow, near-duplicate options. If the session is on a lesser tier, delegate
the approach-generation/synthesis to a pinned `opus` subagent or offer
switch-model-or-continue (the main agent cannot self-switch its model). See
`bitranox:process-agents-subagent-driven-development` ("The session model is fixed").

**Presenting the design:**
- Once you believe you understand what you're building, present the design
- Break it into sections of 200-300 words
- Ask after each section whether it looks right so far
- Cover: architecture, components, data flow, error handling, testing
- **Decide memory in the data-flow section, before the first data structure is chosen.** For
  every input whose size the caller controls (a file, a batch, a list of records, a stream),
  state what is held per item, what grows with the count, and the resulting peak. Default to
  processing items one by one from a re-iterable source, holding only the current one; input that
  can be read only once (stdin, an upload) is spooled to a disk file under a byte limit first (a
  tmpfs `/tmp` is memory). A count limit is not a memory bound: it caps one factor of items x
  size of each, so it bounds time or refuses abuse, never memory; bound the other factor with a
  byte limit per item. "Validate everything before acting" still iterates: a check pass that
  discards each result, then an action pass. What does grow (errors, findings, caches) keeps the
  first N plus a total. Hold the whole only where the output must be built in memory as one piece
  (a complete file that can be streamed does not qualify), behind a byte limit with a typed
  refusal. Asked at review instead, the same question means a rewrite.
- Be ready to go back and clarify if something doesn't make sense

## After the Design

**Documentation:**
- Write the validated design to `docs/plans/YYYY-MM-DD-<topic>-design.md`
- Optional: the `writing-clearly-and-concisely` skill, which ships in the SEPARATE
  `elements-of-style` plugin (`/plugin install elements-of-style@superpowers-marketplace`),
  not in this one - skip this line if you do not have it installed
- Commit the design document to git

**Implementation (if continuing):**
- Ask: "Ready to set up for implementation?"
- **REQUIRED SUB-SKILL:** Use bitranox:git-worktrees to create an isolated workspace
- **REQUIRED SUB-SKILL:** Use bitranox:process-plan-writing-plans to create a detailed implementation plan

## Key Principles

- **One question at a time** - Don't overwhelm with multiple questions
- **Multiple choice preferred** - Easier to answer than open-ended when possible
- **YAGNI ruthlessly** - Remove unnecessary features from all designs
- **Explore alternatives** - Always propose 2-3 approaches before settling
- **Incremental validation** - Present design in sections, validate each
- **Be flexible** - Go back and clarify when something doesn't make sense
