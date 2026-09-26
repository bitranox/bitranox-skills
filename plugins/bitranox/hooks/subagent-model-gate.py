#!/usr/bin/env python3
"""PreToolUse(Task|Agent) gate: subagents must carry an explicit model tier.

The Agent tool takes a subagent's model from the dispatch's `model`, else from the agent type's
own definition (`model:` in its frontmatter), else from the default - the session's model unless a
default subagent model is configured, usually the most capable and most expensive tier. Landing on
that default silently defeats per-role model tiering.
bitranox:process-agents-subagent-driven-development ("Concrete tiers") requires pinning the tier
explicitly: `haiku` (mechanical / scan), `sonnet` (default fan-out / bounded judgment), `opus`
(deep reasoning where being wrong is costly). Reasoning EFFORT is not a per-dispatch field - it
rides the agent-type definition or a Workflow agent() call - so picking the tier (plus the right
agent type) is also how effort is chosen.

Two enforcement levels:
- Normally: WARN (additionalContext on stdout, exit 0) - some dispatches legitimately inherit
  (a `fork` always inherits by design, and sometimes the session model is genuinely right). The
  warn rides `hookSpecificOutput.additionalContext` (no `permissionDecision`), which reaches the
  model as a system-reminder without blocking the dispatch; exit-0 stderr would not reach it.
- While a PLAN EXECUTION is armed in THIS session (a fresh `plan-execution` receipt written by
  `skill_receipt.py start plan-execution` in the session the event comes from - the
  plan-execution skills arm it at their step 0 and disarm with `skill_receipt.py end
  plan-execution` when the plan completes): DENY the dispatch with a reason, so no plan task runs
  on an unpinned model. Another session's plan never arms it here.

A dispatch counts as pinned when it carries `model`, or when its agent type's definition pins
one (anything but `inherit`). Definitions are resolved from three places, first match wins:
- `<plugin>:<name>` for THIS plugin -> `<plugin root>/agents/*.md`;
- a bare `<name>` -> `<project>/.claude/agents/*.md` (project from CLAUDE_PROJECT_DIR, else the
  event's `cwd`), then `~/.claude/agents/*.md` - a project definition shadows a user one.
Only the top level of each agents dir is read, and a definition is matched by its frontmatter
`name`. Another plugin's `<plugin>:<name>`, and any type found nowhere, is treated as unpinned -
the warn/deny below still applies to it.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken gate must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import os
import sys
from pathlib import Path

import skill_receipt

SUBAGENT_TOOLS = {"Task", "Agent"}
PLAN_RECEIPT = "plan-execution"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# Bounds for reading definitions: an agents dir is a handful of small files, so these only stop a
# pathological directory from making every dispatch slow.
_MAX_DEFINITIONS = 500
_FRONTMATTER_BYTES = 64 * 1024

_TIERS = (
    "Pin the tier per bitranox:process-agents-subagent-driven-development (Concrete tiers): "
    "`haiku` = mechanical / transcription / scan, `sonnet` = default fan-out and bounded judgment, "
    "`opus` = deep reasoning where being wrong is costly (architecture, synthesis, adversarial "
    "verify). Effort rides the agent type or a Workflow agent() call, not the dispatch - the tier "
    "(plus the right agent type) is how effort is chosen."
)

_WARN_MESSAGE = (
    "Subagent dispatched without an explicit `model`. " + _TIERS +
    " With no `model` on the dispatch and none pinned in the agent type's own definition, the"
    " subagent runs on the default model - the session model unless a default subagent model is"
    " configured, often the priciest - which silently defeats tiering. (Definitions are read from"
    " this plugin's agents/, <project>/.claude/agents and ~/.claude/agents; another plugin's agent"
    " types are not resolved.)"
)

_DENY_MESSAGE = (
    "DENIED: a plan execution is armed (fresh `plan-execution` receipt), and every dispatched "
    "subagent MUST pin `model` - on the dispatch, or in its agent type's own definition. "
    + _TIERS +
    " Re-dispatch with `model` set. When the plan is complete, disarm with "
    "`skill_receipt.py end plan-execution`."
)


def _frontmatter(path):
    """Top-level `key: value` pairs of a Markdown file's leading `---` block (keys lowercased),
    or {} when the file has no closed block. Stdlib only: a hook gets a bare interpreter, so no
    YAML library is available, and these definitions only ever need flat scalar keys."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(_FRONTMATTER_BYTES)
    except OSError:
        return {}
    # split("\n"), not splitlines(): the latter also breaks on U+2028 and form feed.
    lines = [line.rstrip("\r") for line in text.lstrip("\ufeff").split("\n")]
    if lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.split(" #", 1)[0].strip().strip("'\"").strip()
        fields.setdefault(key.strip().lower(), value)
    return {}                  # never closed: a body that merely starts with ---, not frontmatter


def _definition_in(agents_dir, name):
    """The frontmatter of the definition named `name` in `agents_dir`, or None."""
    try:
        candidates = sorted(Path(agents_dir).glob("*.md"))[:_MAX_DEFINITIONS]
    except OSError:
        return None
    for candidate in candidates:
        fields = _frontmatter(candidate)
        if fields.get("name", "").strip().lower() == name:
            return fields
    return None


def _plugin_name(plugin_root):
    try:
        data = json.loads((Path(plugin_root) / ".claude-plugin" / "plugin.json")
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    name = data.get("name") if isinstance(data, dict) else None
    return name.strip().lower() if isinstance(name, str) else ""


def agent_definition_model(subagent_type, project_dir=None, home=None, plugin_root=PLUGIN_ROOT):
    """The `model:` the agent type's own definition declares, or None when it declares none or no
    definition is found where this gate looks (see the module docstring)."""
    wanted = str(subagent_type or "").strip().lower()
    if not wanted:
        return None
    if ":" in wanted:
        plugin, _, name = wanted.partition(":")
        if not name or plugin != _plugin_name(plugin_root):
            return None
        dirs = [Path(plugin_root) / "agents"]
    else:
        name = wanted
        dirs = []
        if project_dir:
            dirs.append(Path(project_dir) / ".claude" / "agents")
        dirs.append(Path(home if home is not None else Path.home()) / ".claude" / "agents")
    for agents_dir in dirs:
        fields = _definition_in(agents_dir, name)
        if fields is not None:
            # The first definition found is the one the Agent tool uses, so a shadowing project
            # definition with no model decides even when a user one of that name pins one.
            return fields.get("model") or None
    return None


def _pins(model):
    return isinstance(model, str) and bool(model.strip()) and model.strip().lower() != "inherit"


def assess(tool_name, tool_input, plan_armed=False, definition_model=None):
    """Pure: return (action, message) with action in {'deny', 'warn', None}.

    A non-fork subagent dispatch with no `model`, whose agent type's definition pins none
    (`definition_model`, resolved by the caller), warns - or denies while a plan execution is
    armed. Everything else passes silently, including a tool name that is not a string: testing
    that against the set would raise, and the fail-open wrapper would turn the exception into a
    lost verdict.
    """
    if not isinstance(tool_name, str) or tool_name not in SUBAGENT_TOOLS:
        return (None, "")
    if not isinstance(tool_input, dict):
        return (None, "")
    subagent_type = str(tool_input.get("subagent_type") or "").strip().lower()
    if subagent_type == "fork":  # a fork always inherits the parent model by design
        return (None, "")
    model = tool_input.get("model")
    if isinstance(model, str) and model.strip():
        return (None, "")  # explicitly pinned - good
    if _pins(definition_model):
        return (None, "")  # the agent type pins its own model, which the dispatch then uses
    if plan_armed:
        return ("deny", _DENY_MESSAGE)
    return ("warn", _WARN_MESSAGE)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        # The EVENT's session: a plan armed in another session must not deny dispatches here.
        plan_armed = skill_receipt.is_fresh(PLAN_RECEIPT, session_id=event.get("session_id"))
    except Exception:  # noqa: BLE001 - receipt trouble must not wedge a turn
        plan_armed = False
    tool_input = event.get("tool_input") or {}
    try:
        definition_model = agent_definition_model(
            tool_input.get("subagent_type") if isinstance(tool_input, dict) else None,
            project_dir=os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd"))
    except Exception:  # noqa: BLE001 - an unreadable definition leaves the dispatch unpinned
        definition_model = None
    action, message = assess(event.get("tool_name"), tool_input, plan_armed, definition_model)
    if action == "deny":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }}) + "\n")
    elif action == "warn":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "SUBAGENT-MODEL GATE: " + message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
