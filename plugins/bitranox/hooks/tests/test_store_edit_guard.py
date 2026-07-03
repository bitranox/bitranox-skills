"""Tests for store-edit-guard.py: deny a hand-edit of the curated store (exit 2), allow else, env
opt-out, fail-open. Uses the REAL Claude Code event keys (tool_name / tool_input)."""

import json
import store_edit_guard as G


def _ev(tool, path):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def test_deny_reason_on_index_edit():
    reason = G.decide(_ev("Edit", "/repo/.claude-bx-selflearning/index.md"), {})
    assert reason and "memory_engine.py" in reason


def test_deny_on_facts_body_and_write_and_multiedit_and_relative():
    assert G.decide(_ev("Write", "/x/.claude-bx-selflearning/facts/foo.md"), {})
    assert G.decide(_ev("MultiEdit", "/x/.claude-bx-selflearning/facts/ab/uuid.md"), {})  # sharded
    assert G.decide(_ev("Edit", ".claude-bx-selflearning/index.md"), {})                  # relative path


def test_allow_non_store_files():
    assert G.decide(_ev("Edit", "/x/CLAUDE.md"), {}) is None                    # ancestor marker, not store
    assert G.decide(_ev("Edit", "/x/CLAUDE.local.md"), {}) is None              # import host, hand-editable
    assert G.decide(_ev("Edit", "/x/.claude-bx-selflearning-old/facts/a.md"), {}) is None  # not the seg
    assert G.decide(_ev("Edit", "/x/src/main.py"), {}) is None


def test_allow_non_edit_tools():
    assert G.decide(_ev("Bash", "/x/.claude-bx-selflearning/index.md"), {}) is None
    assert G.decide({"tool_name": "Read",
                     "tool_input": {"file_path": "/x/.claude-bx-selflearning/index.md"}}, {}) is None


def test_env_bypass_allows_silently():
    assert G.decide(_ev("Edit", "/x/.claude-bx-selflearning/index.md"),
                    {"BITRANOX_MEMORY_ENGINE": "1"}) is None


def test_missing_tool_input_is_allowed():
    assert G.decide({"tool_name": "Edit"}, {}) is None


def test_main_blocks_with_exit_2_and_stderr(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/.claude-bx-selflearning/index.md"))))
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)
    assert G.main() == 2                              # non-zero blocks the tool call
    assert "STORE-EDIT GUARD" in capsys.readouterr().err


def test_main_allows_when_env_set(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/.claude-bx-selflearning/facts/a.md"))))
    monkeypatch.setenv("BITRANOX_MEMORY_ENGINE", "1")
    assert G.main() == 0
    assert capsys.readouterr().err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert G.main() == 0                              # allow, never wedge
    assert capsys.readouterr().err == ""
