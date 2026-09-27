# The 33 hook events

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
| inject context at session start                 | `SessionStart`                                                  |
| vet or block a prompt                           | `UserPromptSubmit`, `UserPromptExpansion`                       |
| keep Claude working instead of stopping         | `Stop`, `SubagentStop`, `TeammateIdle`                          |
| **react to a file changing on disk**            | **`FileChanged`**                                               |
| react to a directory change                     | `CwdChanged`, `DirectoryAdded`                                  |
| guard configuration or instruction loading      | `ConfigChange`, `InstructionsLoaded`                            |
| hook compaction                                 | `PreCompact`, `PostCompact`                                     |
| gate a model switch, or follow the model        | `PreModelSwitch`, `PostModelSwitch`                             |
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

Matcher: `startup`, `resume`, `clear`, `compact`, `fork`. Before v2.1.214 a forked session reported `resume`.

At launch, on `--continue`/`--resume` and on `/clear` the hooks run **in the background**: the user can type at
once, but the first response waits for the hooks. An interactive `/resume` waits for them instead. If the user
runs `/clear` or switches conversation while they are still running, **nothing they return applies**.

Input adds `source` (the same values as the matcher) and, **not guaranteed**, `model` - it can be omitted, for
example after `/clear`, so check for it before reading it. This is the only event that receives `model`, and there is
no `$CLAUDE_MODEL`. To follow the model as it changes during a session, use
[`PostModelSwitch`](#postmodelswitch), which receives `from_model` and `to_model`; to gate a switch, use
[`PreModelSwitch`](#premodelswitch).

Also optional: `agent_type` (with `claude --agent <name>`) and `session_title` (the title already set, via `--name`
or `/rename` - check it before returning `sessionTitle`, so you do not overwrite one the user chose). On `resume` or
`fork` with at least one earlier response, v2.1.251+ adds four cost fields: `seconds_since_last_response`,
`context_tokens`, `prompt_cache_likely_expired` and `estimated_cache_write_usd`, so a hook can report what resuming
a stale conversation will cost before the first request.

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

Fires on `claude --init-only`, or `--init` / `--maintenance` in `-p` mode, never on a normal startup. For one-time
preparation in CI or scripts. **Cannot be blocked**, and its exit code and stderr are ignored.

Matcher: `init`, `maintenance`. Input adds `trigger`.

**Setup has no output channel.** On every exit code Claude Code discards its JSON output, `additionalContext`,
`systemMessage` and `continue` included; under `-p` its stdout, stderr and exit code appear only as `hook_response`
events with `--output-format stream-json --verbose`. Only `command` hooks run: an `mcp_tool` hook is accepted in
the configuration but **always skipped**, because Setup fires before MCP servers are available. `CLAUDE_ENV_FILE`
works here as on `SessionStart`. Because Setup does not fire on every launch, a plugin cannot rely on it to install
a dependency; check for the dependency on first use instead.

### SessionEnd

Fires when the session terminates. **Cannot be blocked**; no decision control.

Matcher: `clear`, `resume`, `logout`, `prompt_input_exit`, `other`. Input adds `reason`.

Claude Code **discards their JSON output**, `systemMessage` included.

**All SessionEnd hooks share a 1.5-second budget**, applied to session exit, `/clear`, and switching sessions
via interactive `/resume`. A longer per-hook `timeout` in a **settings file** raises the shared budget up to
60s; a timeout on a **plugin-provided** hook does not. Raising the budget that way does **not** lengthen a hook
without its own `timeout`: that one still gets 1.5 seconds. `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` overrides the
budget explicitly, in milliseconds, and from v2.1.268 also becomes the timeout of every hook without its own (before
that it raised only the overall budget). Do cleanup that fits, or accept being cut off.

---

## Prompt handling

### UserPromptSubmit

Fires when a prompt is submitted, before Claude processes it. **Can block**: exit 2 blocks processing and
**erases the prompt**.

No matcher support. Input adds `prompt` (the submitted text). Note the field is `prompt`, not `user_input`.
Pasted text arrives expanded in place, and in sessions that mark pasted text for Claude it sits between
`<pasted_content id="...">` and `</pasted_content id="...">` lines, which a parser must allow for.

Plain-text stdout **is** added to Claude's context. Decision control is the top-level `decision: "block"` plus
`reason`; `additionalContext` is injected alongside the prompt. It **cannot replace** the prompt. The block
`reason`, like exit-2 stderr, is shown **to the user only** and never reaches Claude's context. Two more outputs:
`sessionTitle` names the session, and `suppressOriginalPrompt: true` on a block omits the prompt text from the
block message.

Default `timeout` is lowered to 30 seconds for `command`, `http` and `mcp_tool` handlers. A timed-out one is
cancelled and its `additionalContext` discarded, and the prompt still goes through.

### UserPromptExpansion

Fires when a user-typed command expands into a prompt, before it reaches Claude. **Can block** the expansion.

Matcher: your skill or command names; an empty matcher fires on every prompt-type command. Input adds
`expansion_type` (`slash_command` or `mcp_prompt`), `command_name`, `command_args`, `command_source`, `prompt`.
Plain-text stdout reaches Claude. Top-level `decision` blocks.

> **Gating a skill needs two hooks.** A `PreToolUse` hook matching the `Skill` tool fires only when **Claude**
> calls it; a user typing `/skillname` bypasses `PreToolUse` entirely and fires `UserPromptExpansion` instead.

### MessageDisplay

Fires while assistant message text is displayed. **Display only, cannot block.**

No matcher support. Input adds `turn_id`, `message_id`, `index`, `final`, `delta`.

`hookSpecificOutput.displayContent` replaces what appears **on screen only** - the transcript and what Claude sees
keep the original. Default `timeout` is lowered to **10 seconds**.

Interactively it runs once per batch of completed lines. Under `-p` and the Agent SDK it runs **once per message**,
after it completes: `index` is `0`, `final` is `true`, and `delta` holds the whole message. Treat `final`, not a
non-empty `delta`, as the end-of-message signal: an interactive message ending on a newline has an empty final
`delta`.

---

## Tool calls

### PreToolUse

Fires before a tool call executes. **Can block.**

Matcher: tool name (`Bash`, `Edit|Write`, `mcp__.*`). Input adds `tool_name`, `tool_input`, `tool_use_id`.
For an MCP tool it also carries `mcp_server`, an object with the server's `name` and a `source` saying where the
server was defined (`plugin`, `sdk`, a scope such as `user` or `project`); v2.1.274+. **Base a trust decision on
`source`**, not on `name` or the `mcp__<server>__` prefix. The same object arrives on `PermissionRequest`,
`PostToolUse`, `PostToolUseFailure` and `PermissionDenied` for MCP tools.

> **`@` references never reach this hook.** Files the user references with `@` in a prompt are inserted while the
> prompt is built, with no tool call, so no `PreToolUse` hook fires for them - not even one matching `Read`. Protect
> a path from `@` with a `Read` deny rule.

Decision control via `hookSpecificOutput`:

| Field                      | Values / effect                                                                                                                                  |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `permissionDecision`       | **`allow`, `deny`, `ask`, `defer`**. Deny and ask **rules** are evaluated whatever the hook returns, so `allow` never loosens them               |
| `permissionDecisionReason` | for `allow` and `ask`, shown to the **user**, not Claude; for `deny`, shown to **Claude**; ignored for `defer`                                   |
| `updatedInput`             | replaces the **whole** input object - include the unchanged fields. Permission rules are evaluated against what you return, not what Claude sent |
| `additionalContext`        | extra context, delivered next to the tool result                                                                                                 |

Across several hooks the precedence is `deny` > `defer` > `ask` > `allow`. The top-level `decision`/`reason` form is
deprecated on this event (`approve` and `block` map to `allow` and `deny`).

- **`allow` does not skip every prompt.** Actions no permission mode auto-approves still prompt; `AskUserQuestion`
  and `ExitPlanMode` need `updatedInput` paired with it; and from v2.1.199 an MCP tool flagged
  `_meta["anthropic/requiresUserInteraction"]` keeps its approval prompt whatever the hook says.
- **`ask` forces a prompt even in auto mode** (v2.1.211+): the classifier may still deny, but it cannot approve
  silently. The prompt carries a source label: `[settings]`, `[plugin:<name>]` or `[skill]`.
- **`defer` works only under `-p` and only for a single tool call in the turn.** In an interactive session it is
  logged and ignored; with several tool calls in the turn it is ignored and the call proceeds through the normal
  permission flow. Either way it is not a deny.

Exit 2 blocks regardless of JSON. Staying silent (exit 0, no output) does **not** approve: the call continues
through the normal permission flow. A hook can deny; it cannot rubber-stamp by silence.

It fires **before any permission-mode check, in every mode**: a `deny` holds even under `bypassPermissions`,
`--dangerously-skip-permissions` and `dontAsk`, so it is the place for policy a user cannot switch off. The reverse
does not hold - hooks tighten permissions, they never loosen them past the rules.

A hook that times out does **not** block. Do not rely on a hook that may hang as a gate.

`tool_input` differs per tool. The reference documents schemas for `Bash`, `PowerShell`, `Write`, `Edit`, `Read`,
`Glob`, `Grep`, `WebFetch`, `WebSearch`, `Agent`, `AskUserQuestion` and `ExitPlanMode`; read the upstream section
when you depend on a specific field.

### PermissionRequest

Fires when a tool call needs a permission decision. **Exit 2 is not honoured** - the permission flow proceeds
unchanged. Decide through JSON. Where no prompt can be shown - a background subagent in `-p` mode - the hooks
still run, and **if no hook decides, the call is denied**. In plain `-p` runs, or with `--permission-prompt-tool`,
there is no prompt for this hook to answer unless an Agent SDK `canUseTool` callback supplies one; decide with
`PreToolUse` there instead.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `permission_suggestions` (with `type`, `rules`,
`toolName`, `ruleContent`, `behavior`, `destination`).

Decision control is `hookSpecificOutput.decision`, an **object**:

```json
{ "hookSpecificOutput": { "hookEventName": "PermissionRequest",
    "decision": { "behavior": "allow", "updatedInput": { "command": "npm run lint" } } } }
```

`behavior` is `allow` or `deny`. `updatedInput` lives **inside** the decision object here, unlike `PreToolUse`.
The rest of the decision object:

| Field                | With    | Effect                                                                                                          |
|----------------------|---------|-----------------------------------------------------------------------------------------------------------------|
| `updatedInput`       | `allow` | replaces the input; re-checked against deny and ask rules. `allow` never overrides a matching deny rule         |
| `updatedPermissions` | `allow` | permission updates: `addRules`, `replaceRules`, `removeRules`, `setMode`, `addDirectories`, `removeDirectories` |
| `message`            | `deny`  | tells Claude why                                                                                                |
| `interrupt`          | `deny`  | `true` also stops Claude                                                                                        |

Each update entry names a `destination`: `session`, `localSettings`, `projectSettings` or `userSettings`. A
`setMode` to `bypassPermissions` has no effect unless bypass mode was available when the session launched.

### PermissionDenied

Fires when auto mode denies a tool call. **Cannot block** - the denial already happened, and exit code and stderr
are ignored.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_use_id`, `reason`.

`hookSpecificOutput.retry: true` tells the model it may retry the denied call. It is **ignored for no-verdict
denials**.

### PostToolUse

Fires after a tool call succeeds. **Cannot block** - the tool already ran - but exit 2 shows stderr **to Claude**.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `duration_ms`.
`tool_response` is the tool's own structured output, so its shape varies per tool: `Write` gives `filePath` and
`type` (`create`, ...), `Bash` gives `stdout`, `stderr`, `interrupted`, `isImage`.

Top-level `decision: "block"` plus `reason` gives feedback. `updatedToolOutput` replaces the tool's result -
this is the inbound half of a redaction pair with `PreToolUse`. It must match the tool's output shape, or a
built-in tool silently keeps its original output (see the [rewrite note](io-contract.md#rewriting-content-rather-than-allowing-or-blocking)).

For `Bash`, v2.1.269+ can add `tool_response.bashEditDiff`: the files a command changed in a Git repository
(`changedFiles`, up to 5 diffs in `files`, plus `moreFiles`, `unavailable`, `skipped`, `shared`). It is recorded in
auto and `bypassPermissions` mode, or in any mode with the `bashEditDiffEnabled` setting. It is best effort and in
public beta, so use it to find what to review, **not to enforce a policy**.

### PostToolUseFailure

Fires after a tool call fails. **Cannot block**; exit 2 shows stderr to Claude.

Matcher: tool name. Input adds `tool_name`, `tool_input`, `tool_use_id`, `error`, `is_interrupt`, `duration_ms`.

It fires only for a tool that **started executing**. An unknown tool name or input that fails validation fires
neither `PreToolUse` nor this event; a permission denial fires `PreToolUse` but not this event; and a
user cancelling a running tool does not fire it either.

### PostToolBatch

Fires after a whole batch of parallel tool calls resolves, before the next model call. **Can block**: exit 2 stops
the agentic loop.

No matcher support. Input adds `tool_calls`, an array whose entries carry `tool_name`, `tool_input`,
`tool_use_id`, `tool_response`. Use it when a check only makes sense once per batch rather than per call.

Here `tool_response` is **not** `PostToolUse`'s structured object: it is the serialized `tool_result` content the
model sees, a string or content-block array (for `Read`, line-number-prefixed text).

---

## Turn ends

### Stop

Fires when Claude finishes responding. **Can block**: exit 2 prevents stopping and continues the conversation.

No matcher support. Input adds `stop_hook_active`, `last_assistant_message`, `background_tasks` (entries with
`id`, `type`, `status`, `description`, `command`) and `session_crons` (with `schedule`, `recurring`, `prompt`).

**Use `last_assistant_message`, not the transcript**, for this turn's final text: the transcript lags.

`stop_hook_active` tells you a Stop hook already caused this continuation. Check it, or you can loop.

**A Stop block is capped at eight in a row.** After Stop hooks have continued the turn eight consecutive times -
by `decision: "block"` or by `additionalContext`, which goes through the same loop protection -
Claude Code overrides the next block and ends the turn anyway, so a hook that needs many iterations to converge
silently stops being obeyed. `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` raises the cap (`0` disables it); it applies to
`SubagentStop` as well.

Decision control is top-level `decision: "block"` plus `reason`; `hookSpecificOutput.additionalContext` gives
non-error feedback that continues the conversation.

### StopFailure

Fires when the turn ends due to an API error. **Output and exit code are entirely ignored**, except
`terminalSequence`.

Matcher: `rate_limit`, `overloaded`, `authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`,
`billing_error`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `cloud_credential_error`,
`unknown`. `cloud_credential_error` needs v2.1.267+; older builds report a credential-load failure as
`server_error` or `unknown`.

Input adds `error`, `error_details`, `last_assistant_message` - here the API error string itself, not Claude's
output. Useful only for notification and logging.

### SubagentStart

Fires when a subagent is spawned, when Claude resumes a subagent, and each time an in-process agent-team teammate
handles a new message. **Cannot be blocked**; stderr appears in the **subagent's own** transcript. When it fires
again for the same subagent, its `additionalContext` is injected only if the earlier copy is gone (for example
after auto-compaction), so a re-run does not stack duplicates.

Matcher: agent type (`general-purpose`, `Explore`, `Plan`, custom names, `^my-plugin:reviewer$`).
Input adds `agent_id`, `agent_type`. Output: `additionalContext`.

### SubagentStop

Fires when a subagent finishes. **Can block**: exit 2 prevents it stopping.

Matcher: agent type. Input adds `stop_hook_active`, `agent_id`, `agent_type`, `agent_transcript_path`,
`last_assistant_message`, `background_tasks`, `session_crons`.

A `Stop` hook declared in **subagent frontmatter** is converted to `SubagentStop`.

A block (`decision: "block"` with `reason`, or exit-2 stderr) keeps the subagent running and delivers the reason
**to the subagent** as its next instruction. To put context into the parent session instead, use a `PostToolUse`
hook on the `Agent` tool.

It also fires for Claude Code's **internal** agents (prompt suggestions, `/btw` side questions). For those,
`agent_type` is the session's own agent name, or an empty string when there is none. A matcher naming agent types
never matches an empty `agent_type`; an omitted, `""` or `"*"` matcher does, so an unfiltered `SubagentStop` hook
sees these runs too.

From v2.1.271 a subagent using the `SubagentHandback` tool delivers its report through that tool, and
`last_assistant_message` holds only its closing text, **not the report**. Read the report as `tool_input.message`
from a `PreToolUse` or `PostToolUse` hook matched on `SubagentHandback`.

### TeammateIdle

Fires when an agent-team teammate is about to go idle. **Can block**: exit 2 keeps it working.

No matcher support. Input adds `teammate_name` and `team_name` (deprecated, to be removed).
`{"continue": false, "stopReason": "..."}` also stops the teammate entirely.

---

## Tasks

### TaskCreated

Fires when a task is being created via `TaskCreate`. **Can block**: exit 2 or `decision: "block"` rolls the
creation back and returns the message to Claude. **`continue: false` is ignored here.**

No matcher support. Input adds `task_id`, `task_subject`, `task_description`, `teammate_name`, `team_name`
(deprecated, to be removed).

### TaskCompleted

Fires when a task is being marked completed - either an agent marks it through the `TaskUpdate` tool, or an
agent-team teammate finishes its turn with tasks still in progress. **Can block**: exit 2 prevents the completion
in both cases.

No matcher support. Same input fields as `TaskCreated`. `continue: false` stops the teammate only in the teammate
case; when `TaskUpdate` triggered the event it is **ignored**, and only exit 2 blocks.

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

`CLAUDE_ENV_FILE` is available here too, but what a `FileChanged` hook writes to it lasts only until the next
`CwdChanged`, when Claude Code clears it.

> **Write the guard so the hook cannot retrigger itself.** A hook that rewrites its own watched file fires again
> on that rewrite. Test for exactly what you change (`grep -q $'\r$'` before stripping CRs), because a tool like
> `perl -i` rewrites the file even when it substitutes nothing, and a looser guard loops forever.

### CwdChanged

Fires when the working directory changes, for example when Claude runs `cd`. **Cannot be blocked**; stderr to the
user only. Useful for reactive environment management with direnv and similar.

No matcher support. Input adds `old_cwd` and `new_cwd`. Can return `watchPaths`. `CLAUDE_ENV_FILE` is available;
variables written to it persist into later Bash commands until the next `CwdChanged`, when they are cleared.

### DirectoryAdded

Fires when a directory is added mid-session via `/add-dir` or the SDK `register_repo_root`. **Cannot be blocked** -
the add has already completed - and Claude Code does not wait for the hook: it runs in the background with the
600-second default timeout. It does not fire for `--add-dir` at startup (`SessionStart` covers those), for the
`/permissions` Workspace tab, or for a directory already inside a working directory.

Matcher: `slash_command`, `register_repo_root`. Input adds `directory` and `source`.

`continue` is discarded. On `slash_command` the hook's `systemMessage` is delivered **to Claude** as context on the
next turn rather than shown to you; on `register_repo_root` it goes to the debug log only.

### ConfigChange

Fires when a configuration file changes during a session. **Can block**: exit 2 blocks the change from taking
effect, **except for `policy_settings`**.

Matcher: `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`.
Input adds `source` and `file_path`. Top-level `decision: "block"`.

**A blocked change is silent.** `reason` is accepted but never shown, and neither is exit-2 stderr: neither you nor
Claude sees a message, only the debug log gets a line. `policy_settings` fires only when `managed-settings.json` or a
file in `managed-settings.d/` changes; server-managed settings and macOS or Windows OS policy are applied without
running any `ConfigChange` hook.

### InstructionsLoaded

Fires when a CLAUDE.md or `.claude/rules/*.md` file is loaded, at session start and on lazy load.
**Exit code is ignored**; no decision control.

Matcher: `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`.
Input adds `file_path`, `memory_type`, `load_reason`, and optionally `globs` (for `path_glob_match`),
`trigger_file_path` (for lazy loads) and `parent_file_path` (for `include`). It does not fire when Claude reads
`AGENTS.md` directly through the Project instructions setting; it does when a `CLAUDE.md` imports it or is a
symlink to it.

---

## Compaction

### PreCompact

Fires before context compaction. **Can block**: exit 2 blocks compaction.

Matcher: `manual`, `auto`. Input adds `trigger` and `custom_instructions`. Top-level `decision: "block"`.

Blocking an `auto` compaction only skips it when it was proactive. When compaction was triggered to recover from
a context-limit error the API already returned, blocking it surfaces that error and **the request fails**.

### PostCompact

Fires after compaction completes. **Cannot be blocked**; stderr to the user only.

Matcher: `manual`, `auto`. Input adds `trigger` and `compact_summary`.

---

## Model switches

Both events need CLI v2.1.251 or later. They are how a hook follows the model: `SessionStart` may carry
`model`, but only these two see it change mid-session.

**The matcher** is compared against the **canonical name of the model being switched to** (from `to_model`),
ignoring any `[1m]` suffix. An alias such as `opus`, a dated ID and a provider ID such as an Amazon Bedrock
one all resolve to one canonical name, so `claude-opus-5` covers every spelling. Write an exact name, a `|` list
(`claude-opus-4-6|claude-opus-5`) or a regex (`.*opus.*`).

> **A target with no canonical name runs every hook, matcher or not.** A custom model ID that only your LLM
> gateway knows cannot be canonicalised, so Claude Code runs every `PreModelSwitch` hook for it. A blocking
> hook must re-check `to_model` from its input rather than trust the matcher alone.

### PreModelSwitch

Fires before Claude Code applies a model switch **that you or a client requested**: `/model <name>` and the
`/model` picker, the `Option+P`/`Alt+P` picker, the Model setting in `/config`, turning on fast mode when that
changes the model, and a `set_model` (or model change in `apply_flag_settings`) from an Agent SDK host or Remote
Control. It does **not** fire for switches Claude Code makes on its own - an automatic model fallback, or the
model restored on resume. Those reach `PostModelSwitch` only, so a `PreModelSwitch` policy cannot stop them.

**Can block.** Exit 2 or top-level `decision: "block"` cancels the switch, with stderr shown to the user.

A blocking hook, nested the usual three levels deep. The matcher narrows when it runs; the command still re-checks
`to_model`, because a target with no canonical name runs the hook whatever the matcher says:

```json
{
  "hooks": {
    "PreModelSwitch": [
      {
        "matcher": "claude-opus-4-6",
        "hooks": [
          { "type": "command",
            "command": "jq -e '.to_model | test(\"opus-4-6\")' > /dev/null && { echo 'Opus 4.6 is retired here.' >&2; exit 2; }; exit 0" }
        ]
      }
    ]
  }
}
```

Input adds:

| Field                       | Meaning                                                                                                                      |
|-----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `from_model`, `to_model`    | model IDs the switch changes from and to                                                                                     |
| `requested_model`           | what the request named: an alias, a full ID, or `null` for the default model                                                 |
| `source`                    | `command` (`/model <name>`, `/config`, fast mode), `picker`, or `sdk`                                                        |
| `context_tokens`            | tokens the next request re-sends as its prompt; `0` before the first response                                                |
| `prompt_cache_warm`         | whether the current model's prompt cache is likely still warm, so the switch forfeits it                                     |
| `cache_ttl`                 | the prompt cache lifetime the session requests, `5m` or `1h`                                                                 |
| `estimated_cache_write_usd` | estimated cost of writing `context_tokens` to the cache on `to_model`, excluding the next response. An estimate, not a bill  |
| `pricing`                   | how that estimate was priced: `configured` (your organization's rates), `catalog` (list price), or `default` (unknown model) |

Decision control is `hookSpecificOutput.permissionDecision`, as on `PreToolUse` but narrower:

| `permissionDecision` | Effect                                                                                         |
|----------------------|------------------------------------------------------------------------------------------------|
| `allow`              | proceeds, and skips the confirmation Claude Code shows while the prompt cache is warm          |
| `deny`               | cancels; `permissionDecisionReason` is shown to the user, or returned as the `set_model` error |
| `ask`                | prompts the user to confirm, quoting `permissionDecisionReason`                                |

`defer`, `updatedInput` and `additionalContext` are **not** accepted. Across several hooks, `deny` beats `ask`
beats `allow`. **`ask` is a refusal everywhere except interactive `/model`** - under `-p`, from `/config` and
for a `set_model` request there is no prompt to show, so it cancels the switch.

`systemMessage` is shown to the user whatever the decision, so a cost-report hook can print
`{"systemMessage": "..."}` and exit 0.

> **A timeout here blocks.** A `PreModelSwitch` hook that does not answer before its timeout cancels the
> switch - the opposite of `PreToolUse`, where a timed-out command hook lets the call through. The default
> timeout for `command`, `http` and `mcp_tool` is lowered to **30 seconds**; `prompt` and `agent` handlers are
> not supported on this event.

An exit code other than 0 or 2 with no JSON decision does **not** block: stderr is shown and the switch applies.

### PostModelSwitch

Fires after the session's model changed, **whatever changed it**: a requested switch, an automatic fallback,
`opusplan` entering or leaving plan mode, or the model restored on resume. It does not fire when a model from a
fallback chain serves a single turn, because the session's model is unchanged. **Cannot block** - the model has
already switched; exit-2 stderr renders as a `<hook name> hook error` notice to the user, and Claude does not
see it.

Input: the same fields as `PreModelSwitch`, with two more `source` values: `auto` (a fallback or other change
Claude Code made itself, where `requested_model` is `null`) and `resume` (where `requested_model` is the restored
setting).

Plain-text stdout on exit 0, or `additionalContext` from JSON, reaches Claude **with the next request after the
switch**. This is the event for model-specific guidance without editing CLAUDE.md. Two delivery limits: if the
hook has not finished five seconds after the next prompt is sent, its output rides the request after that; and
if the model changes several times before the next request, only the output for the last switch's target is
delivered. Default timeout for `command`, `http` and `mcp_tool` is **30 seconds**.

---

## Worktrees

### WorktreeCreate

Fires when a worktree is being created via `--worktree`, `isolation: "worktree"`, or for a background session.
**Defining this hook replaces the default git behaviour.**

No matcher support. Input adds `name`.

This event does not follow the normal contract:

- **any non-zero exit code fails creation**, not just exit 2
- a **command** hook prints the **worktree path** as the last non-empty line of stdout (ANSI codes stripped, so a
  shell banner before it is harmless) and therefore cannot return JSON at all (so `terminalSequence` is
  unavailable to it). Send any other output to stderr
- an **HTTP** hook returns `hookSpecificOutput.worktreePath` and can use JSON normally
- a failure or a missing path fails creation
- a relative path is resolved against the hook's directory; one that is not an enterable directory exits the
  session with code 1. From v2.1.216 an absolute path containing `.` or `..`, or any path through a symlink below
  the repository root, is refused
- `.worktreeinclude` is not processed, so the hook must copy files such as `.env` itself

### WorktreeRemove

Fires when a worktree is removed at session exit, when a subagent finishes, or when a background session is
deleted. JSON output is discarded.

No matcher support. Input adds `worktree_path`.

**The exit code decides the outcome.** Any non-zero exit fails the removal if the directory at `worktree_path`
still exists afterwards: the worktree stays on disk with the hook's stderr in the debug log, and a background
session being deleted stays too. Exit non-zero only when you mean to keep the worktree.

---

## MCP elicitation

### Elicitation

Fires when an MCP server requests user input during a tool call. **Can block**: exit 2 denies the elicitation.

Matcher: MCP server name. Input adds `mcp_server_name`, `message`, and optional `mode` (`form` or `url`), `url`,
`elicitation_id`, `requested_schema`.

`hookSpecificOutput.action` is `accept`, `decline` or `cancel`; `content` supplies form field values on accept.
**On exit 2 the `hookSpecificOutput` is ignored**, and the stderr is shown nowhere.

### ElicitationResult

Fires after the user responds, before the response goes back to the server. **Can block**: exit 2 makes the action
a decline.

Matcher: MCP server name. Input adds `mcp_server_name`, `action`, and optional `mode`, `elicitation_id`, `content`.
`hookSpecificOutput.action` and `content` can override the response. Exit 2 ignores `hookSpecificOutput`, and its
stderr is shown nowhere.

---

## Notifications

### Notification

Fires when Claude Code sends a notification. **Exit code and stderr are ignored**; no decision control.

Matcher: `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_url_dialog`,
`elicitation_complete`, `elicitation_response`, `agent_needs_input`, `agent_completed`,
`quota_auto_resume_fired`, `quota_auto_resume_stale`, `quota_auto_resume_disabled`. Version floors:
`agent_needs_input` and `agent_completed` need v2.1.198 (and `agent_needs_input` for a teammate's terminal setup
question v2.1.248); the three quota values, which fire on claude.ai usage-limit auto-resume, need v2.1.234.

Input adds `message`, `title`, `notification_type`.

`terminalSequence` still works here even though `systemMessage` and `continue` are discarded, which makes this the
event for desktop notifications.

`permission_prompt` is timed differently in sessions that route permission requests to the Agent SDK
`canUseTool` callback, which is how Claude Desktop and the VS Code extension host Claude Code: expect it about
six seconds after Claude asks, it is not deferred while you type, and it does not run at all if you or a
`PermissionRequest` hook answer sooner. Set `CLAUDE_CODE_DISABLE_PERMISSION_PROMPT_NOTIFY_HOOKS` to `1` to turn
it off there. Before v2.1.233 it did not fire in those sessions at all.

**In a terminal session these are timed like desktop notifications**, so they fire only when you seem to be away:
`permission_prompt`, `elicitation_dialog` and `elicitation_url_dialog` about six seconds after the dialog appears
with no keystroke (each keystroke defers it), and `idle_prompt` about 60 seconds after the response, only if you
have not typed since, and never while waiting out a usage limit. For an immediate signal when Claude asks for
permission, use `PermissionRequest`.

In a TERMINAL session, `permission_prompt` also fires for a sandboxed command's network request,
but only from CLI v2.1.246. A hook written against an older build sees nothing for that case, so
do not read its silence as the request not having happened.
