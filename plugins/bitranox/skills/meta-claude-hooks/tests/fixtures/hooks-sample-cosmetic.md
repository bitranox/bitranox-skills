> ## Documentation Index
> Fetch the complete documentation index at: https://example.com/docs/llms.txt

# Hooks reference

A reference covering hook events, the configuration schema, and exit code handling.

## Configuration

You define hooks inside JSON settings files, at three levels of nesting.

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
```

| Field     | Required | Description               |
|-----------|----------|---------------------------|
| `if`      | no       | One permission rule       |
| `timeout` | no       | Seconds before cancelling |
| `type`    | yes      | The handler type          |

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
```

## Hook events

### SessionStart

This event fires for SessionStart; refer to the table above.

### Setup

This event fires for Setup; refer to the table above.

### InstructionsLoaded

This event fires for InstructionsLoaded; refer to the table above.

### UserPromptSubmit

This event fires for UserPromptSubmit; refer to the table above.

### UserPromptExpansion

This event fires for UserPromptExpansion; refer to the table above.

### MessageDisplay

This event fires for MessageDisplay; refer to the table above.

### PreToolUse

This event fires for PreToolUse; refer to the table above.

### PermissionRequest

This event fires for PermissionRequest; refer to the table above.

### PostToolUse

This event fires for PostToolUse; refer to the table above.

### PostToolUseFailure

This event fires for PostToolUseFailure; refer to the table above.

### PostToolBatch

This event fires for PostToolBatch; refer to the table above.

### PermissionDenied

This event fires for PermissionDenied; refer to the table above.

### Notification

This event fires for Notification; refer to the table above.

### SubagentStart

This event fires for SubagentStart; refer to the table above.

### SubagentStop

This event fires for SubagentStop; refer to the table above.

### TaskCreated

This event fires for TaskCreated; refer to the table above.

### TaskCompleted

This event fires for TaskCompleted; refer to the table above.

### Stop

This event fires for Stop; refer to the table above.

### StopFailure

This event fires for StopFailure; refer to the table above.

### TeammateIdle

This event fires for TeammateIdle; refer to the table above.

### ConfigChange

This event fires for ConfigChange; refer to the table above.

### CwdChanged

This event fires for CwdChanged; refer to the table above.

### DirectoryAdded

This event fires for DirectoryAdded; refer to the table above.

### FileChanged

This event fires for FileChanged; refer to the table above.

### WorktreeCreate

This event fires for WorktreeCreate; refer to the table above.

### WorktreeRemove

This event fires for WorktreeRemove; refer to the table above.

### PreCompact

This event fires for PreCompact; refer to the table above.

### PostCompact

This event fires for PostCompact; refer to the table above.

### SessionEnd

This event fires for SessionEnd; refer to the table above.

### Elicitation

This event fires for Elicitation; refer to the table above.

### ElicitationResult

This event fires for ElicitationResult; refer to the table above.

## Security considerations

Command hooks execute with your full user permissions.

