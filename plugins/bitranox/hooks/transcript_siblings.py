#!/usr/bin/env python3
"""The shell calls sent EARLIER in the same assistant message as the call a PreToolUse hook judges.

Several tool calls in one assistant message are siblings. Probed on Claude Code 2.1.296: sibling
Bash calls run one after another, not side by side; each tool_use is its own transcript record
carrying the message's `message.id`; and all of them are on disk before the second call's
PreToolUse hook runs. The FIRST call's hook sees none of them, so a guard reading siblings can only
ever judge a call against the ones sent BEFORE it.

Guards that need this: `block-write-after-sibling-cd` (an earlier sibling moved the shell) and
`block-commit-beside-sibling-gate` (an earlier sibling ran a gate whose verdict nobody has read).
One reader, so the two cannot disagree about which calls are siblings.

A subagent's event carries the PARENT's `transcript_path` plus `agent_id`, and the subagent's own
records sit in `<parent minus .jsonl>/subagents/agent-<agent_id>.jsonl` (probed on 2.1.295), so a
call made inside a subagent is looked up there.

Only the tail of the transcript is read: the current message sits at the very end. Every failure
answers None ("nothing known"), which a guard must read as "allow".
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from shell_text import is_shell_tool

#: How far the transcript tail is read before giving up: the current message sits at the very end.
TAIL_BYTES = (256 * 1024, 4 * 1024 * 1024)


def _tool_uses(record):
    message = record.get("message") or {}
    content = message.get("content")
    if record.get("type") != "assistant" or not isinstance(content, list):
        return
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield message.get("id"), block


def earlier_siblings(records, tool_use_id):
    """Commands of the shell calls in the same message as `tool_use_id` that come before it.

    None when `tool_use_id` is not among `records`: then nothing is known about its siblings.
    """
    uses = [(mid, block) for record in records for mid, block in _tool_uses(record)]
    position = next((i for i, (_mid, block) in enumerate(uses) if block.get("id") == tool_use_id), None)
    if position is None:
        return None
    message_id = uses[position][0]
    return [block.get("input", {}).get("command", "") for mid, block in uses[:position]
            if mid == message_id and is_shell_tool(block.get("name"))]


def tail_records(path, size):
    """The JSON records in the last `size` bytes of `path`; a record cut by the seek is dropped."""
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        end = handle.tell()
        handle.seek(max(0, end - size))
        lines = handle.read().split(b"\n")
    if end > size:
        lines = lines[1:]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def siblings_from_transcript(path, tool_use_id):
    """`earlier_siblings` read from the tail of the transcript at `path`; None when not found."""
    for size in TAIL_BYTES:
        found = earlier_siblings(tail_records(path, size), tool_use_id)
        if found is not None:
            return found
    return None


def transcript_of(event):
    """The transcript holding the event's own records: the subagent's when `agent_id` is set."""
    path = event.get("transcript_path")
    if not path:
        return None
    agent_id = event.get("agent_id")
    if agent_id:
        main = Path(path)
        return str(main.with_suffix("") / "subagents" / f"agent-{agent_id}.jsonl")
    return path


def siblings_for_event(event):
    """The earlier shell siblings of the call a PreToolUse `event` describes; None when unknown."""
    path, tool_use_id = transcript_of(event), event.get("tool_use_id")
    if not path or not tool_use_id or not os.path.isfile(path):
        return None
    try:
        return siblings_from_transcript(path, tool_use_id)
    except OSError:
        return None
