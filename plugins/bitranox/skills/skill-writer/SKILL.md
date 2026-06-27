---
name: skill-writer
description: Use when creating new skills, editing existing skills, structuring SKILL.md files, writing skill frontmatter, testing skills with subagents, deploying skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

**Personal skills live in agent-specific directories (`~/.claude/skills` for Claude Code, `~/.agents/skills/` for Codex)** 

**if there is a skill in the current directory, work on AND test THAT skill, not `~/.claude/skills` or `~/.agents/skills/`**

You write test cases (pressure scenarios with subagents), watch them fail (baseline behavior), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand bitranox:test-driven-development before using this skill. That skill defines the fundamental RED-GREEN-REFACTOR cycle. This skill adapts TDD to documentation.

**Official guidance:** For Anthropic's official skill authoring best practices, see anthropic-best-practices.md. This document provides additional patterns and guidelines that complement the TDD-focused approach in this skill.

## Reference Files

| Topic                                                                      | File                             |
|----------------------------------------------------------------------------|----------------------------------|
| Testing methodology - pressure scenarios, RED/GREEN/REFACTOR, meta-testing | testing-skills-with-subagents.md |
| Persuasion principles - authority, commitment, scarcity, social proof      | persuasion-principles.md         |
| Anthropic official best practices - conciseness, freedom, structure        | anthropic-best-practices.md      |
| Graphviz conventions - node shapes, edge labels, naming patterns           | graphviz-conventions.dot         |
| Flowchart rendering - SVG output from dot diagrams                         | render-graphs.js                 |
| Worked example - full test campaign testing CLAUDE.md variants             | examples/CLAUDE_MD_TESTING.md    |

Use the Read tool to load referenced files identified as relevant for full details.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools. Skills help future Claude instances find and apply effective approaches.

**Skills are:** Reusable techniques, patterns, tools, reference guides

**Skills are NOT:** Narratives about how you solved a problem once

## TDD Mapping for Skills

| TDD Concept             | Skill Creation                                   |
|-------------------------|--------------------------------------------------|
| **Test case**           | Pressure scenario with subagent                  |
| **Production code**     | Skill document (SKILL.md)                        |
| **Test fails (RED)**    | Agent violates rule without skill (baseline)     |
| **Test passes (GREEN)** | Agent complies with skill present                |
| **Refactor**            | Close loopholes while maintaining compliance     |
| **Write test first**    | Run baseline scenario BEFORE writing skill       |
| **Watch it fail**       | Document exact rationalizations agent uses       |
| **Minimal code**        | Write skill addressing those specific violations |
| **Watch it pass**       | Verify agent now complies                        |
| **Refactor cycle**      | Find new rationalizations -> plug -> re-verify   |

The entire skill creation process follows RED-GREEN-REFACTOR.

## When to Create a Skill

**Create when:**
- Technique wasn't intuitively obvious to you
- You'd reference this again across projects
- Pattern applies broadly (not project-specific)
- Others would benefit

**Don't create for:**
- One-off solutions
- Standard practices well-documented elsewhere
- Project-specific conventions (put in project instructions file: CLAUDE.md / AGENTS.md)
- Mechanical constraints (if it's enforceable with regex/validation, automate it - save documentation for judgment calls)

## Skill Types

### Technique
Concrete method with steps to follow (condition-based-waiting, root-cause-tracing)

### Pattern
Way of thinking about problems (flatten-with-flags, test-invariants)

### Reference
API docs, syntax guides, tool documentation (office docs)

## Directory Structure


```
skills/
  skill-name/
    SKILL.md              # Main reference (required)
    supporting-file.*     # Only if needed
```

**Flat namespace** - all skills in one searchable namespace

**Separate files for:**
1. **Heavy reference** (100+ lines) - API docs, comprehensive syntax
2. **Reusable tools** - Scripts, utilities, templates

**Keep inline:**
- Principles and concepts
- Code patterns (< 50 lines)
- Everything else

**Hub skills with supporting files:** When SKILL.md is an index that points to separate reference files, add an explicit instruction in the body (not frontmatter) telling Claude to use the Read tool. This prevents Claude from trying to answer from summary tables alone instead of loading the detailed file.

```markdown
Use the Read tool to load referenced files identified as relevant for full details.
```

Only add this for hub/reference skills with supporting files. Self-contained skills (where everything is in SKILL.md) don't need it - the full body is already loaded when invoked.

**Upstream doc linking:** When hub skills consolidate content from original source documents in subdirectories (e.g., `docs/`, `tutorial/`, `api/`), include a two-tier routing table in SKILL.md:
1. **Tier 1** - distilled reference files (same directory as SKILL.md)
2. **Tier 2** - original upstream docs (subdirectory paths for deeper detail)

Don't rely on passive `> Source:` annotations in supporting files - agents treat these as attribution, not as actionable links. The hub must provide an explicit routing table for upstream docs.

```markdown
## Reference Files

| Topic                                           | Distilled reference | Upstream source (full detail)      |
|-------------------------------------------------|---------------------|------------------------------------|
| Core API - Client, Session, request(), stream() | api-reference.md    | docs/api/full-reference.md         |
| Config - Settings, env vars, pyproject section  | configuration.md    | docs/guides/configuration.md       |
| Tutorials - quickstart, first app, deployment   | quick-start.md      | tutorial/getting-started/README.md |

Use the Read tool to load a distilled reference first.
If it lacks the detail you need, load the upstream source.
```

The upstream table should work as a comprehensive index so an agent can jump straight to the right file for any specific class, function, or method. Each row needs to list the concrete API symbols the file covers, not just a prose summary.

```markdown
| Topic                                                   | Upstream source |
|---------------------------------------------------------|-----------------|
| NO Widgets                                              | docs/widgets.md |
| OK Widgets - DataTable, Tree, OptionList, Select, Input | docs/widgets.md |
```

**Building routing tables:** For each supporting file, use `grep -E '^#{2,3} ' filename.md` to extract H2/H3 headings. For tier 1 (distilled reference) rows, list the 3-5 most important headings, class names, or function names as the topic description. If a file covers more than 5 key terms, pick the ones an agent is most likely to search for and add an "etc." or "and more" suffix. For tier 2 (upstream source) rows, list all classes, functions, API endpoints, and key concepts - the upstream column serves as a comprehensive index, so every symbol must be findable through the topic description.

**Evaluating routing descriptions:** For each row in a routing table, ask: given a realistic user query, could Claude pick the right file from the topic description alone? If two rows sound equally plausible for the same query, the descriptions need more differentiation.

Common failures:
- Topic names too generic ("API", "Config") - Claude can't distinguish files
- Overlapping scope - two files both sound relevant for the same query
- Missing subtopics - key content buried inside a file isn't mentioned in the description

Fix: expand topic descriptions to include 2-3 disambiguating subtopics or keywords.

```markdown
| Topic                                         | Distilled reference |
|-----------------------------------------------|---------------------|
| NO API                                        | api-reference.md    |
| NO Config                                     | configuration.md    |
| OK Core API - endpoints, auth, rate limits    | api-reference.md    |
| OK Config - env vars, CLI flags, config files | configuration.md    |
```

**Verifying routing tables:** After writing a routing table, run two checks to confirm it is both complete and accurate. For two-tier tables, run both checks independently for the distilled reference column and the upstream source column:

1. **Coverage check (file -> table):** For each referenced file, run `grep -E '^#{2,3} ' filename.md` to extract its headings. For each heading or key term, confirm it appears in the routing table's topic description for that file. Missing terms = content agents can't find through the table.
2. **Accuracy check (table -> file):** For each search term listed in the routing table, run `grep -i "term" filename.md` to confirm the file actually contains it. Mismatches = stale entries that route agents to the wrong file.

A routing table passes when every key term in the file appears in the table (coverage) and every term in the table appears in the file (accuracy). For tier 1 rows with 10+ headings, coverage is sufficient if the top 5 most-queried terms are represented. For tier 2 rows, coverage requires all classes, functions, and API endpoints - no "top 5" shortcut. Both columns must pass independently.

Example:

```markdown
Referenced file `widgets.md` contains headings: DataTable, Tree, Select, Input, OptionList

OK Coverage check passes - routing table says:
| Widgets - DataTable, Tree, OptionList, Select, Input | widgets.md |

NO Coverage check fails - routing table says:
| Widgets                                              | widgets.md |
(agent searching for "DataTable" won't find the right file)

OK Accuracy check passes - grep widgets.md for "DataTable" -> found
NO Accuracy check fails - routing table lists "TreeView" but file only contains "Tree"
```

Tier 2 example (upstream source column):

```markdown
Routing table row:
| Core API - Client, Session, request(), stream() | api-reference.md | docs/api/full-reference.md  |

Upstream file `docs/api/full-reference.md` contains headings: Client, Session, request, stream, Connection, Retry

NO Tier 2 coverage check fails - topic lists 4 of 6 symbols; missing Connection and Retry -> add them to topic description
NO Tier 2 accuracy check fails - topic lists "stream()" but upstream file heading is "Streaming" -> fix topic or confirm alias

Fixed topic: Core API - Client, Session, request(), Streaming, Connection, Retry
```

**Presence gate:** Before checking coverage and accuracy, first confirm a tier 2 table exists at all. Run `find <upstream-dirs> -name '*.md'` to list all upstream files. If any exist but the routing table has no tier 2 (upstream source) column, the skill is incomplete - add the column and populate it before proceeding with coverage/accuracy checks.

## SKILL.md Structure

**Frontmatter (YAML):**
- Only two fields supported: `name` and `description` (custom fields are stripped by Claude Code)
- Max 1024 characters total
- `name`: Use letters, numbers, and hyphens only (no parentheses, special chars)
- `description`: Third-person, describes ONLY when to use (NOT what it does)
  - Start with "Use when..." to focus on triggering conditions
  - Include specific symptoms, situations, and contexts
  - **NEVER summarize the skill's process or workflow** (see CSO section for why)
  - Keep under 500 characters if possible

```markdown
---
name: skill-name-with-hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
What is this? Core principle in 1-2 sentences.

## When to Use
[Small inline flowchart IF decision non-obvious]

Bullet list with SYMPTOMS and use cases
When NOT to use

## Core Pattern (for techniques/patterns)
Before/after code comparison

## Quick Reference
Table or bullets for scanning common operations

## Implementation
Inline code for simple patterns
Link to file for heavy reference or reusable tools

## Common Mistakes
What goes wrong + fixes

## Real-World Impact (optional)
Concrete results
```


## Claude Search Optimization (CSO)

**Critical for discovery:** Future Claude needs to FIND your skill

### 1. Rich Description Field

**Purpose:** Claude reads description to decide which skills to load for a given task. Make it answer: "Should I read this skill right now?"

**Format:** Start with "Use when..." to focus on triggering conditions

**CRITICAL: Description = When to Use, NOT What the Skill Does**

The description should ONLY describe triggering conditions. Do NOT summarize the skill's process or workflow in the description.

**Why this matters:** Testing revealed that when a description summarizes the skill's workflow, Claude may follow the description instead of reading the full skill content. A description saying "code review between tasks" caused Claude to do ONE review, even though the skill's flowchart clearly showed TWO reviews (spec compliance then code quality).

When the description was changed to just "Use when executing implementation plans with independent tasks" (no workflow summary), Claude correctly read the flowchart and followed the two-stage review process.

**The trap:** Descriptions that summarize workflow create a shortcut Claude will take. The skill body becomes documentation Claude skips.

```yaml
# NO BAD: Summarizes workflow - Claude may follow this instead of reading skill
description: Use when executing plans - dispatches subagent per task with code review between tasks

# NO BAD: Too much process detail
description: Use for TDD - write test first, watch it fail, write minimal code, refactor

# OK GOOD: Just triggering conditions, no workflow summary
description: Use when executing implementation plans with independent tasks in the current session

# OK GOOD: Triggering conditions only
description: Use when implementing any feature or bugfix, before writing implementation code
```

**Content:**
- Use concrete triggers, symptoms, and situations that signal this skill applies
- Describe the *problem* (race conditions, inconsistent behavior) not *language-specific symptoms* (setTimeout, sleep)
- Keep triggers technology-agnostic unless the skill itself is technology-specific
- If skill is technology-specific, make that explicit in the trigger
- Write in third person (injected into system prompt)
- **NEVER summarize the skill's process or workflow**

```yaml
# NO BAD: Too abstract, vague, doesn't include when to use
description: For async testing

# NO BAD: First person
description: I can help you with async tests when they're flaky

# NO BAD: Mentions technology but skill isn't specific to it
description: Use when tests use setTimeout/sleep and are flaky

# OK GOOD: Starts with "Use when", describes problem, no workflow
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently

# OK GOOD: Technology-specific skill with explicit trigger
description: Use when using React Router and handling authentication redirects
```

### 2. Keyword Coverage

Use words Claude would search for:
- Error messages: "Hook timed out", "ENOTEMPTY", "race condition"
- Symptoms: "flaky", "hanging", "zombie", "pollution"
- Synonyms: "timeout/hang/freeze", "cleanup/teardown/afterEach"
- Tools: Actual commands, library names, file types

### 3. Descriptive Naming

**Use active voice, verb-first:**
- OK `creating-skills` not `skill-creation`
- OK `condition-based-waiting` not `async-test-helpers`

**If the target marketplace defines a naming registry, follow it.** Some marketplaces enforce a
category-prefix scheme (e.g. `<category>-[<sub>-]<name>` like `coding-python-...`, `marketing-...`)
via a registry file and a contribution gate. When contributing there, pick the category per that
repo's rules and keep the verb-first/descriptive style for the `<name>` part. The scheme itself is
repo-specific - see that repo's `CONTRIBUTING.md` (for this marketplace, `skill-taxonomy.json`).

### 4. Token Efficiency (Critical)

**Problem:** getting-started and frequently-referenced skills load into EVERY conversation. Every token counts.

**Target word counts (tiered by skill type):**
- getting-started workflows: <150 words each
- Frequently-loaded / process skills: <200 words total
- Other process/technique skills: <500 words (still be concise)
- Reference/hub skills (routing tables + supporting files): MAY exceed 500 words, but keep the SKILL.md lean - push detail into reference files and let the body stay an index. This skill-writer is itself a hub skill and legitimately runs long.

**Techniques:**

**Move details to tool help:**
```bash
# NO BAD: Document all flags in SKILL.md
search-conversations supports --text, --both, --after DATE, --before DATE, --limit N

# OK GOOD: Reference --help
search-conversations supports multiple modes and filters. Run --help for details.
```

**Use cross-references:**
```markdown
# NO BAD: Repeat workflow details
When searching, dispatch subagent with template...
[20 lines of repeated instructions]

# OK GOOD: Reference other skill
Always use subagents (50-100x context savings). REQUIRED: Use [other-skill-name] for workflow.
```

**Compress examples:**
```markdown
# NO BAD: Verbose example (42 words)
your human partner: "How did we handle authentication errors in React Router before?"
You: I'll search past conversations for React Router authentication patterns.
[Dispatch subagent with search query: "React Router authentication error handling 401"]

# OK GOOD: Minimal example (20 words)
Partner: "How did we handle auth errors in React Router?"
You: Searching...
[Dispatch subagent -> synthesis]
```

**Eliminate redundancy:**
- Don't repeat what's in cross-referenced skills
- Don't explain what's obvious from command
- Don't include multiple examples of same pattern

**Verification:**
```bash
wc -w skills/path/SKILL.md
# getting-started workflows: aim for <150 each
# Other frequently-loaded: aim for <200 total
```

**Name by what you DO or core insight:**
- OK `condition-based-waiting` > `async-test-helpers`
- OK `using-skills` not `skill-usage`
- OK `flatten-with-flags` > `data-structure-refactoring`
- OK `root-cause-tracing` > `debugging-techniques`

**Gerunds (-ing) work well for processes:**
- `creating-skills`, `testing-skills`, `debugging-with-logs`
- Active, describes the action you're taking

### 5. Cross-Referencing Other Skills

**When writing documentation that references other skills:**

Use skill name only, with explicit requirement markers:
- OK Good: `**REQUIRED SUB-SKILL:** Use bitranox:test-driven-development`
- OK Good: `**REQUIRED BACKGROUND:** You MUST understand bitranox:systematic-debugging`
- NO Bad: `See skills/testing/test-driven-development` (unclear if required)
- NO Bad: `@skills/testing/test-driven-development/SKILL.md` (force-loads, burns context)

**Why no @ links:** `@` syntax force-loads files immediately, consuming 200k+ context before you need them.

## Flowchart Usage

```dot
digraph when_flowchart {
    "Need to show information?" [shape=diamond];
    "Decision where I might go wrong?" [shape=diamond];
    "Use markdown" [shape=box];
    "Small inline flowchart" [shape=box];

    "Need to show information?" -> "Decision where I might go wrong?" [label="yes"];
    "Decision where I might go wrong?" -> "Small inline flowchart" [label="yes"];
    "Decision where I might go wrong?" -> "Use markdown" [label="no"];
}
```

**Use flowcharts ONLY for:**
- Non-obvious decision points
- Process loops where you might stop too early
- "When to use A vs B" decisions

**Never use flowcharts for:**
- Reference material -> Tables, lists
- Code examples -> Markdown blocks
- Linear instructions -> Numbered lists
- Labels without semantic meaning (step1, helper2)

**REFERENCE:** See graphviz-conventions.dot for graphviz style rules.

**Visualizing for your human partner:** Use `render-graphs.js` in this directory to render a skill's flowcharts to SVG:
```bash
./render-graphs.js ../some-skill           # Each diagram separately
./render-graphs.js ../some-skill --combine # All diagrams in one SVG
```

## Code Examples

**One excellent example beats many mediocre ones**

Choose most relevant language:
- Testing techniques -> TypeScript/JavaScript
- System debugging -> Shell/Python
- Data processing -> Python

**Good example:**
- Complete and runnable
- Well-commented explaining WHY
- From real scenario
- Shows pattern clearly
- Ready to adapt (not generic template)

**Don't:**
- Implement in 5+ languages
- Create fill-in-the-blank templates
- Write contrived examples

You're good at porting - one great example is enough.

## File Organization

### Self-Contained Skill
```
defense-in-depth/
  SKILL.md    # Everything inline
```
When: All content fits, no heavy reference needed

### Skill with Reusable Tool
```
condition-based-waiting/
  SKILL.md    # Overview + patterns
  example.ts  # Working helpers to adapt
```
When: Tool is reusable code, not just narrative

### Skill with Heavy Reference
```
pptx/
  SKILL.md       # Overview + workflows
  pptxgenjs.md   # 600 lines API reference
  ooxml.md       # 500 lines XML structure
  scripts/       # Executable tools
```
When: Reference material too large for inline

### Bundled scripts and hooks: keep them cross-platform

Any script you ship inside a skill or as a hook (a `.sh`, `.py`, `.js`, scripts in
`scripts/`, or a hook command) runs on a user's machine that may be Windows. Author it
so Windows does not silently break it:

- **Write the logic in Python, not bash or `jq`.** A script's or hook's real work belongs in a
  typed, testable language (Python with the standard library is the default); use bash only as a
  thin launcher shim. Bash/`jq` pipelines are hard to unit-test, behave differently across OSes,
  and are the usual source of silent Windows breakage.
- **Line endings: LF only.** Commit a `.gitattributes` that pins `*.sh text eol=lf`
  (and `*.py`/`*.json` for stable hashing). A CRLF `.sh` makes Git Bash on Windows fail
  with "cannot execute: required file not found" or `$'\r': command not found`, and a
  Stop/PreToolUse hook that exits cleanly on failure then disappears with no error.
- **Force UTF-8 in launched interpreters.** A non-UTF-8 Windows locale (e.g. German
  cp1252) corrupts IO. For Python set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`
  before exec; read/write files with explicit `encoding="utf-8"`.
- **Do not assume an interpreter name resolves.** On Windows `python3` is usually the
  Microsoft Store stub (exits non-zero in a subprocess), `python` may be Python 2, and
  `py -3` is Windows-only. Launch Python through a small bash shim that probes
  `python3 -> python -> py -3` and converts POSIX paths with `cygpath` when present.
  The plugin's `hooks/run-python.sh` is the working reference; reuse it.
- **Git Bash only on Windows.** Hooks run through Git Bash (Git for Windows), not WSL or
  Cygwin (those mount drives differently and resolve a Linux interpreter). Guard
  `uname -s` and skip loudly to stderr under an unexpected shell.
- **A hook must never wedge a turn.** Every failure path exits 0; degrade silently
  (with a one-line stderr note) rather than erroring.
- **Set the executable bit in git, not the working tree.** A file run directly (`./script`, or a
  hook invoked by path with a `#!` shebang) needs its exec bit recorded in git. A working-tree
  `chmod +x` does NOT persist when `core.fileMode = false`; set it in the index with
  `git update-index --chmod=+x <file>` and verify with `git ls-files -s` (mode `100755`).
  Interpreter-run files with no shebang (a `.py`/`.js` run as `python x.py`) are never `./`-run,
  so they stay `100644`.
- **Match signals to their source.** A gate that scans transcript text for a trigger
  must run intent/correction patterns against the *user* role and self-admission
  patterns against the *assistant* role; matching both over concatenated text fires on
  ordinary assistant phrasing.
- **Do real work in this preference order; drop a level only when the one above cannot do it:**
  1. **A modern, well-maintained library for the job.** Consult the
     **`python-use-modern-libraries`** skill and use its pick (httpx2 for HTTP, orjson for
     JSON, rtoml for TOML, ruamel.yaml for YAML, and so on). Do not fall back to dated
     defaults (`urllib`/`requests`, stdlib `json`) when a clearly better library exists.
     Declare deps via `uv` so they land in an isolated, reproducible environment, never the
     user's system Python: a CLI tool via `uvx <tool>`, or a script with PEP-723 inline
     metadata run by `uv run script.py` (uv fetches the deps on run, no prompt).
     - **Libraries on the `python-use-modern-libraries` list are pre-approved** - use them and
       let `uv` fetch them; do NOT ask first.
     - For a library NOT on that list, first vet it: trustworthy (reputable maintainer or
       community, not a typo-squat), common (widely adopted), and modern (actively maintained,
       current releases). If it passes, propose adding it to the `python-use-modern-libraries`
       list so the curated set grows. Each new entry needs: a proper one-line description of
       what it is for, the older library/libraries it replaces, and why it is better. Then use
       it. If it fails vetting, prefer a curated alternative or stdlib. Either way surface the
       choice to the user (name it, say why, note it is new to the list).
     - `uv` itself is the one prerequisite: if it is not installed, STOP and ask permission to
       install it (explaining what for) rather than installing it silently.
  2. **Standard library when no third-party library is warranted** (small glue, no hot path,
     or the stdlib module is genuinely the best tool: `pathlib`, `dataclasses`, `zoneinfo`,
     `re`, `subprocess`). The goal is the best tool, not the most dependencies.
  3. **An external command (last resort).** Only when neither of the above fits. Shelling out
     is the least portable choice because the program and its flags differ per OS:
     - **It must EXIST on every target OS.** Windows usually has no `grep`, `sed`, `awk`,
       `curl`, `jq`, `timeout`, or `make`. Probe with `shutil.which(prog)` and fail with a
       clear message (or fall back to stdlib) instead of crashing with "file not found".
     - **Its flags must be valid for THAT OS's build.** The same tool name is often a
       different program with different options (GNU vs BSD/macOS `sed`/`date`/`stat`; the
       Windows port of a tool; PowerShell vs `cmd.exe` builtins). Do not assume a Linux flag
       works elsewhere; stick to the common documented subset or branch per platform.
     - **Pass an argv list, never a shell string.** Use `subprocess.run([...])`, not
       `shell=True`. A shell string (pipes, `||`, `$?`, redirects, `case`) is POSIX-only,
       breaks under Windows `cmd.exe`, and is a command-injection risk. Decide success from
       the return code plus an output-file or output-text check in your own code, not shell
       glue. If you must accept a user-supplied command template, parse it once with
       `shlex.split` and substitute placeholders into the list elements (no shell).

### Ship tests for every script (and they MUST pass)

A skill that bundles Python scripts MUST also ship a `tests/` directory with pytest tests, and
those tests MUST pass before the skill is considered done. This is not optional.

- **Cover every important/main function** - each script's public/main functions need a test
  with decent coverage (happy path plus the key edge cases), not just an import smoke test.
- **Tests must pass.** Run them (`uv run --with pytest pytest tests/` or the project's runner)
  and confirm green. A skill with failing or missing tests does not ship.
- **Test by behaviour with real inputs:** build a tiny fixture project/data, run the function,
  assert on the actual output (e.g. the analyzer flags the planted case and skips the
  decorated/compiled one). Writing the tests routinely surfaces real bugs (argv ignored,
  order-sensitive regex, wrong thresholds) - fix the script, do not weaken the test.
- **Keep scripts import-safe** so they can be tested: all run-time work behind
  `if __name__ == "__main__":`, never at module top level (a script that executes on import
  cannot be unit-tested and will run side effects when imported).
- A `tests/conftest.py` that puts the skill dir on `sys.path` lets tests `import <script>` by
  module name.

### Universal rules vs. marketplace plumbing

Everything in this skill (CSO/description craft, structure, flowcharts, cross-platform scripts,
tests, library choices) applies to **any** skill you author - a standalone skill for your own
machine just as much as one you contribute to a marketplace. Follow it either way.

A skill you contribute to a **specific plugin marketplace** has EXTRA rules layered on top, and
those are repo-specific, so they live in that repo's `CONTRIBUTING.md` (and `CLAUDE.md`), not
here. Typically: a release/versioning policy, a contribution gate (pre-commit/CI check), an
index or registry to update when you add a skill, and a git-history policy. Read that repo's
`CONTRIBUTING.md` before contributing.

When you discover a NEW authoring rule: if it helps any skill author (a portability gotcha, a
testing habit, a structural pattern), it belongs **here** in `skill-writer`; if it only matters
for one repo's release machinery, it belongs in **that repo's** `CONTRIBUTING.md`.

### Persisting durable state: choose a memory backend (do not hard-code MEMORY.md)

If the skill you author persists durable facts, learnings, preferences, or state across sessions,
treat the **store backend as a choice**, not "write it to `MEMORY.md`". Route by the push/pull split:

- **Push tier - the most important standing rules** that must be in context every session: the
  `MEMORY.md` index and CLAUDE.md guardrails (always loaded, zero query). Keep must-hold rules here,
  never only in a search-only store.
- **Pull tier - the larger episodic/searchable tail:** where a **memory MCP server** is installed
  (`basic-memory` over the memory files, or `@modelcontextprotocol/server-memory`), route the tail
  there so the always-loaded context stays small.

So consider whether a memory MCP server is (or should be) installed and send the episodic tail to
it, reserving `MEMORY.md`/CLAUDE.md for the standing rules. Wire any MCP server through the
`update-config` skill, never silently. The full memory-lane model, detection, and the basic-memory
setup caveats live in `bitranox:self-improve` - cross-reference it rather than restating it.

## The Iron Law (Same as TDD)

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

This applies to NEW skills AND EDITS to existing skills.

Write skill before testing? Delete it. Start over.
Edit skill without testing? Same violation.

**No exceptions:**
- Not for "simple additions"
- Not for "just adding a section"
- Not for "documentation updates"
- Don't keep untested changes as "reference"
- Don't "adapt" while running tests
- Delete means delete

**REQUIRED BACKGROUND:** The bitranox:test-driven-development skill explains why this matters. Same principles apply to documentation.

## Testing All Skill Types

Different skill types need different test approaches:

### Discipline-Enforcing Skills (rules/requirements)

**Examples:** TDD, verification-before-completion, designing-before-coding

**Test with:**
- Academic questions: Do they understand the rules?
- Pressure scenarios: Do they comply under stress?
- Multiple pressures combined: time + sunk cost + exhaustion
- Identify rationalizations and add explicit counters

**Success criteria:** Agent follows rule under maximum pressure

### Technique Skills (how-to guides)

**Examples:** condition-based-waiting, root-cause-tracing, defensive-programming

**Test with:**
- Application scenarios: Can they apply the technique correctly?
- Variation scenarios: Do they handle edge cases?
- Missing information tests: Do instructions have gaps?

**Success criteria:** Agent successfully applies technique to new scenario

### Pattern Skills (mental models)

**Examples:** reducing-complexity, information-hiding concepts

**Test with:**
- Recognition scenarios: Do they recognize when pattern applies?
- Application scenarios: Can they use the mental model?
- Counter-examples: Do they know when NOT to apply?

**Success criteria:** Agent correctly identifies when/how to apply pattern

### Reference Skills (documentation/APIs)

**Examples:** API documentation, command references, library guides

**Test with:**
- Retrieval scenarios: Can they find the right information?
- Application scenarios: Can they use what they found correctly?
- Gap testing: Are common use cases covered?

**Success criteria:** Agent finds and correctly applies reference information

## Common Rationalizations for Skipping Testing

| Excuse                         | Reality                                                          |
|--------------------------------|------------------------------------------------------------------|
| "Skill is obviously clear"     | Clear to you  is not  clear to other agents. Test it.            |
| "It's just a reference"        | References can have gaps, unclear sections. Test retrieval.      |
| "Testing is overkill"          | Untested skills have issues. Always. 15 min testing saves hours. |
| "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying.        |
| "Too tedious to test"          | Testing is less tedious than debugging bad skill in production.  |
| "I'm confident it's good"      | Overconfidence guarantees issues. Test anyway.                   |
| "Academic review is enough"    | Reading  is not  using. Test application scenarios.              |
| "No time to test"              | Deploying untested skill wastes more time fixing it later.       |

**All of these mean: Test before deploying. No exceptions.**

## Bulletproofing Skills Against Rationalization

Skills that enforce discipline (like TDD) need to resist rationalization. Agents are smart and will find loopholes when under pressure.

**Psychology note:** Understanding WHY persuasion techniques work helps you apply them systematically. See persuasion-principles.md for research foundation (Cialdini, 2021; Meincke et al., 2025) on authority, commitment, scarcity, social proof, and unity principles.

### Close Every Loophole Explicitly

Don't just state the rule - forbid specific workarounds:

<Bad>
```markdown
Write code before test? Delete it.
```
</Bad>

<Good>
```markdown
Write code before test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete
```
</Good>

### Address "Spirit vs Letter" Arguments

Add foundational principle early:

```markdown
**Violating the letter of the rules is violating the spirit of the rules.**
```

This cuts off entire class of "I'm following the spirit" rationalizations.

### Build Rationalization Table

Capture rationalizations from baseline testing (see Testing section below). Every excuse agents make goes in the table:

```markdown
| Excuse                           | Reality                                                                 |
|----------------------------------|-------------------------------------------------------------------------|
| "Too simple to test"             | Simple code breaks. Test takes 30 seconds.                              |
| "I'll test after"                | Tests passing immediately prove nothing.                                |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
```

### Create Red Flags List

Make it easy for agents to self-check when rationalizing:

```markdown
## Red Flags - STOP and Start Over

- Code before test
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "It's about spirit not ritual"
- "This is different because..."

**All of these mean: Delete code. Start over with TDD.**
```

### Update CSO for Violation Symptoms

Add to description: symptoms of when you're ABOUT to violate the rule:

```yaml
description: use when implementing any feature or bugfix, before writing implementation code
```

## Planning Before You Start

**Before writing any skill, plan the work.** Use your task/todo tooling (e.g. TodoWrite) to build a task list, then execute it step by step. This prevents skipping steps and makes progress visible.

### Step 0: Create a Plan

1. **Identify skill type** - Is this a discipline skill, technique, pattern, or reference? (See "Skill Types" above.) This determines the test approach.
2. **Choose test approach** - Discipline skills need pressure scenarios with 3+ combined pressures. Technique skills need application scenarios. Reference skills need retrieval scenarios. (See "Testing All Skill Types" below.)
3. **List pressure scenarios** - Draft 2-3 scenario descriptions before writing anything.
4. **Estimate scope** - Self-contained SKILL.md or hub with supporting files?
5. **Create task list** - Use your task/todo tooling (e.g. TodoWrite) with one task per phase:

```
TaskCreate: "RED - Write and run baseline pressure scenarios"
TaskCreate: "GREEN - Write minimal SKILL.md addressing baseline failures"
TaskCreate: "REFACTOR - Close loopholes from GREEN testing"
TaskCreate: "Deploy - Commit, push, verify discoverability"
```

### Using Agent Teams for Skill Creation

For complex skills, if you have agent-team tooling available, you can parallelize work:

```
TeamCreate: team_name="skill-creation"

Task (subagent_type="general-purpose", team_name="skill-creation"):
  "Run 3 baseline pressure scenarios WITHOUT the skill, document rationalizations"

Task (subagent_type="general-purpose", team_name="skill-creation"):
  "Draft SKILL.md structure: frontmatter, overview, core pattern sections"
```

**Parallelizable work:**
- Multiple pressure scenarios can run as separate subagents simultaneously
- Routing table coverage and accuracy checks can run in parallel per file
- Different test types (pressure, application, retrieval) can run concurrently

**Sequential work (must wait for previous step):**
- GREEN phase depends on RED phase results (you need baseline failures to address)
- REFACTOR depends on GREEN test results (you need new rationalizations to counter)
- Deployment depends on all tests passing

## RED-GREEN-REFACTOR for Skills

Follow the TDD cycle:

### RED: Write Failing Test (Baseline)

Run pressure scenario with subagent WITHOUT the skill. Document exact behavior:
- What choices did they make?
- What rationalizations did they use (verbatim)?
- Which pressures triggered violations?

**How to dispatch a baseline test:**

```
Task tool call:
  subagent_type: "general-purpose"
  prompt: |
    IMPORTANT: This is a real scenario. Choose and act.
    [Your pressure scenario here]

    Choose A, B, or C. Be honest.

  # Do NOT include the skill in the prompt - this is the baseline test.
  # The subagent must work without skill guidance to reveal natural behavior.
```

This is "watch the test fail" - you must see what agents naturally do before writing the skill.

### GREEN: Write Minimal Skill

Write skill that addresses those specific rationalizations. Don't add extra content for hypothetical cases.

> **CRITICAL: Test the version you are editing, not a stale installed copy.**
>
> When developing a skill in the current directory (e.g., `./my-skill/SKILL.md`), GREEN and REFACTOR tests MUST use that file - not whatever may be installed at `~/.claude/skills/`. Two approaches:
> 1. **Paste content into prompt** (subagent testing): Read the current `./SKILL.md` and paste its full content into the subagent prompt.
> 2. **Copy to project skills dir** (live-agent testing): `cp -r ./my-skill/ .claude/skills/my-skill/` - project-level skills take priority over user-space.

**How to dispatch a verification test:**

```
Task tool call:
  subagent_type: "general-purpose"
  prompt: |
    You have access to this skill:
    [Paste the full SKILL.md content here]

    IMPORTANT: This is a real scenario. Choose and act.
    [Same pressure scenario as baseline]

    Choose A, B, or C. Be honest.

  # Include the full skill content in the prompt so the subagent can follow it.
```

Agent should now comply. If agent still fails: skill is unclear or incomplete - revise and re-test.

### REFACTOR: Close Loopholes

Agent found new rationalization? Add explicit counter. Re-test until bulletproof.

**REQUIRED REFERENCE:** See testing-skills-with-subagents.md for the complete testing methodology:
- How to write pressure scenarios
- Pressure types (time, sunk cost, authority, exhaustion)
- Plugging holes systematically
- Meta-testing techniques

## Anti-Patterns

### NO Narrative Example
"In session 2025-10-03, we found empty projectDir caused..."
**Why bad:** Too specific, not reusable

### NO Multi-Language Dilution
example-js.js, example-py.py, example-go.go
**Why bad:** Mediocre quality, maintenance burden

### NO Code in Flowcharts
```dot
step1 [label="import fs"];
step2 [label="read file"];
```
**Why bad:** Can't copy-paste, hard to read

### NO Generic Labels
helper1, helper2, step3, pattern4
**Why bad:** Labels should have semantic meaning

## STOP: Before Moving to Next Skill

**After writing ANY skill, you MUST STOP and complete the deployment process.**

**Do NOT:**
- Create multiple skills in batch without testing each
- Move to next skill before current one is verified
- Skip testing because "batching is more efficient"

**The deployment checklist below is MANDATORY for EACH skill.**

**Gate enforcement:** Use your task/todo tooling (e.g. TodoWrite) to track the deployment checklist. Do NOT mark the final deployment task as completed until you have verified the skill is discoverable in a fresh session. Only after the deployment task is completed may you begin the next skill.

Deploying untested skills = deploying untested code. It's a violation of quality standards.

## Skill Creation Checklist (TDD Adapted)

**IMPORTANT: Use your task/todo tooling (e.g. TodoWrite) to create tasks for EACH checklist item below.** For complex skills, if agent-team tooling is available, parallelize testing work across subagents.

**PLAN Phase - Before Writing Anything:**
- [ ] Identify skill type (discipline, technique, pattern, or reference)
- [ ] Choose test approach based on skill type (see "Testing All Skill Types")
- [ ] Draft 2-3 pressure/application/retrieval scenarios
- [ ] Decide scope: self-contained SKILL.md or hub with supporting files
- [ ] Create task list with your task/todo tooling, e.g. TodoWrite (one task per phase)

**RED Phase - Write Failing Test:**
- [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
- [ ] Run scenarios WITHOUT skill - document baseline behavior verbatim
- [ ] Identify patterns in rationalizations/failures

**GREEN Phase - Write Minimal Skill:**
- [ ] Name uses only letters, numbers, hyphens (no parentheses/special chars)
- [ ] YAML frontmatter with only name and description (max 1024 chars)
- [ ] Description starts with "Use when..." and includes specific triggers/symptoms
- [ ] Description does NOT summarize workflow (triggers only - see CSO section)
- [ ] Description written in third person
- [ ] Keywords throughout for search (errors, symptoms, tools)
- [ ] Clear overview with core principle
- [ ] Address specific baseline failures identified in RED
- [ ] Code inline OR link to separate file
- [ ] One excellent example (not multi-language)
- [ ] Cross-references use skill name with REQUIRED markers (no `@` links)
- [ ] Test uses current working-directory version (not a stale copy at `~/.claude/skills/`)
- [ ] Run scenarios WITH skill - verify agents now comply

**REFACTOR Phase - Close Loopholes:**
- [ ] Identify NEW rationalizations from testing
- [ ] Add explicit counters (if discipline skill)
- [ ] Build rationalization table from all test iterations
- [ ] Create red flags list
- [ ] Re-test until bulletproof

**Quality Checks:**
- [ ] Small flowchart only if decision non-obvious
- [ ] Quick reference table
- [ ] Common mistakes section
- [ ] No narrative storytelling
- [ ] Supporting files only for tools or heavy reference
- [ ] Hub skills: routing table with topic descriptions for each supporting file
- [ ] Hub skills: "Use the Read tool..." instruction in body
- [ ] Hub skills: routing table passes coverage check (file -> table) and accuracy check (table -> file) for all columns (both distilled reference and upstream source if tier 2 exists)
- [ ] Hub skills: if upstream reference documents exist in subdirectories (e.g., `docs/`, `tutorial/`, `api/`), tier 2 table is present and lists every upstream file with concrete API symbols - run `find docs/ tutorial/ api/ -name '*.md'` (adjust paths) and confirm each result has a row in the tier 2 column
- [ ] Token budget (tiered): `wc -w SKILL.md` body under 500 words for process/technique skills; reference/hub skills may exceed but keep the body a lean index and push detail to reference files

**Deployment:**
- [ ] Place skill in the correct directory:
  - **Project skills** (shared with team): `<project-root>/.claude/skills/skill-name/SKILL.md`
  - **Personal skills** (your own): `~/.claude/skills/skill-name/SKILL.md`
- [ ] Verify frontmatter parses: `head -5 SKILL.md` - confirm `---` delimiters and valid YAML
- [ ] Check token budget: `wc -w SKILL.md` - target under 500 words for process/technique SKILL.md bodies; reference/hub skills may exceed but should keep the body lean and push detail to reference files
- [ ] **If the skill ships Python scripts: `tests/` exists, covers every main function, and PASSES** (`uv run --with pytest pytest tests/`). Do not ship with missing or failing tests.
- [ ] **Security review before any PR/push:** review the full diff for secrets, credentials, private hostnames/IPs, internal paths, PII, and unsafe code (`shell=True` on untrusted input, `eval`/`exec`, command injection, path traversal, unpinned `curl | sh`). Run the `security-review` skill/command on the change. Fix findings before opening the PR.
- [ ] Commit skill to git: `git add skills/skill-name/ && git commit -m "Add skill-name skill"`
- [ ] Push to remote (if configured): `git push`
- [ ] **Verify discoverability:** Start a fresh Claude session, describe a problem the skill should match, and confirm Claude selects and loads the skill
- [ ] Consider contributing back via PR (if broadly useful)

## Discovery Workflow

How future Claude finds your skill:

1. **Encounters problem** ("tests are flaky")
2. **Searches skills** (description keywords match query)
3. **Finds SKILL** (description matches)
4. **Scans overview** (is this relevant?)
5. **Reads patterns** (quick reference table)
6. **Loads example** (only when implementing)

**Optimize for this flow** - put searchable terms early and often.

## The Bottom Line

**Creating skills IS TDD for process documentation.**

Same Iron Law: No skill without failing test first.
Same cycle: RED (baseline) -> GREEN (write skill) -> REFACTOR (close loopholes).
Same benefits: Better quality, fewer surprises, bulletproof results.

If you follow TDD for code, follow it for skills. It's the same discipline applied to documentation.
