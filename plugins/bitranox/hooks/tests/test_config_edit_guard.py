"""Tests for config-edit-guard.py (PreToolUse: route Claude Code config JSON through update-config).

Two things carry the weight.

The WINDOWS path case, because it is the one that fails silently: `file_path` arrives with
backslash separators on Windows even under Git Bash, so a guard written with forward slashes never
matches there and the edit proceeds exactly as if the hook had found nothing to say. That case is
asserted directly rather than left to a platform this suite mostly does not run on.

The NEGATIVE cases, because a reminder that fires on any JSON would train the reader to ignore the
channel. A file merely named `settings.json` somewhere unrelated, a package.json, a fixture path -
all must stay silent.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import config_edit_guard as G

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "config-edit-guard.py"
SHIM = HOOKS_DIR / "run-python.sh"


# ---------------------------------------------------------------- targets_config()

@pytest.mark.parametrize("path", [
    "/home/u/.claude/settings.json",
    "/home/u/.claude/settings.local.json",
    "/home/u/.claude.json",
    "/etc/claude-code/managed-settings.json",
    "/repo/.claude/settings.json",
    "/repo/.claude/SETTINGS.JSON",                       # case-insensitive
])
def test_a_config_path_is_recognised(path):
    assert G.targets_config(path) is True


@pytest.mark.parametrize("path", [
    "C:\\Users\\u\\.claude\\settings.json",
    "C:\\Users\\u\\.claude\\settings.local.json",
    "C:\\Users\\u\\.claude.json",
])
def test_a_windows_path_is_recognised(path):
    """The silent-failure case: backslashes arrive even under Git Bash."""
    assert G.targets_config(path) is True


@pytest.mark.parametrize("path", [
    "/repo/package.json",
    "/repo/tsconfig.json",
    "/repo/plugins/bitranox/hooks/hooks.json",
    "/repo/settings.json",                               # not under .claude/
    "/repo/.claude/skills/x/SKILL.md",
    "/repo/tests/fixtures/settings.json.golden",         # a fixture that only looks like one
    "",
    None,
])
def test_an_unrelated_path_is_ignored(path):
    assert G.targets_config(path) is False


# ---------------------------------------------------------------- notice()

def test_notice_fires_for_a_config_edit():
    event = {"tool_name": "Edit", "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    message = G.notice(event)
    assert message is not None and "update-config" in message


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", "Glob"])
def test_a_non_writing_tool_is_ignored(tool):
    """Reading settings.json is not editing it."""
    event = {"tool_name": tool, "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    assert G.notice(event) is None


def test_notice_is_silent_for_an_unrelated_write():
    event = {"tool_name": "Write", "tool_input": {"file_path": "/repo/package.json"}}
    assert G.notice(event) is None


@pytest.mark.parametrize("event", [None, {}, [], "x", {"tool_name": "Edit"}])
def test_notice_is_silent_for_a_malformed_event(event):
    assert G.notice(event) is None


# ---------------------------------------------------------------- end to end

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_emits_context_and_never_blocks():
    rc, out, _err = _run({
        "session_id": "t", "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse", "tool_name": "Write",
        "tool_input": {"file_path": "/home/u/.claude/settings.json", "content": "{}"},
    })
    assert rc == 0, "this is a reminder, never a refusal - it must not block the sanctioned path"
    assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_is_silent_for_an_unrelated_file():
    assert _run({
        "session_id": "t", "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse", "tool_name": "Write",
        "tool_input": {"file_path": "/repo/package.json", "content": "{}"},
    }) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open(payload):
    rc, out, _err = _run(payload)
    assert (rc, out) == (0, "")
