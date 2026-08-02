"""Tests for toolbox-nudge.py (PreToolUse Bash nudge toward a local toolbox tool). ASCII only."""
import io
import json
import sys

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


def test_main_falls_back_to_the_shipped_copy_when_the_local_one_is_absent(home, monkeypatch, capsys):
    """An empty local toolbox is no longer silence: git_state ships with the plugin.

    This test used to assert silence, which encoded the old local-only contract. Retiring a local
    tool after contributing it upstream is now the norm, so silence there would lose the guard for
    exactly the tools broadly useful enough to ship.
    """
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)   # empty, no git_state.py
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s2"))
    N.main()
    out = capsys.readouterr().out.strip()
    assert "compuse-toolbox" in out and "git_state" in out


def test_main_silent_when_the_tool_exists_neither_locally_nor_shipped(home, monkeypatch, capsys):
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)
    monkeypatch.setattr(N, "_shipped_dir", lambda: home / "no-such-plugin-dir")
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s2b"))
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


# ---- claim_check: a presence check whose NEGATIVE answer cannot be trusted ------------------------

def test_match_claim_check_on_grep_count():
    """`grep -c` decides "is it there?" - and returns file:count under -r, exits 1 on zero.

    Both shapes produced a confident false ABSENT in one session, twice.
    """
    assert N.match_tool('grep -c "LC_ALL=C" skill.md')[0] == "claim_check"
    assert N.match_tool('grep -ric "pattern" file.md')[0] == "claim_check"


def test_match_claim_check_on_file_listing():
    assert N.match_tool('grep -l "needle" *.md')[0] == "claim_check"
    assert N.match_tool('grep -rL "needle" src/')[0] == "claim_check"


def test_claim_check_does_not_hijack_an_ordinary_grep():
    """A plain search is not a presence CHECK; nudging on every grep would get the hook ignored."""
    for cmd in ('grep -rn "needle" src/', 'grep -i pattern file', "grep --color=auto x y"):
        matched = N.match_tool(cmd)
        assert matched is None or matched[0] != "claim_check", cmd


def test_conflict_scan_still_wins_its_own_shape():
    """conflict_scan's rule is listed first and uses -rn, so the new rule must not shadow it."""
    assert N.match_tool("grep -rn '^<<<<<<<' .")[0] == "conflict_scan"


# --- a heredoc body is DATA, not a command ------------------------------------------------------

def test_a_tool_name_inside_a_heredoc_body_does_not_nudge():
    """Writing prose that MENTIONS a chore must not fire the nudge for it.

    A fact body containing the word pgrep, written with `cat > f <<'EOF' ... EOF`, fired the
    procsig nudge: the heredoc body is data being written, not a command being run. Same family
    as the git-footgun and shell-prefix guards, which already strip heredoc bodies."""
    command = (
        "cat > /tmp/body.md <<'EOF'\n"
        "Same root as the pgrep -f \"X\" self-match trap, where a keyword that also appears in\n"
        "your own command line makes the check match itself.\n"
        "EOF\n"
        "echo done\n"
    )
    assert N.match_tool(N.extract_text("Bash", {"command": command})) is None


def test_a_real_invocation_outside_the_heredoc_still_nudges():
    """The control: stripping data must not disarm the guard for an actual command."""
    command = (
        "cat > /tmp/body.md <<'EOF'\n"
        "just some prose\n"
        "EOF\n"
        "pgrep -f openvmm\n"
    )
    matched = N.match_tool(N.extract_text("Bash", {"command": command}))
    assert matched is not None and matched[0] == "procsig"


# ---- a tool that moved upstream must still be nudged, pointing at the shipped copy ---------------

def _event(cmd, session="s1"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": session}


def _run(event, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    N.main()
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else None


def test_nudge_points_at_the_shipped_copy_when_there_is_no_local_one(tmp_path, monkeypatch, capsys):
    """Retiring a local tool after contributing it upstream must not silence its nudge.

    The tools most worth nudging about are exactly the ones broadly useful enough to ship, so
    keying the nudge on the LOCAL file alone turns a successful contribution into a lost guard.
    """
    monkeypatch.setenv("HOME", str(tmp_path))          # no local toolbox at all
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    msg = _run(_event("pkill -f myserver"), monkeypatch, capsys)
    assert msg is not None, "nudge went silent for a tool that ships with the plugin"
    assert "compuse-toolbox" in msg and "procsig" in msg


def test_a_local_tool_still_wins(tmp_path, monkeypatch, capsys):
    """Local-only tools (no shipped twin) keep working, and a local copy is preferred if present."""
    tools = tmp_path / ".claude" / "skills" / "toolbox" / "tools"
    tools.mkdir(parents=True)
    (tools / "procsig.py").write_text("# local\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    msg = _run(_event("pkill -f myserver", session="s2"), monkeypatch, capsys)
    assert msg is not None and "skills/toolbox/tools/procsig.py" in msg


def test_still_silent_for_a_tool_that_exists_nowhere(tmp_path, monkeypatch, capsys):
    """Must-not-break: a match for a tool neither local nor shipped stays silent."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(N, "_shipped_dir", lambda: tmp_path / "nowhere")
    assert _run(_event("pkill -f myserver", session="s3"), monkeypatch, capsys) is None
