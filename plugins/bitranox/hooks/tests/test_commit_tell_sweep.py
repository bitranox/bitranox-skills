"""Tests for commit-tell-sweep.py (git commit-message tell PreToolUse guard).

Drives main() with a stdin PreToolUse Bash payload; a subprocess smoke test runs the shim.
All source ASCII; tell characters via chr(), never pasted.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import commit_tell_sweep as C

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "commit-tell-sweep.py"
SHIM = HOOKS_DIR / "run-python.sh"

EM_DASH = chr(0x2014)
CURLY = chr(0x201C)


def _run(monkeypatch, command):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    return C.main()


def test_clean_commit_passes(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "Fix the bug - properly"') == 0


def test_em_dash_in_message_blocks(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "Fix %s properly"' % EM_DASH) == 2


def test_curly_quote_blocks(monkeypatch):
    assert _run(monkeypatch, 'git commit -m %sTitle%s' % (CURLY, CURLY)) == 2


def test_second_m_body_scanned(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "clean" -m "body %s here"' % EM_DASH) == 2


def test_attached_m_form(monkeypatch):
    assert _run(monkeypatch, 'git commit -m"msg %s"' % EM_DASH) == 2


def test_git_tag_and_merge_messages_scanned(monkeypatch):
    assert _run(monkeypatch, 'git tag -a v1 -m "release %s"' % EM_DASH) == 2
    assert _run(monkeypatch, 'git merge --no-ff -m "merge %s"' % EM_DASH) == 2


def test_backtick_reference_ignored(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "do not use `%s` in prose"' % EM_DASH) == 0


def test_non_git_command_ignored(monkeypatch):
    # a non-git -m value with a tell (e.g. grep) must not fire
    assert _run(monkeypatch, 'grep -m 5 "%s" file' % EM_DASH) == 0


def test_message_file_scanned(monkeypatch, tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Subject %s tell\n" % EM_DASH, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F %s' % f) == 2


def test_bad_payload_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert C.main() == 0


def test_unbalanced_quotes_safe(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "oops') == 0    # shlex fails -> fail-open


def test_shim_smoke(tmp_path):
    payload = json.dumps({"tool_input": {"command": 'git commit -m "bad %s dash"' % EM_DASH}})
    r = subprocess.run(["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True)
    assert r.returncode == 2 and "tell(s)" in r.stderr
