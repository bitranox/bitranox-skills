#!/usr/bin/env python3
"""PostToolBatch: say so when a commit, push or PR ran after a file edit of the same message failed.

The incident, 2026-10-23 (bmk): one message held an Edit of CHANGELOG.md and a
`git add CHANGELOG.md ... && git commit`. The Edit was refused (the file had not been Read in
that session), and the commit, its sibling, ran anyway, so the fix commit went out without its
changelog line. It was the seventh recorded miss of the rule "send a state change only after
reading what it depends on" (feedback-chain-state-changing-steps-with-and-confirm-the-end-state).

Why a note after the batch and not a refusal before the commit: an edit that fails validation
(file not Read, file missing, old_string not found) fires NO PreToolUse and NO PostToolUseFailure
hook (probed on Claude Code 2.1.309), so nothing that runs before the commit can know the edit
failed. PostToolBatch does: it lists every call of the message in order with the result the model
sees, and the failed edit's result begins with `<tool_use_error>`. Its `additionalContext` reaches
the model beside the tool results, before its next reply (probed on the same CLI), which is in time
to amend a commit before anything is pushed.

PRICED before shipping, by replaying every publishing shell call in the local transcript corpus
(6,381) against its same-message siblings: 851 had an earlier edit sibling, so refusing after ANY
edit would have hit one publishing call in eight; only 6 followed an edit that FAILED, and in 4 of
those the commit or push then ran (the other 2 failed for their own reasons). This hook speaks only
in that case: a failed edit, then a publishing call that was not itself refused or failed.

Never blocks (a block here would stop the agentic loop, not the commit, which already ran): exit 0,
the note as `hookSpecificOutput.additionalContext`, nothing on any other path. Fail-open. ASCII only.
"""

import json
import re
import sys

from shell_text import is_gated_command, is_shell_tool

EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
_ERROR_PREFIX = "<tool_use_error>"
# What the model sees for a call a PreToolUse hook refused (`PreToolUse:Bash hook error: ...`):
# that call did not run. Matched at the START only, so a commit subject naming the words is output.
_HOOK_REFUSAL = re.compile(r"PreToolUse:\w+ hook error:")


def _text_of(response):
    """The tool result as one string: PostToolBatch sends a string or a list of content blocks."""
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "\n".join(str(block.get("text", "")) for block in response if isinstance(block, dict))
    return ""


def _failed(response):
    """Whether a result is the error the model was shown in place of the call's output."""
    return _text_of(response).lstrip().startswith(_ERROR_PREFIX)


def _ran(response):
    """Whether a publishing call actually ran: neither an error result nor a hook's refusal."""
    head = _text_of(response).lstrip()
    return not head.startswith(_ERROR_PREFIX) and _HOOK_REFUSAL.match(head) is None


def findings(tool_calls):
    """(failed edit call, publishing call that ran after it) pairs, in message order."""
    pairs = []
    failed_edits = []
    for call in tool_calls or []:
        if not isinstance(call, dict):
            continue
        name = call.get("tool_name")
        tool_input = call.get("tool_input") if isinstance(call.get("tool_input"), dict) else {}
        if name in EDIT_TOOLS and _failed(call.get("tool_response")):
            failed_edits.append(call)
        elif failed_edits and is_shell_tool(name):
            command = tool_input.get("command") or ""
            if is_gated_command(command, name) and _ran(call.get("tool_response")):
                pairs.extend((edit, call) for edit in failed_edits)
    return pairs


def _first_line(text, limit=120):
    return ((text or "").strip().splitlines() or [""])[0][:limit]


def note(pairs):
    """The factual note for the model; one line per failed edit and the publishing call after it."""
    lines = ["Batch check: a commit, push or PR in this message ran AFTER a file edit of the same",
             "message had failed, so what it published does not contain that edit."]
    for edit, publish in pairs:
        edit_input = edit.get("tool_input") if isinstance(edit.get("tool_input"), dict) else {}
        target = edit_input.get("file_path") or edit_input.get("notebook_path") or "?"
        reason = _first_line(_text_of(edit.get("tool_response")).replace(_ERROR_PREFIX, ""))
        command = _first_line((publish.get("tool_input") or {}).get("command"))
        lines.append("  failed: %s %s (%s)" % (edit.get("tool_name"), target, reason))
        lines.append("  then ran: %s" % command)
    lines.append("`git show --name-only HEAD` lists what the commit holds. An unpushed commit can")
    lines.append("still take the edit by amending; a pushed one needs a follow-up commit.")
    return "\n".join(lines)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or event.get("hook_event_name") != "PostToolBatch":
        return 0
    pairs = findings(event.get("tool_calls"))
    if pairs:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolBatch", "additionalContext": note(pairs)}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a note must never wedge a turn
        sys.exit(0)
