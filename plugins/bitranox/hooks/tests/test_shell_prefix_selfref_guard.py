"""The prefix-assignment self-reference guard.

`VAR=value cmd ... "$VAR"` never does what it looks like: a prefix assignment
sets the variable in the COMMAND's environment, while `$VAR` on the same line is
expanded by the CURRENT shell first, which has not been assigned. The reference
therefore expands to the shell's own value, usually empty - silently, with exit 0.

That is how a release commit got the message `chores`: the composed message was
written to a file correctly, then delivered with
`MSG="$(cat f)" make push MSG="$MSG"`, and the program received an empty string.
"""

from __future__ import annotations

import shell_prefix_selfref_guard as guard
import pytest


def blocked(command: str) -> bool:
    """Return whether the guard would block this command line."""

    return guard.self_referencing_prefix(command)


# ---------------------------------------------------------------- the real bug


def test_the_release_failure_that_motivated_this_guard() -> None:
    assert blocked('MSG="$(cat msg.txt)" make push MSG="$MSG"')


def test_a_bare_unquoted_reference_is_the_same_bug() -> None:
    assert blocked("FOO=1 printf %s $FOO")


def test_a_braced_reference_is_the_same_bug() -> None:
    assert blocked("FOO=1 printf %s ${FOO}")


def test_an_env_wrapper_between_the_assignment_and_the_use_still_counts() -> None:
    # `env -u X cmd` is a common shape and hides nothing: the prefix still binds
    # to env's environment, and "$MSG" is still expanded by the outer shell.
    assert blocked('MSG="$(cat f)" env -u VIRTUAL_ENV make push MSG="$MSG"')


def test_only_the_offending_segment_matters() -> None:
    assert blocked('echo start && MSG="x" make push MSG="$MSG"')


# ------------------------------------------------------- legitimate, must pass


def test_a_single_quoted_reference_is_correct_and_must_not_block() -> None:
    # The outer shell does NOT expand inside single quotes; the child shell does,
    # and it HAS the variable. This form works and is idiomatic.
    assert not blocked("FOO=bar sh -c 'echo $FOO'")


def test_an_exported_variable_used_later_is_not_a_prefix_assignment() -> None:
    assert not blocked('export MSG="$(cat f)"; make push MSG="$MSG"')


def test_a_prefix_assignment_with_no_reference_is_fine() -> None:
    assert not blocked("LC_ALL=C sort file.txt")


def test_a_reference_to_a_different_variable_is_fine() -> None:
    assert not blocked('LC_ALL=C make push MSG="$OTHER"')


def test_a_separate_statement_is_not_the_same_line() -> None:
    # After the `;` the prefix is long gone, so this references the shell's own
    # variable deliberately - not the trap.
    assert not blocked('FOO=1 true; echo "$FOO"')


def test_prose_mentioning_the_pattern_is_not_an_invocation() -> None:
    # The guard must not block writing about the footgun it guards.
    command = "python3 - <<'PY'\nprint('never write MSG=\"$(cat f)\" make push MSG=\"$MSG\"')\nPY"
    assert not blocked(command)


def test_an_assignment_that_is_only_a_comparison_is_not_a_prefix() -> None:
    assert not blocked('[ "$MSG" = "x" ] && echo yes')


# ------------------------------------------------------------------ the plumbing


@pytest.mark.parametrize(
    ("command", "expected_exit"),
    [('MSG="$(cat f)" make push MSG="$MSG"', 2), ("LC_ALL=C sort f", 0)],
)
def test_the_hook_exit_code_matches_the_verdict(command: str, expected_exit: int, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import io
    import json

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))

    assert guard.main() == expected_exit
    if expected_exit == 2:
        assert "prefix assignment" in capsys.readouterr().err


def test_malformed_input_never_wedges_a_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("not json at all"))

    assert guard.main() == 0


# ---- command substitution inside SELF-AUTHORED TEXT --------------------------------------------
# Same family as the prefix self-reference: the shell evaluates the text before the program sees
# it. Measured 2026-07-12: a memory --hook describing a fix wrapped the word shutdown in
# backticks, the double-quoted argument command-substituted it, and the dev box ran the real
# shutdown - it only survived because polkit denied it.

def test_backticks_inside_a_text_carrying_flag_are_blocked():
    assert guard.substitutes_inside_text_arg(
        'memory_engine add --hook "When the box hangs, run `shutdown -r now`."') is True
    assert guard.substitutes_inside_text_arg(
        'git commit -m "fix $(whoami) crash"') is True
    assert guard.substitutes_inside_text_arg(
        'tool add --why "see `git log`"') is True


def test_ordinary_command_substitution_is_untouched():
    """$() is legitimate nearly everywhere - only text-carrying flags are in scope."""
    assert guard.substitutes_inside_text_arg("cd $(dirname /a/b) && ls") is False
    assert guard.substitutes_inside_text_arg('rc=$?; echo "$rc"') is False
    assert guard.substitutes_inside_text_arg("files=$(ls | head -3)") is False
    assert guard.substitutes_inside_text_arg('git commit -F /tmp/msg.txt') is False


def test_a_text_flag_with_no_substitution_is_fine():
    assert guard.substitutes_inside_text_arg('git commit -m "plain subject line"') is False
    assert guard.substitutes_inside_text_arg("tool add --title 'single quoted $(safe)'") is False


# ------------------------------------------- the UNQUOTED HEREDOC (recurrence 5)
#
# Bash performs parameter expansion, command substitution and arithmetic expansion in the body of
# a bare `<<EOF`, and NONE of it in `<<'EOF'`. So self-authored prose carrying backticks inside a
# bare heredoc is executed before the program ever sees it. Measured 2026-08-27: composing a
# memory body that way turned 4 KB of prose into 3.4 MB of shell output, exit 0, no warning.
#
# The argument-position half of this rule has been guarded since plugin 5.161.0. The heredoc half
# was NOT, and the same fact has now been violated in that position twice - because
# `strip_heredoc_bodies` hides every heredoc body from every command-scanning guard, which is
# correct for a QUOTED delimiter and wrong for a bare one.


def heredoc_blocked(command: str) -> bool:
    return guard.substitutes_inside_unquoted_heredoc(command)


def test_the_composition_that_produced_3_4_mb_of_garbage() -> None:
    assert heredoc_blocked("python3 - <<EOPY\nextra = '''see `avg-*.txt`'''\nEOPY")


def test_dollar_paren_in_a_bare_heredoc_body_is_the_same_bug() -> None:
    assert heredoc_blocked("cat > f.md <<EOF\nrun $(git rev-parse HEAD) first\nEOF")


def test_the_dash_form_is_the_same_opener() -> None:
    assert heredoc_blocked("cat <<-EOF\n\tsee `date` here\n\tEOF")


def test_an_unterminated_bare_heredoc_still_counts() -> None:
    """It consumes the rest of the command, so the substitution is still expanded."""

    assert heredoc_blocked("python3 - <<EOPY\nprose with `backticks` and no terminator")


# ------------------------------------------------------- what must NOT be blocked


def test_a_quoted_delimiter_is_the_documented_fix_and_must_pass() -> None:
    """<<'EOF' is inert: bash expands nothing inside it. Blocking it would block the fix."""

    assert not heredoc_blocked("python3 - <<'EOPY'\nextra = '''see `avg-*.txt`'''\nEOPY")
    assert not heredoc_blocked('python3 - <<"EOPY"\nsee `avg-*.txt`\nEOPY')


def test_a_bare_heredoc_without_substitution_is_ordinary_work() -> None:
    assert not heredoc_blocked("cat > f.txt <<EOF\nplain prose, nothing to expand\nEOF")


def test_a_bare_dollar_var_does_not_count() -> None:
    """Templating a value into a heredoc is normal and does not EXECUTE anything.

    Only the substituting forms run a command. Including $VAR would fire on ordinary work,
    and a guard that fires on ordinary work gets disabled rather than obeyed.
    """

    assert not heredoc_blocked("cat > f.conf <<EOF\npath = $HOME/x\nEOF")


def test_an_opener_inside_a_quoted_string_is_not_an_opener() -> None:
    """The false positive that showed up when this rule was priced against real history.

    A `python3 -c "...<<EOPY..."` argument MENTIONS a heredoc; it does not open one. Read
    literally, the mention has no terminator, so it swallows the rest of the command and every
    backtick in it. This is the shape that makes a guard block its own documentation.
    """

    assert not heredoc_blocked(
        'python3 -c "real = \\"python3 - <<EOPY\\nsee `x`\\nEOPY\\""'
    )
    assert not heredoc_blocked("echo 'use <<EOPY and then `cmd`'")


def test_prose_inside_a_QUOTED_heredoc_may_mention_a_bare_one() -> None:
    """Writing the documentation for this very rule must not trip it."""

    command = (
        "cat > doc.md <<'MDEOF'\n"
        "Bash expands `$(...)` inside a bare <<EOF and not inside <<'EOF'.\n"
        "MDEOF"
    )
    assert not heredoc_blocked(command)


def test_commands_with_no_heredoc_at_all() -> None:
    for text in ("", "git status", "echo `date`", 'git commit -m "see `date`"'):
        assert not heredoc_blocked(text), text


def test_an_escaped_backtick_in_a_bare_heredoc_runs_nothing() -> None:
    r"""A bare heredoc still honours a backslash, so \` is a literal backtick.

    Adjudicating this rule's firings against their source transcripts, this was 9 of 12: the
    author had already escaped, precisely because they knew the delimiter was unquoted. Firing
    on them would make the guard mostly wrong, which is how a guard gets disabled.
    """

    assert not heredoc_blocked("cat > f.md <<EOF\nsee \\`avg.txt\\` here\nEOF")
    assert not heredoc_blocked("cat > f.sh <<EOF\ndeadline=\\$(( \\$(date +%s) + 780 ))\nEOF")


def test_an_escaped_and_an_unescaped_span_in_one_body_still_blocks() -> None:
    """The escape blanking must not excuse a real substitution sitting beside a safe one."""

    assert heredoc_blocked("cat > f.md <<EOF\nsafe \\`a\\` then live `b`\nEOF")
