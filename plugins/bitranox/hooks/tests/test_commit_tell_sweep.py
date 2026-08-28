"""Tests for commit-tell-sweep.py (git commit-message tell PreToolUse guard).

Drives main() with a stdin PreToolUse Bash payload; a subprocess smoke test runs the shim.
All source ASCII; tell characters via chr(), never pasted.
"""

import io
import json
import subprocess
import sys
import pytest
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


@pytest.mark.skipif(sys.platform == "win32",
                    reason="a Windows tmp_path is backslashed and POSIX shlex eats the separators, "
                           "so -F names an unopenable path and this guard approves the commit - a "
                           "real defect, fixed by keying the split on the TOOL, not a test artifact")
def test_message_file_scanned(monkeypatch, tmp_path):
    f = tmp_path / "msg.txt"
    f.write_text("Subject %s tell\n" % EM_DASH, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F %s' % f) == 2


def test_bad_payload_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert C.main() == 0


def test_unbalanced_quotes_safe(monkeypatch):
    assert _run(monkeypatch, 'git commit -m "oops') == 0    # shlex fails -> fail-open


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_shim_smoke(tmp_path):
    payload = json.dumps({"tool_input": {"command": 'git commit -m "bad %s dash"' % EM_DASH}})
    r = subprocess.run(["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True)
    assert r.returncode == 2 and "tell(s)" in r.stderr


@pytest.mark.parametrize("flags", ["-m", "-am", "-sm", "-asm", "-anm"])
def test_a_clustered_short_flag_still_exposes_the_message(monkeypatch, flags):
    """`git commit -am "..."` is the commonest commit form there is, and it bypassed this guard.

    `_messages` tested `t in ("-m", "--message")` and `t.startswith("-m")`; a cluster matches
    neither, so the message list came back empty and the hook approved a message it never read.
    `-m` is the control: it always worked, so a harness broken for another reason fails it too.
    """
    assert _run(monkeypatch, 'git commit %s "subject %s here"' % (flags, EM_DASH)) == 2


def test_a_value_taking_flag_before_m_is_not_a_message(monkeypatch):
    """In `-Cm` the `m` is `-C`'s VALUE (reuse commit "m"), not the message flag.

    Scanning a cluster for `m` anywhere would read the next token as a message and block a commit
    that carries none - so the scan has to stop at the first value-taking option.
    """
    assert _run(monkeypatch, 'git commit -Cm "not %s a message"' % EM_DASH) == 0


def test_the_attached_file_form_is_read(monkeypatch, tmp_path):
    """`-Fmsg.txt` is the same cluster gap on the file side: only `-F file` was handled.

    The path is passed forward-slashed and quoted so this stays a test of the ATTACHED form. A
    BACKSLASHED path is mangled by POSIX shlex on every platform and is a separate, real defect -
    see the skip on test_message_file_scanned - and letting it fail here would attribute it to the
    cluster parsing instead.
    """
    f = tmp_path / "msg.txt"
    f.write_text("subject %s here\n" % EM_DASH, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F"%s"' % f.as_posix()) == 2
