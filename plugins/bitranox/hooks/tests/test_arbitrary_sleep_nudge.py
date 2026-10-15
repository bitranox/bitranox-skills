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


# --- a trailing & on a waiter or a gate (contrib #22, refusal since OPEN-WORK [9](2)) -------------
# Corpus replay 2026-10-15 (143,483 shell commands): the waiter shape fired 21 times, every one a
# gate.py, ci_wait.py or `gh run watch` detached with `&`. Widened to a GATE detached with `&` it
# fired 30 more: 27 real detached gates (the 2026-10-09 subagent `make test &` among them), 1 a
# pair a later ` wait` collects (missed by the old wait pattern, fixed below), 2 one fixture that
# names a fake process `pytest-control`.


@pytest.mark.parametrize("command", [
    "nohup python3 /p/scripts/gate.py --gate 'make test' --log /tmp/g.log > /dev/null 2>&1 &",
    "nohup uv run /p/scripts/ci_wait.py --sha $(git rev-parse HEAD) > w.log 2>&1 &\necho started",
    "(sleep 600; echo TIMEOUT >> run.log) &",
    "until test -f /tmp/done.flag; do sleep 5; done &",
    "while pgrep -x make >/dev/null; do sleep 10; done & echo armed",
    "gh run watch 123 --exit-status > watch.log 2>&1 &",
    "python3 backstop.py --deadline 900 &",
])
def test_a_backgrounded_waiter_is_named(command):
    assert N.backgrounded_waiter(command, "Bash") is not None


@pytest.mark.parametrize("command", [
    "(sleep 0.5; rm -rf /tmp/x) & python3 -m pytest -q; wait",   # a later wait collects it
    "nohup myserver --port 8080 > s.log 2>&1 &",                  # a daemon, not a waiter
    "sleep 5 && echo ready",                                      # no &
    "make test 2>&1 | tee log",
    "cat > notes.md <<'EOF'\nsleep 300 &\nEOF",                  # heredoc body is data
    "echo 'gate.py --gate x &'",                                  # quoted data
])
def test_a_non_waiter_or_a_collected_one_is_silent(command):
    assert N.backgrounded_waiter(command, "Bash") is None


def test_powershell_is_out_of_scope_for_the_ampersand_check():
    """In PowerShell `&` is the CALL operator: `& gate.py ...` runs it in the foreground."""
    assert N.backgrounded_waiter("& python gate.py --gate 'x'", "PowerShell") is None


@pytest.mark.parametrize("command", [
    "make test &",
    "nohup env -u VIRTUAL_ENV make test > /tmp/g.log 2>&1 &\necho \"started pid $!\"",
    "(make test > g.log 2>&1; echo RC=$? >> g.log) &",
    ".venv/bin/python -m pytest -q -p no:cacheprovider > full.log 2>&1 &",
    "timeout 600 .venv/bin/pyright -p . > pyr.txt 2>&1 &",
    "BMK_OUTPUT_FORMAT=text make test-all > all.log 2>&1 &",
    "cd /repo && make test > g.log 2>&1 &",
    "make test && git push &",
])
def test_a_gate_detached_with_an_ampersand_is_named(command):
    """The 2026-10-09 recurrence was a subagent's `make test &`, which no waiter word matched.

    The last case backgrounds the whole AND-list, gate included: `a && b &` detaches `a` too.
    """
    assert N.backgrounded_waiter(command, "Bash") is not None


@pytest.mark.parametrize("command", [
    "(pytest a > r.log 2>&1) & (pytest b > s.log 2>&1) & wait; tail r.log s.log",
    "(sleep 600; touch a) & (sleep 600; touch b) & wait",
    "make test > g.log 2>&1 & pid=$!; do_other_work; wait $pid",
    "make test > g.log 2>&1",
    "echo 'make test' &",
    "cat > notes.md <<'EOF'\nmake test &\nEOF",
])
def test_a_collected_or_a_quoted_gate_is_silent(command):
    """A `wait` after the last `&` collects it, a space before `wait` included.

    The first case is a real corpus command: the old pattern needed `wait` glued to the separator,
    so ` & wait` after the second job did not count and a correctly collected pair was flagged.
    """
    assert N.backgrounded_waiter(command, "Bash") is None


def _run_hook(command, *, background=False, tool_name="Bash"):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool_name,
             "tool_input": {"command": command, "run_in_background": background}}
    return subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


@pytest.mark.parametrize("background,phrase", [(True, "exits at once"), (False, "orphan")])
@pytest.mark.parametrize("command", [
    "nohup python3 gate.py --gate 'make test' > g.log 2>&1 &",
    "nohup make test > g.log 2>&1 &",
])
def test_main_refuses_a_detached_waiter_and_says_why_in_each_mode(command, background, phrase):
    """A REFUSAL, by the user's decision of 2026-10-12: the warning recurred while it existed.

    Replaces a test that pinned exit 0 with an advisory - the behaviour the decision changed.
    Exit 2 is the block code, the reason goes to stderr, and stdout stays empty so no
    additionalContext competes with it.
    """
    proc = _run_hook(command, background=background)
    assert proc.returncode == 2
    assert phrase in proc.stderr
    assert "BLOCKED" in proc.stderr
    assert proc.stdout.strip() == ""


def test_the_refusal_names_the_way_out_for_a_job_that_must_outlive_the_session():
    """run_in_background is reaped with the session, so the refusal must name the other route."""
    proc = _run_hook("nohup make test > g.log 2>&1 &")
    assert "setsid nohup" in proc.stderr and "script" in proc.stderr


@pytest.mark.parametrize("command", [
    "nohup myserver --port 8080 > s.log 2>&1 &",
    "(sleep 0.5; rm -rf /tmp/x) & python3 -m pytest -q; wait",
])
def test_main_lets_a_daemon_or_a_collected_job_through(command):
    assert _run_hook(command).returncode == 0


def test_main_never_refuses_the_powershell_call_operator():
    proc = _run_hook("& make test", tool_name="PowerShell")
    assert proc.returncode == 0


def test_a_long_bare_sleep_stays_advisory():
    """Only the detached shape became a refusal; a long sleep in the foreground is still a nudge."""
    proc = _run_hook("sleep 300 && echo done")
    assert proc.returncode == 0
    assert "ARBITRARY SLEEP" in json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
