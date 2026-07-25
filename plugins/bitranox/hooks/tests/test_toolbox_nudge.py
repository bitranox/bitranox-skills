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


def test_match_procsig_pkill():
    assert N.match_tool("pkill -f 'vm-79099-disk-0'")[0] == "procsig"


def test_match_procsig_pgrep():
    assert N.match_tool("pgrep -af openvmm -f")[0] == "procsig"


def test_match_guestip_ip_neigh():
    assert N.match_tool("ip neigh show dev vmbr0 | grep bc:24")[0] == "guestip"


def test_match_guestip_getent_ovm():
    assert N.match_tool("getent hosts OVM-64000")[0] == "guestip"


def test_match_ovmlog():
    assert N.match_tool("tail -100 /var/log/openvmm/79099.log")[0] == "ovmlog"


def test_no_match_on_plain_commands():
    assert N.match_tool("ls -la /tmp") is None
    assert N.match_tool("echo hello && cat file.py") is None


# ---- the pure text extractor (which field each tool hides the chore in) --------------------------
def test_extract_text_bash_is_the_command():
    assert N.extract_text("Bash", {"command": "ls -la"}) == "ls -la"


def test_extract_text_write_is_the_content():
    assert N.extract_text("Write", {"file_path": "/tmp/x.py", "content": "print(1)"}) == "print(1)"


def test_extract_text_edit_is_the_new_string():
    assert N.extract_text("Edit", {"old_string": "a", "new_string": "print(1)"}) == "print(1)"


def test_extract_text_multiedit_joins_new_strings():
    txt = N.extract_text("MultiEdit", {"edits": [{"new_string": "alpha"}, {"new_string": "beta"}]})
    assert "alpha" in txt and "beta" in txt


def test_extract_text_unscanned_tool_is_none():
    assert N.extract_text("Read", {"file_path": "x"}) is None


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


def test_main_nudges_on_hand_rolled_write(home, monkeypatch, capsys):
    """The blind spot: a chore hand-rolled by WRITING a script file, not a Bash one-liner."""
    _with_tool(home, "jsonl_grep")
    _feed(monkeypatch, {"tool_name": "Write", "session_id": "w1",
                        "tool_input": {"file_path": "/tmp/scratch.py",
                                       "content": 'import json\n[json.loads(l) for l in open("t.jsonl")]'}})
    assert N.main() == 0
    out = capsys.readouterr().out
    assert "jsonl_grep" in out and "additionalContext" in out


def test_main_nudges_on_edit_new_string(home, monkeypatch, capsys):
    _with_tool(home, "sshf")
    _feed(monkeypatch, {"tool_name": "Edit", "session_id": "e1",
                        "tool_input": {"file_path": "/tmp/f.sh", "old_string": "x",
                                       "new_string": "ssh -o StrictHostKeyChecking=no -i k host uptime"}})
    assert N.main() == 0
    assert "sshf" in capsys.readouterr().out


def test_main_silent_on_write_without_matching_content(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, {"tool_name": "Write", "session_id": "w2",
                        "tool_input": {"file_path": "/tmp/x.py", "content": "print('hello world')"}})
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_ignores_unscanned_tool(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, {"tool_name": "Read", "session_id": "r1", "tool_input": {"file_path": "x"}})
    N.main()
    assert capsys.readouterr().out.strip() == ""
