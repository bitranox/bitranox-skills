"""Tests for warn-inline-powershell.py. ASCII only.

Both directions matter equally: the nudge must fire on the mangling shape, and must stay silent on
the `-File` form it asks for - otherwise it nags the person who already complied.
"""
import json
import subprocess
import sys
from pathlib import Path

import warn_inline_powershell as W

HOOK = Path(__file__).resolve().parent.parent / "warn-inline-powershell.py"


# ---- when it must fire -------------------------------------------------------------------------

def test_fires_on_inline_command_over_ssh():
    notice = W.build_notice('ssh win-host \'powershell -Command "Get-Process | Select Name"\'')
    assert notice and "INLINE REMOTE POWERSHELL" in notice


def test_fires_for_pwsh_and_for_the_exe_suffix():
    assert W.build_notice('ssh host \'pwsh -Command "ls | more"\'')
    assert W.build_notice('ssh host \'powershell.exe -Command "ls | more"\'')


def test_fires_on_the_short_and_abbreviated_command_flags():
    for flag in ("-c", "-Com", "-Comm", "-Command"):
        assert W.build_notice('ssh host \'powershell %s "a | b"\'' % flag), flag


def test_explains_that_more_escaping_will_not_help():
    notice = W.build_notice('ssh host \'powershell -Command "a | b"\'')
    assert "cmd.exe" in notice
    assert "-File" in notice


# ---- when it must stay silent ------------------------------------------------------------------

def test_silent_on_the_file_form_it_asks_for():
    assert W.build_notice("ssh host 'powershell -File C:\\tmp\\job.ps1'") is None
    assert W.build_notice("ssh host 'pwsh -f C:\\tmp\\job.ps1'") is None


def test_silent_without_ssh():
    """Local PowerShell has no cmd.exe layer in between, so the mangling does not apply."""
    assert W.build_notice('powershell -Command "Get-Process | Select Name"') is None


def test_silent_without_powershell():
    assert W.build_notice("ssh host 'ls -la | wc -l'") is None


def test_silent_when_no_command_string_is_passed():
    assert W.build_notice("ssh host 'powershell'") is None
    assert W.build_notice("ssh host 'powershell -NoProfile'") is None


def test_flag_matching_does_not_trip_on_a_longer_word():
    """-Comparison / --command-file are not the flag; a naive substring match would fire."""
    assert W.build_notice("ssh host 'powershell -Comparison foo'") is None
    assert W.build_notice("ssh host 'powershell --command-file x'") is None


def test_empty_command_is_silent():
    assert W.build_notice("") is None
    assert W.build_notice(None) is None


# ---- the hook contract -------------------------------------------------------------------------

def _run(payload):
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True)


def test_hook_emits_additional_context():
    r = _run({"tool_input": {"command": 'ssh host \'powershell -Command "a | b"\''}})
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "INLINE REMOTE POWERSHELL" in payload["hookSpecificOutput"]["additionalContext"]


def test_hook_is_silent_on_the_file_form():
    r = _run({"tool_input": {"command": "ssh host 'powershell -File job.ps1'"}})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_hook_never_wedges_a_turn_on_bad_input():
    for bad in ("", "garbage", "[]"):
        r = subprocess.run([sys.executable, str(HOOK)], input=bad, capture_output=True, text=True)
        assert r.returncode == 0, bad
