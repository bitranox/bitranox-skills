"""Tests for commit-tell-sweep.py (git commit-message tell PreToolUse guard).

Drives main() with a stdin PreToolUse Bash payload; a subprocess smoke test runs the shim.
All source ASCII; tell characters via chr(), never pasted.
"""

import io
import json
import os
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


def _run(monkeypatch, command, tool_name="Bash"):
    payload = {"tool_name": tool_name, "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
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
    """Runs on every platform now.

    It was skipped on Windows because a Windows tmp_path is backslashed and shlex eats the
    separators - but that is what BASH does too (verified against real bash: an unquoted
    C:\\Users\\me\\f.txt reaches the program as C:Usersmef.txt), so on the Bash arm it was never a
    defect, only an unrealistic command. Hand bash a path bash can carry and the test is portable.
    The backslash case that IS a defect lives on the PowerShell arm, below.
    """
    f = tmp_path / "msg.txt"
    f.write_text("Subject %s tell\n" % EM_DASH, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F "%s"' % f.as_posix()) == 2


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


def _backslashed_file(tmp_path, text):
    """A file that really exists and whose path string contains a backslash, on either platform.

    On Windows every path already is one. On POSIX a backslash is an ordinary filename character,
    which is what lets the PowerShell arm be tested on the platform this suite mostly runs on.
    """
    if os.name == "nt":
        f = tmp_path / "sub" / "msg.txt"
        f.parent.mkdir()
    else:
        f = tmp_path / "sub\\msg.txt"
    f.write_text(text, encoding="utf-8")
    return f


def test_a_powershell_backslashed_message_file_is_read(monkeypatch, tmp_path):
    """The defect this whole split exists for: in PowerShell a backslash is a PATH SEPARATOR.

    POSIX shlex eats it, the -F path opens nothing, and the guard returns 0 on a commit whose
    message it never inspected - a guard approving precisely what it exists to block.
    """
    f = _backslashed_file(tmp_path, "Subject %s tell\n" % EM_DASH)
    assert _run(monkeypatch, 'git commit -F %s' % f, tool_name="PowerShell") == 2


def test_the_same_command_under_bash_is_not_second_guessed(monkeypatch, tmp_path):
    """The control that proves the split is KEYED rather than made uniform.

    Real bash mangles that unquoted path identically, so the guard reading nothing here is the
    guard agreeing with the shell. Applying the Windows rules to a Bash command would be a new
    defect, not a wider net.
    """
    f = _backslashed_file(tmp_path, "Subject %s tell\n" % EM_DASH)
    assert _run(monkeypatch, 'git commit -F %s' % f, tool_name="Bash") == 0


REPLACEMENT = chr(0xFFFD)


def test_a_non_utf8_message_file_is_not_called_a_tell(monkeypatch, tmp_path):
    """The reader must not manufacture the character the detector hunts for.

    U+FFFD is in RANGES on purpose - it is mojibake and worth reporting. But decoding with
    errors="replace" MINTS one for every undecodable byte, so any file that is not UTF-8 was
    reported as carrying AI-writing tells and its commit blocked on a message that named a
    character the file does not contain.
    """
    f = tmp_path / "msg.txt"
    f.write_bytes("Subject line, plain ASCII\n".encode("utf-8") + b"\xff\xfe\x00tail\n")
    assert _run(monkeypatch, 'git commit -F "%s"' % f.as_posix()) == 0


def test_a_genuine_replacement_character_is_still_a_tell(monkeypatch, tmp_path):
    """The direction the fix must NOT reach: a U+FFFD that was really encoded in the file.

    Without this the previous test is satisfied by deleting U+FFFD from the tell set, which
    would silently stop reporting real mojibake.
    """
    f = tmp_path / "msg.txt"
    f.write_text("Subject %s tail\n" % REPLACEMENT, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F "%s"' % f.as_posix()) == 2


def test_a_message_file_s_content_is_never_echoed_to_the_model(monkeypatch, tmp_path, capsys):
    """PreToolUse runs BEFORE the Bash call is approved, so the path is still just a string the
    model named. Quoting the matched lines back on exit 2 hands it up to 20 lines of a file the
    Read tool's permission rules might refuse. A line number and a codepoint fix the message
    just as well and carry nothing the model did not already have.
    """
    f = tmp_path / "msg.txt"
    f.write_text("private-value-from-a-file %s\n" % EM_DASH, encoding="utf-8")
    assert _run(monkeypatch, 'git commit -F "%s"' % f.as_posix()) == 2
    err = capsys.readouterr().err
    assert "private-value-from-a-file" not in err
    assert "1: U+2014" in err


def test_an_inline_message_is_still_quoted_back(monkeypatch, capsys):
    """The direction the containment fix must NOT reach: the model typed this text itself, so
    quoting the offending line is free and is what makes the block actionable."""
    assert _run(monkeypatch, 'git commit -m "Fix the widget %s properly"' % EM_DASH) == 2
    assert "Fix the widget" in capsys.readouterr().err


def test_the_message_file_read_is_capped(tmp_path):
    """A commit message file is small. Reading an unbounded one lets a guard that runs before
    approval pull an arbitrary amount of a file into the hook."""
    f = tmp_path / "big.txt"
    f.write_text("x" * 200000, encoding="utf-8")
    assert len(C._read_message_file(str(f))) <= 65536
