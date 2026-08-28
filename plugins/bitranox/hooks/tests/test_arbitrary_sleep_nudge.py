"""A long bare `sleep` is waiting on the CLOCK, which is the thing the wait rule forbids.

From `feedback-match-the-wait-to-the-event-s-actual-timing-do-not-over-wait` (recurrence 2): wait
on a concrete signal, or on a measured duration plus a small margin - never an arbitrary sleep,
and stop and investigate at roughly 2x the expected time rather than waiting longer.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "arbitrary-sleep-nudge.py"
_spec = importlib.util.spec_from_file_location("arbitrary_sleep_nudge", _HOOK)
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


@pytest.mark.parametrize("command", [
    "sleep 300",
    "sleep 120 && curl -s http://host/health",
    "ssh host 'sleep 600; systemctl status app'",
    "sleep 10m",
    "sleep 2h",
])
def test_a_long_bare_sleep_is_nudged(command):
    notice = N.notice(command)
    assert notice is not None
    assert "signal" in notice.lower()


@pytest.mark.parametrize("command", [
    "sleep 2",
    "sleep 30",
    "sleep 0.5",
])
def test_a_short_settle_pause_is_left_alone(command):
    """The negative must be reachable: a couple of seconds to let a service settle is not this."""
    assert N.notice(command) is None


def test_a_sleep_inside_a_polling_loop_is_the_right_shape_already():
    """Sleeping between CHECKS is waiting on a signal - exactly what the rule asks for."""
    assert N.notice("until curl -sf http://h/ready; do sleep 300; done") is None
    assert N.notice("while ! test -f /tmp/done; do sleep 600; done") is None
    assert N.notice("for i in $(seq 1 10); do check || sleep 120; done") is None


def test_prose_mentioning_sleep_does_not_fire():
    doc = "cat > note.md <<'EOF'\nnever write sleep 600 and hope\nEOF"
    assert N.notice(doc) is None


def test_junk_is_ignored():
    assert N.notice("") is None
    assert N.notice(None) is None
    assert N.notice("sleep") is None


@pytest.mark.parametrize("command", [
    "sleep 300 && echo done",
    "sleep 120; echo done",
    "sleep 900 && tail -n 50 build.log | grep -i done",
    "sleep 300 && curl -s localhost:8080/health   # give it a while to boot",
    "sleep 300; while true; do work; done",
])
def test_a_loop_word_outside_a_loop_body_does_not_exempt(command):
    """The exemption is for a sleep PACING a poll, so it must key on the do/done BODY.

    Matching the bare word anywhere in the command silenced the nudge on the exact shape it
    exists to catch - a fixed clock wait followed by an announcement. The last case is the
    sharpest: a real loop is present, but the sleep sits outside its body.
    """
    assert N.notice(command) is not None


def test_an_overflowing_sleep_argument_still_nudges():
    """A number that overflows float to inf must not take the nudge down with it.

    `int(inf)` raises, main() has no try around notice(), and the top-level fail-open turns that
    into exit 0 with no output - the nudge is lost exactly where the input is most absurd.
    """
    notice = N.notice("sleep " + "9" * 400)
    assert notice is not None
    assert "signal" in notice.lower()


@pytest.mark.parametrize("command", [
    "Start-Sleep -Seconds 600",
    "Start-Sleep 600",
    "start-sleep -s 600",
    "Start-Sleep -Milliseconds 600000",
])
def test_the_powershell_spelling_is_nudged(command):
    """hooks.json matches Bash|PowerShell, so the detector has to know both spellings.

    A hook that runs and finds nothing is as silent as one that never fires.
    """
    assert N.notice(command) is not None


@pytest.mark.parametrize("command", [
    "Start-Sleep -Milliseconds 5000",
    "Start-Sleep -Milliseconds 500",
])
def test_a_short_powershell_pause_is_left_alone(command):
    """-Milliseconds is not seconds: 5000 of them is a settle pause, not a wait on an event."""
    assert N.notice(command) is None


def test_main_writes_the_pretooluse_additional_context_envelope():
    """No test reached main(): the stdin parse, the tool gate and the envelope keys all shipped
    unexercised, and silence is this hook's normal output so nothing else would notice."""
    event = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
             "tool_input": {"command": "sleep 300"}}
    proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "signal" in payload["hookSpecificOutput"]["additionalContext"].lower()


@pytest.mark.parametrize("command", [
    "while (-not (Test-Path C:\\ready)) { Start-Sleep -Seconds 300 }",
    "do { Start-Sleep -Seconds 300 } while (-not $ok)",
    "while ($true) { Get-Job; Start-Sleep -Seconds 600 }",
    "foreach ($h in $hosts) { Invoke-Rest $h; Start-Sleep -Seconds 120 }",
])
def test_a_powershell_polling_loop_is_left_alone(command):
    """PowerShell paces a poll with a BRACE block, not do/done.

    Regression guard: keying the exemption on do/done alone would start nudging every Windows
    polling loop the moment the detector learned the Start-Sleep spelling.
    """
    assert N.notice(command, "PowerShell") is None


@pytest.mark.parametrize("command", [
    "awk '/for/ { system(\"sleep 300\") }' file.txt",
    "awk '/while/ { system(\"sleep 600\") }' log",
])
def test_a_brace_block_never_exempts_a_bash_command(command):
    """A brace block is PowerShell LOOP syntax; in Bash it is not a loop body at all.

    awk pairs a loop WORD with a later brace and really does wait on the clock, so exempting it
    would be silent - the failure mode nobody reports. Bash keeps do/done and nothing else.
    """
    assert N.notice(command, "Bash") is not None


def test_the_tool_defaults_to_the_stricter_shell():
    """An unknown tool must not buy the PowerShell exemption: fewer silent misses is the safe
    default for a nudge that fails open anyway."""
    assert N.notice("awk '/for/ { system(\"sleep 300\") }' f") is not None



@pytest.mark.parametrize("tool_name,expect_silence", [("PowerShell", True), ("Bash", False)])
def test_main_forwards_the_event_s_tool_to_the_exemption(tool_name, expect_silence):
    """The same command, two tools, two verdicts - through main(), which is where the tool lives.

    Every other tool-keyed test calls notice() directly, so main() could stop forwarding
    tool_name and the suite would stay green while every Windows polling loop got nudged.
    """
    event = {"hook_event_name": "PreToolUse", "tool_name": tool_name,
             "tool_input": {"command": "while ($true) { Start-Sleep -Seconds 300 }"}}
    proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert proc.returncode == 0
    assert (proc.stdout.strip() == "") is expect_silence
