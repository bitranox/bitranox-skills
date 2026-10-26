"""Tests for tail-obsolete-count-nudge.py - catch `tail -N` handed two or more files.

uutils tail (the coreutils of Ubuntu 26.04) accepts the obsolete `-N` / `+N` count with ONE file
and rejects it with two or more: exit 1, "unexpected argument". In a read-back line after a gate
or a push, that exit 1 becomes the call's exit code and reads as a failure of the work it was only
displaying.
"""
import json

import tail_obsolete_count_nudge as N


def _n(cmd):
    return N.notice(cmd)


# --- fires on the trap ---------------------------------------------------------------------------

def test_a_count_with_two_files_is_flagged():
    assert _n("tail -1 a.out b.out")


def test_the_read_back_after_two_runs_is_flagged():
    """The shape both recorded hits had: a display line chained after the work."""
    assert _n("python3 x.py > a.out 2>&1; echo rc=$?; tail -1 a.out b.out")


def test_a_count_with_trailing_letters_is_flagged():
    """`-1q` and `-5f` are the obsolete form too, and fail the same way."""
    assert _n("tail -1q a b")
    assert _n("tail -5f a b")


def test_a_plus_count_is_flagged():
    assert _n("tail +2 a b")


def test_files_after_a_double_dash_count():
    assert _n("tail -3 -- a b")


def test_a_launcher_in_front_does_not_hide_it():
    assert _n("sudo tail -3 x y")
    assert _n("timeout 5 tail -3 x y")


def test_a_redirect_after_two_files_still_fires():
    assert _n("tail -1 a b 2>/dev/null")


def test_the_message_names_the_portable_form():
    ctx = _n("tail -1 a b")
    assert "tail -n 1" in ctx


# --- stays quiet otherwise -----------------------------------------------------------------------

def test_a_count_with_one_file_is_quiet():
    assert _n("tail -1 a.out") is None


def test_the_n_option_is_quiet():
    assert _n("tail -n 1 a b") is None
    assert _n("tail -n1 a b") is None
    assert _n("tail -n +2 a b") is None


def test_a_byte_count_option_is_quiet():
    assert _n("tail -c 5 a b") is None


def test_a_pipe_into_tail_is_quiet():
    assert _n("make test 2>&1 | tail -20") is None


def test_redirect_targets_are_not_files():
    """`> out` and `2> err` name where output goes, not what tail reads."""
    assert _n("tail -1 a > out") is None
    assert _n("tail -1 a 2> err") is None
    assert _n("tail -1 a 2>/dev/null") is None


def test_head_is_quiet():
    """head accepts the obsolete count with several files."""
    assert _n("head -1 a b") is None


def test_tail_as_data_is_quiet():
    assert _n("grep tail -1 a b") is None
    assert _n("echo 'tail -1 a b'") is None


def test_a_heredoc_body_is_quiet():
    assert _n("cat > note.md <<'EOF'\ntail -1 a b\nEOF") is None


def test_a_file_named_like_a_count_after_double_dash_is_a_file():
    """After `--` every word is a file, so `-1` there is not a count."""
    assert _n("tail -n 1 -- -1 b") is None


def test_a_count_shaped_word_after_double_dash_is_a_file_not_a_count():
    """Without `--` ending the options, `-1` would read as a count and b, c as two files."""
    assert _n("tail -n 1 -- -1 b c") is None


def test_digits_inside_a_file_name_are_not_a_count():
    """The count must be the WHOLE word: `x-1` is a file, not `-1`."""
    assert _n("tail -n 1 x-1 y z") is None


def test_empty_and_non_string_input_is_quiet():
    assert _n("") is None
    assert _n(None) is None


# --- the hook contract ---------------------------------------------------------------------------

def test_main_emits_additional_context_when_it_fires(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "tail -1 a b"}}
    assert N.main(json.dumps(event)) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "tail -n 1" in out["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_for_another_tool(capsys):
    event = {"tool_name": "Read", "tool_input": {"command": "tail -1 a b"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out == ""


def test_main_survives_garbage(capsys):
    assert N.main("not json") == 0
    assert N.main("[]") == 0
    assert N.main(json.dumps({"tool_name": "Bash", "tool_input": "x"})) == 0
    assert capsys.readouterr().out == ""
