"""Tests for sed-line1-range-nudge.py - catch `sed '1,/re/d'`, which eats one block too many.

sed's `1,/re/` range starts hunting for the END pattern at line 2. So on a file whose line 1 is the
opening delimiter, the range already closes on the CLOSING delimiter, and a second chained sed then
runs to EOF. Measured 2026-08-02: two curated memory bodies truncated 33->15 and 28->13 lines, still
parsing and still rendering, so the loss was invisible until the sizes were compared.
"""
import json

import pytest

import sed_line1_range_nudge as N


def _n(cmd):
    return N.notice(cmd)


# --- fires on the trap ---------------------------------------------------------------------------

def test_the_frontmatter_strip_shape_is_flagged():
    assert _n("sed '1,/^---$/d' fact.md")


def test_the_chained_form_that_caused_the_loss_is_flagged():
    cmd = "cat f.md | sed '1,/^---$/d' | sed '1,/^---$/d' > body.md"
    ctx = _n(cmd)
    assert ctx and "1," in ctx


def test_double_quoted_and_unquoted_forms_are_flagged():
    assert _n('sed "1,/^---$/d" f.md')
    assert _n("sed 1,/^---$/d f.md")


def test_a_different_end_pattern_still_trips_it():
    """The bug is the range shape, not the delimiter - any 1,/re/ has the off-by-one."""
    assert _n("sed '1,/^BEGIN$/d' notes.txt")


def test_gsed_counts_too():
    assert _n("gsed '1,/^---$/d' f.md")


def test_the_message_names_the_python_replacement():
    ctx = _n("sed '1,/^---$/d' f.md")
    assert "split" in ctx


# --- stays quiet otherwise -----------------------------------------------------------------------

def test_a_line_numbered_range_is_quiet():
    """`1,5d` is exact and has no regex end, so it cannot overshoot."""
    assert _n("sed '1,5d' f.md") is None


def test_a_range_not_anchored_at_line_1_is_quiet():
    assert _n("sed '2,/^---$/d' f.md") is None


def test_an_ordinary_substitution_is_quiet():
    assert _n("sed -i 's/foo/bar/' f.md") is None


def test_a_print_range_is_quiet():
    """Only the DELETE form silently loses content; `1,/re/p` shows you what it did."""
    assert _n("sed -n '1,/^---$/p' f.md") is None


def test_the_pattern_inside_a_heredoc_body_is_quiet():
    """A body is DATA - documenting the footgun must not trip the guard for it."""
    cmd = ("cat > /tmp/doc.md <<'EOF'\n"
           "Never use sed '1,/^---$/d' to strip a frame; it eats the body.\n"
           "EOF\necho ok")
    assert _n(cmd) is None


def test_empty_and_garbage_never_raise():
    for cmd in ("", "   ", None, "sed", "sed '1,/'"):
        N.notice(cmd)


# --- hook contract -------------------------------------------------------------------------------

def test_main_emits_additional_context_and_exits_zero(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "sed '1,/^---$/d' f.md"}}
    assert N.main(json.dumps(event)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_main_is_silent_for_a_clean_command(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "sed -n '1,5p' f.md"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_never_wedges_on_malformed_input():
    for raw in ("", "not json", "{}", '{"tool_name": "Bash"}'):
        assert N.main(raw) == 0


def test_a_real_sed_range_is_still_noticed():
    """The direction where it must NOT apply."""
    assert N.notice("sed -i '1,/^---$/d' file.md") is not None


# ---- a mention is not an instance ---------------------------------------------------------------
#
# A real sed range is itself single-quoted, so quote-masking would delete exactly what this nudge
# looks for. What separates `sed -i '1,/re/d'` from `echo '... 1,/re/d ...'` is the ENCLOSING
# program, which shell_text.strip_data_sink_statements decides.

def test_an_echo_of_the_footgun_is_quiet():
    assert N.notice("echo 'never use sed 1,/^---$/d on a frame'") is None


def test_a_commit_message_describing_the_footgun_is_quiet():
    assert N.notice("git commit -m 'guard against sed 1,/^---$/d'") is None


def test_a_real_range_after_an_echo_of_one_still_fires():
    """The sink blanking must not swallow the statement after it."""
    assert N.notice("echo 'sed 1,/re/d is a trap' && sed -i '1,/^---$/d' f.md") is not None


def test_the_tool_name_reaches_the_sink_strip():
    r"""A PowerShell command must be split by PowerShell's rules, not Bash's.

    Both directions are asserted, because only the pair is discriminating. Under the PowerShell
    reading `C:\bin\echo.exe` has basename `echo`, so the statement is inert and the nudge is
    silent. Under the Bash reading shlex eats the separators, the program reads as one long
    filename, nothing is blanked, and the nudge fires. A one-sided version of this test passed
    with the tool name thrown away.
    """
    cmd = 'C:\\bin\\echo.exe "the sed 1,/^---$/d trap"'
    assert N.notice(cmd, "PowerShell") is None
    assert N.notice(cmd, "Bash") is not None


# ---- a quote is a command position too ----------------------------------------------------------
#
# `sed` after ssh's opening quote is the same trap run on another host, and it read as invisible
# for as long as `_TRAP` accepted only whitespace or a separator in front. Closing it widened that
# class by two characters; these pin both directions of the widening, because only the pair is
# discriminating - the quiet cases below stay quiet through the data-sink strip, NOT through
# `_TRAP`, so a regression in either one alone would still leave half of them passing.

def test_a_sed_range_inside_an_ssh_argument_is_noticed():
    assert N.notice("ssh host 'sed -i 1,/^---$/d /etc/x'") is not None


def test_a_sed_range_inside_a_double_quoted_remote_argument_is_noticed():
    assert N.notice('ssh host "sed -i 1,/^---$/d /etc/x"') is not None


def test_a_sed_range_inside_bash_c_is_noticed():
    """Any wrapper that puts a quote in front of the command has the same shape as ssh."""
    assert N.notice("bash -c 'sed -i 1,/^---$/d /etc/x'") is not None


def test_an_echo_whose_argument_opens_with_sed_stays_quiet():
    """The direction the widening must NOT reach.

    This is the exact shape the new quote-prefix accepts, sitting in a data sink: the quote is
    immediately before `sed`, so `_TRAP` matches the text and only strip_data_sink_statements
    keeps it quiet. Before the widening this test could not discriminate, because `_TRAP` refused
    the string on its own.
    """
    assert N.notice("echo 'sed 1,/^---$/d eats the body'") is None


def test_a_commit_message_that_opens_with_sed_stays_quiet():
    assert N.notice("git commit -m 'sed 1,/^---$/d is the trap this guards'") is None


def test_a_word_ending_in_sed_is_still_not_a_command():
    """The anchor is a BOUNDARY, not an anything-goes prefix - it must not match mid-word."""
    assert N.notice("mysed 1,/^---$/d f.md") is None
    assert N.notice("use-parsed 1,/^---$/d f.md") is None


def test_a_flag_ending_in_sed_is_not_a_command():
    """A hyphen is part of a word here, so `--use-sed` must not read as an invocation."""
    assert N.notice("tool --use-sed 1,/^---$/d f.md") is None


def test_sed_invoked_by_path_is_noticed():
    """A path separator is a command boundary exactly as a quote and a space are.

    This is the same defect the quote case was, one character over: an ENUMERATED boundary class
    is wrong every time it omits a character, and it omits them silently. Scripts, sudo rules and
    systemd units all invoke sed by absolute path, which is where this trap does its quiet damage.
    """
    assert N.notice("/usr/bin/sed -i '1,/^---$/d' f.md") is not None
    assert N.notice("./sed -i '1,/^---$/d' f.md") is not None


def test_sed_invoked_by_path_inside_a_remote_argument_is_noticed():
    """Both boundaries at once - ssh's quote, then a path - which is the realistic remote form."""
    assert N.notice("ssh host '/usr/bin/sed -i 1,/^---$/d /etc/x'") is not None
