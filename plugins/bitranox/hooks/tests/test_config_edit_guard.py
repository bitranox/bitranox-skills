"""Tests for config-edit-guard.py (PreToolUse: route Claude Code config JSON through update-config).

This guard BLOCKS (exit 2) with a `BITRANOX_CONFIG_EDIT` bypass, like its two siblings. Three
things therefore have to hold and each is asserted: it blocks the real thing, the bypass actually
releases it, and it stays silent on everything else. The bypass test is not a formality - a guard
whose escape hatch does not work is a guard that has to be disabled wholesale the first time it is
wrong.

Beyond that, the WINDOWS path case, because it is the one that fails silently: `file_path` arrives with
backslash separators on Windows even under Git Bash, so a guard written with forward slashes never
matches there and the edit proceeds exactly as if the hook had found nothing to say. That case is
asserted directly rather than left to a platform this suite mostly does not run on.

The NEGATIVE cases matter more here than they did when this only nudged: a block that fires on any
JSON does not merely add noise, it stops work. A file merely named `settings.json` somewhere
unrelated, a package.json, a fixture path - all must stay allowed.
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


# ---------------------------------------------------------------- decide()

def test_a_config_edit_is_blocked():
    event = {"tool_name": "Edit", "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    reason = G.decide(event, {})
    assert reason is not None
    assert "update-config" in reason
    assert G._BYPASS_ENV in reason, "the deny must name its own bypass, or it is a dead end"


def test_the_bypass_releases_the_block():
    """An escape hatch that does not work gets the whole guard disabled the first time it is wrong."""
    event = {"tool_name": "Edit", "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    assert G.decide(event, {G._BYPASS_ENV: "1"}) is None


def test_an_empty_bypass_value_does_not_release_the_block():
    event = {"tool_name": "Edit", "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    assert G.decide(event, {G._BYPASS_ENV: ""}) is not None


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", "Glob"])
def test_a_non_writing_tool_is_ignored(tool):
    """Reading settings.json is not editing it."""
    event = {"tool_name": tool, "tool_input": {"file_path": "/home/u/.claude/settings.json"}}
    assert G.decide(event, {}) is None


def test_an_unrelated_write_is_allowed():
    event = {"tool_name": "Write", "tool_input": {"file_path": "/repo/package.json"}}
    assert G.decide(event, {}) is None


@pytest.mark.parametrize("event", [None, {}, [], "x", {"tool_name": "Edit"}])
def test_a_malformed_event_is_allowed(event):
    assert G.decide(event, {}) is None


# ---------------------------------------------------------------- end to end

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_blocks_with_the_reason_on_stderr():
    rc, _out, err = _run({
        "session_id": "t", "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse", "tool_name": "Write",
        "tool_input": {"file_path": "/home/u/.claude/settings.json", "content": "{}"},
    })
    assert rc == 2, "exit 1 does NOT block a PreToolUse call - only exit 2 does"
    assert "CONFIG-EDIT GUARD" in err


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
