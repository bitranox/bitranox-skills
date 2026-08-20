"""Tests for retry-with-a-flag-nudge.py (PostToolUseFailure records, PreToolUse judges).

The pair only works if both halves run, so there is an end-to-end test that records through one
event and judges through the other, not just unit tests of the two pure functions.

The negative cases carry the weight here. A nudge that fired on ordinary iteration would be worse
than no nudge - the reader learns to ignore the channel - so "changed an operand", "removed a
flag", "different program" and "unrelated command" all have to stay silent.
"""

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

import retry_with_a_flag_nudge as R

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "retry-with-a-flag-nudge.py"
SHIM = HOOKS_DIR / "run-python.sh"


# ---------------------------------------------------------------- shape()

def test_shape_splits_program_flags_and_operands():
    assert R.shape("rsync -a src dst") == ("rsync", ("-a",), ("src", "dst"))


def test_shape_takes_the_last_statement_because_that_is_the_one_that_failed():
    assert R.shape("cd /tmp && rsync -a src dst") == ("rsync", ("-a",), ("src", "dst"))


def test_shape_uses_the_basename_so_a_full_path_is_the_same_program():
    assert R.shape("/usr/bin/sed -i s/a/b/ f")[0] == "sed"


def test_shape_ignores_flag_order():
    assert R.shape("tool -a -b x") == R.shape("tool -b -a x")


def test_shape_drops_a_heredoc_body_so_a_written_script_is_not_a_command():
    command = "cat > s.sh <<'EOF'\nrsync -avz src dst\nEOF"
    assert R.shape(command)[0] != "rsync"


@pytest.mark.parametrize("command", ["", None, "   ", 42])
def test_shape_is_none_for_nothing_runnable(command):
    assert R.shape(command) is None


# --------------------------------------------- what the corpus replay found (regression)
#
# The first version fired 536 times over 181 real sessions, 216 of them in one session, and
# essentially every hit was a pipeline tail rather than a retry. These two cases are that bug,
# pinned: after the fix the same replay fires twice in total.

def test_a_pipeline_is_one_statement_so_the_filter_is_not_the_command():
    """`grep ... | head -60` is a grep, not a head. Splitting on `|` was the whole 536."""
    assert R.shape("grep -n pattern f.md | head -60")[0] == "grep"


def test_a_command_with_no_operand_has_no_retry_target():
    """With operands empty, "same operands" is vacuously true and any two invocations match."""
    assert R.shape("head -60") is None
    assert R.shape("pytest") is None
    assert R.shape("ls -la") is None


def test_two_unrelated_pipelines_ending_in_head_do_not_match():
    """The exact false positive: different greps whose pipeline tails differ only by a flag."""
    failed = R.shape("grep -n alpha a.md | head")
    pending = R.shape("grep -n beta b.md | head -60")
    assert R.only_flags_added(pending, failed) is False


# ---------------------------------------------------------------- only_flags_added()

def test_the_same_command_with_one_more_flag_is_the_pattern():
    assert R.only_flags_added(R.shape("rsync -a -z src dst"), R.shape("rsync -a src dst")) is True


def test_an_identical_command_is_not_the_pattern():
    """A plain re-run is a different mistake, and this hook is not the one to report it."""
    assert R.only_flags_added(R.shape("rsync -a src dst"), R.shape("rsync -a src dst")) is False


def test_a_changed_operand_is_a_different_target_not_this():
    assert R.only_flags_added(R.shape("rsync -a -z src other"), R.shape("rsync -a src dst")) is False


def test_removing_a_flag_is_not_this():
    assert R.only_flags_added(R.shape("rsync src dst"), R.shape("rsync -a src dst")) is False


def test_a_different_program_is_not_this():
    """Changing the INSTRUMENT is exactly what the skill asks for - never nudge on it."""
    assert R.only_flags_added(R.shape("rclone -a -z src dst"), R.shape("rsync -a src dst")) is False


# ---------------------------------------------------------------- notice()

def test_notice_names_the_flag_that_was_added():
    recorded = [list(R.shape("rsync -a src dst"))]
    message = R.notice("rsync -a -z src dst", recorded)
    assert message is not None and "-z" in message
    assert "process-stop-repeating-failure" in message


def test_notice_is_silent_when_nothing_matches():
    assert R.notice("ls -la", [list(R.shape("rsync -a src dst"))]) is None


def test_notice_is_silent_with_an_empty_ledger():
    assert R.notice("rsync -a -z src dst", []) is None


# ---------------------------------------------------------------- end to end, both events

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.fixture
def session(request):
    """A session id unique to this test AND this run, with its state file removed afterwards.

    The hook persists per-session state in the shared audit dir, and `FIRE_CAP` bounds how often it
    will speak per session. A fixed session name therefore makes these tests pass twice and fail on
    the third run, which is exactly the order-dependent shape that reads as a defect in the code
    under test. Measured before this fixture existed: runs 1-2 green, runs 3-4 red.
    """
    name = f"retryflag-{request.node.name}-{uuid.uuid4().hex[:8]}"
    yield name
    try:
        R._state_path(name).unlink()
    except OSError:
        pass


def _failure(session, command, is_interrupt=False):
    return {"session_id": session, "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
            "hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
            "tool_input": {"command": command}, "error": "boom", "is_interrupt": is_interrupt}


def _pending(session, command, tool_name="Bash"):
    return {"session_id": session, "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
            "hook_event_name": "PreToolUse", "tool_name": tool_name,
            "tool_input": {"command": command}}


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_record_then_judge_fires(session):
    assert _run(_failure(session, "rsync -a src dst")) == (0, "", "")
    rc, out, _err = _run(_pending(session, "rsync -a -z src dst"))
    assert rc == 0, "the nudge must never block"
    assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PreToolUse"


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_judging_without_a_recorded_failure_is_silent(session):
    """The control: the same pending command, with nothing recorded, must say nothing."""
    assert _run(_pending(session, "rsync -a -z src dst")) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_an_interrupt_is_not_recorded_as_a_failure(session):
    """A user interrupt is the user changing their mind, not the command failing."""
    _run(_failure(session, "rsync -a src dst", is_interrupt=True))
    assert _run(_pending(session, "rsync -a -z src dst")) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_powershell_is_treated_like_bash_on_both_halves(session):
    failure = _failure(session, "rsync -a src dst")
    failure["tool_name"] = "PowerShell"
    assert _run(failure) == (0, "", "")
    rc, out, _err = _run(_pending(session, "rsync -a -z src dst", tool_name="PowerShell"))
    assert rc == 0 and out, "PowerShell must record and judge exactly like Bash"


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert (proc.returncode, proc.stdout.strip()) == (0, "")
