# The I/O contract: what a hook receives, what it may print, what the exit code means

Command hooks get JSON on **stdin** and answer through **exit code + stdout**. HTTP hooks get the same JSON as
the POST body and answer through the response body. Everything here applies to both unless stated.

On macOS and Linux a command hook runs in its own session with **no controlling terminal**: it cannot open
`/dev/tty` or write escape sequences to the interface. Windows has no `/dev/tty` at all. Use `systemMessage` to
reach the user and `terminalSequence` to ring a bell or set a title.

## Common input fields

| Field             | Present                         | Description                                                                                                                                                                              |
|-------------------|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `session_id`      | always                          | current session identifier                                                                                                                                                               |
| `prompt_id`       | after the first user input      | UUID of the prompt being processed; matches the OpenTelemetry `prompt.id` so hook output can be correlated with telemetry. Needs v2.1.196+                                               |
| `transcript_path` | always                          | path to the conversation JSON. **Written asynchronously and may lag the current turn**                                                                                                   |
| `cwd`             | always                          | working directory when the hook was invoked                                                                                                                                              |
| `permission_mode` | not all events                  | `default`, `plan`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`. The mode labelled **Manual** arrives as `default`, never `manual`                                              |
| `effort`          | tool-use context events         | object with `level`: `low`, `medium`, `high`, `xhigh`, `max`. The **downgraded** level if the model does not support the request. Ultracode reports as `xhigh`. Also in `$CLAUDE_EFFORT` |
| `hook_event_name` | always                          | the event that fired                                                                                                                                                                     |
| `agent_id`        | inside a subagent only          | use it to tell subagent calls from main-thread calls                                                                                                                                     |
| `agent_type`      | with `--agent` or in a subagent | e.g. `Explore`. A subagent's own type wins over the session `--agent` value                                                                                                              |

Do not read the transcript for the current turn's final assistant text; it may not be there yet. Use
`last_assistant_message` on `Stop` and `SubagentStop`.

Only `SessionStart` can receive a `model` field, and it is **not guaranteed**. There is no `$CLAUDE_MODEL`.
`$ANTHROPIC_MODEL` is inherited from your shell if set, but does not change when you switch with `/model`.

`OTEL_*` exporter variables are **removed** from every subprocess Claude Code spawns, hooks included.

## What `tool_input` holds, per tool

Tool events carry `tool_name`, `tool_input` and `tool_use_id`. The shape of `tool_input` depends on the tool,
and most hooks are written against one or two of these.

For the file tools `Write`, `Edit` and `Read`, **`tool_input.file_path` is always absolute**. Claude Code expands
`~` and relative paths before hooks run, so a path-matching hook cannot be bypassed by spelling the same path
differently.

> **The Windows path trap.** On Windows the path arrives with **backslash** separators, even when your hook runs
> under Git Bash where `$PWD` looks like `/c/project`. A comparison written with forward slashes, such as a
> `/src/` check, never matches, and the tool call proceeds exactly as if the hook had found nothing to block.
> Normalise first - `FILE_PATH="${FILE_PATH//\\//}"` in Bash, `file_path.replace("\\", "/")` in Python - then
> match a path **segment** like `/src/` rather than anchoring with `^`, since the path is absolute.

| Tool              | `tool_input` fields                                                                                                                                                                                                               |
|-------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Bash`            | `command` (string), `description` (string), `timeout` (ms; above the maximum it is reduced, not rejected), `run_in_background` (bool)                                                                                             |
| `PowerShell`      | same four as `Bash`, with the command string in `command`                                                                                                                                                                         |
| `Write`           | `file_path`, `content`                                                                                                                                                                                                            |
| `Edit`            | `file_path`, `old_string`, `new_string`, `replace_all` (bool)                                                                                                                                                                     |
| `Read`            | `file_path`, `offset` (line), `limit` (lines)                                                                                                                                                                                     |
| `Glob`            | `pattern`, `path` (defaults to cwd)                                                                                                                                                                                               |
| `Grep`            | `pattern`, `path`, `glob`, `output_mode` (`content` / `files_with_matches` / `count`, default `files_with_matches`), `-i` (bool), `multiline` (bool)                                                                              |
| `WebFetch`        | `url`, `prompt`                                                                                                                                                                                                                   |
| `WebSearch`       | `query`, `allowed_domains` (array), `blocked_domains` (array)                                                                                                                                                                     |
| `Agent`           | `prompt`, `description`, `subagent_type`, `model`                                                                                                                                                                                 |
| `AskUserQuestion` | `questions` (array; each has `question`, `header`, `options`, optional `multiSelect`), `answers` (object mapping question text to chosen label - Claude never sets this, supply it via `updatedInput` to answer programmatically) |
| `ExitPlanMode`    | `plan` (Markdown), `planFilePath`, `allowedPrompts` (**deprecated**, accepted and ignored)                                                                                                                                        |

**Match `Bash|PowerShell`, not `Bash` alone**, in any hook that inspects shell commands. On Windows where the
PowerShell tool is enabled Claude routes shell commands through it, and on Windows without Git Bash the Bash tool
is not registered at all - so a `Bash`-only matcher never fires there.

`ExitPlanMode` is worth knowing about: Claude writes the plan to disk before calling the tool, so the literal
`tool_input` from the model is typically empty and Claude Code **injects** `plan` and `planFilePath` before hooks
see it. In `PostToolUse`, read `tool_response.plan` rather than re-reading the file.

### `tool_response` from an `Agent` call

A foreground `Agent` call gives `PostToolUse` the subagent's final text plus run telemetry:

| Field                                  | Meaning                                                                          |
|----------------------------------------|----------------------------------------------------------------------------------|
| `status`                               | `completed`, or `async_launched` for a background subagent                       |
| `agentId`                              | identifier for the run                                                           |
| `content`                              | array of the subagent's final text blocks                                        |
| `resolvedModel`                        | the model it **started** on, which may differ from the requested one (v2.1.174+) |
| `modelsUsed`                           | models in order with repeats collapsed, set only on a mid-run swap (v2.1.212+)   |
| `totalTokens`, `usage`                 | the **final API request only**, not a total across the run                       |
| `totalDurationMs`, `totalToolUseCount` | wall-clock duration and tool-call count                                          |

As of v2.1.198 subagents run in the background by default, so an omitted `run_in_background` still yields
`async_launched`. A background launch returns immediately and carries **no usage fields** - only `status`,
`agentId`, `description`, `prompt`, `outputFile` and `resolvedModel`. For rollups across subagents use the token
and cost counters filtered to `query_source` `subagent`, because `totalTokens` covers one request.

## Exit codes

The exit code does not act alone: Claude Code reads JSON from stdout on **every** exit code. Exit 2's block is the
one outcome JSON cannot override.

### Exit 0

Success, and the intended code when printing JSON for structured control.

Stdout goes to the debug log and is **not** shown in the transcript, except on `UserPromptSubmit`,
`UserPromptExpansion` and `SessionStart`, where plain-text stdout is added as context Claude can see.

How stdout is read depends on its **first non-whitespace character**:

- starts with `{` - parsed as JSON; if invalid, treated as plain text
- anything else - plain text, **including a JSON array or a quoted JSON string**

**Stderr from a hook that exits 0 goes to the debug log only. Claude never sees it.** To surface a warning to
Claude from `PostToolUse` or `PostToolUseFailure`, exit 2 instead.

A parsed object that fails schema validation is a non-blocking error: the action proceeds and the transcript shows
a `<hook name> hook error` notice with the validation message.

### Exit 2

A blocking error. On events that can block it blocks **whether or not** you print JSON: even a
`permissionDecision` of `allow` cannot override it. On `Elicitation` and `ElicitationResult` an exit-2 hook's
`hookSpecificOutput` is ignored.

The blocking message is the `reason` from your JSON when it makes a blocking decision, and your stderr otherwise.

A hook that exits 2 while printing schema-invalid JSON still blocks, using stderr as the reason. Before v2.1.214
that combination was a non-blocking error and the action proceeded.

### Any other exit code

Not a block, for most events. What happens depends on stdout:

- **valid object, passes validation** - the exit code is ignored and the JSON alone decides. Every field the event
  supports is honoured (`permissionDecision`, `additionalContext`, `updatedInput`, `systemMessage`), and the hook
  is not reported as an error
- **valid object, fails validation** - non-blocking error, as on exit 0
- **plain text, or empty** - non-blocking error: the transcript shows `<hook name> hook error` and the first line
  of stderr prefixed `Failed with non-blocking status code:`

> **Exit 1 does not block.** It is the conventional Unix failure code and Claude Code treats it as a non-blocking
> error, proceeding with the action. A policy hook must `exit 2`. The sole exception is `WorktreeCreate`, where
> **any** non-zero exit aborts creation.

A hook that cannot start lands in the same bucket: a missing or non-executable script exits 127 and you get
`Failed with non-blocking status code: /bin/sh: /path/to/hook.sh: No such file or directory`. **Watch for that
notice on a policy hook's first run - a mistyped path leaves the gate silently disabled.**

### Timeouts

A timed-out `command`, `http` or `mcp_tool` hook is cancelled, its output discarded, and it renders no decision.

On `PreToolUse` this means a stalled hook **does not block** the call, which continues through the normal
permission flow. Do not rely on a hook that might hang as a gate. An Agent SDK callback hook is the exception:
exceeding its timeout does block the tool call.

### What exit 2 does, per event

| Event                 | Can block? | Effect of exit 2                                          |
|-----------------------|------------|-----------------------------------------------------------|
| `PreToolUse`          | yes        | blocks the tool call                                      |
| `UserPromptSubmit`    | yes        | blocks prompt processing and **erases the prompt**        |
| `UserPromptExpansion` | yes        | blocks the expansion                                      |
| `Stop`                | yes        | prevents stopping, continues the conversation             |
| `SubagentStop`        | yes        | prevents the subagent stopping                            |
| `TeammateIdle`        | yes        | prevents the teammate going idle                          |
| `TaskCreated`         | yes        | rolls back the task creation                              |
| `TaskCompleted`       | yes        | prevents completion being marked                          |
| `ConfigChange`        | yes        | blocks the change (except `policy_settings`)              |
| `PostToolBatch`       | yes        | stops the agentic loop before the next model call         |
| `PreCompact`          | yes        | blocks compaction                                         |
| `Elicitation`         | yes        | denies the elicitation                                    |
| `ElicitationResult`   | yes        | blocks the response, which becomes a decline              |
| `WorktreeCreate`      | yes        | **any** non-zero exit fails creation                      |
| `PermissionRequest`   | no         | not honoured; deny through the `decision` object instead  |
| `PermissionDenied`    | no         | ignored, the denial already happened; use `retry: true`   |
| `PostToolUse`         | no         | shows stderr **to Claude**; the tool already ran          |
| `PostToolUseFailure`  | no         | shows stderr **to Claude**; the tool already failed       |
| `StopFailure`         | no         | output and exit ignored, except `terminalSequence`        |
| `Notification`        | no         | exit code and stderr ignored                              |
| `SessionStart`        | no         | stderr to the user only                                   |
| `Setup`               | no         | stderr to the user only                                   |
| `SubagentStart`       | no         | stderr to the user only, in the subagent's own transcript |
| `SessionEnd`          | no         | stderr to the user only                                   |
| `CwdChanged`          | no         | stderr to the user only                                   |
| `FileChanged`         | no         | stderr to the user only                                   |
| `PostCompact`         | no         | stderr to the user only                                   |
| `DirectoryAdded`      | no         | stderr to the debug log; the directory is already added   |
| `WorktreeRemove`      | no         | failures logged in debug mode only                        |
| `InstructionsLoaded`  | no         | exit code ignored                                         |
| `MessageDisplay`      | no         | the original text is displayed                            |

For `SessionStart`, `Setup` and `SubagentStart`, exit-2 stderr renders as a `<hook name> hook error` notice.
**Claude does not see it** and the session or subagent proceeds.

## HTTP response handling

HTTP hooks cannot signal a blocking error through status codes at all. To block, return **2xx with a JSON body**
carrying the decision fields.

| Response                         | Meaning                                                           |
|----------------------------------|-------------------------------------------------------------------|
| 2xx, empty body                  | success, same as exit 0 with no output                            |
| 2xx, JSON object body            | parsed with the same schema as command stdout                     |
| 2xx, any other body (plain text) | non-blocking error; the text is **not** added to Claude's context |
| non-2xx                          | non-blocking error, execution continues                           |
| connection failure               | non-blocking error, execution continues                           |
| timeout                          | cancelled, no decision, execution continues                       |

## JSON output

Print the object on stdout and exit 0. **Stdout must contain only the JSON object** - a shell profile that prints
a banner on startup will break parsing.

Hook output strings, `additionalContext` and `systemMessage` and plain stdout alike, are capped at **10,000
characters**. Longer output is written to a file and replaced with a preview plus the path.

Three kinds of field: universal ones, top-level `decision`/`reason`, and the nested `hookSpecificOutput` (which
requires `hookEventName` set to the event name).

### Universal fields

| Field              | Default | Description                                                                                                                        |
|--------------------|---------|------------------------------------------------------------------------------------------------------------------------------------|
| `continue`         | `true`  | `false` stops Claude processing entirely after the hook runs. **Takes precedence over every event-specific decision field**        |
| `stopReason`       | none    | shown to the user when `continue` is `false`. **Not shown to Claude**                                                              |
| `suppressOutput`   | `false` | **has no effect.** Accepted and ignored; successful stdout is never in the transcript anyway                                       |
| `systemMessage`    | none    | warning shown to the user. Can arrive as an `SDKInformationalMessage` under the Agent SDK or `--output-format stream-json`         |
| `terminalSequence` | none    | an escape sequence for Claude Code to emit for you. Restricted to OSC `0`/`1`/`2`/`9`/`99`/`777` and BEL; anything else is ignored |

### `terminalSequence`

Because hooks have no controlling terminal, this is the only way to fire a desktop notification, set a window
title, or ring the bell. Claude Code writes it through its own terminal path, which is race-free and works in
tmux, screen and on Windows.

Allowed: OSC 0/1/2 (titles), OSC 9 (iTerm2, ConEmu, Windows Terminal, WezTerm, including `9;4` taskbar progress),
OSC 99 (Kitty), OSC 777 (urxvt, Ghostty, Warp), bare BEL. Terminate with BEL or ST. Rejected: CSI cursor and
colour sequences, OSC palette, OSC 8 hyperlinks, OSC 52 clipboard, OSC 1337.

It works even on events that discard `systemMessage` and `continue`, such as `Notification` and `StopFailure`.
Two limits: it is ignored in non-interactive `-p` mode and in the Agent SDK, and a **command** `WorktreeCreate`
hook cannot return JSON at all because its stdout is read as the worktree path.

### `additionalContext`

Passes a string into Claude's context window, wrapped in a system reminder and inserted where the hook fired.
Claude reads it on the next model request; it is not a chat message.

Where the reminder lands:

| Event                                                              | Position                                           |
|--------------------------------------------------------------------|----------------------------------------------------|
| `SessionStart`, `Setup`, `SubagentStart`                           | start of the conversation, before the first prompt |
| `UserPromptSubmit`, `UserPromptExpansion`                          | alongside the submitted prompt                     |
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch` | next to the tool result                            |
| `Stop`, `SubagentStop`                                             | end of the turn; the conversation continues        |

Several hooks returning it for the same event all get through.

**Write it as factual statements, not imperative system instructions.** "The deployment target is production"
reads as project information; text framed as an out-of-band system command can trip Claude's prompt-injection
defenses, which surfaces the text to the user instead of treating it as context.

For instructions that never change, prefer CLAUDE.md: it loads without running a script.

On `--continue` or `--resume`, Claude Code **replays the saved text** for past turns rather than re-running the
hook, so timestamps and commit SHAs go stale. `SessionStart` does run again, with `source` set to `resume` (or
`fork` with `--fork-session`).

### Decision control, per event

| Events                                                                                                                                                | Pattern                           | Key fields                                                                                                        |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `UserPromptSubmit`, `UserPromptExpansion`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Stop`, `SubagentStop`, `ConfigChange`, `PreCompact` | top-level `decision`              | `decision: "block"` plus `reason`. `Stop`/`SubagentStop` also take `hookSpecificOutput.additionalContext`         |
| `TeammateIdle`, `TaskCompleted`                                                                                                                       | exit code or `continue: false`    | exit 2 blocks with stderr feedback; `{"continue": false, "stopReason": "..."}` stops the teammate entirely        |
| `TaskCreated`                                                                                                                                         | exit code or top-level `decision` | exit 2 or `decision: "block"` cancels the task. **`continue: false` is ignored**                                  |
| `PreToolUse`                                                                                                                                          | `hookSpecificOutput`              | `permissionDecision`: **`allow` / `deny` / `ask` / `defer`**, plus `permissionDecisionReason`                     |
| `PermissionRequest`                                                                                                                                   | `hookSpecificOutput`              | `decision.behavior`: `allow` / `deny` (an **object**, not a string)                                               |
| `PermissionDenied`                                                                                                                                    | `hookSpecificOutput`              | `retry: true`; ignored for no-verdict denials                                                                     |
| `WorktreeCreate`                                                                                                                                      | path return                       | command hook prints the path on **stdout**; HTTP hook returns `hookSpecificOutput.worktreePath`                   |
| `Elicitation`                                                                                                                                         | `hookSpecificOutput`              | `action`: `accept` / `decline` / `cancel`, plus `content` for accept                                              |
| `ElicitationResult`                                                                                                                                   | `hookSpecificOutput`              | `action`: `accept` / `decline` / `cancel`, plus `content` to override                                             |
| `MessageDisplay`                                                                                                                                      | `hookSpecificOutput`              | `displayContent` replaces the text on screen only; transcript and Claude keep the original                        |
| `SessionStart`, `Setup`, `SubagentStart`                                                                                                              | context only                      | `additionalContext`; `SessionStart` also takes `initialUserMessage`, `watchPaths`, `sessionTitle`, `reloadSkills` |
| `WorktreeRemove`, `Notification`, `SessionEnd`, `PostCompact`, `InstructionsLoaded`, `StopFailure`, `CwdChanged`, `DirectoryAdded`, `FileChanged`     | none                              | side effects only, such as logging or cleanup                                                                     |

The only value for a top-level `decision` is `"block"`. To allow, omit it or exit 0 with no JSON.

### Rewriting content rather than allowing or blocking

| Event               | Field                                                                              |
|---------------------|------------------------------------------------------------------------------------|
| `PreToolUse`        | `updatedInput` directly under `hookSpecificOutput`, replacing the tool's arguments |
| `PermissionRequest` | `updatedInput` **inside** the `decision` object                                    |
| `PostToolUse`       | `updatedToolOutput`, replacing the tool's result                                   |
| `UserPromptSubmit`  | cannot replace the prompt; only injects `additionalContext` alongside it           |

For redaction, intercept `PreToolUse` on the way out and `PostToolUse` on the way back.

### Choose one signalling style

Either use exit codes alone, or exit 0 and print JSON. If you mix them, exit 2 keeps its blocking effect and the
JSON is still read (except the elicitation case above).
