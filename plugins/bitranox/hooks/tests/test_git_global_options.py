"""`git <global options> <verb>` must be seen wherever a hook asks what a git command is doing.

Git accepts global options between `git` and its subcommand, and two of them take a SEPARATE
following token (`-c key=value`, `-C path`, `--work-tree p`, ...). Four places in this plugin ask
"is this segment `git <verb>`?" and they answered it three different ways:

  shell_text.COMMIT_RE / PUSH_RE   a regex listing `-C` plus any single `-flag`
  git-footgun-guard                a token walk with GIT_VALUE_OPTS - the only correct one
  git-revparse-nudge               `\\bgit\\s+rev-parse\\b`, no options at all
  gated-prep-nudge                 `git\\s+(?:commit|push|tag)`, no options at all

The 2026-08-28 hook audit VERIFIED the last two: each is silent on the exact shape it exists to
teach. Probing the first for the same class of gap found something the audit never looked at,
because it reviewed the hooks and not the shared module - `is_gated_command` is what `repo-gate.py`
consults to decide whether to BLOCK, and it returned False for `git -c user.name=bob commit`. A
commit carrying a two-token global option was not gated at all.

The table is the point. Fixing one caller leaves the shape that produced the other three, and this
is the third time in this work that a per-caller fix would have read as complete.

All content is ASCII.
"""

import pytest

import gated_prep_nudge
import git_footgun_guard
import git_revparse_nudge
import shell_text


# Every spelling of "pin the repository / set a config" that git accepts before the subcommand.
# `-c key=value` and `-C path` are the two-token forms a regex most easily gets wrong.
GLOBAL_OPTS = [
    "",                              # control: no options at all, must keep working
    "-C /repo ",
    "-c user.name=bob ",
    "--git-dir=/repo/.git ",
    "--work-tree /repo ",
    "--work-tree /repo -C /repo ",
    "-c core.hooksPath=gh -C /repo ",
]


@pytest.mark.parametrize("opts", GLOBAL_OPTS, ids=[o.strip() or "<none>" for o in GLOBAL_OPTS])
def test_the_commit_gate_sees_a_commit_whatever_global_options_precede_it(opts):
    """repo-gate blocks on this predicate. A commit it cannot see is a commit it cannot gate."""
    assert shell_text.is_gated_command("git %scommit -m x" % opts) is True


@pytest.mark.parametrize("opts", GLOBAL_OPTS, ids=[o.strip() or "<none>" for o in GLOBAL_OPTS])
def test_the_commit_gate_sees_a_push_whatever_global_options_precede_it(opts):
    assert shell_text.is_gated_command("git %spush origin master" % opts) is True


@pytest.mark.parametrize("opts", GLOBAL_OPTS, ids=[o.strip() or "<none>" for o in GLOBAL_OPTS])
def test_the_revparse_nudge_fires_whatever_global_options_precede_it(opts):
    """A model that pinned the repo but forgot `--verify` is exactly who this nudge is for, and
    `git -C <path>` is the other canonical way to pin it."""
    assert git_revparse_nudge.notice("git %srev-parse master" % opts), (
        "silent on `git %srev-parse master`" % opts)


@pytest.mark.parametrize("opts", GLOBAL_OPTS, ids=[o.strip() or "<none>" for o in GLOBAL_OPTS])
def test_the_gated_prep_nudge_fires_whatever_global_options_precede_it(opts):
    cmd = 'printf "msg" > /tmp/m.txt && git %scommit -F /tmp/m.txt' % opts
    assert gated_prep_nudge.notice(cmd), "silent on `%s`" % cmd


@pytest.mark.parametrize("opts", GLOBAL_OPTS, ids=[o.strip() or "<none>" for o in GLOBAL_OPTS])
def test_the_footgun_guard_still_sees_a_broken_revparse(opts):
    """The KNOWN NEGATIVE of this table: the footgun guard already walks GIT_VALUE_OPTS, so it
    passes before the change too. A table whose every row fails cannot show that the rows differ,
    and this is the row that proves the shared helper did not lose anything."""
    # `--short` plus two revisions is the shape that exits 128; without `--short` the guard is
    # correctly silent, so the control has to use the real footgun, not a bare rev-parse.
    assert git_footgun_guard.broken_revparse("git %srev-parse --short HEAD HEAD~1" % opts) is True


def test_a_git_verb_inside_an_argument_is_still_not_a_command():
    """The direction where it must NOT apply. Widening what counts as `git <verb>` must not start
    matching the words as DATA - over-matching is not harmless here, because the repo gate BLOCKS
    on this predicate and a changelog line about committing would then block its own commit."""
    assert shell_text.is_gated_command('echo "git -C /repo commit -m x"') is False
    assert shell_text.is_gated_command('grep -r "git -c a=b push" .') is False
    assert not git_revparse_nudge.notice('echo "git -C /repo rev-parse master"')


def test_an_option_value_is_not_mistaken_for_the_verb():
    """`-c` takes the NEXT token, so a value that happens to read like a verb must not count."""
    assert shell_text.is_gated_command("git -c alias.x=commit status") is False
    assert shell_text.is_gated_command("git -C commit status") is False


NESTED = [
    'A=$(git %scommit -m x)',
    'echo "$(git %scommit -m x)"',
    'A=`git %scommit -m x`',
]


@pytest.mark.parametrize("wrap", NESTED, ids=["$( )", 'echo "$( )"', "backticks"])
def test_a_git_verb_inside_a_command_substitution_still_counts(wrap):
    """A command substitution runs a real command. The token walk anchors at a segment START, so
    `$(` and a backtick have to BE segment starts - otherwise anchoring silently narrows what the
    old anywhere-matching regex saw. Caught as a regression by the existing revparse-nudge suite:
    `A=$(git rev-parse mybranch)` stopped being nudged."""
    assert shell_text.is_gated_command(wrap % "") is True
    assert shell_text.is_gated_command(wrap % "-C /repo ") is True


def test_a_rev_parse_inside_a_command_substitution_is_still_nudged():
    assert git_revparse_nudge.notice('A=$(git rev-parse mybranch); echo "$A"')
    assert git_revparse_nudge.notice('A=$(git -C /repo rev-parse mybranch)')


def test_the_gate_predicate_does_not_backtrack_on_a_long_option_list():
    """`is_gated_command` runs inside repo-gate, a PreToolUse hook. The regex it used had a nested
    quantifier - `(?:\\s+-C\\s+\\S+|\\s+--?\\S+)*` - which backtracks exponentially when the segment
    does NOT end in the verb. Measured on the pre-change pattern: 0.4 ms at 10 options, 113 ms at
    18, 1815 ms at 22, and no result at all at 40 within two minutes. A hook that hangs is worse
    than a hook that is wrong, because the session stops.

    A wall-clock assertion is normally a flaky test. It is sound here only because the separation
    is exponential rather than marginal: the token walk is ~0.04 ms where the old pattern did not
    terminate, so any bound in between cannot be reached by ordinary machine noise.
    """
    import time

    seg = "git " + " ".join("--opt%d" % i for i in range(60)) + " status"
    start = time.perf_counter()
    assert shell_text.is_gated_command(seg) is False
    assert time.perf_counter() - start < 1.0, "the gate predicate is backtracking again"


# --- Quoting: a separator only separates where the shell would act on it. -----------------
# `is_gated_command` is what repo-gate BLOCKS on, so a false positive here refuses a command
# that runs nothing. Every case below is paired with the direction where it must NOT apply.

def test_a_single_quoted_substitution_is_inert():
    """'$( )' inside SINGLE quotes is literal text - the shell never runs it."""
    assert shell_text.is_gated_command("echo '$(git commit -m x)'") is False
    assert shell_text.is_gated_command("echo '`git commit -m x`'") is False


def test_a_double_quoted_substitution_still_runs():
    """The direction where it must NOT apply: double quotes do NOT stop a substitution."""
    assert shell_text.is_gated_command('echo "$(git commit -m x)"') is True


def test_a_quoted_statement_separator_does_not_separate():
    """`;` is literal inside quotes of either kind, so what follows is not a new statement."""
    assert shell_text.is_gated_command("echo 'a; git commit -m x'") is False
    assert shell_text.is_gated_command('echo "a; git commit -m x"') is False
    assert shell_text.is_gated_command("echo 'a && git push'") is False


def test_quoting_state_is_restored_after_a_substitution_closes():
    """The silent-miss direction. If `)` does not restore the quoting in force before `$(`, the
    closing `"` reads as an OPENING one and every separator after it looks quoted - so a real
    `git commit` later on the line stops being seen at all."""
    assert shell_text.is_gated_command('echo "$(date)" ; git commit -m x') is True
    assert shell_text.is_gated_command('echo "$(date)" && git push origin master') is True


def test_an_apostrophe_inside_double_quotes_opens_nothing():
    """A single quote is literal inside double quotes; reading it as an opener would swallow the
    rest of the line and hide the real command after it."""
    assert shell_text.is_gated_command('git log -m "it\'s fine" && git commit -m x') is True


def test_an_escaped_separator_is_not_a_separator():
    assert shell_text.is_gated_command(r"echo a\; git commit -m x", tool_name="Bash") is False


def test_a_substitution_in_an_env_prefix_does_not_hide_the_command():
    """`FOO=$(date) git commit -m x` sets FOO for a real commit. The `)` has to CLOSE the
    substitution's segment, or the rest of the statement stays glued to it as `date) git commit`
    and anchoring at the segment start no longer finds the verb - a commit the gate cannot see.
    The env-assignment prefix is already in scope everywhere else here (COMMIT_RE and
    git_verb_operands both skip one), so this was a gap in a capability, not a missing feature."""
    assert shell_text.is_gated_command("foo=$(ls) git commit -m x") is True
    assert shell_text.is_gated_command("A=`date` git push origin master") is True


def test_a_closing_paren_does_not_start_a_statement_on_its_own():
    """The direction where it must NOT apply: a subshell's `)` closes no substitution, so it must
    not manufacture a segment - and what follows a real one is still judged as data when quoted."""
    assert shell_text.is_gated_command("(cd /x && ls)") is False
    assert shell_text.is_gated_command("echo '$(ls) git commit -m x'") is False


# --- The escape character is the TOOL's, not the host's. ---------------------------------
# `is_gated_command` runs on PowerShell commands too, where `\` is a PATH SEPARATOR and the
# escape is a BACKTICK. Reading `\` as an escape there eats the separator behind a Windows
# path, so the gate stops seeing a real commit - the silent-miss direction, in a blocking gate.

def test_a_windows_path_separator_is_not_an_escape():
    assert shell_text.is_gated_command(r"cd C:\; git commit -m x", tool_name="PowerShell") is True
    assert shell_text.is_gated_command(
        r"Set-Location C:\src\; git push origin master", tool_name="PowerShell"
    ) is True


def test_a_posix_escape_is_still_an_escape_under_bash():
    """The direction where it must NOT apply: threading the tool must not cost the Bash case."""
    assert shell_text.is_gated_command(r"echo a\; git commit -m x", tool_name="Bash") is False


def test_a_backtick_escapes_under_powershell_and_substitutes_under_bash():
    """The backtick is the mirror image: PowerShell's escape character, and Bash's command
    substitution. Reading it as a substitution under PowerShell invents a statement; reading it
    as an escape under Bash loses one."""
    assert shell_text.is_gated_command("A=`git commit -m x`", tool_name="Bash") is True
    assert shell_text.is_gated_command(r"echo a`; git commit -m x", tool_name="PowerShell") is False
    assert shell_text.is_gated_command(r"cd C:\a; git commit -m x", tool_name="PowerShell") is True


def test_an_unknown_tool_takes_the_stricter_reading():
    """The two readings are NOT symmetric: the Bash one ENABLES backslash escaping, which is what
    can swallow a separator and hide a command. So an unrecognised tool must escape NOTHING -
    erring toward more separators and a false block, which is visible and recoverable, rather than
    a silent miss, which is neither. `split_for_tool` states the same rule one function down."""
    assert shell_text.is_gated_command(r"cd C:\; git commit -m x", tool_name="Zsh") is True
    assert shell_text.is_gated_command(r"echo a\; git commit -m x", tool_name="Zsh") is True
    assert shell_text.is_gated_command(r"echo a`; git commit -m x", tool_name="Zsh") is True


def test_the_two_known_tools_are_unaffected_by_the_unknown_rule():
    """The direction where it must NOT apply: widening the fallback must not loosen either
    tool that IS recognised."""
    assert shell_text.is_gated_command(r"echo a\; git commit -m x", tool_name="Bash") is False
    assert shell_text.is_gated_command(r"echo a`; git commit -m x", tool_name="PowerShell") is False
    assert shell_text.is_gated_command("A=`git commit -m x`", tool_name="Bash") is True


def test_an_unspecified_tool_is_an_unknown_tool():
    """There is ONE rule for every way of not naming a tool. A bare call states no tool, so it gets
    the same stricter reading an unrecognised one does - otherwise omitting the argument silently
    picks the reading that can hide a command, which is the shape this whole fix exists to close.
    A caller that means Bash says so."""
    assert shell_text.is_gated_command(r"echo a\; git commit -m x") is True
    assert shell_text.is_gated_command(r"echo a\; git commit -m x", tool_name="Bash") is False
