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
```

| Field     | Required | Description               |
|-----------|----------|---------------------------|
| `type`    | yes      | the handler type          |
| `timeout` | no       | seconds before cancelling |
| `if`      | no       | one permission rule       |

## Hook input and output

Hooks receive JSON on stdin. The `CLAUDE_PROJECT_DIR` variable points at the project root.
