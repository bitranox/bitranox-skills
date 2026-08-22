"""Tests for block-pgrep-self-match.py (PreToolUse(Bash) bracket-trick guard).

Contract: reads a PreToolUse event JSON on stdin. Exit 2 (with stderr) blocks only
when a pgrep/pkill bracket-trick pattern [X]rest has its de-bracketed literal Xrest
appearing contiguously elsewhere in the same command. Every other path exits 0.

All content is ASCII.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import block_pgrep_self_match as B

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "block-pgrep-self-match.py"
SHIM = HOOKS_DIR / "run-python.sh"


def run_main(monkeypatch, command):
    payload = json.dumps({"tool_input": {"command": command}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return B.main()


def test_no_pgrep_pkill_passes(monkeypatch):
    assert run_main(monkeypatch, "ls -la /tmp && echo done") == 0


def test_bracket_trick_clean_passes(monkeypatch):
    # The literal 'nginx' appears ONLY via the bracket form -> trick intact -> allow.
    assert run_main(monkeypatch, 'pgrep -f "[n]ginx"') == 0


def test_bracket_trick_defeated_by_echo_blocks(monkeypatch, capsys):
    cmd = 'pgrep -f "[n]ginx"; echo "=== nginx running? ==="'
    assert run_main(monkeypatch, cmd) == 2
    err = capsys.readouterr().err
    assert "BLOCKED" in err
    assert "[n]ginx -> nginx" in err


def test_plain_f_literal_blocks(monkeypatch, capsys):
    # This case used to be ALLOWED, on the recorded belief that catching it would
    # mean "blocking every pkill -f". That premise was wrong, and it is why the
    # error kept recurring: a plain `-f` literal ALWAYS self-matches, because -f
    # matches /proc/*/cmdline and this shell's own cmdline holds the literal.
    assert run_main(monkeypatch, "pgrep -f nginx") == 2
    assert "PLAIN" in capsys.readouterr().err


def test_plain_f_literal_over_ssh_blocks(monkeypatch):
    # The real hit that forced the hardening: killed the REMOTE shell (exit 255).
    assert run_main(monkeypatch, "ssh host 'pkill -f \"iperf3 -s\" 2>/dev/null'") == 2


def test_plain_f_literal_bundled_flags_blocks(monkeypatch):
    assert run_main(monkeypatch, 'pkill -af "vnc.*py"') == 2


def test_f_pattern_from_variable_passes(monkeypatch):
    # argv holds the UNEXPANDED "$NAME", so the expanded value is never in this
    # shell's own cmdline and cannot self-match.
    assert run_main(monkeypatch, 'pkill -f "$NAME"') == 0


def test_pkill_without_dash_f_passes(monkeypatch):
    # Without -f, pkill/pgrep match comm (the program name), not the full cmdline,
    # so a shell named bash/sh cannot match a program-name pattern.
    assert run_main(monkeypatch, "pkill -x iperf3") == 0
    assert run_main(monkeypatch, "pgrep iperf3") == 0


def test_explicit_self_exclusion_passes(monkeypatch):
    assert run_main(monkeypatch, 'pgrep -f "[n]ginx" | grep -vw "$$"') == 0


def test_git_commit_heredoc_body_not_blocked(monkeypatch):
    # The real false positive: a commit message (heredoc body) that DISCUSSES the pattern.
    # A heredoc body is stdin data, never the shell's argv, so it cannot self-match.
    cmd = "git commit -q -F - <<'MSG'\nnudge: pkill/pgrep -f -> procsig, ip neigh -> guestip\nMSG"
    assert run_main(monkeypatch, cmd) == 0


def test_git_commit_dash_m_message_not_blocked(monkeypatch):
    # git commit runs git, not pkill - the -m message text cannot self-match a pgrep/pkill call.
    assert run_main(monkeypatch, 'git commit -m "block pkill -f self-match footgun"') == 0


def test_real_pkill_after_commit_message_still_blocks(monkeypatch):
    # stripping the message must NOT hide a real pkill elsewhere in the command.
    assert run_main(monkeypatch, 'git commit -m "wip"; pkill -f nginx') == 2


def test_real_pkill_with_unrelated_heredoc_still_blocks(monkeypatch):
    cmd = "pkill -f nginx; cat <<'EOF'\nhello world\nEOF"
    assert run_main(monkeypatch, cmd) == 2


def test_empty_command_passes(monkeypatch):
    assert run_main(monkeypatch, "") == 0


def test_missing_tool_input_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({})))
    assert B.main() == 0


def test_malformed_stdin_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert B.main() == 0


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_subprocess_block_via_shim():
    cmd = 'pkill -f "[m]yproc"; echo "myproc gone"'
    res = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "BLOCKED" in res.stderr
