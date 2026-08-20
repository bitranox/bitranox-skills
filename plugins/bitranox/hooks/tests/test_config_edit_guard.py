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


# ------------------------------------------- the update-config auto-bypass (measured, not assumed)
#
# update-config's own workflow says "Edit file - Use Edit tool", and driving this guard with the
# event that step produces returned exit 2. Without this detection the guard blocks the very skill
# the rule tells you to use, so these cases pin both directions.

def _transcript(tmp_path, body: str):
    f = tmp_path / "t.jsonl"
    f.write_text(body, encoding="utf-8")
    return str(f)


def _edit_event(transcript):
    return {"tool_name": "Edit", "transcript_path": transcript,
            "tool_input": {"file_path": "/home/u/.claude/settings.json"}}


def _skill_body_line(text: str) -> str:
    """One transcript line carrying `text` as a user-role message. Built with json.dumps.

    Hand-written JSON is how the first version of this fixture passed vacuously: its `\n` became a
    REAL newline inside a JSON string, so the line never parsed - and the substring check under test
    never parsed either, so both were wrong in the same direction and agreed with each other.
    """
    return json.dumps({"type": "user",
                       "message": {"role": "user",
                                   "content": [{"type": "text", "text": text}]}})


def test_an_active_update_config_skill_is_not_blocked(tmp_path):
    t = _transcript(tmp_path, _skill_body_line("# Update Config Skill\n\nModify config") + "\n")
    assert G.update_config_active(t) is True
    assert G.decide(_edit_event(t), {}) is None


def test_a_multiline_skill_body_is_recognised(tmp_path):
    """A real body is many KB of markdown; only its first line carries the marker."""
    body = "# Update Config Skill\n\n" + ("filler line\n" * 500)
    assert G.update_config_active(_transcript(tmp_path, _skill_body_line(body) + "\n")) is True


def test_merely_TALKING_about_update_config_still_blocks(tmp_path):
    """The bare name appears in ordinary prose about the rule - 57 times in one real session."""
    t = _transcript(tmp_path, '{"type":"assistant","message":{"content":"route it through update-config"}}\n')
    assert G.update_config_active(t) is False
    assert G.decide(_edit_event(t), {}) is not None


# The marker must START the text. Presence alone was the FIRST version of this check, and it was
# wrong: in the session that built this the H1 occurred 11 times and only ONE was the skill body -
# the rest were this guard's own source, its tests, a changelog entry and shell commands quoting
# it, echoed back through tool output. A substring test is disarmed by documenting the guard.

@pytest.mark.parametrize("line", [
    # the guard's own source, echoed by a grep
    '{"type":"user","message":{"role":"user","content":[{"type":"text",'
    '"text":"54:_UPDATE_CONFIG_MARK = \\"# Update Config Skill\\""}]}}',
    # an assistant message quoting it
    '{"type":"assistant","message":{"role":"assistant","content":"marker is # Update Config Skill"}}',
    # a tool result that merely contains it mid-text
    '{"type":"user","message":{"role":"user","content":[{"type":"text",'
    '"text":"grep output: 2 hits for # Update Config Skill"}]}}',
])
def test_quoting_the_marker_is_not_an_invocation(tmp_path, line):
    t = _transcript(tmp_path, line + "\n")
    assert G.update_config_active(t) is False
    assert G.decide(_edit_event(t), {}) is not None


def test_the_real_skill_body_starts_with_the_marker(tmp_path):
    """The positive control: the shape the harness actually injects must still be recognised."""
    t = _transcript(tmp_path, '{"type":"user","message":{"role":"user","content":[{"type":"text",'
                              '"text":"# Update Config Skill\\n\\nModify Claude Code config"}]}}\n')
    assert G.update_config_active(t) is True


def test_a_partial_line_from_the_tail_read_is_survivable(tmp_path):
    """The tail seek can land mid-line; an unparseable line is not a match and not a crash."""
    t = _transcript(tmp_path, 'ontent":[{"type":"text","text":"# Update Config Skill"}]}}\n')
    assert G.update_config_active(t) is False


def test_an_unreadable_transcript_fails_OPEN(tmp_path):
    """A real event with a broken path: blocking the sanctioned path is the worse failure."""
    assert G.update_config_active(str(tmp_path / "missing.jsonl")) is True


def test_an_ABSENT_transcript_path_is_not_an_exemption():
    """Every real event carries transcript_path, so a missing one must not disarm the guard."""
    assert G.update_config_active(None) is False
    assert G.update_config_active("") is False


def test_only_the_TAIL_is_scanned(tmp_path, monkeypatch):
    """A skill invoked long ago must not disarm the guard for the rest of the session."""
    monkeypatch.setattr(G, "_TAIL_BYTES", 200)
    t = _transcript(tmp_path, "# Update Config Skill\n" + ("x" * 5000) + "\n")
    assert G.update_config_active(t) is False


# ---------------------------------------------------------------- end to end

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_blocks_with_the_reason_on_stderr(tmp_path):
    # A REAL transcript with no update-config body: "/nonexistent" would fail open by design and
    # the assertion would then be testing the fail-open path while claiming to test the block.
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"type":"user","message":{"content":"hello"}}\n', encoding="utf-8")
    rc, _out, err = _run({
        "session_id": "t", "transcript_path": str(transcript), "cwd": str(HOOKS_DIR),
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
