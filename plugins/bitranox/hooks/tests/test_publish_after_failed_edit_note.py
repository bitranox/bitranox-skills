"""Tests for publish-after-failed-edit-note.py.

The incident: one message held an Edit of CHANGELOG.md and a `git add ... && git commit`. The Edit
was refused (file not Read yet), the commit ran anyway, and the fix shipped without its changelog
line. A failed edit fires no PreToolUse hook, so only PostToolBatch can see it.
"""
import io
import json
import sys

import pytest

import publish_after_failed_edit_note as hook

NOT_READ = "<tool_use_error>File has not been read yet. Read it first before writing to it.</tool_use_error>"
COMMIT = "git add CHANGELOG.md src/x.py && git commit -q -F /tmp/msg.txt && git show --name-only HEAD"
COMMIT_OUT = "abc1234 fix(x): y\n\nCHANGELOG.md\nsrc/x.py"


def _edit(response, *, tool="Edit", path="/w/CHANGELOG.md"):
    return {"tool_name": tool, "tool_input": {"file_path": path, "old_string": "a", "new_string": "b"},
            "tool_use_id": "e1", "tool_response": response}


def _shell(command, response, *, tool="Bash"):
    return {"tool_name": tool, "tool_input": {"command": command}, "tool_use_id": "b1", "tool_response": response}


def test_the_incident_a_commit_after_a_failed_edit_is_named():
    pairs = hook.findings([_edit(NOT_READ), _shell(COMMIT, COMMIT_OUT)])

    assert [(e["tool_input"]["file_path"], p["tool_input"]["command"]) for e, p in pairs] == [
        ("/w/CHANGELOG.md", COMMIT)]
    note = hook.note(pairs)
    assert "/w/CHANGELOG.md" in note
    assert "File has not been read yet" in note
    assert "git add CHANGELOG.md" in note
    assert "<tool_use_error>" not in note


@pytest.mark.parametrize("tool", ["Write", "MultiEdit", "NotebookEdit"])
def test_every_file_edit_tool_counts(tool):
    assert hook.findings([_edit(NOT_READ, tool=tool), _shell("git push origin HEAD", "ok")])


@pytest.mark.parametrize("publish", ["git push", "gh pr create --title t --body-file b.md", COMMIT])
def test_every_publishing_action_counts(publish):
    assert hook.findings([_edit(NOT_READ), _shell(publish, "done")])


def test_a_successful_edit_is_not_a_finding():
    assert hook.findings([_edit("The file /w/CHANGELOG.md has been updated successfully."), _shell(COMMIT, COMMIT_OUT)]) == []


def test_an_edit_that_failed_after_the_commit_did_not_feed_it():
    assert hook.findings([_shell(COMMIT, COMMIT_OUT), _edit(NOT_READ)]) == []


def test_a_commit_a_hook_refused_did_not_run():
    refused = "PreToolUse:Bash hook error: [bash run-python.sh repo-gate.py]: BLOCKED ..."
    assert hook.findings([_edit(NOT_READ), _shell(COMMIT, refused)]) == []


def test_a_commit_that_failed_itself_did_not_publish_anything():
    assert hook.findings([_edit(NOT_READ), _shell(COMMIT, "<tool_use_error>Exit code 1\nnothing to commit</tool_use_error>")]) == []


def test_a_commit_subject_naming_a_hook_error_is_still_output():
    out = "abc1234 fix: PreToolUse:Bash hook error: message in a subject"
    assert hook.findings([_edit(NOT_READ), _shell(COMMIT, out)])


def test_a_shell_call_that_publishes_nothing_is_not_a_finding():
    assert hook.findings([_edit(NOT_READ), _shell("git status --porcelain", " M CHANGELOG.md")]) == []


def test_a_commit_named_only_inside_a_heredoc_is_text():
    command = "cat > /tmp/notes.txt <<'EOF'\ngit commit -m later\nEOF"
    assert hook.findings([_edit(NOT_READ), _shell(command, "")]) == []


def test_content_block_responses_are_read_too():
    blocks = [{"type": "text", "text": NOT_READ}]
    assert hook.findings([_edit(blocks), _shell(COMMIT, [{"type": "text", "text": COMMIT_OUT}])])


def test_the_powershell_tool_is_read_the_same_way():
    assert hook.findings([_edit(NOT_READ), _shell("git push", "ok", tool="PowerShell")])


def _run(monkeypatch, capsys, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload if isinstance(payload, str) else json.dumps(payload)))
    code = hook.main()
    return code, capsys.readouterr()


def test_the_hook_hands_the_note_to_the_model_as_additional_context(monkeypatch, capsys):
    event = {"hook_event_name": "PostToolBatch", "tool_calls": [_edit(NOT_READ), _shell(COMMIT, COMMIT_OUT)]}

    code, out = _run(monkeypatch, capsys, event)

    assert code == 0
    payload = json.loads(out.out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolBatch"
    assert "/w/CHANGELOG.md" in payload["hookSpecificOutput"]["additionalContext"]
    assert out.err == ""


@pytest.mark.parametrize("payload", [
    "not json",
    {"hook_event_name": "PostToolBatch", "tool_calls": [_shell(COMMIT, COMMIT_OUT)]},
    {"hook_event_name": "PostToolBatch", "tool_calls": "garbage"},
    {"hook_event_name": "Stop", "tool_calls": [_edit(NOT_READ), _shell(COMMIT, COMMIT_OUT)]},
])
def test_the_hook_is_silent_otherwise(monkeypatch, capsys, payload):
    code, out = _run(monkeypatch, capsys, payload)

    assert code == 0
    assert (out.out, out.err) == ("", "")
