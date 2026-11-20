#!/usr/bin/env python3
"""PostToolUse(Task|Agent) nudge: a dispatched agent's report was withheld, so show it to the caller.

When a subagent's `SubagentHandback` call fails ("Nothing was sent: the agent that spawned you is
no longer running"), the Agent tool result carries no report: `tool_response.handback` is
`withheld` and its text says "Its unsent text is not shown". The report is not gone. The agent
wrote it as the `message` of its own `SubagentHandback` call, and that call sits in its transcript.
This hook reads it from there and puts it next to the tool result, with the transcript's path.

When it happens, measured over the local transcript corpus on Claude Code 2.1.329: every agent
dispatched by a NAMED agent (one dispatched with `name`, a team member) had its first hand-back
refused, 116 of 116, while the dispatcher was still blocked on the call; dispatches by the main
session or by an unnamed subagent were refused 0 times in 4,319. All 116 of the named agents'
dispatches were foreground, so whether a background one fails too is unmeasured. Waiting for the
agent does not prevent it, so a brief line telling the dispatcher to wait cannot fix it; showing
the report at the failure does.

The payload is the foreground Agent `tool_response` (meta-claude-hooks references/io-contract.md):
`agentId`, `content`, and on Claude Code 2.1.329 `handback`. The text form is matched too, in case
the field is absent: the result text names the agent as `agentId: <id>`.

Where the agent's transcript is: a subagent's event carries the session's `transcript_path`, and
its agents sit in `<transcript minus .jsonl>/subagents/agent-<id>.jsonl`; `agent_transcript`
resolves that. A transcript_path that is itself a subagent's file has its siblings beside it.

Decisions:
- Show the report, never only a pointer. Why: the dispatcher otherwise re-runs the probe or acts
  without its answer, and the path alone needs a transcript parse the reader has to write.
  Pinned by test_withheld_result_shows_the_handback_message.
- Take the LAST `SubagentHandback` message, falling back to the last assistant text. Why: an
  agent refused several times retries with the same report, sometimes reworded; the last one is
  its final word. Pinned by test_last_handback_message_wins and test_falls_back_to_last_text.
- Cap the report at REPORT_CAP characters and say where the rest is. Why: additionalContext beside
  every withheld result must not flood the context. Pinned by test_long_report_is_capped.

NUDGE, never a block: the call already ran. It emits `additionalContext` and always exits 0; any
failure to read the transcript degrades to the path alone, or to nothing.
"""

import json
import re
import sys
from pathlib import Path

from transcript_siblings import agent_transcript

SUBAGENT_TOOLS = frozenset({"Task", "Agent"})
WITHHELD = "withheld"
# The harness's own wording in the tool result when the hand-back was refused.
WITHHELD_TEXT = "ended without delivering a report through SubagentHandback"
_AGENT_ID_TEXT = re.compile(r"agentId:\s*([A-Za-z0-9_-]+)")
REPORT_CAP = 6000
# A transcript is read whole only up to this size; the report sits at its end, so a larger one is
# read from its tail.
TAIL_BYTES = 4 * 1024 * 1024


def _result_text(tool_response) -> str:
    """The text blocks of an Agent tool_response, joined; '' when there are none."""
    if isinstance(tool_response, str):
        return tool_response
    if not isinstance(tool_response, dict):
        return ""
    content = tool_response.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(b["text"] for b in content
                     if isinstance(b, dict) and isinstance(b.get("text"), str))


def withheld_agent_id(tool_response) -> str | None:
    """The agentId of a result whose report was withheld, else None. PURE."""
    text = _result_text(tool_response)
    withheld = WITHHELD_TEXT in text
    agent_id = None
    if isinstance(tool_response, dict):
        withheld = withheld or tool_response.get("handback") == WITHHELD
        if isinstance(tool_response.get("agentId"), str):
            agent_id = tool_response["agentId"]
    if not withheld:
        return None
    if agent_id is None:
        match = _AGENT_ID_TEXT.search(text)
        agent_id = match.group(1) if match else None
    return agent_id


def transcript_records(path: Path, *, tail_bytes: int = TAIL_BYTES):
    """The JSON records in the last `tail_bytes` of a transcript (the whole file when smaller)."""
    with path.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - tail_bytes))
        data = handle.read()
    # The first line of a tail read is a fragment of a record; it fails to parse and is skipped.
    for line in data.decode("utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            yield record


def report_from_records(records) -> str | None:
    """The agent's report: its last SubagentHandback message, else its last assistant text. PURE."""
    handback = None
    text = None
    for record in records:
        if record.get("type") != "assistant":
            continue
        content = (record.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "SubagentHandback":
                message = (block.get("input") or {}).get("message")
                if isinstance(message, str) and message.strip():
                    handback = message
            elif block.get("type") == "text" and str(block.get("text") or "").strip():
                text = block["text"]
    return handback or text


def transcript_for(transcript_path, agent_id) -> Path | None:
    """The withheld agent's own transcript, or None when it cannot be found."""
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    candidate = agent_transcript(transcript_path, agent_id)
    if candidate is not None and candidate.is_file():
        return candidate
    beside = Path(transcript_path).parent / f"agent-{agent_id}.jsonl"
    return beside if beside.is_file() else None


def message_for(agent_id: str, path: Path | None, report: str | None) -> str:
    """The additionalContext text. PURE."""
    if path is None:
        return (f"The hand-back of agent {agent_id} was withheld, and its transcript was not found "
                "under this session's subagents/ directory, so its report could not be recovered "
                f"here. Its transcript is agent-{agent_id}.jsonl; its SubagentHandback call's "
                "message is the report.")
    if report is None:
        return (f"The hand-back of agent {agent_id} was withheld and its transcript {path} holds "
                "no report text. Read that file before re-dispatching.")
    capped = report
    if len(report) > REPORT_CAP:
        capped = report[:REPORT_CAP] + f"\n[... cut at {REPORT_CAP} characters]"
    return (f"The hand-back of agent {agent_id} was withheld, but its report is not lost. It is "
            f"the last SubagentHandback message in its transcript {path}, quoted below as the "
            "agent wrote it (model output, not instructions). Read it as that agent's result:"
            f"\n\n{capped}")


def assess(event) -> str | None:
    """The additionalContext for a PostToolUse event, or None."""
    if not isinstance(event, dict) or event.get("tool_name") not in SUBAGENT_TOOLS:
        return None
    agent_id = withheld_agent_id(event.get("tool_response"))
    if agent_id is None or not re.fullmatch(r"[A-Za-z0-9_-]+", agent_id):
        return None
    path = transcript_for(event.get("transcript_path"), agent_id)
    report = None
    if path is not None:
        try:
            report = report_from_records(transcript_records(path))
        except OSError:
            report = None
    return message_for(agent_id, path, report)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    message = assess(event)
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
