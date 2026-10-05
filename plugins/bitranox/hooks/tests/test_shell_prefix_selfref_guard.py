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


def test_a_separator_inside_a_quoted_value_does_not_split_the_statement():
    """The MISS. `SEP.split` is not quote-aware, so a newline inside the assignment's own quoted
    value split the segment and the prefix self-reference was lost entirely - the guard went
    silent on the exact footgun it exists to block. A two-line commit message is the common case."""
    cmd = 'MSG="Release 5.2\n\nfixes the gate" make push MSG="$MSG"'
    assert guard.self_referencing_prefix(cmd) is True


def test_a_plain_self_reference_is_still_blocked():
    """The direction where it must NOT apply."""
    assert guard.self_referencing_prefix('MSG="Release 5.2" make push MSG="$MSG"') is True
    assert guard.self_referencing_prefix('MSG="Release 5.2" make push') is False


def test_a_single_quoted_mention_is_not_a_substitution():
    """A single-quoted string is inert - no expansion happens there at all - so prose describing
    the footgun is not an instance of it, and blocking it stops the footgun being written down."""
    cmd = """echo 'never write: git commit -m "fix $(whoami)"' >> notes.md"""
    assert guard.substitutes_inside_text_arg(cmd) is False


def test_a_mention_after_a_comment_is_not_a_substitution():
    cmd = 'git commit -F /tmp/msg.txt   # never -m "x $(y)"'
    assert guard.substitutes_inside_text_arg(cmd) is False


def test_a_real_substitution_in_a_double_quoted_message_is_still_blocked():
    """The direction where it must NOT apply: `$( )` DOES expand inside double quotes, which is
    the whole footgun. Blanking those too would delete what this guard looks for."""
    assert guard.substitutes_inside_text_arg('git commit -m "fix $(whoami)"') is True


# ------------------------------------------- the hook's verdicts, driven through main()


def run_hook(command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    """Feed a PreToolUse Bash event to main() the way production does; return (exit, stderr)."""

    import io
    import json

    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    code = guard.main()
    return code, capsys.readouterr().err


# The shell expands a double-quoted string wherever it sits in a word, so an argument ATTACHED to
# its flag runs the substitution exactly like a spaced one. git accepts -m"..." and
# --message="...", gh and argparse accept --flag="...", and all of them see only the result.
@pytest.mark.parametrize(
    "command",
    [
        'git commit -m"fix $(whoami)"',
        'git commit -m="fix $(whoami)"',
        'git commit --message="fix $(whoami)"',
        'gh pr create --body="see `date`"',
        'gh pr create --title="x $(y)"',
        'memory_engine add --hook="run `shutdown -r now`"',
    ],
)
def test_an_attached_text_argument_is_expanded_like_a_spaced_one(
    command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run_hook(command, monkeypatch, capsys)
    assert code == 2, command
    assert "PROSE carries a command substitution" in err


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m"fix whoami"',
        'git commit --message="fix whoami"',
        'gh pr create --body="see date"',
        # -F and --body-file take a PATH, and substituting a path in is ordinary work.
        'git commit -F"$(ls /tmp/msg*)"',
        'gh pr create --body-file="$(mktemp)"',
        # A longer flag that merely starts with a text flag's name is a different flag.
        'tool add --notes="$(date)"',
    ],
)
def test_an_attached_argument_with_nothing_to_run_or_a_path_flag_passes(
    command: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run_hook(command, monkeypatch, capsys)
    assert code == 0, (command, err)


def test_the_spaced_text_argument_still_blocks(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run_hook('git commit -m "fix $(whoami)"', monkeypatch, capsys)
    assert code == 2
    assert "PROSE carries a command substitution" in err
    assert "git commit -F" in err


def test_the_bare_heredoc_verdict_names_its_own_cause_and_fix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run_hook("cat <<EOF\nsee `date`\nEOF", monkeypatch, capsys)
    assert code == 2
    assert "An UNQUOTED heredoc body carries a command substitution" in err
    assert "write <<'EOF', not <<EOF" in err
    # One message per verdict: the text-arg and prefix explanations would misdirect the fix.
    assert "PROSE carries" not in err
    assert "prefix assignment" not in err


def test_a_double_quoted_parameter_delimiter_is_a_quoted_heredoc(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """<<"$DELIM" quotes the delimiter, so bash expands nothing in the body.

    Any quoting of the delimiter word disables body expansion, even when the word itself looks
    like a parameter. Reading the `$` as making it bare would block a correctly quoted heredoc.
    """

    quoted = 'cat <<"$DELIM"\nsee `date`\n$DELIM'
    assert not heredoc_blocked(quoted)
    assert run_hook(quoted, monkeypatch, capsys) == (0, "")
    # The control: the same body under a BARE parameter delimiter is expanded.
    assert heredoc_blocked("cat <<$DELIM\nsee `date`\n$DELIM")


# ------------------------------------------- a subshell is a statement boundary

@pytest.mark.parametrize("command", [
    '(MSG="$(cat f)" make push MSG="$MSG")',
    'cd x && (MSG=1 make push MSG="$MSG")',
    'echo start; (FOO=1 tool --arg "$FOO")',
])
def test_a_prefix_self_reference_inside_a_subshell_is_blocked(command: str) -> None:
    """Statements were cut on a regex that knows no parens, so the first word read `(MSG=...`,
    which is no assignment, and the reference inside the subshell went unjudged."""
    assert blocked('MSG="$(cat f)" make push MSG="$MSG"')                      # control
    assert blocked(command)


def test_a_quoted_paren_label_does_not_split_a_statement() -> None:
    """The replay lesson from 7.23.3: a paren split on raw text cut `echo "(must PASS)"` labels."""
    assert blocked('echo "=== (must PASS) ===" ; MSG=1 make MSG="$MSG"')
    assert not blocked('MSG="(a; b)" make push')


# ------------------------------------------- gh's short text flags, scoped to gh

@pytest.mark.parametrize("command", [
    'gh pr create -t "Fix" -b "see $(whoami)"',
    'gh pr create -b"see `date`"',
    'gh issue create -t "x $(y)" -b body',
    'cd repo && gh pr edit 12 -b "now $(cat body.md)"',
    'gh pr comment 12 -b "ran `make test`"',
])
def test_gh_short_text_flags_carry_prose_too(command: str) -> None:
    """`-t`/`-b` are gh's spellings of --title/--body, and the shell runs a substitution in them
    exactly as it does in the long form, which was already blocked."""
    assert guard.substitutes_inside_text_arg('gh pr create --body "see $(whoami)"') is True  # control
    assert guard.substitutes_inside_text_arg(command) is True


@pytest.mark.parametrize("command", [
    'git checkout -b "feat-$(date +%s)"',
    'docker build -t "img:$(git rev-parse --short HEAD)" .',
    'tar -b "$(nproc)" -cf x.tar dir',
    "gh pr create -t 'single $(quoted)' -b body",
    'gh pr view 12 -t "$(x)"',
    'echo "gh pr create -b"; docker build -t "img:$(git rev-parse HEAD)" .',
])
def test_short_b_and_t_elsewhere_are_ordinary_work(command: str) -> None:
    """Outside gh's prose-carrying subcommands, -b and -t take branch names, image tags, sizes:
    substituting one in is ordinary, and a guard that fired there would be disabled."""
    assert guard.substitutes_inside_text_arg(command) is False


# ------------------------------------------- PowerShell reads its own escape character

def _exit_as(tool_name: str, command: str, monkeypatch: pytest.MonkeyPatch) -> int:
    import io
    import json

    payload = {"tool_name": tool_name, "tool_input": {"command": command}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return guard.main()


def test_powershell_backtick_escaped_dollar_is_literal_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    """Under PowerShell a backtick escapes `$`, so `` `$(rm x) `` is literal text and nothing runs.
    Read as Bash the backtick escaped nothing and the `$(` was blocked as a real substitution."""
    command = 'git commit -m "describe `$(rm x) safely"'
    assert guard.substitutes_inside_text_arg(command, tool_name="PowerShell") is False
    assert _exit_as("PowerShell", command, monkeypatch) == 0


def test_powershell_control_an_unescaped_subexpression_still_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`$(...)` inside double quotes is a PowerShell subexpression: it RUNS, so this must block."""
    command = 'git commit -m "describe $(rm x) safely"'
    assert guard.substitutes_inside_text_arg(command, tool_name="PowerShell") is True
    assert _exit_as("PowerShell", command, monkeypatch) == 2
