"""Parser gaps two independent reviews found in shell_text, each a BLOCKING guard's blind spot.

Every shape here was checked against real bash first: the statement after it really runs. A walk
that fails to separate it hands no guard the command, so each case is pinned at the shell_text
function AND end to end through a real guard process fed a PreToolUse event on stdin - the unit
test alone cannot show the guard consults the fixed function. Each bypass has a control for the
direction the fix must not change. ASCII only.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import ci_watch_nudge
import shell_text as S
import tooling_detour_nudge as TDN

HOOKS = Path(__file__).resolve().parent.parent
_B = "\\"
_REVPARSE = "git rev-parse --short A B"
_SED = "sed -i s/a/b/ config.json"


def _guard(name, command, tmp_path, tool_name="Bash"):
    """Exit code of hook `name` run as a real process on one PreToolUse event."""
    event = {"tool_name": tool_name, "tool_input": {"command": command},
             "cwd": str(tmp_path), "session_id": "parser-gap-test"}
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run([sys.executable, str(HOOKS / (name + ".py"))],
                            input=json.dumps(event), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp_path), env=env,
                            timeout=60, check=False)
    return result.returncode


def _segments(text, tool_name="Bash"):
    return [seg for _at, seg in S.iter_segments(text, tool_name)]


# ---- a comment inside backticks ends at the closing backtick ------------------------------------
# bash extracts a backtick substitution up to its closing backtick BEFORE parsing it, so `#x` in
# `echo \`ls #x\`` is a comment that ends there. Read to the newline, it swallowed the backtick and
# the whole rest of the line, `; git push` included.

def test_a_comment_inside_backticks_ends_at_the_backtick():
    assert S.is_gated_command("echo `ls #x`; git push") is True


def test_control_a_verb_inside_the_backtick_comment_is_still_a_comment():
    assert S.is_gated_command("echo `ls #x git push`; echo done") is False


def test_a_backtick_comment_leaves_a_later_expansion_visible():
    assert "$?" in S.blank_unexpanded_text("echo `ls #x`; echo $?")


def test_a_backtick_comment_still_ends_at_its_own_newline():
    """Real bash: `echo \\`echo a #x<newline>echo b\\`` prints `a b`, so the newline ends it first."""
    assert "echo b" in S.blank_unexpanded_text("echo `echo a #x\necho b`; echo $?")


def test_a_backtick_comment_no_longer_disarms_the_footgun_guard(tmp_path):
    assert _guard("git-footgun-guard", "echo `ls #x`; " + _REVPARSE, tmp_path) == 2


def test_control_the_sed_guard_masks_backticks_whole_and_was_never_disarmed(tmp_path):
    assert _guard("block-sed-structured-files", "echo `ls #x`; " + _SED, tmp_path) == 2


# ---- the argv fallback: a comment's apostrophe, and a continuation ------------------------------
# shlex refuses the unbalanced apostrophe of `# don't`, and the fallback then split the RAW text:
# the continuation stayed a token and a quoted option value fell apart, so the verb was never
# found. The comment is now removed by bash's own word rule before either reading.

@pytest.mark.parametrize("command", [
    "git -C /repo " + _B + "\n  push origin main  # don't force",
    'git -c user.name="A B" push # don' + "'t",
    "git " + _B + "\n  commit -m x # it's fine",
])
def test_a_comment_apostrophe_does_not_hide_the_verb(command):
    assert S.is_gated_command(command, "Bash") is True


def test_argv_for_match_drops_the_comment_by_word_rule():
    assert S.argv_for_match('git -c user.name="A B" push # don' + "'t") == [
        "git", "-c", "user.name=A B", "push"]


def test_control_a_mid_word_hash_is_not_a_comment_in_argv():
    assert S.argv_for_match("git commit -m a#b") == ["git", "commit", "-m", "a#b"]


def test_control_a_verb_named_only_in_a_comment_is_still_not_run():
    assert S.is_gated_command("echo x # then git push, don't") is False


def test_a_comment_apostrophe_no_longer_disarms_the_footgun_guard(tmp_path):
    command = "git " + _B + "\n  rev-parse --short A B # it's"
    assert _guard("git-footgun-guard", command, tmp_path) == 2


# ---- `$$` is the PID, not the start of an ANSI-C string ------------------------------------------

def test_a_pid_before_a_quote_is_not_ansi_c_quoting():
    assert S.is_gated_command("echo $$'x" + _B + "'; git push") is True


def test_the_masks_read_a_pid_before_a_quote_like_bash():
    command = "echo $$'x" + _B + "'; git push"
    assert "; git push" in S.mask_data_regions(command)
    assert "; git push" in S.blank_unexpanded_text(command)


def test_control_a_third_dollar_does_open_ansi_c():
    """`$$$'a\\'b'` is the PID followed by a real ANSI-C string whose `\\'` does not close it."""
    assert S.is_gated_command("echo $$$'a" + _B + "'b'; git push") is True
    assert S.is_gated_command("echo $$$'a" + _B + "'; git push'") is False


def test_a_pid_quote_no_longer_disarms_the_footgun_guard(tmp_path):
    assert _guard("git-footgun-guard", "echo $$'x" + _B + "'; " + _REVPARSE, tmp_path) == 2


# ---- `|&` is one pipe operator ------------------------------------------------------------------

def test_a_stderr_pipe_separates_its_elements():
    assert _segments("ls |& git push") == ["ls ", " git push"]
    assert S.is_gated_command("ls |& git push") is True


def test_the_shared_separator_regex_splits_a_stderr_pipe():
    assert [p.strip() for p in S.SEP.split("ls |& git push")] == ["ls", "git push"]
    assert S.LIST_SEP.split("ls |& git push") == ["ls |& git push"]


def test_control_a_redirection_ampersand_still_joins():
    assert _segments("make 2>&1 | tee log") == ["make 2>&1 ", " tee log"]


def test_a_stderr_pipe_no_longer_disarms_the_footgun_guard(tmp_path):
    assert _guard("git-footgun-guard", "echo x |& " + _REVPARSE, tmp_path) == 2


# ---- a subshell's closing paren is a statement end ----------------------------------------------

@pytest.mark.parametrize("command", ["(cd x && git push)", "(git push)",
                                     "if (git push); then :; fi"])
def test_a_subshell_paren_does_not_hide_the_verb(command):
    assert S.is_gated_command(command) is True


def test_control_a_spaced_subshell_paren_was_already_a_keyword_token():
    assert S.is_gated_command("( git push )") is True


@pytest.mark.parametrize("command", ['echo "(git push)"', "echo '(git push)'",
                                     "f() { echo x; }", "arr=(git push)"])
def test_control_a_paren_that_is_not_a_subshell_stays_data(command):
    assert S.is_gated_command(command) is False


def test_a_subshell_no_longer_disarms_the_footgun_guard(tmp_path):
    assert _guard("git-footgun-guard", "(" + _REVPARSE + ")", tmp_path) == 2
    assert _guard("git-footgun-guard", "(cd x && " + _REVPARSE + ")", tmp_path) == 2


# ---- an unnamed tool masks by the Bash reading --------------------------------------------------
# `tooling-detour-nudge` passed tool_name=None, and the mask read that as "escape nothing", so the
# escaped quote of `"a\" > b.md; c"` closed the string and `> b.md` read as a redirection.

def test_mask_data_regions_reads_no_tool_name_as_bash():
    text = 'echo "a' + _B + '" > b.md; c"'
    assert S.mask_data_regions(text, tool_name=None) == S.mask_data_regions(text, tool_name="Bash")


def test_the_detour_nudge_no_longer_reads_a_quoted_redirection():
    assert TDN._redirect_targets('echo "a' + _B + '" > b.md; c"', None) == []


def test_control_the_detour_nudge_still_reads_a_real_redirection():
    assert TDN._redirect_targets("echo a > b.md", None) == ["b.md"]


# ---- commands_only speaks the tool's language ---------------------------------------------------

def test_commands_only_keeps_a_separator_behind_a_windows_path():
    assert "; git push" in S.commands_only("cd C:" + _B + "; git push", tool_name="PowerShell")


def test_control_commands_only_still_escapes_under_bash():
    assert "; git push" not in S.commands_only("cd C:" + _B + "; git push")


def test_the_ci_watch_nudge_reads_a_powershell_cd_by_powershell_rules(tmp_path):
    here = ci_watch_nudge._cwd_after_any_cd("cd sub" + _B + "; git push", str(tmp_path),
                                            tool_name="PowerShell")
    assert here is not None and ";" not in here


# ---- a heredoc delimiter is a whole shell word ----------------------------------------------------

@pytest.mark.parametrize("opener,delimiter", [
    ("cat <<" + _B + "EOF", "EOF"),
    ("cat <<'END-OF'", "END-OF"),
    ("cat <<END.X", "END.X"),
    ('cat <<E"O"F', "EOF"),
    ("cat <<1", "1"),
])
def test_a_heredoc_delimiter_is_read_as_a_full_word(opener, delimiter):
    assert S.heredoc_delimiter(S.find_heredoc_opener(opener)) == delimiter


@pytest.mark.parametrize("opener,quoted", [
    ("cat <<EOF", False), ("cat <<END.X", False), ("cat <<" + _B + "EOF", True),
    ("cat <<'END-OF'", True), ('cat <<E"O"F', True),
])
def test_a_quoted_delimiter_is_recognised_anywhere_in_the_word(opener, quoted):
    assert S.heredoc_is_quoted(S.find_heredoc_opener(opener)) is quoted


@pytest.mark.parametrize("opener,delimiter", [
    ("cat <<" + _B + "EOF", "EOF"), ("cat <<'END-OF'", "END-OF"), ("cat <<END.X", "END.X"),
])
def test_a_word_delimiter_body_no_longer_hides_the_next_command(opener, delimiter):
    command = f"{opener} > /dev/null\nit's here\n{delimiter}\ngit push"
    assert S.strip_heredoc_bodies(command) == f"{opener} > /dev/null\ngit push"
    assert S.is_gated_command(command) is True


def test_a_heredoc_inside_a_quoted_substitution_is_found():
    command = 'x="$(cat <<' + "'EOF'" + '\nsay "hi\nEOF\n)"\ngit push'
    assert "say" not in S.strip_heredoc_bodies(command)
    assert S.is_gated_command(command) is True


def test_a_heredoc_inside_a_bare_substitution_is_found():
    command = "x=$(cat <<EOF\nit's (1\nEOF\n); git push"
    assert "it's" not in S.strip_heredoc_bodies(command)
    assert S.is_gated_command(command) is True


def test_control_a_quoted_mention_of_a_heredoc_still_opens_nothing():
    command = 'echo "cat <<EOF"\ngit push\nEOF'
    assert S.strip_heredoc_bodies(command) == command


def test_two_heredocs_on_one_line_both_open_bodies():
    command = "cat <<A <<B\nx\nA\ny\nB\ngit push"
    assert S.strip_heredoc_bodies(command) == "cat <<A <<B\ngit push"


@pytest.mark.parametrize("command", [
    "cat <<" + _B + "EOF\nit's here\nEOF\n" + _SED,
    "cat <<'END-OF'\nit's here\nEND-OF\n" + _SED,
    "cat <<END.X\nhere\nEND.X\n" + _SED,
    'x="$(cat <<' + "'EOF'" + '\nsay "hi\nEOF\n)"\n' + _SED,
])
def test_a_heredoc_shape_no_longer_disarms_the_sed_guard(command, tmp_path):
    assert _guard("block-sed-structured-files", command, tmp_path) == 2


def test_a_sed_inside_a_word_delimited_body_is_data_not_a_block(tmp_path):
    """The other direction of the same defect: an unrecognised opener left its body judged as
    commands, so a runbook line naming the footgun blocked the write of the runbook."""
    command = "cat <<'END-OF' > notes.txt\n" + _SED + "\nEND-OF"
    assert _guard("block-sed-structured-files", command, tmp_path) == 0


# ---- linear time on an adversarial command --------------------------------------------------------

@pytest.mark.parametrize("unit", [
    "cat <<E\nx\nE\n", "$( (a; `b #c` |& d) )", "echo $$'x' \"$(ls)\" # it's\n",
])
def test_the_walks_stay_linear_on_a_long_command(unit):
    command = unit * (300_000 // len(unit))
    started = time.perf_counter()
    S.is_gated_command(command)
    S.strip_heredoc_bodies(command)
    S.commands_only(command)
    assert time.perf_counter() - started < 20
