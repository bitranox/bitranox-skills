"""Tests for toolbox-nudge.py (PreToolUse Bash nudge toward a local toolbox tool). ASCII only."""
import io
import json

import pytest

import toolbox_nudge as N


# ---- the pure matcher ---------------------------------------------------------------------------
def test_match_conflict_scan():
    assert N.match_tool("grep -rn '^<<<<<<<' .")[0] == "conflict_scan"


def test_match_jsonl_parse():
    assert N.match_tool('python3 -c "import json;[json.loads(l) for l in open(\'x.jsonl\')]"')[0] == "jsonl_grep"


def test_match_ssh_fleet():
    assert N.match_tool("ssh -o StrictHostKeyChecking=no -i k host uptime")[0] == "sshf"


def test_match_ci_triage():
    assert N.match_tool("cargo build 2>&1 | grep error")[0] == "ci_triage"


def test_match_git_state():
    assert N.match_tool("git rev-parse --abbrev-ref HEAD")[0] == "git_state"


def test_no_match_on_plain_commands():
    assert N.match_tool("ls -la /tmp") is None
    assert N.match_tool("echo hello && cat file.py") is None


# ---- the main() hook behavior -------------------------------------------------------------------
@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _feed(monkeypatch, ev):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))


def _ev(cmd, session="s1"):
    return {"tool_name": "Bash", "session_id": session, "tool_input": {"command": cmd}}


def _with_tool(home, name="git_state"):
    tools = home / ".claude" / "skills" / "toolbox" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / (name + ".py")).write_text("x", encoding="utf-8")


def test_main_nudges_when_tool_present(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD"))
    assert N.main() == 0
    out = capsys.readouterr().out
    assert "git_state" in out and "additionalContext" in out


def test_main_silent_when_tool_absent(home, monkeypatch, capsys):
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)   # empty, no git_state.py
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s2"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_silent_on_plain_command(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("ls -la", "s3"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_dedup_second_time_is_silent(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s4"))
    N.main()
    assert "git_state" in capsys.readouterr().out
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s4"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_ignores_non_bash_tool(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, {"tool_name": "Edit", "session_id": "s5",
                        "tool_input": {"command": "git rev-parse --abbrev-ref HEAD"}})
    N.main()
    assert capsys.readouterr().out.strip() == ""
