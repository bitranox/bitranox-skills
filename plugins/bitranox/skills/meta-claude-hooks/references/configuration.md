# Configuration: where hooks live, how they match, what handlers they run

Three levels of nesting, always:

1. a **hook event** to respond to (`PreToolUse`, `Stop`, ...)
2. a **matcher group** that filters when it fires
3. one or more **hook handlers** that run when matched

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "if": "Bash(rm *)", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh", "args": [] }
        ]
      }
    ]
  },
  "disableAllHooks": false
}
```

## Where a hook can be defined

| Location                      | Scope                                             | Shareable                    |
|-------------------------------|---------------------------------------------------|------------------------------|
| `~/.claude/settings.json`     | all your projects                                 | no, local to the machine     |
| `.claude/settings.json`       | single project                                    | yes, commit it               |
| `.claude/settings.local.json` | single project                                    | no, gitignored               |
| Managed policy settings       | organization-wide                                 | yes, admin-controlled        |
| Plugin `hooks/hooks.json`     | while the plugin is enabled                       | yes, bundled with the plugin |
| Skill frontmatter             | the rest of the session once the skill is invoked | yes, in the skill file       |
| Subagent frontmatter          | only while that subagent runs                     | yes, in the subagent file    |

Entries **merge** across levels rather than replacing each other. User, project and local settings add hooks
without removing managed ones.

Hooks from settings, managed policy and plugins also run **inside subagents**: a subagent's tool call fires the
same `PreToolUse`/`PostToolUse` hooks, with `agent_id` and `agent_type` present in the input.

Cloud sessions on Claude Code on the web do not read your local `~/.claude/settings.json`; hooks there come from
the repo and from server-managed settings.

### Administrator restrictions

`allowManagedHooksOnly` blocks user, project, local and plugin hooks. Plugins force-enabled through managed
`enabledPlugins` are exempt. It also narrows `statusLine`, `fileSuggestion` and `subagentStatusLine` to managed
settings, and disables plugins with a `command` source unless `disableCommandPluginSources` is explicitly `false`.

Two allowlists apply to HTTP hooks from **every** source, managed included:

| Setting                  | Effect                                                            |
|--------------------------|-------------------------------------------------------------------|
| `allowedHttpHookUrls`    | an HTTP handler runs only if its URL matches the merged allowlist |
| `httpHookAllowedEnvVars` | only variables on this list are interpolated into hook headers    |

## Matcher patterns

How a matcher is evaluated depends on **which characters it contains**. This is the single most common source of
a hook that fires too widely.

| Matcher value                                     | Evaluated as                                     | Example                              |
|---------------------------------------------------|--------------------------------------------------|--------------------------------------|
| `"*"`, `""`, or omitted                           | match all                                        | fires on every occurrence            |
| only letters, digits, `_`, `-`, spaces, `,`, `\|` | exact string, or a list separated by `\|` or `,` | `Bash`; `Edit\|Write`; `Edit, Write` |
| contains any other character                      | JavaScript regular expression, **unanchored**    | `^Notebook`; `mcp__memory__.*`       |

The regex path uses `RegExp.prototype.test`, which succeeds on a match **anywhere** in the value. `Edit.*` matches
both `Edit` and `NotebookEdit`. Write `^Edit$` when you mean the whole string.

Version gates worth knowing:

- comma separators and surrounding whitespace need v2.1.191+
- hyphens in the exact-match set need v2.1.195+. Earlier, `code-reviewer` was an unanchored regex, so it also fired
  for `senior-code-reviewer`
- `FileChanged` and `StopFailure` use a **narrower** exact-match set: letters, digits, `_` and `|` only. A hyphen,
  space or comma there keeps the matcher on the regex path, and only `|` separates alternatives

Adding a `matcher` to an event that has no matcher support is **silently ignored**.

### What each event matches on

| Event                                                                                                                                                           | Matcher filters             | Example values                                                                                                                                                                             |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`                                                                      | tool name                   | `Bash`, `Edit\|Write`, `mcp__.*`                                                                                                                                                           |
| `SessionStart`                                                                                                                                                  | how the session started     | `startup`, `resume`, `clear`, `compact`, `fork`                                                                                                                                            |
| `Setup`                                                                                                                                                         | which CLI flag triggered it | `init`, `maintenance`                                                                                                                                                                      |
| `SessionEnd`                                                                                                                                                    | why the session ended       | `clear`, `resume`, `logout`, `prompt_input_exit`, `other`                                                                                                                                  |
| `Notification`                                                                                                                                                  | notification type           | `permission_prompt`, `idle_prompt`, `auth_success`, `elicitation_dialog`, `elicitation_url_dialog`, `elicitation_complete`, `elicitation_response`, `agent_needs_input`, `agent_completed` |
| `SubagentStart`, `SubagentStop`                                                                                                                                 | agent type                  | `general-purpose`, `Explore`, `Plan`, custom names, `^my-plugin:reviewer$`                                                                                                                 |
| `PreCompact`, `PostCompact`                                                                                                                                     | what triggered compaction   | `manual`, `auto`                                                                                                                                                                           |
| `ConfigChange`                                                                                                                                                  | configuration source        | `user_settings`, `project_settings`, `local_settings`, `policy_settings`, `skills`                                                                                                         |
| `DirectoryAdded`                                                                                                                                                | how the directory was added | `slash_command`, `register_repo_root`                                                                                                                                                      |
| `FileChanged`                                                                                                                                                   | literal filenames to watch  | `.envrc\|.env`                                                                                                                                                                             |
| `StopFailure`                                                                                                                                                   | error type                  | `rate_limit`, `overloaded`, `authentication_failed`, `oauth_org_not_allowed`, `billing_error`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `unknown`        |
| `InstructionsLoaded`                                                                                                                                            | load reason                 | `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`                                                                                                               |
| `UserPromptExpansion`                                                                                                                                           | command name                | your skill or command names                                                                                                                                                                |
| `Elicitation`, `ElicitationResult`                                                                                                                              | MCP server name             | your configured server names                                                                                                                                                               |
| `CwdChanged`, `UserPromptSubmit`, `PostToolBatch`, `Stop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `MessageDisplay` | **no matcher support**      | always fires                                                                                                                                                                               |

### Matching MCP tools

MCP tools appear in tool events as `mcp__<server>__<tool>`.

To match every tool from a server you **must** append `.*`. A matcher like `mcp__memory` contains only
exact-match characters, so it is compared as an exact string and matches nothing.

- `mcp__memory__.*` - all tools from the `memory` server
- `mcp__brave-search__.*` - server name containing a hyphen
- `mcp__.*__write.*` - any tool starting with `write`, from any server

A **plugin-bundled** server gets a scoped segment: `mcp__plugin_<plugin-name>_<server-name>__<tool>`. A matcher
written against the bare server key never fires. For plugin `my-plugin` bundling server key `db`, the matcher is
`mcp__plugin_my-plugin_db__.*`.

## Hook handler fields

Five handler types:

| Type       | What it does                                                                                     |
|------------|--------------------------------------------------------------------------------------------------|
| `command`  | runs a shell command; input on stdin, results via exit code and stdout                           |
| `http`     | POSTs the event JSON to a URL; the response body uses the same JSON output format                |
| `mcp_tool` | calls a tool on an **already-connected** MCP server; its text output is read like command stdout |
| `prompt`   | sends a prompt to a model for single-turn evaluation, returning JSON                             |
| `agent`    | spawns a subagent that may use Read, Grep, Glob before deciding. **Experimental, may change**    |

Handlers run **in the current directory**, with Claude Code's environment. A handler that needs the project
root must use `${CLAUDE_PROJECT_DIR}` rather than assuming a cwd.

All matching hooks run **in parallel**. The same handler defined in more than one settings file runs once; a
plugin's or skill's copy of the same handler stays separate.

### Common fields (all types)

| Field           | Required | Description                                                                                                                                                                                                                             |
|-----------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `type`          | yes      | `"command"`, `"http"`, `"mcp_tool"`, `"prompt"`, `"agent"`                                                                                                                                                                              |
| `if`            | no       | one permission rule, e.g. `"Bash(git *)"`, `"Edit(*.ts)"`. **Tool events only** (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionDenied`); on any other event a handler with `if` set **never runs** |
| `timeout`       | no       | seconds before cancelling. 600 for `command`/`http`/`mcp_tool`, 30 for `prompt`, 60 for `agent`                                                                                                                                         |
| `statusMessage` | no       | spinner message shown while it runs                                                                                                                                                                                                     |
| `once`          | no       | run once per session then remove. **Only honoured in skill frontmatter**; ignored in settings files and agent frontmatter                                                                                                               |

Timeout overrides by event: `UserPromptSubmit` lowers `command`/`http`/`mcp_tool` to 30s, `MessageDisplay` to 10s.
`SessionEnd` hooks share a **1.5-second budget** across all of them, raised to match a longer per-hook `timeout`
up to 60s.

`if` holds exactly one rule. There is no `&&`, `||` or list syntax; use a separate handler per condition.

For file tools, a single-segment directory pattern `"Edit(src/**)"` matches only `src` in the working directory.
Use `"Edit(**/src/**)"` to match at any depth. Before v2.1.214 the first form matched at any depth.

#### How a Bash `if` pattern actually matches

Leading `VAR=value` assignments are stripped before matching.

| `if` pattern       | Bash command           | Runs? | Why                                                                                       |
|--------------------|------------------------|-------|-------------------------------------------------------------------------------------------|
| `Bash(git *)`      | `FOO=bar git push`     | yes   | assignments stripped, `git push` matches                                                  |
| `Bash(git *)`      | `npm test && git push` | yes   | each subcommand is checked                                                                |
| `Bash(rm *)`       | `echo $(rm -rf /)`     | yes   | commands inside `$()` and backticks are checked                                           |
| `Bash(rm *)`       | `echo $(date)`         | no    | no subcommand matches                                                                     |
| `Bash(git push *)` | `echo $(date)`         | yes   | a pattern specifying more than the command name runs anyway on `$()`, backticks or `$VAR` |

The filter **fails open**, running your hook regardless of pattern, when the Bash command cannot be parsed.
Because `if` is best-effort, use the permission system, not a hook, to enforce a hard allow or deny.

### Command handler fields

| Field         | Required | Description                                                                                                                                              |
|---------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `command`     | yes      | shell command, or with `args` the executable to spawn                                                                                                    |
| `args`        | no       | argument list. Its presence switches to exec form: `command` is resolved on `PATH` and spawned with no shell                                             |
| `async`       | no       | run in the background without blocking                                                                                                                   |
| `asyncRewake` | no       | run in the background and wake Claude on exit code 2. Implies `async`. Its stderr, or stdout if stderr is empty, is shown to Claude as a system reminder |
| `shell`       | no       | `"bash"` or `"powershell"`. Defaults to `bash`, or `powershell` on Windows when Git Bash is absent. Ignored when `args` is set                           |

#### Exec form vs shell form

**Exec form** (`args` present): no shell at all. Each `args` element is exactly one argument, and path
placeholders are substituted as plain strings. Apostrophes, `$` and backticks pass through verbatim.

**Shell form** (`args` absent): `command` goes to a shell (`sh -c` on macOS/Linux, Git Bash on Windows, or
PowerShell when Git Bash is absent). Pipes, `&&`, redirects and globs work.

Use exec form whenever the hook references a path placeholder. Use shell form when you need shell features.

On Windows, exec form needs `command` to resolve to a real executable. The `.cmd`/`.bat` shims in
`node_modules/.bin` are not executables and cannot be spawned without a shell; invoke the script through `node`
instead, or use shell form.

In exec form, `command` is the executable name or path **only**. A bare name containing whitespace alongside
`args` logs a warning, because there is no executable named `node script.js`.

### HTTP handler fields

| Field            | Required | Description                                                                                                            |
|------------------|----------|------------------------------------------------------------------------------------------------------------------------|
| `url`            | yes      | URL to POST to                                                                                                         |
| `headers`        | no       | extra headers. Values interpolate `$VAR_NAME` or `${VAR_NAME}`                                                         |
| `allowedEnvVars` | no       | env var names permitted in header values. **Required for any interpolation**; unlisted references become empty strings |

The event JSON is the POST body with `Content-Type: application/json`.

### MCP tool handler fields

| Field    | Required | Description                                                                                                                            |
|----------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| `server` | yes      | a configured server name, or the scoped `plugin:<plugin-name>:<server-name>`. Must already be connected; the hook never triggers OAuth |
| `tool`   | yes      | tool name on that server                                                                                                               |
| `input`  | no       | arguments. String values support `${path}` substitution from the hook input, e.g. `"${tool_input.file_path}"`                          |

`SessionStart` and `Setup` typically fire before servers finish connecting, so hooks on those events should expect
a "not connected" error on the first run.

### Prompt and agent handler fields

| Field    | Required | Description                                                                                                   |
|----------|----------|---------------------------------------------------------------------------------------------------------------|
| `prompt` | yes      | prompt text. `$ARGUMENTS` is the hook input JSON. Escape a literal with a backslash: `\$1.00` renders `$1.00` |
| `model`  | no       | model to evaluate with. Defaults to a fast model                                                              |

## Referencing scripts by path

| Placeholder             | Points at                                                           |
|-------------------------|---------------------------------------------------------------------|
| `${CLAUDE_PROJECT_DIR}` | project root. Also set for stdio MCP servers and plugin LSP servers |
| `${CLAUDE_PLUGIN_ROOT}` | the plugin's install directory. **Changes on every plugin update**  |
| `${CLAUDE_PLUGIN_DATA}` | the plugin's persistent data directory, which survives updates      |

Both forms export these as environment variables on the spawned process, so a script can read
`process.env.CLAUDE_PLUGIN_ROOT` however it was launched.

Plugin hooks also substitute `${user_config.*}`, **in exec form only**. A shell-form plugin hook whose `command`
references it fails with an error instead of running; read `$CLAUDE_PLUGIN_OPTION_<KEY>` or add `args` to switch to
exec form. Before v2.1.207 shell form substituted it too.

## Hooks in skills and subagents

Same configuration format, in YAML frontmatter:

```yaml
---
name: secure-operations
description: Perform operations with security checks
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

All hook events are supported. The difference is lifetime:

- **Subagent hooks** run only while that subagent runs, and are removed when it finishes. A `Stop` hook declared
  here is converted to `SubagentStop`.
- **Skill hooks** are registered when the skill is invoked and keep running for the rest of the session, including
  later turns. Use `once: true` for a single run.

Trust differs between the two. A project **skill's** frontmatter hooks follow the settings-file trust rule and are
registered even in a `-p` run in an untrusted folder. A project **subagent's** frontmatter hooks run only after
the workspace trust dialog is accepted for the folder the agent file came from, and a `-p` session does not count
as accepting it. Before v2.1.218 these could run from untrusted folders.

## The `/hooks` menu

`/hooks` opens a **read-only** browser of configured hooks: every event with a count, drill-down into matchers,
and the full detail of each handler. It shows all five types with a `[type]` prefix and the source:
`User Settings`, `Project Settings`, `Local Settings`, `Plugin Hooks`, `Session Hooks`, `Built-in Hooks`.

Read-only means read-only: to change a hook, edit the settings JSON.

## Disabling and removing

Delete the entry to remove a hook. There is **no way to disable an individual hook** while keeping it configured.

`"disableAllHooks": true` turns them all off. Claude Code reads the value left after settings precedence applies,
so a `false` in a project's `.claude/settings.json` overrides a `true` in user settings. For a single run,
`--settings '{"disableAllHooks": true}'` takes precedence over project and local settings.

It respects the managed hierarchy: only `disableAllHooks` at the managed level can disable managed hooks.

Direct edits to settings files are normally picked up automatically by the file watcher.
