"""Tests for make-push-args-nudge: a bmk commit message with shell metacharacters in ARGS=."""

import io
import json
import sys

import pytest

import make_push_args_nudge as M


@pytest.mark.parametrize("command", [
    'make push ARGS="fix: guard the parser (unicode)"',
    "make push ARGS='first; second'",
    'make ship ARGS="feat: y (z)"',
    'make commit ARGS="x; y"',
    'make -C /repo push ARGS="a (b)"',
    'cd /repo && make push ARGS="costs \\$5"',
    'make push ARGS="run `date`"',
    "make push ARGS=\"'quoted'\"",
    'make push "fix: trailing words (quoted)"',
    'make push MSG="ok" ARGS="still (wins)"',
    'env -u VIRTUAL_ENV make push ARGS="a; b"',
])
def test_fires_on_metacharacters_in_the_args_channel(command):
    assert M.notice(command) is not None


@pytest.mark.parametrize("command", [
    'make push MSG="fix: guard the parser (unicode)"',
    'make push MSG="first; second"',
    'make push ARGS="fix login bug"',
    "make push fix login bug",
    'make push ARGS="feat: add x, y"',
    'make push ARGS="fix-it"',
    "make push",
    # Not a message-taking target: ARGS goes to pytest or similar, where parentheses are syntax.
    'make test ARGS="-k (a or b)"',
    # Data, not a command.
    "echo 'make push ARGS=\"a (b)\"'",
    "cat <<'EOF' > note.md\nmake push ARGS=\"a (b)\"\nEOF",
    # Prose after a `$(...)` inside double quotes: the separator walk opens a segment there, but
    # nothing in a quoted string runs. Measured in the replay: a handover log line.
    "printf '%s\\n' \"$(date +%H:%M) make bump-minor; then make push (later)\" >> log.md",
    # Redirections are not message words.
    'make push MSG="fix (x)" > /tmp/push.log 2>&1',
    'make push MSG="fix (x)" </dev/null >>log.txt',
    "make push fix login bug > log 2>&1",
    # Another program.
    'bmk push "fix (x)"',
])
def test_quiet_on_msg_plain_words_and_other_targets(command):
    assert M.notice(command) is None


def test_notice_names_msg_and_the_readback():
    text = M.notice('make push ARGS="a (b)"')
    assert 'MSG="' in text
    assert "git log -1 --format=%s" in text
    assert "bitranox:devops-bmk" in text


def test_non_string_input_is_quiet():
    assert M.notice(None) is None
    assert M.notice(["make", "push"]) is None


def _run_main(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    rc = M.main()
    return rc, capsys.readouterr().out


def test_main_emits_additional_context_and_never_blocks(monkeypatch, capsys):
    rc, out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": 'make push ARGS="a; b"'}})
    assert rc == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "MSG=" in payload["additionalContext"]
    assert "permissionDecision" not in payload


def test_main_ignores_other_tools(monkeypatch, capsys):
    rc, out = _run_main(monkeypatch, capsys, {
        "tool_name": "Write", "tool_input": {"command": 'make push ARGS="a; b"'}})
    assert (rc, out) == (0, "")


def test_main_survives_garbage_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert M.main() == 0
    assert capsys.readouterr().out == ""
