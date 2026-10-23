#!/usr/bin/env python3
"""The shell calls sent EARLIER in the same assistant message as the call a PreToolUse hook judges.

Several tool calls in one assistant message are siblings. They run one after another, not side by
side, so a guard can only ever judge a call against the ones sent BEFORE it. Two sources answer:

- `sibling_ledger`, the record `sibling-ledger.py` keeps from the hook events themselves. It is
  asked first, because on Claude Code 2.1.309 it is the only one that works live (probed): a later
  sibling's PreToolUse hook runs before the earlier siblings are written to the transcript.
- the transcript, where each tool_use is its own record carrying the message's `message.id`. On
  2.1.296 every sibling was on disk before the second call's hook ran (probed then), so it is kept
  as the fallback for a CLI that writes them in time, or a session the ledger did not cover.

Guards that need this: `block-write-after-sibling-cd` (an earlier sibling moved the shell) and
`block-commit-beside-sibling-gate` (an earlier sibling ran a gate whose verdict nobody has read).
One reader, so the two cannot disagree about which calls are siblings.

A subagent's event carries the PARENT's `transcript_path` plus `agent_id`, and the subagent's own
records sit in `<parent minus .jsonl>/subagents/agent-<agent_id>.jsonl` (probed on 2.1.295), or
one level deeper, in `subagents/workflows/<wf_id>/`, for an agent a Workflow script started. A
call made inside a subagent is looked up there; `agent_transcript` is the one resolver every hook
that needs a subagent's own file uses.

Only the tail of the transcript is read: the current message sits at the very end. Every failure
answers None ("nothing known"), which a guard must read as "allow".
"""

import json
import os
import re
from pathlib import Path

import sibling_ledger
from shell_text import is_shell_tool

#: How far the transcript tail is read before giving up: the current message sits at the very end.
TAIL_BYTES = (256 * 1024, 4 * 1024 * 1024)

# agent_id becomes a file-name segment and a glob pattern; anything but a plain name could leave
# subagents/ or match another agent's file.
_AGENT_ID = re.compile(r"[A-Za-z0-9_-]+")


def agent_transcript(main_path, agent_id):
    """The subagent `agent_id`'s own transcript in the session at `main_path`, as a Path.

    A Task subagent's file is `subagents/agent-<id>.jsonl`; a Workflow agent's is
    `subagents/workflows/<wf_id>/agent-<id>.jsonl`, and the event does not name the workflow.
    When neither exists the direct path is returned, so a caller reports it as unreadable. None
    when the id is not a plain name, or when it matches in more than one workflow: neither file
    can then be told to be this agent's own.
    """
    if not isinstance(agent_id, str) or not _AGENT_ID.fullmatch(agent_id):
        return None
    agents = Path(main_path).with_suffix("") / "subagents"
    name = "agent-%s.jsonl" % agent_id
    direct = agents / name
    if direct.is_file():
        return direct
    found = sorted((agents / "workflows").glob("*/" + name))
    if len(found) > 1:
        return None
    return found[0] if found else direct


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
        own = agent_transcript(path, agent_id)
        return str(own) if own is not None else None
    return path


def siblings_for_event(event):
    """The earlier shell siblings of the call a PreToolUse `event` describes; None when unknown.

    The ledger's answer when it names any; otherwise the transcript's, which on an older CLI may
    know siblings the ledger never saw (a session that started before the recorder was installed).
    """
    try:
        recorded = sibling_ledger.earlier(event)
    except OSError:
        recorded = None
    if recorded:
        return recorded
    from_transcript = _siblings_from_transcript_of(event)
    return from_transcript if from_transcript is not None else recorded


def _siblings_from_transcript_of(event):
    """`siblings_from_transcript` for the transcript `event` belongs to; None when unknown."""
    path, tool_use_id = transcript_of(event), event.get("tool_use_id")
    if not path or not tool_use_id or not os.path.isfile(path):
        return None
    try:
        return siblings_from_transcript(path, tool_use_id)
    except OSError:
        return None
