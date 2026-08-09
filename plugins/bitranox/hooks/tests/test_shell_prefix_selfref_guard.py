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
