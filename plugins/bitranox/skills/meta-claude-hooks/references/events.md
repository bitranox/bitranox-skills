# The 31 hook events

Every event, what fires it, what its matcher filters, the fields it adds to the
[common input](io-contract.md#common-input-fields), and how it can answer.

Events fall into three cadences: **once per session** (`SessionStart`, `SessionEnd`), **once per turn**
(`UserPromptSubmit`, `Stop`, `StopFailure`), and **on every tool call** inside the agentic loop (`PreToolUse`,
`PostToolUse`). `EndConversation` calls skip both tool events.

Quick index by what you are trying to do:

| I want to...                                    | Event                                                           |
|-------------------------------------------------|-----------------------------------------------------------------|
| block or rewrite a tool call before it runs     | `PreToolUse`                                                    |
| decide a permission prompt on the user's behalf | `PermissionRequest`                                             |
| react after a tool ran, or rewrite its result   | `PostToolUse`, `PostToolUseFailure`                             |
| act once after a whole parallel batch           | `PostToolBatch`                                                 |
| inject context at session start                 | `SessionStart`, `Setup`                                         |
| vet or block a prompt                           | `UserPromptSubmit`, `UserPromptExpansion`                       |
| keep Claude working instead of stopping         | `Stop`, `SubagentStop`, `TeammateIdle`                          |
| **react to a file changing on disk**            | **`FileChanged`**                                               |
| react to a directory change                     | `CwdChanged`, `DirectoryAdded`                                  |
| guard configuration or instruction loading      | `ConfigChange`, `InstructionsLoaded`                            |
| hook compaction                                 | `PreCompact`, `PostCompact`                                     |
| own worktree creation or removal                | `WorktreeCreate`, `WorktreeRemove`                              |
| observe or gate tasks and subagents             | `TaskCreated`, `TaskCompleted`, `SubagentStart`, `SubagentStop` |
| notify a desktop or terminal                    | `Notification`, `StopFailure`                                   |
| intercept MCP user prompts                      | `Elicitation`, `ElicitationResult`                              |
| rewrite what is shown on screen                 | `MessageDisplay`                                                |
| clean up at the end                             | `SessionEnd`                                                    |

---

## Session lifecycle

### SessionStart

Fires when a session begins or resumes. **Cannot be blocked**; stderr goes to the user only.

Matcher: `startup`, `resume`, `clear`, `compact`, `fork`.

Input adds `source` (the same values as the matcher) and, **not guaranteed**, `model`. This is the only event that
can receive `model`, and there is no `$CLAUDE_MODEL`.

Plain-text stdout is added to Claude's context, so a hook that only loads context can just `echo` it.

Output fields beyond the universal set:

| Field                | Effect                                                                                                                                 |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| `additionalContext`  | string added at the start of the conversation, before the first prompt                                                                 |
| `initialUserMessage` | becomes the **first user message**. Applies in `-p` mode even with no prompt; a supplied prompt follows as the next turn               |
| `sessionTitle`       | same effect as `/rename`. Applies on `startup`, `resume`, `fork`; ignored on `clear` and `compact`                                     |
| `watchPaths`         | array of absolute paths to watch for `FileChanged` this session                                                                        |
| `reloadSkills`       | boolean. Re-scans skill and command directories after SessionStart hooks finish, so skills the hook installed work in the same session |

`reloadSkills` exists because skill discovery normally runs *before* SessionStart hooks finish, so files the hook
writes to `~/.claude/skills/` would otherwise appear only next session.

**`CLAUDE_ENV_FILE`**: SessionStart hooks get this path. `export` lines appended to it persist into every later
Bash command in the session. Append with `>>` so you do not clobber another hook's variables.

### Setup

Fires on `claude --init-only`, or `--init` / `--maintenance` in `-p` mode. For one-time preparation in CI or
scripts. **Cannot be blocked**; stderr to the user only.

Matcher: `init`, `maintenance`. Input adds `trigger`. Output: `additionalContext` only.

### SessionEnd

Fires when the session terminates. **Cannot be blocked**; no decision control.

Matcher: `clear`, `resume`, `logout`, `prompt_input_exit`, `other`. Input adds `reason`.

Claude Code **discards their JSON output**, `systemMessage` included.

**All SessionEnd hooks share a 1.5-second budget**, applied to session exit, `/clear`, and switching sessions
via interactive `/resume`. A longer per-hook `timeout` in a **settings file** raises the shared budget up to
60s; a timeout on a **plugin-provided** hook does not. `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` overrides the
budget explicitly, in milliseconds. Do cleanup that fits, or accept being cut off.

---

## Prompt handling

### UserPromptSubmit

Fires when a prompt is submitted, before Claude processes it. **Can block**: exit 2 blocks processing and
**erases the prompt**.

No matcher support. Input adds `prompt` (the submitted text). Note the field is `prompt`, not `user_input`.

Plain-text stdout **is** added to Claude's context. Decision control is the top-level `decision: "block"` plus
`reason`; `additionalContext` is injected alongside the prompt. It **cannot replace** the prompt.

Default `timeout` is lowered to 30 seconds for `command`, `http` and `mcp_tool` handlers.

### UserPromptExpansion

Fires when a user-typed command expands into a prompt, before it reaches Claude. **Can block** the expansion.

Matcher: your skill or command names. Input adds `expansion_type`, `command_name`, `command_args`,
`command_source`, `prompt`. Plain-text stdout reaches Claude. Top-level `decision` blocks.

### MessageDisplay

Fires while assistant message text is displayed. **Display only, cannot block.**

No matcher support. Input adds `turn_id`, `message_id`, `index`, `final`, `delta`.

`hookSpecificOutput.displayContent` replaces what appears **on screen only** - the transcript and what Claude sees
keep the original. Default `timeout` is lowered to **10 seconds**.

---

## Tool calls

### PreToolUse

Fires before a tool call executes. **Can block.**

Matcher: tool name (`Bash`, `Edit|Write`, `mcp__.*`). Input adds `tool_name`, `tool_input`, `tool_use_id`.

Decision control via `hookSpecificOutput`:

| Field                      | Values / effect                                  |
|----------------------------|--------------------------------------------------|
| `permissionDecision`       | **`allow`, `deny`, `ask`, `defer`**              |
| `permissionDecisionReason` | explanation shown with the decision              |
| `updatedInput`             | replaces the tool's arguments before it runs     |
| `additionalContext`        | extra context, delivered next to the tool result |

Exit 2 blocks regardless of JSON. Staying silent (exit 0, no output) does **not** approve: the call continues
through the normal permission flow. A hook can deny; it cannot rubber-stamp by silence.

A hook that times out does **not** block. Do not rely on a hook that may hang as a gate.

`tool_input` differs per tool. The reference documents schemas for `Bash`, `PowerShell`, `Write`, `Edit`, `Read`,
`Glob`, `Grep`, `WebFetch`, `WebSearch`, `Agent`, `AskUserQuestion` and `ExitPlanMode`; read the upstream section
when you depend on a specific field.

### PermissionRequest

Fires when a tool call needs a permission decision. **Exit 2 is not honoured** - the permission flow proceeds
unchanged. Decide through JSON.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `permission_suggestions` (with `type`, `rules`,
`toolName`, `ruleContent`, `behavior`, `destination`).

Decision control is `hookSpecificOutput.decision`, an **object**:

```json
{ "hookSpecificOutput": { "hookEventName": "PermissionRequest",
    "decision": { "behavior": "allow", "updatedInput": { "command": "npm run lint" } } } }
```

`behavior` is `allow` or `deny`. `updatedInput` lives **inside** the decision object here, unlike `PreToolUse`.

### PermissionDenied

Fires when auto mode denies a tool call. **Cannot block** - the denial already happened, and exit code and stderr
are ignored.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_use_id`, `reason`.

`hookSpecificOutput.retry: true` tells the model it may retry the denied call. It is **ignored for no-verdict
denials**.

### PostToolUse

Fires after a tool call succeeds. **Cannot block** - the tool already ran - but exit 2 shows stderr **to Claude**.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_response` (with `filePath`, `success`),
`tool_use_id`, `duration_ms`.

Top-level `decision: "block"` plus `reason` gives feedback. `updatedToolOutput` replaces the tool's result -
this is the inbound half of a redaction pair with `PreToolUse`.

### PostToolUseFailure

Fires after a tool call fails. **Cannot block**; exit 2 shows stderr to Claude.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt`, `duration_ms`.

### PostToolBatch

Fires after a whole batch of parallel tool calls resolves, before the next model call. **Can block**: exit 2 stops
the agentic loop.

No matcher support. Input adds `tool_calls`, an array whose entries carry `tool_name`, `tool_input`,
`tool_use_id`, `tool_response`. Use it when a check only makes sense once per batch rather than per call.

---

## Turn ends

### Stop

Fires when Claude finishes responding. **Can block**: exit 2 prevents stopping and continues the conversation.

No matcher support. Input adds `stop_hook_active`, `last_assistant_message`, `background_tasks` (entries with
`id`, `type`, `status`, `description`, `command`) and `session_crons` (with `schedule`, `recurring`, `prompt`).

**Use `last_assistant_message`, not the transcript**, for this turn's final text: the transcript lags.

`stop_hook_active` tells you a Stop hook already caused this continuation. Check it, or you can loop.

Decision control is top-level `decision: "block"` plus `reason`; `hookSpecificOutput.additionalContext` gives
non-error feedback that continues the conversation.

### StopFailure

Fires when the turn ends due to an API error. **Output and exit code are entirely ignored**, except
`terminalSequence`.

Matcher: `rate_limit`, `overloaded`, `authentication_failed`, `oauth_org_not_allowed`, `billing_error`,
`invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `unknown`.

Input adds `error`, `error_details`, `last_assistant_message`. Useful only for notification and logging.

### SubagentStart

Fires when a subagent is spawned. **Cannot be blocked**; stderr appears in the **subagent's own** transcript.

Matcher: agent type (`general-purpose`, `Explore`, `Plan`, custom names, `^my-plugin:reviewer$`).
Input adds `agent_id`, `agent_type`. Output: `additionalContext`.

### SubagentStop

Fires when a subagent finishes. **Can block**: exit 2 prevents it stopping.

Matcher: agent type. Input adds `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path`,
`last_assistant_message`, `background_tasks`, `session_crons`.

A `Stop` hook declared in **subagent frontmatter** is converted to `SubagentStop`.

### TeammateIdle

Fires when an agent-team teammate is about to go idle. **Can block**: exit 2 keeps it working.

No matcher support. Input adds `teammate_name`, `team_name`. `{"continue": false, "stopReason": "..."}` also
stops the teammate entirely.

---

## Tasks

### TaskCreated

Fires when a task is being created via `TaskCreate`. **Can block**: exit 2 or `decision: "block"` rolls the
creation back and returns the message to Claude. **`continue: false` is ignored here.**

No matcher support. Input adds `task_id`, `task_subject`, `task_description`, `teammate_name`, `team_name`.

### TaskCompleted

Fires when a task is being marked completed. **Can block**: exit 2 prevents the completion.

No matcher support. Same input fields as `TaskCreated`. Accepts exit code 2 or `continue: false`.

---

## Files, directories and configuration

### FileChanged

Fires when a watched file changes on disk. **Cannot be blocked.**

This is the event most people do not know exists. Claude Code uses a **filesystem watcher**, not tool-call
inspection, so it fires no matter what changed the file: an `Edit`, a `Bash` command, or a process outside Claude
Code entirely.

Input adds `file_path` (absolute) and `event`: `"change"`, `"add"` or `"unlink"`.

**The matcher does two jobs**, which is unique to this event:

1. **it builds the watch list** - the value is split on `|` and each segment is registered as a **literal
   filename** in the working directory. `".envrc|.env"` watches exactly those two. A regex is useless here:
   `^\.env` watches a file literally named `^\.env`.
2. **it filters which hook groups run**, by the standard matcher rules, against the changed file's basename.

`FileChanged` and `StopFailure` use the narrower exact-match set (letters, digits, `_`, `|` only), so any other
character - a hyphen, a space, a comma, **or the dot in a filename** - pushes the *filtering* half onto the regex
path. The two halves stay consistent: the watch list is always built from literal `|`-separated segments, while
filtering treats the same string as a regex. A dot is therefore harmless in practice, since `.` as a regex still
matches the literal dot in the basename, which is why upstream's own example is `"matcher": "data.csv"`.

`hookSpecificOutput.watchPaths` (array of absolute paths) replaces the dynamic watch list at runtime. Paths from
the `matcher` are always watched. **The watcher only starts once something names a file to watch**, so seed it
with a matcher naming at least one file, or with `SessionStart`/`CwdChanged` returning `watchPaths`. Give the
group that handles dynamic paths an **omitted** matcher: `"*"` also matches everything but gets registered in the
watch list as a literal file named `*`. To watch a file that is not in the working directory, name a
working-directory file in one group's matcher to start the watcher, and return the nested absolute path from a
`SessionStart` or `CwdChanged` hook's `watchPaths`.

**What it can return is narrower than it looks, and this is the trap.** Claude Code reads only `watchPaths` and
`systemMessage`, and **discards `continue`**. The `systemMessage` shows as a brief terminal notification **to the
user** and does not reach the SDK message stream.

`additionalContext` is **not** among the fields this event delivers - `FileChanged` does not appear in the
[placement table](io-contract.md#additionalcontext) at all. So a `FileChanged` hook **cannot put anything into
Claude's context by itself**. A hook that returns `additionalContext` here looks correct, exits 0, and silently
reaches nobody.

To make Claude aware of a file that changed, pair the two halves: let the `FileChanged` hook record the change
(a state file, or `CLAUDE_ENV_FILE`), and let a hook on an event that *can* inject - `UserPromptSubmit` or
`PreToolUse` - read that record and return `additionalContext`. Use `FileChanged` alone when notifying the
**user** is the actual goal.

`CLAUDE_ENV_FILE` is available here too.

> **Write the guard so the hook cannot retrigger itself.** A hook that rewrites its own watched file fires again
> on that rewrite. Test for exactly what you change (`grep -q $'\r$'` before stripping CRs), because a tool like
> `perl -i` rewrites the file even when it substitutes nothing, and a looser guard loops forever.

### CwdChanged

Fires when the working directory changes, for example when Claude runs `cd`. **Cannot be blocked**; stderr to the
user only. Useful for reactive environment management with direnv and similar.

No matcher support. Input adds `old_cwd` and `new_cwd`. Can return `watchPaths`.

### DirectoryAdded

Fires when a directory is added mid-session via `/add-dir` or the SDK `register_repo_root`. **Cannot be blocked**;
stderr goes to the debug log only.

Matcher: `slash_command`, `register_repo_root`. Input adds `directory` and `source`.

### ConfigChange

Fires when a configuration file changes during a session. **Can block**: exit 2 blocks the change from taking
effect, **except for `policy_settings`**.

Matcher: `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`.
Input adds `source` and `file_path`. Top-level `decision: "block"`.

### InstructionsLoaded

Fires when a CLAUDE.md or `.claude/rules/*.md` file is loaded, at session start and on lazy load.
**Exit code is ignored**; no decision control.

Matcher: `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`.
Input adds `file_path`, `memory_type`, `load_reason`.

---

## Compaction

### PreCompact

Fires before context compaction. **Can block**: exit 2 blocks compaction.

Matcher: `manual`, `auto`. Input adds `trigger` and `custom_instructions`. Top-level `decision: "block"`.

### PostCompact

Fires after compaction completes. **Cannot be blocked**; stderr to the user only.

Matcher: `manual`, `auto`. Input adds `trigger` and `compact_summary`.

---

## Worktrees

### WorktreeCreate

Fires when a worktree is being created via `--worktree`, `isolation: "worktree"`, or for a background session.
**Defining this hook replaces the default git behaviour.**

No matcher support. Input adds `name`.

This event does not follow the normal contract:

- **any non-zero exit code fails creation**, not just exit 2
- a **command** hook prints the **worktree path on stdout** and therefore cannot return JSON at all (so
  `terminalSequence` is unavailable to it)
- an **HTTP** hook returns `hookSpecificOutput.worktreePath` and can use JSON normally
- a failure or a missing path fails creation

### WorktreeRemove

Fires when a worktree is removed at session exit, when a subagent finishes, or when a background session is
deleted. **Cannot be blocked**; failures are logged in debug mode only. No decision control.

No matcher support. Input adds `worktree_path`.

---

## MCP elicitation

### Elicitation

Fires when an MCP server requests user input during a tool call. **Can block**: exit 2 denies the elicitation.

Matcher: MCP server name. Input adds `mcp_server_name`, `message`, `mode`, `requested_schema`.

`hookSpecificOutput.action` is `accept`, `decline` or `cancel`; `content` supplies form field values on accept.
**On exit 2 the `hookSpecificOutput` is ignored.**

### ElicitationResult

Fires after the user responds, before the response goes back to the server. **Can block**: exit 2 makes the action
a decline.

Matcher: MCP server name. Input adds `mcp_server_name`, `action`, `content`, `elicitation_id`.
`hookSpecificOutput.action` and `content` can override the response. Exit 2 ignores `hookSpecificOutput`.

---

## Notifications

### Notification

Fires when Claude Code sends a notification. **Exit code and stderr are ignored**; no decision control.

Matcher: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_url_dialog`,
`elicitation_complete`, `elicitation_response`, `agent_needs_input`, `agent_completed`,
`quota_auto_resume_fired`, `quota_auto_resume_stale`, `quota_auto_resume_disabled` - the three quota values fire on claude.ai usage-limit
auto-resume and need CLI 2.1.234 or newer.

Input adds `message`, `title`, `notification_type`.

`terminalSequence` still works here even though `systemMessage` and `continue` are discarded, which makes this the
event for desktop notifications.

`permission_prompt` is timed differently in sessions that route permission requests to the Agent SDK
`canUseTool` callback, which is how Claude Desktop and the VS Code extension host Claude Code: expect it about
six seconds after Claude asks, it is not deferred while you type, and it does not run at all if you or a
`PermissionRequest` hook answer sooner. Set `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS` to `1` to turn
it off there. Before v2.1.233 it did not fire in those sessions at all.

In a TERMINAL session, `permission_prompt` also fires for a sandboxed command's network request,
but only from CLI v2.1.246. A hook written against an older build sees nothing for that case, so
do not read its silence as the request not having happened.
