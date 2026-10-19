"""Tests for unbuffered-python-nudge.py - a Python whose output can die unflushed.

Off a tty Python's stdout is BLOCK-buffered and flushed at exit. Over ssh, or backgrounded into a
log, the process can be killed or hang before that exit, and then nothing it
printed arrives - not even how far it got. Twice in two months a hung probe hid where it hung.
"""
import json

import unbuffered_python_nudge as N


def _n(cmd, background=False):
    return N.notice(cmd, background=background)


# --- fires where the output can be lost ----------------------------------------------------------

def test_a_remote_python_script_over_ssh_is_flagged():
    assert _n("ssh host 'python3 probe.py'")


def test_a_remote_python_reading_a_heredoc_is_flagged():
    """`ssh host python3 - <<'EOF'` is the probe shape that hung."""
    assert _n("ssh -o BatchMode=yes host python3 - <<'EOF'\nprint('x')\nEOF")


def test_a_remote_python_behind_cd_and_a_pipe_is_flagged():
    assert _n("ssh -i key.pem root@host \"cd /opt/x && python3 run.py | tail -5\"")


def test_a_remote_venv_interpreter_by_path_is_flagged():
    assert _n("ssh host /opt/app/.venv/bin/python -c 'import app; app.scan()'")


def test_a_remote_uv_run_script_is_flagged_and_told_to_use_the_env_var():
    ctx = _n("ssh host 'uv run --script probe.py'")
    assert ctx and "PYTHONUNBUFFERED=1" in ctx


def test_ssh_option_values_are_not_read_as_the_host_or_a_tty():
    """`-vi key` takes the key as a value; the `t` in an -o value is not `-t`."""
    assert _n("ssh -vi key.pem host python3 probe.py")
    assert _n("ssh -oStrictHostKeyChecking=no host python3 probe.py")
    assert _n("ssh -o StrictHostKeyChecking=no -p 2222 host python3 probe.py")


def test_ssh_t_inside_a_flag_cluster_is_quiet():
    assert _n("ssh -At host python3 probe.py") is None
    assert _n("ssh -tt host python3 probe.py") is None


def test_a_local_python_under_timeout_is_quiet():
    """A timeout kills only a hang; a gate under one delivers its output at its normal exit, and
    flagging it was 92 percent of all firings in the corpus replay."""
    assert _n("timeout 900 .venv/bin/python -m pytest -q") is None


def test_an_ssh_call_under_timeout_is_still_flagged():
    assert _n("timeout 60 ssh host python3 probe.py")


def test_a_backgrounded_python_writing_a_log_is_flagged():
    assert _n("python3 long_job.py > job.log 2>&1", background=True)


def test_a_nohup_python_writing_a_log_is_flagged():
    assert _n("nohup python3 long_job.py > job.log 2>&1 &")


def test_a_remote_bash_c_python_is_flagged():
    assert _n("ssh host bash -c 'python3 probe.py'")


def test_the_message_names_the_fix():
    ctx = _n("ssh host python3 probe.py")
    assert "-u" in ctx and "PYTHONUNBUFFERED=1" in ctx


# --- stays quiet where it is already unbuffered or cannot be lost -------------------------------

def test_dash_u_is_quiet():
    assert _n("ssh host python3 -u probe.py") is None


def test_dash_u_inside_a_flag_cluster_is_quiet():
    assert _n("ssh host python3 -Iu probe.py") is None


def test_the_environment_variable_is_quiet():
    assert _n("ssh host PYTHONUNBUFFERED=1 python3 probe.py") is None
    assert _n("timeout 60 env PYTHONUNBUFFERED=1 uv run probe.py") is None


def test_ssh_with_a_tty_is_quiet():
    """`ssh -t` gives the remote a tty, so its stdout is line-buffered."""
    assert _n("ssh -t host python3 probe.py") is None


def test_a_plain_local_python_is_quiet():
    """Not killed early, not detached: the exit flush delivers everything."""
    assert _n("python3 probe.py | tail -5") is None


def test_a_backgrounded_python_with_no_log_file_is_quiet():
    """Output to the task's own pipe is captured at exit; only a log someone reads is at risk."""
    assert _n("python3 probe.py", background=True) is None


def test_version_and_installer_calls_are_quiet():
    assert _n("ssh host python3 --version") is None
    assert _n("ssh host python3 -m venv /opt/v") is None
    assert _n("ssh host python3 -m pip install x") is None


def test_a_dash_after_c_is_not_read_as_an_interpreter_flag():
    """`-c 'print(-u)'`: the code is data, not a -u flag."""
    assert _n("ssh host python3 -c 'import sys; sys.argv[1:]' -u") is not None


def test_python_mentioned_in_a_heredoc_body_is_quiet():
    cmd = ("cat > notes.md <<'EOF'\n"
           "run ssh host python3 probe.py to check\n"
           "EOF\necho ok")
    assert _n(cmd) is None


def test_a_word_containing_python_is_not_an_interpreter():
    assert _n("ssh host pythonista-sync run") is None
    assert _n("ssh host cat python3.log") is None


def test_empty_and_garbage_never_raise():
    for cmd in ("", "   ", None, "ssh", "ssh -i", "timeout", "ssh host 'python3", "uv run"):
        N.notice(cmd)


# --- the hook contract ---------------------------------------------------------------------------

def _run(payload, capsys):
    rc = N.main(json.dumps(payload))
    return rc, capsys.readouterr().out


def test_main_emits_additional_context_and_exits_0(capsys):
    rc, out = _run({"tool_name": "Bash",
                    "tool_input": {"command": "ssh host python3 probe.py"}}, capsys)
    assert rc == 0
    body = json.loads(out)["hookSpecificOutput"]
    assert body["hookEventName"] == "PreToolUse" and "-u" in body["additionalContext"]


def test_main_reads_run_in_background(capsys):
    rc, out = _run({"tool_name": "Bash",
                    "tool_input": {"command": "python3 job.py > job.log 2>&1",
                                   "run_in_background": True}}, capsys)
    assert rc == 0 and out


def test_main_is_silent_on_other_tools_and_bad_input(capsys):
    assert _run({"tool_name": "Read", "tool_input": {"file_path": "x"}}, capsys) == (0, "")
    assert N.main("not json") == 0
    assert N.main("[]") == 0
