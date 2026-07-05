"""Tests for skill-edit-guard.py: deny a SKILL.md edit (exit 2), allow else, env opt-out, fail-open."""

import json

import pytest

import skill_edit_guard as G


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    # isolate HOME so a REAL session receipt on the dev machine cannot flip deny tests to allow
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _ev(tool, path):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def test_deny_reason_on_skill_md_edit():
    reason = G.decide(_ev("Edit", "/repo/plugins/bitranox/skills/foo/SKILL.md"), {})
    assert reason and "meta-skill-writer" in reason


def test_deny_on_write_and_multiedit_and_relative_path():
    assert G.decide(_ev("Write", "/x/skills/bar/SKILL.md"), {})
    assert G.decide(_ev("MultiEdit", "skills/baz/SKILL.md"), {})              # relative path still matches


def test_allow_non_skill_files():
    assert G.decide(_ev("Edit", "/x/skills/foo/README.md"), {}) is None       # not SKILL.md
    assert G.decide(_ev("Edit", "/x/notskills/foo/SKILL.md"), {}) is None     # "skills" not a path seg
    assert G.decide(_ev("Edit", "/x/src/SKILL.md"), {}) is None               # no /skills/<name>/


def test_allow_non_edit_tools():
    assert G.decide(_ev("Bash", "/x/skills/foo/SKILL.md"), {}) is None
    assert G.decide({"tool_name": "Read", "tool_input": {"file_path": "/x/skills/foo/SKILL.md"}}, {}) is None


def test_env_bypass_allows_silently():
    assert G.decide(_ev("Edit", "/x/skills/foo/SKILL.md"), {"BITRANOX_SKILL_WRITER": "1"}) is None


def test_missing_tool_input_is_allowed():
    assert G.decide({"tool_name": "Edit"}, {}) is None


def test_main_blocks_with_exit_2_and_stderr(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/skills/foo/SKILL.md"))))
    monkeypatch.delenv("BITRANOX_SKILL_WRITER", raising=False)
    assert G.main() == 2                              # non-zero blocks the tool call
    assert "SKILL-EDIT GUARD" in capsys.readouterr().err


def test_main_allows_when_env_set(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/skills/foo/SKILL.md"))))
    monkeypatch.setenv("BITRANOX_SKILL_WRITER", "1")
    assert G.main() == 0
    assert capsys.readouterr().err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert G.main() == 0                              # allow, never wedge
    assert capsys.readouterr().err == ""
