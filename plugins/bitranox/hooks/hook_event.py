"""Typed views of the JSON event a hook reads on stdin.

A hook receives one JSON object per run. `json.load` hands it back as `Any`, and the usual guard
`isinstance(event, dict)` turns that into `dict[Unknown, Unknown]`, so every value a hook reads
from it is untyped and reaches typed helpers unchecked. The parse functions here are the one place
that untyped value enters: each takes whatever `json.load` returned and gives back a TypedDict
holding only the fields the hooks read, each checked with `isinstance`.

A field of the wrong type is dropped, so the hook sees it as absent - never `cast`, which would
hand a list to code that expects a str and crash the hook mid-turn. A payload that is not a JSON
object parses to None, which every caller treats as "nothing to judge".

The shapes list the fields the hooks in this directory actually read, not every field the harness
sends: a field nobody reads is not copied, and a hook that starts reading a new one adds it here.

Examples:
    >>> parse_pre_tool_use({"tool_name": "Bash", "tool_input": {"command": "ls"}})
    {'tool_name': 'Bash', 'tool_input': {'command': 'ls'}}
    >>> parse_pre_tool_use({"tool_name": 7, "cwd": "/opt/x"})
    {'cwd': '/opt/x'}
    >>> parse_pre_tool_use(["not", "an", "object"]) is None
    True
"""

from __future__ import annotations

from typing import TypedDict, TypeIs

__all__ = [
    "EditEntry",
    "HookEventBase",
    "PostToolBatchEvent",
    "PostToolUseEvent",
    "PostToolUseFailureEvent",
    "PreToolUseEvent",
    "StopEvent",
    "ToolInput",
    "ToolResponse",
    "UserPromptSubmitEvent",
    "parse_hook_event",
    "parse_post_tool_batch",
    "parse_post_tool_use",
    "parse_post_tool_use_failure",
    "parse_pre_tool_use",
    "parse_stop",
    "parse_tool_input",
    "parse_user_prompt_submit",
]


class EditEntry(TypedDict, total=False):
    """One element of a MultiEdit `edits` list."""

    old_string: str
    new_string: str
    replace_all: bool


class ToolInput(TypedDict, total=False):
    """The `tool_input` fields the hooks read, across the tools they judge.

    `old_string`, `new_string` and `replace_all` match `EditEntry`, so a single Edit's input can
    stand in for a one-element edit list.
    """

    command: str
    description: str
    run_in_background: bool
    file_path: str
    notebook_path: str
    content: str
    old_string: str
    new_string: str
    replace_all: bool
    new_source: str
    edits: list[EditEntry]
    prompt: str
    name: str
    subagent_type: str
    model: str
    effort: str
    to: str
    task_id: str
    shell_id: str


class ToolResponse(TypedDict, total=False):
    """The `tool_response` fields a PostToolUse hook reads: a Bash call's output, and the text a
    Write replaced (`originalFile`)."""

    stdout: str
    stderr: str
    interrupted: bool
    backgroundTaskId: str
    originalFile: str


class HookEventBase(TypedDict, total=False):
    """The fields every hook event carries."""

    hook_event_name: str
    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: str
    agent_id: str
    agent_type: str


class PreToolUseEvent(HookEventBase, total=False):
    """A PreToolUse event: the call about to run."""

    tool_name: str
    tool_input: ToolInput
    tool_use_id: str


class PostToolUseEvent(PreToolUseEvent, total=False):
    """A PostToolUse event: the call that ran, with its response."""

    tool_response: ToolResponse


class PostToolUseFailureEvent(PreToolUseEvent, total=False):
    """A PostToolUseFailure event: the call that failed, and whether the user interrupted it."""

    error: str
    is_interrupt: bool


class PostToolBatchEvent(HookEventBase, total=False):
    """A PostToolBatch event: every call of the batch that just finished.

    Each element stays as it was decoded: a call's `tool_response` is a string for one tool and an
    object for another, and the hook that reads the batch already checks each element itself.
    """

    tool_calls: list[object]


class StopEvent(HookEventBase, total=False):
    """A Stop event: the turn is ending."""

    stop_hook_active: bool
    last_assistant_message: str


class UserPromptSubmitEvent(HookEventBase, total=False):
    """A UserPromptSubmit event: the prompt just submitted."""

    prompt: str


def _is_object(value: object) -> TypeIs[dict[str, object]]:
    """True for a decoded JSON object; json gives its keys as str, its values are checked per field."""
    return isinstance(value, dict)


def _is_array(value: object) -> TypeIs[list[object]]:
    """True for a decoded JSON array; its elements are checked one by one."""
    return isinstance(value, list)


def _text(fields: dict[str, object], key: str) -> str | None:
    """The field as a str, or None when it is absent or not a str."""
    value = fields.get(key)
    return value if isinstance(value, str) else None


def _flag(fields: dict[str, object], key: str) -> bool | None:
    """The field as a bool, or None when it is absent or not a bool."""
    value = fields.get(key)
    return value if isinstance(value, bool) else None


def _parse_edit(raw: object) -> EditEntry | None:
    """One `edits` element, or None when it is not a JSON object."""
    if not _is_object(raw):
        return None
    edit: EditEntry = {}
    if (old := _text(raw, "old_string")) is not None:
        edit["old_string"] = old
    if (new := _text(raw, "new_string")) is not None:
        edit["new_string"] = new
    if (replace_all := _flag(raw, "replace_all")) is not None:
        edit["replace_all"] = replace_all
    return edit


def _parse_edits(raw: object) -> list[EditEntry] | None:
    """The `edits` list without its non-object elements, or None when it is not a list."""
    if not _is_array(raw):
        return None
    return [edit for edit in map(_parse_edit, raw) if edit is not None]


def parse_tool_input(raw: object) -> ToolInput | None:
    """Narrow a `tool_input` value; None when it is not a JSON object.

    Args:
        raw: The value under `tool_input`, as decoded, of any type.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_tool_input({"command": "ls", "run_in_background": "yes"})
        {'command': 'ls'}
        >>> parse_tool_input({"edits": [{"new_string": "b"}, 3]})
        {'edits': [{'new_string': 'b'}]}
        >>> parse_tool_input("ls") is None
        True
    """
    if not _is_object(raw):
        return None
    tool_input: ToolInput = {}
    if (value := _text(raw, "command")) is not None:
        tool_input["command"] = value
    if (value := _text(raw, "description")) is not None:
        tool_input["description"] = value
    if (value := _text(raw, "file_path")) is not None:
        tool_input["file_path"] = value
    if (value := _text(raw, "notebook_path")) is not None:
        tool_input["notebook_path"] = value
    if (value := _text(raw, "content")) is not None:
        tool_input["content"] = value
    if (value := _text(raw, "old_string")) is not None:
        tool_input["old_string"] = value
    if (value := _text(raw, "new_string")) is not None:
        tool_input["new_string"] = value
    if (value := _text(raw, "new_source")) is not None:
        tool_input["new_source"] = value
    if (value := _text(raw, "prompt")) is not None:
        tool_input["prompt"] = value
    if (value := _text(raw, "name")) is not None:
        tool_input["name"] = value
    if (value := _text(raw, "subagent_type")) is not None:
        tool_input["subagent_type"] = value
    if (value := _text(raw, "model")) is not None:
        tool_input["model"] = value
    if (value := _text(raw, "effort")) is not None:
        tool_input["effort"] = value
    if (value := _text(raw, "to")) is not None:
        tool_input["to"] = value
    if (value := _text(raw, "task_id")) is not None:
        tool_input["task_id"] = value
    if (value := _text(raw, "shell_id")) is not None:
        tool_input["shell_id"] = value
    if (background := _flag(raw, "run_in_background")) is not None:
        tool_input["run_in_background"] = background
    if (replace_all := _flag(raw, "replace_all")) is not None:
        tool_input["replace_all"] = replace_all
    if (edits := _parse_edits(raw.get("edits"))) is not None:
        tool_input["edits"] = edits
    return tool_input


def _parse_tool_response(raw: object) -> ToolResponse | None:
    """Narrow a `tool_response` value; None when it is not a JSON object (a plain-text response)."""
    if not _is_object(raw):
        return None
    response: ToolResponse = {}
    if (stdout := _text(raw, "stdout")) is not None:
        response["stdout"] = stdout
    if (stderr := _text(raw, "stderr")) is not None:
        response["stderr"] = stderr
    if (interrupted := _flag(raw, "interrupted")) is not None:
        response["interrupted"] = interrupted
    if (task := _text(raw, "backgroundTaskId")) is not None:
        response["backgroundTaskId"] = task
    if (original := _text(raw, "originalFile")) is not None:
        response["originalFile"] = original
    return response


def _fill_base(fields: dict[str, object], event: HookEventBase) -> None:
    """Copy the fields every event carries from `fields` into `event`."""
    if (name := _text(fields, "hook_event_name")) is not None:
        event["hook_event_name"] = name
    if (session := _text(fields, "session_id")) is not None:
        event["session_id"] = session
    if (transcript := _text(fields, "transcript_path")) is not None:
        event["transcript_path"] = transcript
    if (cwd := _text(fields, "cwd")) is not None:
        event["cwd"] = cwd
    if (mode := _text(fields, "permission_mode")) is not None:
        event["permission_mode"] = mode
    if (agent := _text(fields, "agent_id")) is not None:
        event["agent_id"] = agent
    if (agent_type := _text(fields, "agent_type")) is not None:
        event["agent_type"] = agent_type


def _fill_tool_call(fields: dict[str, object], event: PreToolUseEvent) -> None:
    """Copy the base fields plus the tool call's name, input and id into `event`."""
    _fill_base(fields, event)
    if (tool_name := _text(fields, "tool_name")) is not None:
        event["tool_name"] = tool_name
    if (tool_input := parse_tool_input(fields.get("tool_input"))) is not None:
        event["tool_input"] = tool_input
    if (tool_use_id := _text(fields, "tool_use_id")) is not None:
        event["tool_use_id"] = tool_use_id


def parse_pre_tool_use(raw: object) -> PreToolUseEvent | None:
    """Narrow a PreToolUse payload; None when it is not a JSON object.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_pre_tool_use({"tool_name": "Bash", "tool_input": ["ls"]})
        {'tool_name': 'Bash'}
        >>> parse_pre_tool_use(None) is None
        True
    """
    if not _is_object(raw):
        return None
    event: PreToolUseEvent = {}
    _fill_tool_call(raw, event)
    return event


def parse_post_tool_use(raw: object) -> PostToolUseEvent | None:
    """Narrow a PostToolUse payload; None when it is not a JSON object.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_post_tool_use({"tool_name": "Bash", "tool_response": {"stdout": "", "x": 1}})
        {'tool_name': 'Bash', 'tool_response': {'stdout': ''}}
        >>> parse_post_tool_use({"tool_response": "plain text"})
        {}
    """
    if not _is_object(raw):
        return None
    event: PostToolUseEvent = {}
    _fill_tool_call(raw, event)
    if (response := _parse_tool_response(raw.get("tool_response"))) is not None:
        event["tool_response"] = response
    return event


def parse_stop(raw: object) -> StopEvent | None:
    """Narrow a Stop payload; None when it is not a JSON object.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_stop({"stop_hook_active": True, "session_id": "s"})
        {'session_id': 's', 'stop_hook_active': True}
        >>> parse_stop({"stop_hook_active": "true"})
        {}
    """
    if not _is_object(raw):
        return None
    event: StopEvent = {}
    _fill_base(raw, event)
    if (active := _flag(raw, "stop_hook_active")) is not None:
        event["stop_hook_active"] = active
    if (message := _text(raw, "last_assistant_message")) is not None:
        event["last_assistant_message"] = message
    return event


def parse_user_prompt_submit(raw: object) -> UserPromptSubmitEvent | None:
    """Narrow a UserPromptSubmit payload; None when it is not a JSON object.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_user_prompt_submit({"prompt": "hello", "session_id": 4})
        {'prompt': 'hello'}
    """
    if not _is_object(raw):
        return None
    event: UserPromptSubmitEvent = {}
    _fill_base(raw, event)
    if (prompt := _text(raw, "prompt")) is not None:
        event["prompt"] = prompt
    return event


def parse_hook_event(raw: object) -> HookEventBase | None:
    """Narrow a payload whose readers need only the fields every event carries.

    SubagentStart (its `agent_type`) and PostCompact (its `cwd`, `session_id` and
    `transcript_path`) are read this way: no hook here reads a field of theirs beyond the common
    ones, so a shape of their own would declare nothing more.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The common fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_hook_event({"hook_event_name": "SubagentStart", "agent_type": "Explore"})
        {'hook_event_name': 'SubagentStart', 'agent_type': 'Explore'}
        >>> parse_hook_event({"agent_type": ["Explore"]})
        {}
    """
    if not _is_object(raw):
        return None
    event: HookEventBase = {}
    _fill_base(raw, event)
    return event


def parse_post_tool_use_failure(raw: object) -> PostToolUseFailureEvent | None:
    """Narrow a PostToolUseFailure payload; None when it is not a JSON object.

    A PreToolUse payload parses too, to the fields the two share, so a hook registered for both
    events can read either through this one function.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The declared fields that hold the declared type, or None for a non-object.

    Examples:
        >>> parse_post_tool_use_failure({"tool_name": "Bash", "is_interrupt": True})
        {'tool_name': 'Bash', 'is_interrupt': True}
        >>> parse_post_tool_use_failure({"is_interrupt": "yes", "error": 2})
        {}
    """
    if not _is_object(raw):
        return None
    event: PostToolUseFailureEvent = {}
    _fill_tool_call(raw, event)
    if (error := _text(raw, "error")) is not None:
        event["error"] = error
    if (interrupt := _flag(raw, "is_interrupt")) is not None:
        event["is_interrupt"] = interrupt
    return event


def parse_post_tool_batch(raw: object) -> PostToolBatchEvent | None:
    """Narrow a PostToolBatch payload; None when it is not a JSON object.

    Args:
        raw: What `json.load` returned for the hook's stdin.

    Returns:
        The common fields and the `tool_calls` list that hold the declared type, or None for a
        non-object. The list's elements are kept as decoded.

    Examples:
        >>> parse_post_tool_batch({"hook_event_name": "PostToolBatch", "tool_calls": [{"a": 1}, 2]})
        {'hook_event_name': 'PostToolBatch', 'tool_calls': [{'a': 1}, 2]}
        >>> parse_post_tool_batch({"tool_calls": {"a": 1}})
        {}
    """
    if not _is_object(raw):
        return None
    event: PostToolBatchEvent = {}
    _fill_base(raw, event)
    calls = raw.get("tool_calls")
    if _is_array(calls):
        event["tool_calls"] = calls
    return event
