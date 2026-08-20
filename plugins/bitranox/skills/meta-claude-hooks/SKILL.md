---
name: meta-claude-hooks
description: Use when writing, editing, debugging or reviewing a Claude Code hook - picking a hook event, writing a matcher, choosing a command/http/mcp_tool/prompt/agent handler, working out what arrives on stdin and what to print to allow, deny or inject context, why exit code 2 blocks one event and is ignored on another, why a hook silently never fires, or how to test one without a live session.
---

# Claude Code hooks

Reference baseline: hooks.md, fetched 2026-08-20, 31 events, content 17e8aaf586b4

Hooks are the deterministic layer around the agent: Claude Code runs your handler at a fixed point in its
lifecycle, so a rule holds whether or not the model decides to honour it.

There are **31 hook events** and **five handler types**. Most people know nine events and one type, which is why
the common failure here is not a bug but an absence: building a polling workaround for something a dedicated
event already does, or declaring a capability missing because it is not in the familiar nine.

## The shape of every hook, in one block

Three levels of nesting, always: the **event**, a **matcher group** that filters it, and the **handlers** that run.
Copy this rather than reconstructing it, because the wrapper is the part people invent.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/check.sh", "args": [] }
        ]
      }
    ]
  }
}
```

The event name is a **key**, its value is a **list of matcher groups**, and each group has its own inner `hooks`
list. An event with no matcher support simply omits `matcher`. Full schema in `references/configuration.md`.

## Step 0: check this reference against upstream, before quoting it

The hooks API moves fast - the upstream page carries version-gated behaviour notes spanning many releases, some
of them reversals. Run this first:

```bash
uv run scripts/hookdoc_stamp.py check --json      # from this skill's directory
```

It is cached for seven days, so it normally costs nothing. **In your reply, paste these values from its output:**

```
data.verdict
data.checked_at
data.cached
data.sources[].content_sha256      (first 12 hex)
data.sources[].structure_sha256    (first 12 hex)
```

If you cannot paste them, the check did not run: say so. Do **not** write "the skill is current" - that sentence
is cheap to produce without looking.

| Verdict      | Exit | What you do                                                                                                                                               |
|--------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CURRENT`    | 0    | proceed; these files are authoritative                                                                                                                    |
| `COSMETIC`   | 0    | proceed; upstream prose changed but the API surface did not. Say which sections moved                                                                     |
| `STRUCTURAL` | 1    | **stop treating this skill as exhaustive.** Report the added/removed names, read those upstream sections, update the reference file, then `stamp --write` |
| `BROKEN`     | 2    | say "freshness unverified: <reason>". Do **not** say up to date, and do **not** say stale. Keep using the files, flagged as unverified                    |

`BROKEN` is a real answer, not a failure to answer: "nothing changed" and "I never looked" are the same output,
so they must never share a verdict.

## Reference files

Use the Read tool to load the file identified as relevant for full details.

| Topic                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Read                          |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| **All 31 events** - SessionStart, Setup, InstructionsLoaded, UserPromptSubmit, UserPromptExpansion, MessageDisplay, PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, PostToolBatch, PermissionDenied, Notification, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, SessionEnd, Elicitation, ElicitationResult | `references/events.md`        |
| **Configuration** - hook locations and precedence, matcher patterns and the exact-match vs regex rule, MCP tool matchers, the five handler types, common fields, `if` and Bash pattern matching, exec form vs shell form, HTTP and MCP tool and prompt fields, path placeholders, hooks in skill and subagent frontmatter, `/hooks`, `disableAllHooks`                                                                                                                                  | `references/configuration.md` |
| **I/O contract** - common input fields, exit codes 0/2/other, timeouts, exit-code-2-per-event table, HTTP response handling, JSON output, `continue`, `stopReason`, `systemMessage`, `terminalSequence`, `additionalContext`, decision control per event, `updatedInput` and `updatedToolOutput`                                                                                                                                                                                        | `references/io-contract.md`   |
| **Authoring** - which handler types each event supports, prompt and agent response schema and `continueOnBlock`, async and `asyncRewake`, testing a hook from stdin, `claude --debug`, traps, security and workspace trust, Windows PowerShell, environment variables                                                                                                                                                                                                                   | `references/authoring.md`     |

Upstream, for detail beyond these files: <https://code.claude.com/docs/en/hooks.md> (reference) and
<https://code.claude.com/docs/en/hooks-guide.md> (guide). Both serve raw markdown.

## Before you write a hook, answer these

1. **Which event?** Read the index at the top of `references/events.md` rather than reaching for the familiar
   one. If you are about to poll for something, check whether an event already reports it.
2. **Can that event block at all?** Roughly half cannot. Check the exit-code-2 table in `references/io-contract.md`.
3. **Does it take a matcher, and will yours be read as an exact string or as a regex?** Any character outside
   letters, digits, `_`, `-`, space, `,` and `|` makes it an **unanchored** regex, so `Edit.*` also matches
   `NotebookEdit`.
4. **Which handler type, and does that event support it?** `prompt` and `agent` work on 13 events only;
   `SessionStart` and `Setup` take just `command` and `mcp_tool`.
5. **How does it answer?** `exit 2`, or exit 0 with JSON. Not both by accident.
6. **What happens when it breaks?** Decide deliberately, because a hook's failure mode is its real behaviour.

## The five that bite hardest

- **`exit 1` does not block.** It is a non-blocking error and the action proceeds. Policy hooks use `exit 2`.
  `WorktreeCreate` is the only event where any non-zero exit blocks.
- **Exit-0 stderr never reaches Claude.** It goes to the debug log. Use `hookSpecificOutput.additionalContext`.
- **Silence is not approval.** A `PreToolUse` hook that exits 0 with no output has expressed no opinion; the call
  continues through the normal permission flow.
- **A hook that never fires looks exactly like one that fires and finds nothing.** Both are silent. On the first
  run of a policy hook, look for `Failed with non-blocking status code: ... No such file or directory`.
- **A guard judges the whole pending command.** A `PreToolUse` Bash hook sees the entire command string and the
  state as it was before any of it ran.

## Related skills

| For                                                                  | Use                                          |
|----------------------------------------------------------------------|----------------------------------------------|
| packaging a shipped hook script cross-platform (LF, UTF-8, exec bit) | `bitranox:meta-skill-writer`                 |
| auditing hooks already installed on a machine                        | `bitranox:meta-audit-local-skills-and-hooks` |
| deciding when prose should become a deterministic guard              | `bitranox:meta-self-improve`                 |
| editing `settings.json` itself                                       | the host `update-config` skill               |
| validating untrusted input inside a hook                             | `bitranox:coding-input-sanitization`         |

## Maintaining this skill

```bash
uv run scripts/hookdoc_stamp.py coverage          # offline: every stamped name is documented here
uv run scripts/hookdoc_stamp.py selftest          # proves the drift detector is not a rubber stamp
uv run scripts/hookdoc_stamp.py stamp --write     # re-stamp; refuses while coverage has gaps
uv run scripts/hookdoc_stamp.py baseline --write  # refresh the baseline line above
```

After a `STRUCTURAL` verdict: update the reference files **first**, then re-stamp. `stamp` runs `coverage` before
writing and refuses while a newly-appeared event is undocumented, so the stamp cannot quietly move ahead of the
documentation it certifies.
