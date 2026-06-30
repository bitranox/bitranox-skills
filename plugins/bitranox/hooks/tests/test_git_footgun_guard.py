"""Tests for git-footgun-guard.py (blocks `git rev-parse --short` with 2+ revs).

Pure-function tests on broken_revparse plus end-to-end tests that drive main()
with a stdin payload, and a subprocess smoke test through run-python.sh.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import git_footgun_guard as G

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "git-footgun-guard.py"
SHIM = HOOKS_DIR / "run-python.sh"


# broken_revparse: the broken form is --short with 2+ revisions.
def test_two_revs_with_short_is_broken():
    assert G.broken_revparse("git rev-parse --short feat origin/feat") is True


def test_two_revs_with_short_and_dash_c():
    assert G.broken_revparse("git -C /repo rev-parse --short A B") is True


def test_short_eq_len_form_is_broken():
    assert G.broken_revparse("git rev-parse --short=12 A B") is True


def test_single_rev_with_short_is_ok():
    assert G.broken_revparse("git rev-parse --short HEAD") is False


def test_two_revs_without_short_is_ok():
    assert G.broken_revparse("git rev-parse HEAD~1 HEAD") is False


def test_short_with_other_flags_single_rev_ok():
    assert G.broken_revparse("git rev-parse --short --verify HEAD") is False


def test_neighbour_segment_not_conflated():
    # rev-parse here has one rev; the two refs are a separate piped command.
    assert G.broken_revparse("git rev-parse --short HEAD | grep A B") is False


def test_non_git_command_ignored():
    assert G.broken_revparse("echo rev-parse --short A B") is False


def test_redirection_not_counted_as_operand():
    # the bug: a redirection target was miscounted as a second revision -> false block
    assert G.broken_revparse("git rev-parse --short origin/master 2>/dev/null") is False
    assert G.broken_revparse("git rev-parse --short HEAD 2> /dev/null") is False
    assert G.broken_revparse("git rev-parse --short HEAD >out 2>&1") is False


def test_redirection_does_not_mask_real_breakage():
    # two genuine revisions are still broken even with a trailing redirection
    assert G.broken_revparse("git rev-parse --short A B 2>/dev/null") is True


def _run(monkeypatch, command):
    payload = {"tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return G.main()


def test_main_blocks_broken(monkeypatch):
    assert _run(monkeypatch, "git rev-parse --short A B") == 2


def test_main_allows_ok(monkeypatch):
    assert _run(monkeypatch, "git rev-parse --short HEAD") == 0


def test_main_bad_payload_is_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0


def test_shim_smoke():
    payload = json.dumps({"tool_input": {"command": "git rev-parse --short A B"}})
    r = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True
    )
    assert r.returncode == 2
    assert "needed a single commit" in r.stderr
