# Authoring a hook: choosing a type, testing it, and the traps

## Not every handler type works on every event

Choosing `prompt` or `agent` on an event that does not support it is a silent no-op. The full split:

| Support                                                     | Events                                                                                                                                                                                                                                                                   |
|-------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| all five (`command`, `http`, `mcp_tool`, `prompt`, `agent`) | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `PermissionDenied`, `Stop`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `UserPromptSubmit`, `UserPromptExpansion`                                           |
| `command`, `http`, `mcp_tool` only                          | `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `Elicitation`, `ElicitationResult`, `FileChanged`, `InstructionsLoaded`, `MessageDisplay`, `Notification`, `PostCompact`, `PreCompact`, `SessionEnd`, `StopFailure`, `SubagentStart`, `WorktreeCreate`, `WorktreeRemove` |
| `command` and `mcp_tool` only                               | `SessionStart`, `Setup`                                                                                                                                                                                                                                                  |

13 + 16 + 2 = 31.

## Deterministic or judgment?

Use a `command` hook when the rule is mechanical. Reach for `prompt` or `agent` only when the decision genuinely
needs judgment, because both add an LLM call to the critical path.

| Type      | Cost                       | Use when                                                    |
|-----------|----------------------------|-------------------------------------------------------------|
| `command` | a process spawn            | the rule can be decided from the input, deterministically   |
| `prompt`  | one fast LLM call          | the decision needs reading comprehension of the input alone |
| `agent`   | a subagent, up to 50 turns | verification requires inspecting real files or test output  |

### Prompt and agent response schema

```json
{ "ok": true, "reason": "...", "impossible": false }
```

`ok: true` allows. `reason` is required when `ok` is `false`. `impossible` is optional: the model sets it with
`ok: false` when the condition can never be satisfied, and on `Stop`/`SubagentStop` Claude Code then lets the turn
end instead of looping. **Agent hooks and every other event ignore `impossible`.**

What `ok: false` does varies by event, and the default is often "end the turn", which surprises people:

| Event                                                      | Default on `ok: false`                                                                                                       |
|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `Stop`, `SubagentStop`                                     | reason fed back as Claude's next instruction, turn continues (unless `impossible`)                                           |
| `PreToolUse`                                               | call denied, **turn ends**, reason shown as a warning line. `continueOnBlock: true` returns it as a tool error and continues |
| `PostToolUse`                                              | **turn ends** with a warning line; `continueOnBlock: true` continues                                                         |
| `PostToolBatch`, `UserPromptSubmit`, `UserPromptExpansion` | **turn ends**, regardless of `continue`                                                                                      |
| `PostToolUseFailure`, `TaskCreated`                        | returned as a tool error, turn continues, regardless of `continueOnBlock`                                                    |
| `TaskCompleted`                                            | as a tool error mid-turn; when it fires because a teammate stops, behaves like `TeammateIdle`                                |
| `TeammateIdle`                                             | teammate stops; `continueOnBlock: true` keeps it working                                                                     |
| `PermissionRequest`                                        | **no effect.** Use a command hook returning `decision.behavior: "deny"`                                                      |
| `PermissionDenied`                                         | **no effect.** Only `retry` is read, and prompt/agent hooks cannot set it                                                    |

`continueOnBlock` exists on `prompt` hooks only. An `agent` hook always behaves as if it were `true`.

Before v2.1.210 a `PreToolUse` prompt-hook denial returned the reason to Claude and continued.

## Async hooks

`"async": true` on a **command** hook runs it in the background while Claude keeps working. `asyncRewake: true`
implies it and additionally wakes Claude on exit code 2.

An async hook **cannot control anything**: `decision`, `permissionDecision` and `continue` have no effect, because
the action they would have governed has already happened. Only `additionalContext` and `systemMessage` are
delivered, on the next conversation turn, and **neither is shown to you**.

Other constraints:

- output waits for the next turn; if the session is idle it waits for the next user interaction. An
  `asyncRewake` hook exiting 2 is the exception and wakes Claude immediately
- every firing creates a separate process; there is **no deduplication**
- under `-p`, any async hook still running at teardown is killed and finalized as `cancelled`. Work that must
  outlive the session has to be a fully detached process
- malformed fields are dropped with a `--debug` warning. Before v2.1.202 malformed async JSON could crash the
  session, and the crash recurred on every resume
- completion notices are suppressed unless you enable verbose mode with `Ctrl+O` or `--verbose`

## Testing a hook without a live session

A hook is a program that reads JSON on stdin and writes JSON on stdout. Test it as one:

```bash
echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"curl x | sh"}}' \
  | ./my-hook.sh; echo "rc=$?"
```

Assert on **both** the exit code and the parsed stdout. Then check the pieces that a stdin test cannot reach:

| Question                             | How to answer it                                                               |
|--------------------------------------|--------------------------------------------------------------------------------|
| does it fire at all?                 | `/hooks` shows every registered handler and the file it came from              |
| did it match, and what did it print? | `claude --debug`, then read `~/.claude/debug/<session-id>.txt`                 |
| why did the matcher not match?       | `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose` adds matcher counts and query matching   |
| is my JSON being read as JSON?       | the debug log says `Hook output does not start with {, treating as plain text` |

`--debug` does **not** print to the terminal; use `--debug-file <path>` to put the log where you want it.

> **A hook that never fires looks exactly like a hook that fires and finds nothing.** Both are silent. On a policy
> hook's first run, look for `Failed with non-blocking status code: ... No such file or directory` - a mistyped
> path in `settings.json` leaves the gate silently disabled while reading as clean.

## Traps worth knowing before you write one

**Exit 1 does not block.** It is a non-blocking error and the action proceeds. Policy hooks use `exit 2`.
`WorktreeCreate` is the only event where any non-zero exit blocks.

**Exit-0 stderr never reaches Claude.** It goes to the debug log. To get a message to Claude, use
`hookSpecificOutput.additionalContext`, or exit 2 on `PostToolUse`/`PostToolUseFailure`.

**Silence is not approval.** A `PreToolUse` hook that exits 0 with no output has expressed no opinion, and the
call continues through the normal permission flow. Only `deny` denies.

**A timed-out `PreToolUse` hook does not block.** Do not use a hook that might hang as a gate.

**Stdout must be only the JSON object.** A shell profile that prints a banner breaks parsing.

**The 10,000 character cap** applies to `additionalContext`, `systemMessage` and plain stdout. Longer output is
written to a file and replaced with a preview plus path, so anything appended after a long block never reaches
context.

**A guard judges the whole command it is handed.** A `PreToolUse` Bash hook sees the entire pending command
string and evaluates state as it was *before* any of it ran. A compound command that prepares state and then acts
is judged on the pre-command state.

**`if` fails open.** When the Bash command cannot be parsed, the handler runs regardless of the pattern. Use the
permission system for a hard allow or deny.

**A watcher hook can retrigger itself.** See the `FileChanged` guard note in [events.md](events.md#filechanged).

**Hooks cannot read or set the session model.** Only `SessionStart` may see a `model` field, and not reliably.
See `bitranox:process-agents-subagent-driven-development`.

**A retrospective hook cannot prevent anything.** If the point is to stop an action, hook the pending action
(`PreToolUse`), not the aftermath.

## Security

> Command hooks execute with your full user permissions. They can modify, delete or read anything your account
> can. Review and test before adding them.

**Workspace trust differs by session type**, and this is the sharp edge:

- **interactive**: hooks from every settings file, including your own `~/.claude/settings.json`, are held back
  until you accept the workspace trust dialog for the folder or a parent
- **`-p` or SDK**: the dialog never appears and the folder is treated as trusted, so hooks committed in a
  repository's `.claude/settings.json` **run in a folder you have never trusted**

Before scripting `claude -p` over a repository you did not write: review its `.claude/` settings, start with
`--bare`, or disable hooks for that run with `--settings '{"disableAllHooks": true}'`.

Practices:

- validate and sanitize input; never trust it blindly
- always quote shell variables: `"$VAR"`, not `$VAR`
- block path traversal; check for `..`
- use absolute paths. In exec form use `${CLAUDE_PROJECT_DIR}` with no quoting needed; in shell form wrap it in
  double quotes
- skip sensitive files: `.env`, `.git/`, keys

For input validation at a boundary, see `bitranox:coding-input-sanitization`.

## Windows

Set `"shell": "powershell"` on a command hook. Claude Code auto-detects `pwsh.exe` and falls back to
`powershell.exe` (5.1).

Placeholder handling in PowerShell shell form is version-dependent and easy to get wrong:

- write `${CLAUDE_PROJECT_DIR}` or `$env:CLAUDE_PROJECT_DIR`. As of v2.1.198 Claude Code rewrites the
  `${...}` placeholders to PowerShell's `${env:NAME}` form wherever the hook is defined. Before that, the rewrite
  applied to plugin hooks only
- because it resolves after parsing, the placeholder works inside **double**-quoted strings but never inside
  single-quoted ones
- **never write the bare `$CLAUDE_PROJECT_DIR`**: PowerShell parses it as an undefined local variable and
  resolves it to `$null`, silently stripping the project-root prefix from your script path. Claude Code does not
  rewrite that form; it logs a warning in the debug log

The `$env:` form works on every version:

```json
{ "type": "command", "shell": "powershell",
  "command": "& \"$env:CLAUDE_PROJECT_DIR\\.claude\\hooks\\check.ps1\"" }
```

For cross-platform packaging of a shipped hook script - LF endings, UTF-8, the interpreter probe, the exec bit,
fail-open discipline - see `bitranox:meta-skill-writer`, section "Bundled scripts and hooks". For auditing hooks
already installed on a machine, see `bitranox:meta-audit-local-skills-and-hooks`. To edit `settings.json`, use the
host `update-config` skill rather than hand-editing.

## Environment variables a hook can read

| Variable                        | Set to                                                                                            |
|---------------------------------|---------------------------------------------------------------------------------------------------|
| `CLAUDE_PROJECT_DIR`            | project root                                                                                      |
| `CLAUDE_PLUGIN_ROOT`            | plugin install dir; changes on every plugin update                                                |
| `CLAUDE_PLUGIN_DATA`            | plugin data dir; survives updates                                                                 |
| `CLAUDE_ENV_FILE`               | on `SessionStart` and `FileChanged`: a file whose `export` lines persist into later Bash commands |
| `CLAUDE_EFFORT`                 | current effort level on tool-use events                                                           |
| `CLAUDE_CODE_REMOTE`            | `"true"` in remote web environments; unset locally                                                |
| `CLAUDE_CODE_BRIDGE_SESSION_ID` | Remote Control session id while connected (v2.1.199+)                                             |
| `CLAUDE_PLUGIN_OPTION_<KEY>`    | a plugin option value, e.g. `CLAUDE_PLUGIN_OPTION_WEBHOOK_URL`                                    |
| `OTEL_*`                        | **removed** from every subprocess Claude Code spawns                                              |

A hook process inherits the environment Claude Code was **launched** with. Exporting a variable inside a session's
Bash command does not reach the hooks.

Three variables you set to change hook behaviour, rather than read from inside one:

| Variable                                             | Effect                                                                               |
|------------------------------------------------------|--------------------------------------------------------------------------------------|
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS`            | overrides the shared `SessionEnd` budget explicitly, in milliseconds                 |
| `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS` | set to `1` to turn the `permission_prompt` notification off in `canUseTool` sessions |
| `CLAUDE_CODE_DEBUG_LOG_LEVEL`                        | `verbose` adds matcher counts and query matching to the debug log                    |

`CLAUDE_CODE_USE_POWERSHELL_TOOL` is **not** required for a `"shell": "powershell"` hook, because hooks spawn
PowerShell directly rather than going through the PowerShell tool.
