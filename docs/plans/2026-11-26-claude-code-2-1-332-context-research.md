# Claude Code 2.1.33x: what it offers bitranox-skills for context use

Research note from 2026-11-26, against Claude Code 2.1.332 and marketplace 11.26.0. It is a
work list, not a design: each numbered section below is tracked by its own line in
`OPEN-WORK.md`, and the probes it names come before any change. Items for private projects that
also ship skills are tracked in those projects' own backlogs.

## 1. What the release notes and docs actually say

- **Skills over MCP (beta):** in the changelog under 2.1.332 ("Added skills from MCP servers
  (beta)"); the docs name v2.1.331 as the floor. Built on the MCP Skills extension (SEP-2640,
  `io.modelcontextprotocol/skills`), MCP revision 2026-07-28 or later.
  - An MCP skill ignores the frontmatter fields `allowed-tools`, `disallowed-tools`, `hooks`,
    `model`, `effort`, `context`, `agent`, `background`, `shell`, `paths` and `metadata`; `!`
    commands do not run, `@` references are not attached, `${CLAUDE_PROJECT_DIR}` and
    `${CLAUDE_SESSION_ID}` are not substituted.
  - Not supported in cloud sessions, `claude -p`, remote-control server mode, GitHub Actions or
    the Agent SDK, nor with a custom `ANTHROPIC_BASE_URL`, `apiKeyHelper` or
    `ANTHROPIC_AUTH_TOKEN`. Off by default for Team and Enterprise members until enabled.
  - In auto mode "the classifier decides whether the skill loads, without reading it".
  - Python SDK: merged upstream, not released (mcp 2.3.0 on PyPI has no support); FastMCP 4.2.0
    ships an experimental API; the TypeScript SDK 2.4.0 supports it.
- **2.1.331:** `optionalDependencies` in plugin manifests (plugins that install with the plugin
  listing them and can be disabled or uninstalled on their own).
- **2.1.332:** `PreSkillShellCommand` hook event (refuse a skill's inline shell commands as it
  loads); hook output over about 50,000 characters is now shortened.
- **Unified plugins hub:** the claude.ai app directory (Skills, Connectors, Plugins tabs), not a
  CLI feature.
- **Skill mechanics that already exist and that bitranox does not use** (skills doc):
  - Listing: description plus `when_to_use` capped at 1,536 characters per entry
    (`skillListingMaxDescChars`); the whole listing capped at a fraction of the window
    (`skillListingBudgetFraction`, default 0.01), least-used descriptions dropped first.
  - Compaction: Claude Code re-attaches the most recent invocation of each skill, keeping its
    first 5,000 tokens, within 25,000 tokens for all skills together, newest first.
  - `disable-model-invocation: true` takes the description out of the listing; `context: fork`
    runs the skill in a forked subagent; `paths` limits which files activate it;
    `skillOverrides` (not applicable to plugin skills); `/skill-doctor`; `claude plugin eval`
    with a `tool_used: Skill` grader.
  - Path-scoped rules: a `.claude/rules/*.md` file with a `paths:` list loads only when Claude
    works with matching files. Symlinked rules from outside the working directory load only after
    external imports are approved, and then only the ones WITHOUT `paths`.

## 2. Where context goes today (measured 2026-11-26)

| Source                                       | Size               | Note                                             |
|----------------------------------------------|--------------------|--------------------------------------------------|
| CLAUDE.md + CLAUDE.local.md cascade, one cwd | 451 KB (~110k tok) | 418 KB of it is memory-index pointer lines       |
| largest single memory-index level            | 179 KB             | the tree top                                     |
| skill listing, 92 descriptions               | 40.5 KB (~10k tok) | already sized by `hooks/skill-listing-budget.py` |
| skill bodies when invoked                    | median 18.9 KB     | 44 of 92 over ~5k tok, 27 over ~10k, 6 over ~20k |
| `compuse-toolbox/SKILL.md`                   | 409 KB (~100k tok) | 469 lines, so a 500-line rule passes it          |
| SessionStart: `meta-using-bitranox-skills`   | 9.2 KB             | injected whole every session                     |
| frontmatter beyond `name` and `description`  | none               | in all 92 skills                                 |

The memory index costs about ten times the skill listing. After a compaction, 44 skills lose
everything past their first ~5k tokens.

## 3. Changes to bitranox-skills, highest value first

### 3.1 Path-scoped rules for the memory index

Move facts whose trigger is a file type (most of the Python facts, for one) out of the
always-loaded index into `.claude/rules/*.md` files with `paths:`. The memory engine writes the
index, so this is an engine change, not a hand edit. The doc says a symlinked rule with `paths`
does not load, so each level needs real files.

**Probe result (2026-11-26, Claude Code 2.1.332, haiku, `--setting-sources project,local`).**
Tree: a non-git ancestor `T`, the cwd `T/proj` (a git repo), a nested git repo `T/proj/nested`;
each `CLAUDE.md` and rule file holds a unique token, and the evidence is the captured request
body, never the model's answer. Probe: `docs/plans/probes/2026-11-26-rules-loading/`.

| Scenario                         | Loaded with it                                                         |
|----------------------------------|------------------------------------------------------------------------|
| launch, no file touched          | both `CLAUDE.md`, both always-on rules (ancestor one too), no `paths:` |
| Read `src/a.py`                  | adds the ancestor's AND the project's `**/*.py` rule                   |
| Bash `cat src/a.py`              | same as Read: the rule arrives beside the Bash result                  |
| Grep in `src/` (a directory)     | nothing added                                                          |
| Read `nested/b.py` (nested repo) | adds nested `CLAUDE.md`, nested rules, ancestor and project `*.py`     |

So a level can carry a path-scoped rule file that fires for any matching file below it, nested
repos included, on Read and on a Bash command naming the file, but not on Grep. A rule arrives as
a `system-reminder` next to the tool result that triggered it.

Follow-up probes, same harness (one session across resumed `claude -p` turns, `--resume`):

| Chain step                                   | `proj-py` rule attachments in the request          |
|----------------------------------------------|----------------------------------------------------|
| read `a.py`, then `c.py`, then `a.py` again  | 1 throughout: attached once per session            |
| three reads batched in ONE turn              | 1                                                  |
| first request after `/compact`               | 0: not re-attached (only the summary may quote it) |
| next matching read after `/compact` (`c.py`) | 1: attached again                                  |

So a moved fact costs its bytes once per session (and once more after each compaction, on the next
matching file), never once per read. After a compaction it is absent until a matching file is
touched again; `CLAUDE.md` and always-on rules are re-injected at once. Not measured: more than
one ancestor level. A tree under Claude Code's own temp dir (`/tmp/claude-<uid>`) loads no
`CLAUDE.md` and no rule at all, so the probe refuses one.

**Decision (user, 2026-11-26): not built.** The saving holds only in sessions that touch no
matching file. Over the 185 main-session transcripts of the last 30 days whose cwd lay in a
project tree, 14% (by a `.py` path in Read/Edit/Write or a Bash command) to 26% (Read/Edit/Write
only) never touched a `.py` file, so moving the Python facts (a keyword estimate of 116 KB of
this cwd's 409 KB index) saves about 16-30 KB per session on average, 4-7% of the index. Against
that stand an engine change, facts arriving only after the first matching read, and a gap after
every compaction. Reopen if the share of sessions without a matching file grows well past a
quarter, or if Claude Code gains a cheaper per-topic loading mechanism.

### 3.2 Split oversized SKILL.md files into `references/`

Start with `compuse-toolbox` (409 KB). Invoking it loads ~100k tokens, and after a compaction only
its first ~5k survive. Then the other skills over ~20 KB, putting each skill's must-hold rules in
its first ~5k tokens.

### 3.3 Plugin split with `optionalDependencies`

A core plugin pulling in optional domain plugins (infra, web, marketing, rust, pwsh) that a user
can disable. `skillOverrides` does not reach plugin skills, so plugin granularity is the only
switch a user has. Collides with the append-only history, the mirrored-skill map and repo-gate,
so it needs the user's design decision before anything else.

### 3.4 `context: fork` for heavy report-style skills

Candidates: `meta-dream-tree`, `meta-dream-crosstree`, `meta-dream-crosstree-deep`,
`meta-skill-audit`, `meta-collect-knowledge`. Probe first: what a fork inherits (a fork that
carries the whole parent context saves nothing), and whether a skill that asks the user (dream
`propose` mode) still works from a fork.

### 3.5 `paths:` on file-type skills

Candidates: `files-edit-*`, `coding-rust-*`, `docs-md-table-formatting`. The doc says `paths`
decides which files "activate" a skill, not whether the description stays out of the listing until
then; probe that, and check how the skill router treats such a skill.

### 3.6 `disable-model-invocation: true` for user-only skills

Only for skills nothing tells Claude to run on its own (for example `meta-dream-crosstree-deep`,
`meta-memory-settings`). A skill a hook or nudge asks Claude to invoke must keep model invocation.

### Not recommended: shipping bitranox skills over MCP

An MCP skill drops hooks, `!` commands, `context`, `paths` and `model`, does not run in `claude -p`
or the Agent SDK (the A/B harness uses both), and lands in the same listing, so it saves nothing.

## 4. Gaps in `meta-skill-writer`

A grep of the skill shows no mention of `disable-model-invocation`, `user-invocable`,
`context: fork`, `paths`, `when_to_use`, the 5,000/25,000-token compaction re-attach rule,
`skillOverrides`, `/skill-doctor`, `claude plugin eval`, `optionalDependencies` or
`PreSkillShellCommand`. Its size rule is "under 500 lines", inherited from
`anthropic-best-practices.md`; section 2 shows line count is the wrong measure. To add:

- size a skill in tokens, not lines;
- must-hold rules in the first ~5k tokens, because that is what survives a compaction;
- a short table choosing among the frontmatter fields above;
- a section on serving a skill over MCP: when it fits (a server teaching its own tools, plain
  instructions) and what it loses.

## Sources

- Claude Code changelog: https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
- Skills: https://code.claude.com/docs/en/skills.md
- MCP, skills from MCP servers: https://code.claude.com/docs/en/mcp.md
- Memory and path-specific rules: https://code.claude.com/docs/en/memory.md
- MCP Skills extension: https://modelcontextprotocol.io/extensions/skills/overview
- SEP-2640: https://modelcontextprotocol.io/seps/2640-skills-extension.md
- Extension implementations: https://github.com/modelcontextprotocol/ext-skills/blob/main/docs/implementations.md
- Unified directory: https://support.claude.com/en/articles/14328846-browse-skills-connectors-and-plugins-in-one-directory
