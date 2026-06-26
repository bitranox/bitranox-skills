---
name: using-bitranox-skills
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific, already-scoped task, skip this skill and do that task.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

bitranox skills override default system-prompt behavior where they conflict, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, AGENTS.md, direct requests) - highest priority
2. **bitranox skills** - override default system behavior where they conflict
3. **Default system prompt** - lowest priority

If CLAUDE.md says "don't use TDD" and a skill says "always use TDD", follow the user's instructions. The user is in control.

## How to Access Skills

**Never read a skill's `SKILL.md` manually with file tools.** Always invoke it through the `Skill` tool so it activates properly and you get the current version, not a stale memory of it.

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you: follow it directly. Use the Read tool only for the supporting files a skill references (its `scripts/`, templates, references), never to re-read the skill body itself.

**In other environments:** Check your platform's documentation for how skills are loaded.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

Before entering plan mode, brainstorm first with `bitranox:brainstorming` unless you already have.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to enter plan mode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke bitranox:brainstorming" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to enter plan mode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke bitranox:brainstorming" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke bitranox:brainstorming" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP - you're rationalizing:

| Thought                             | Reality                                                                          |
|-------------------------------------|----------------------------------------------------------------------------------|
| "This is just a simple question"    | Questions are tasks. Check for skills.                                           |
| "I need more context first"         | Skill check comes BEFORE clarifying questions.                                   |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first.                                     |
| "I can check git/files quickly"     | Files lack conversation context. Check for skills.                               |
| "Let me gather information first"   | Skills tell you HOW to gather information.                                       |
| "This doesn't need a formal skill"  | If a skill exists, use it.                                                       |
| "I remember this skill"             | Skills evolve. Read current version.                                             |
| "This doesn't count as a task"      | Action = task. Check for skills.                                                 |
| "The skill is overkill"             | Simple things become complex. Use it.                                            |
| "I'll just do this one thing first" | Check BEFORE doing anything.                                                     |
| "This feels productive"             | Undisciplined action wastes time. Skills prevent this.                           |
| "I know what that means"            | Knowing the concept is not using the skill. Invoke it.                           |
| "I'll just start planning"          | Brainstorm first (bitranox:brainstorming) before plan mode, unless already done. |
| "I'll read the skill file myself"   | Never open SKILL.md with file tools. Invoke it via the Skill tool.               |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (`bitranox:brainstorming`, `bitranox:systematic-debugging`) - these determine HOW to approach the task
2. **Implementation skills second** - these guide execution

"Let's build X" -> brainstorming first, then implementation skills.
"Fix this bug" -> systematic-debugging first, then domain-specific skills.

## Skills Span Every Domain, Not Just Process

bitranox ships far more than the workflow/process skills. Before concluding "no skill applies," scan these domains: there is very likely a relevant one. The authoritative, current list is your injected available-skills - invoke any by name with the Skill tool.

- **Process and quality:** `brainstorming`, `writing-plans`, `plan-executor`, `subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `finishing-development-branch`, `git-worktrees`, `enhance-code-quality`, `self-improve`, `skill-writer`, `adopting-external-skills`
- **Architecture:** `python-clean-architecture`, `bash-clean-architecture`, `python-enforce-data-architecture-strict`
- **Language and tooling references:** `bash-reference`, `uv`, `rpyc`, `textual`, `python-performance-review`, `python-use-modern-libraries`, `python-gitignore`
- **Editing structured files and docs:** `edit-json`, `edit-xml`, `edit-yml`, `md-table-formatting`, `markitdown`
- **Shell / git / ssh / remote-control mechanics:** `computer-use-bash`, `computer-use-git`, `computer-use-ssh`, `computer-use-vnc`
- **Writing:** `humanize-de`, `humanize-en`
- **Infrastructure and ops:** `proxmox`, `proxmox-bindsnap`, `rotating-proxies`
- **Persuasion and business:** `rory`

This grouping is orientation, not the source of truth: skills get added and renamed. Trust the available-skills list for what currently exists, and never skip a domain skill just because the task looked like "only" a coding task (e.g. editing a YAML file -> `edit-yml`; writing a user-facing message -> `humanize-en`/`humanize-de`; touching a Proxmox host -> `proxmox`).

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
