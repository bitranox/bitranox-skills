"""Tests for block-unbounded-find.py: refuse `find /` with no -maxdepth and no timeout."""

import io
import json
import sys

import pytest

import block_unbounded_find as G


@pytest.mark.parametrize("command", [
    "find / -name foo",
    "find / -xdev -name foo 2>/dev/null",
    "sudo find / -type f -name x",
    "cd /tmp && find / -name x | head",
    "ls; find -L / -name x",
    "find /opt/x / -name y",
])
def test_an_unbounded_walk_of_the_root_is_refused(command):
    assert "UNBOUNDED FIND" in G.assess(command)


@pytest.mark.parametrize("command", [
    "find / -maxdepth 2 -name foo",
    "timeout 30 find / -name foo",
    "find /etc -name foo",
    "find . -name foo",
    "find $HOME -name foo",
    "grep -rn 'find / is slow' docs",
    "echo find / -name foo",
    "ssh host 'find / -name foo'",
    "cat > x <<'EOF'\nfind / -name foo\nEOF\n",
    "git log -- 'find / x'",
])
def test_a_bounded_or_unrelated_command_passes(command):
    assert G.assess(command) is None


def test_powershell_is_not_judged():
    assert G.assess("find / -name foo", "PowerShell") is None


def test_main_refuses_with_exit_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "find / -name foo"}})))
    assert G.main() == 2
    assert "UNBOUNDED FIND" in capsys.readouterr().err


def test_main_passes_junk(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0
