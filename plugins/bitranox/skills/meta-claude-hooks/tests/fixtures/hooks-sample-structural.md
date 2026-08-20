> ## Documentation Index
> Fetch the complete documentation index at: https://example.com/docs/llms.txt

# Hooks reference

Reference for hook events, configuration schema, and exit codes.

## Configuration

Hooks are defined in JSON settings files.

```json theme={null}
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "./x.sh" } ] }
    ]
  }
}
```

### Hook handler fields

```json theme={null}
{ "type": "command" }
{ "type": "http" }
{ "type": "mcp_tool" }
{ "type": "prompt" }
{ "type": "agent" }
{ "type": "webhook" }
```

| Field     | Required | Description               |
|-----------|----------|---------------------------|
| `type`    | yes      | the handler type          |
| `timeout` | no       | seconds before cancelling |
| `if`      | no       | one permission rule       |

## Hook input and output

Hooks receive JSON on stdin. The `CLAUDE_PROJECT_DIR` variable points at the project root.

```json theme={null}
  "session_id": "...",
  "cwd": "...",
  "hook_event_name": "...",
  "continue": "...",
  "stopReason": "...",
  "systemMessage": "...",
  "permissionDecision": "...",
  "additionalContext": "...",
  "updatedInput": "...",
  "newThing": "...",
```

## Hook events

### SessionStart

Fires for SessionStart. See the table above.

### Setup

Fires for Setup. See the table above.

### InstructionsLoaded

Fires for InstructionsLoaded. See the table above.

### UserPromptSubmit

Fires for UserPromptSubmit. See the table above.

### UserPromptExpansion

Fires for UserPromptExpansion. See the table above.

### MessageDisplay

Fires for MessageDisplay. See the table above.

### PreToolUse

Fires for PreToolUse. See the table above.

### PermissionRequest

Fires for PermissionRequest. See the table above.

### PostToolUse

Fires for PostToolUse. See the table above.

### PostToolUseFailure

Fires for PostToolUseFailure. See the table above.

### PostToolGroup

Fires for PostToolGroup. See the table above.

### PermissionDenied

Fires for PermissionDenied. See the table above.

### Notification

Fires for Notification. See the table above.

### SubagentStart

Fires for SubagentStart. See the table above.

### SubagentStop

Fires for SubagentStop. See the table above.

### TaskCreated

Fires for TaskCreated. See the table above.

### TaskCompleted

Fires for TaskCompleted. See the table above.

### Stop

Fires for Stop. See the table above.

### StopFailure

Fires for StopFailure. See the table above.

### TeammateIdle

Fires for TeammateIdle. See the table above.

### ConfigChange

Fires for ConfigChange. See the table above.

### CwdChanged

Fires for CwdChanged. See the table above.

### DirectoryAdded

Fires for DirectoryAdded. See the table above.

### FileChanged

Fires for FileChanged. See the table above.

### WorktreeCreate

Fires for WorktreeCreate. See the table above.

### WorktreeRemove

Fires for WorktreeRemove. See the table above.

### PreCompact

Fires for PreCompact. See the table above.

### PostCompact

Fires for PostCompact. See the table above.

### SessionEnd

Fires for SessionEnd. See the table above.

### Elicitation

Fires for Elicitation. See the table above.

### ElicitationResult

Fires for ElicitationResult. See the table above.

## Security considerations

Command hooks execute with your full user permissions.

