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


def test_plain_pgrep_without_bracket_passes(monkeypatch):
    # No bracket-trick token at all -> nothing for this guard to flag.
    assert run_main(monkeypatch, "pgrep -f nginx") == 0


def test_empty_command_passes(monkeypatch):
    assert run_main(monkeypatch, "") == 0


def test_missing_tool_input_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({})))
    assert B.main() == 0


def test_malformed_stdin_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert B.main() == 0


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
