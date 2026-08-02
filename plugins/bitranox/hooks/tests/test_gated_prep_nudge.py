"""Tests for gated-prep-nudge.py - warn when a gated verb shares a command with its own prep.

A PreToolUse gate judges the WHOLE command before any statement runs, so a block discards the
heredoc that wrote the commit message too. The retry then fails on a missing `-F` input and points
at the wrong cause. Recorded six times; this hook is the escalation from prose to a signal.
"""
import json

import gated_prep_nudge as N


def _ctx(command):
    """The additionalContext a PreToolUse run would emit, or None when it stays quiet."""
    return N.notice(command)


# --- it fires on the real shape -----------------------------------------------------------------

def test_heredoc_written_message_plus_git_commit_dash_f_is_flagged():
    """The exact shape that has cost six retries."""
    cmd = ("cat > /tmp/msg.txt <<'EOF'\nsubject line\n\nbody\nEOF\n"
           "git add -A && git commit -F /tmp/msg.txt")
    ctx = _ctx(cmd)
    assert ctx and "/tmp/msg.txt" in ctx and "commit" in ctx


def test_the_file_it_names_is_the_one_that_would_be_lost():
    cmd = "cat > notes/COMMIT_MSG <<EOF\nhi\nEOF\ngit commit -F notes/COMMIT_MSG"
    ctx = _ctx(cmd)
    assert "notes/COMMIT_MSG" in ctx


def test_git_push_counts_as_a_gated_verb():
    cmd = "cat > /tmp/m <<'EOF'\nx\nEOF\ngit push origin master"
    assert _ctx(cmd)


def test_printf_redirect_also_counts_as_prep():
    """Not every prep is a heredoc; a redirect that creates the input has the same failure."""
    cmd = "printf 'subject\\n' > /tmp/m.txt\ngit commit -F /tmp/m.txt"
    ctx = _ctx(cmd)
    assert ctx and "/tmp/m.txt" in ctx


def test_semicolon_separated_statements_are_seen():
    cmd = "cat > /tmp/m <<'EOF'\nx\nEOF\n; git commit -F /tmp/m"
    assert _ctx(cmd)


# --- it stays quiet otherwise -------------------------------------------------------------------

def test_a_commit_with_no_prep_in_the_same_command_is_quiet():
    """The correct shape must never be nagged, or the nudge trains itself out."""
    assert _ctx("git commit -F /tmp/msg.txt") is None


def test_writing_a_file_with_no_gated_verb_is_quiet():
    assert _ctx("cat > /tmp/notes.md <<'EOF'\nhello\nEOF") is None


def test_a_gated_verb_named_only_inside_the_heredoc_body_is_quiet():
    """The body is DATA. A guard that reads it fires on prose that documents the footgun."""
    cmd = ("cat > /tmp/doc.md <<'EOF'\n"
           "Never run `git commit -F msg` in the same command that writes msg.\n"
           "EOF\n"
           "echo done")
    assert _ctx(cmd) is None


def test_a_gated_verb_inside_a_heredoc_plus_an_unrelated_write_is_quiet():
    cmd = ("cat > /tmp/a.md <<'EOF'\ngit push origin master\nEOF\n"
           "cat > /tmp/b.md <<'EOF'\nmore prose\nEOF")
    assert _ctx(cmd) is None


def test_a_non_gated_git_verb_is_quiet():
    assert _ctx("cat > /tmp/m <<'EOF'\nx\nEOF\ngit status --porcelain") is None


def test_empty_and_garbage_input_never_raise():
    for cmd in ("", "   ", None, "cat > <<", "git commit -F"):
        N.notice(cmd)


# --- the hook contract --------------------------------------------------------------------------

def test_main_emits_additional_context_and_exits_zero(capsys):
    """Non-blocking: exit 0 with hookSpecificOutput, never a permissionDecision."""
    event = {"tool_name": "Bash",
             "tool_input": {"command": "cat > /tmp/m <<'EOF'\nx\nEOF\ngit commit -F /tmp/m"}}
    code = N.main(json.dumps(event))
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "additionalContext" in payload["hookSpecificOutput"]
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_main_is_silent_for_a_clean_command(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "git commit -F /tmp/m"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_never_wedges_on_malformed_input(capsys):
    for raw in ("", "not json", "{}", '{"tool_name": "Bash"}'):
        assert N.main(raw) == 0


def test_a_non_bash_tool_is_ignored(capsys):
    event = {"tool_name": "Write", "tool_input": {"content": "git commit -F x"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out.strip() == ""
