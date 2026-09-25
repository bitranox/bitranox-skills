"""Shapes that made the shared shell parser miss a statement. ASCII only.

A statement the walk fails to separate is a statement no guard judges, so every case here was a
BLOCKING guard silently allowing a command it exists to stop. Each shape is pinned twice: at the
shell_text function, and end to end through at least one real guard fed a PreToolUse event on
stdin. The unit test alone cannot show that the guard actually consults the fixed function - a
guard with its own private copy of the rule stays broken while the helper's tests go green.

Every bypass test is paired with a control for the direction the fix must NOT change: the nearest
input that keeps today's verdict.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import block_git_semicolon_chain
import block_masked_gate_exit
import ci_watch_nudge
import gated_prep_nudge
import git_commit_branch_guard
import git_path_not_here_nudge
import git_wrong_repo_nudge
import reformat_md_tables
import retry_with_a_flag_nudge
import shell_text as S
import venv_guard

HOOKS = Path(__file__).resolve().parent.parent
_B = "\\"


def _guard(name, command, tmp_path, tool_name="Bash", **extra):
    """Exit code of hook `name` run as a real process on one PreToolUse event.

    HOME points at the test's own directory so a hook that keeps state cannot touch the real one.
    """
    event = {"tool_name": tool_name, "tool_input": {"command": command},
             "cwd": str(tmp_path), "session_id": "bypass-test", **extra}
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run([sys.executable, str(HOOKS / (name + ".py"))],
                            input=json.dumps(event), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp_path), env=env,
                            timeout=60)
    return result.returncode


def _segments(text, tool_name="Bash"):
    return [seg for _at, seg in S.iter_segments(text, tool_name)]


# ---- a here-string is not a heredoc -------------------------------------------------------------
# `<<< word` feeds one word on stdin and opens nothing. Read as `<< word` from its second `<`, the
# strip dropped EVERY later line as a body, and about twenty hooks strip bodies first.

@pytest.mark.parametrize("text", ["tr a b <<< hello", "tr a b <<<hello", "tr a b <<< 'hello'",
                                  'tr a b <<<"hello"'])
def test_a_here_string_is_not_a_heredoc_opener(text):
    assert S.HEREDOC_OPEN.search(text) is None


@pytest.mark.parametrize("text", ["cat <<EOF", "cat << EOF", "cat <<-EOF", "cat <<'EOF'"])
def test_a_real_heredoc_opener_still_matches(text):
    assert S.heredoc_delimiter(S.HEREDOC_OPEN.search(text)) == "EOF"


@pytest.mark.parametrize("herestring", ["<<< hello", "<<<hello"])
def test_a_here_string_keeps_every_later_line(herestring):
    command = "tr a-z A-Z %s\ngit push origin main" % herestring
    assert S.strip_heredoc_bodies(command) == command
    assert S.is_gated_command(command) is True


def test_a_real_heredoc_after_a_here_string_is_still_stripped():
    command = "tr a b <<< x\ncat <<EOF\ngit push origin main\nEOF\necho done"
    assert "git push" not in S.strip_heredoc_bodies(command)
    assert S.is_gated_command(command) is False


@pytest.mark.parametrize("hook,command", [
    ("block-sed-structured-files", "tr a b <<< x\nsed -i s/a/b/ config.json"),
    ("git-footgun-guard", "tr a b <<< x\ngit rev-parse --short A B"),
    ("shell-prefix-selfref-guard", 'tr a b <<< x\nMSG=hi make push MSG="$MSG"'),
])
def test_a_here_string_no_longer_hides_the_next_line_from_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


@pytest.mark.parametrize("hook,command", [
    ("block-sed-structured-files", "cat <<EOF\nsed -i s/a/b/ config.json\nEOF"),
    ("git-footgun-guard", "cat <<EOF\ngit rev-parse --short A B\nEOF"),
])
def test_a_heredoc_body_is_still_data_to_the_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 0


def test_a_here_string_word_is_not_a_delimiter_for_the_unquoted_body_check(tmp_path):
    """The mirror image: a here-string used to open a phantom BARE heredoc, so a later line
    carrying `$( )` read as an expanding body and was blocked for nothing."""
    assert _guard("shell-prefix-selfref-guard", 'tr a b <<< hello\necho "$(date)"\nhello',
                  tmp_path) == 0


# ---- an apostrophe inside a comment ------------------------------------------------------------
# `# don't` opened a single-quoted span that swallowed the newline and every command after it.

def test_an_apostrophe_in_a_comment_does_not_hide_the_next_line():
    assert S.is_gated_command("ls # don't care\ngit push origin main") is True


def test_a_comment_without_an_apostrophe_keeps_its_verdict():
    assert S.is_gated_command("ls # do not care\ngit push origin main") is True


def test_a_separator_inside_a_comment_separates_nothing():
    assert _segments("ls # a; git push") == ["ls # a; git push"]
    assert S.is_gated_command("ls # a; git push") is False


@pytest.mark.parametrize("command,expected", [
    ("echo a#b; git push", True),              # mid-word: not a comment
    ("echo ${#arr}; git push", True),          # parameter length, not a comment
    ("echo a#'; git push'", False),            # mid-word, so the quote really opens
    ("ls;# note\ngit push", True),             # a word after `;` can start a comment
    ("echo a" + _B + " #b; git push", True),   # an ESCAPED space does not end the word
])
def test_only_a_hash_at_a_word_start_opens_a_comment(command, expected):
    assert S.is_gated_command(command, "Bash") is expected


@pytest.mark.parametrize("hook,command", [
    ("block-pgrep-self-match", "echo hi # don't\npkill -f myserver # won't"),
    ("git-footgun-guard", "ls # don't\ngit rev-parse --short A B"),
])
def test_an_apostrophe_in_a_comment_no_longer_disarms_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


# ---- a lone ampersand ends a statement ---------------------------------------------------------

def test_a_lone_ampersand_separates_statements():
    assert _segments("sleep 1 & git commit -m x") == ["sleep 1 ", " git commit -m x"]
    assert S.is_gated_command("sleep 1 & git commit -m x") is True


@pytest.mark.parametrize("text,count", [
    ("a 2>&1 b", 1),            # redirect a descriptor
    ("a &>f b", 1),             # redirect both streams
    ("a &>>f b", 1),
    ("a <&3 b", 1),             # duplicate an input descriptor
    ("a >& f", 1),
    ("a |& b", 2),              # pipe stderr too: ONE separator, not a pipe plus a background
    ("a && b", 2),
    ("a & b & c", 3),
])
def test_only_a_lone_ampersand_is_a_separator(text, count):
    assert len(_segments(text)) == count


@pytest.mark.parametrize("text,count", [
    ("a 2>&1 b", 1), ("a &>f b", 1), ("a <&3 b", 1), ("a |& b", 2), ("a && b", 2),
    ("a & b", 2), ("a \\& b", 1),
])
def test_the_shared_separator_regex_agrees_with_the_walk(text, count):
    assert len(S.SEP.split(text)) == count


def test_the_list_separator_keeps_a_pipeline_whole():
    assert S.LIST_SEP.split("a | b & c") == ["a | b ", " c"]
    assert S.LIST_SEP.split("a 2>&1 | b") == ["a 2>&1 | b"]


@pytest.mark.parametrize("hook,command", [
    ("block-pgrep-self-match", "echo stopping & pkill -f myserver"),
    ("git-footgun-guard", "sleep 1 & git rev-parse --short A B"),
    ("block-sed-structured-files", "echo hi & sed -i s/a/b/ config.json"),
    ("shell-prefix-selfref-guard", 'echo hi & MSG=x make push MSG="$MSG"'),
])
def test_a_lone_ampersand_no_longer_hides_a_command_from_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


@pytest.mark.parametrize("hook,command,code", [
    ("git-footgun-guard", "git rev-parse --short HEAD 2>&1", 0),
    ("block-sed-structured-files", "sed -i s/a/b/ config.json 2>&1", 2),
    ("block-sed-structured-files", "sed -i s/a/b/ config.json &>/dev/null", 2),
])
def test_a_redirection_ampersand_keeps_the_guard_verdict(hook, command, code, tmp_path):
    assert _guard(hook, command, tmp_path) == code


def test_a_backgrounded_pipe_before_a_success_claim_is_blocked(tmp_path):
    """block-masked-gate-exit asks whether the statement AFTER a masked pipeline claims success.
    Glued together by an unseen `&`, the claim sat inside the pipeline's own statement."""
    assert _guard("block-masked-gate-exit", "pytest | tail -5 & echo PASS", tmp_path) == 2
    assert _guard("block-masked-gate-exit", "pytest | tail -5; echo PASS", tmp_path) == 2


def test_every_sibling_splitter_sees_the_lone_ampersand():
    """The guards that split masked or raw text with a regex take it from shell_text, so one
    separator set serves them all. Each assertion fails if that sibling keeps a private copy."""
    assert venv_guard.looks_like_a_gate_run("sleep 1 & pytest") is True
    assert venv_guard.looks_like_a_gate_run("echo pytest 2>&1") is False
    _masked, spans = git_path_not_here_nudge._statements("a & git ls-files x")
    assert len(spans) == 2
    _masked, spans = git_wrong_repo_nudge._statements("cd /a & git status")
    assert len(spans) == 2
    text = "git push --dry-run x & git push x"
    assert ci_watch_nudge._statement_around(text, text.rindex("push")).strip() == "git push x"
    assert retry_with_a_flag_nudge.shape("sleep 1 & sed -i x f")[0] == "sed"
    parts = block_git_semicolon_chain.SEP_SPLIT.split("a |& b")
    assert parts == ["a ", "|&", " b"]              # one pipe operator, no `&` glued to `b`


# ---- `if`, `while` and `until` open a statement ------------------------------------------------

@pytest.mark.parametrize("command", [
    "if git push; then echo ok; fi",
    "while ! git push; do sleep 5; done",
    "until git push; do sleep 5; done",
])
def test_a_loop_or_branch_keyword_does_not_hide_the_verb(command):
    assert S.is_gated_command(command) is True


@pytest.mark.parametrize("command", ["echo if git push", "git log --grep until"])
def test_a_keyword_as_an_operand_is_still_data(command):
    assert S.is_gated_command(command) is False


def test_a_keyword_no_longer_disarms_the_footgun_guard(tmp_path):
    assert _guard("git-footgun-guard", "if git rev-parse --short A B; then :; fi", tmp_path) == 2


# ---- tool_name reaches the verb walk -----------------------------------------------------------

_PS_COMMIT = "C:" + _B + "Git" + _B + "cmd" + _B + "git.exe commit -m x"


def test_is_gated_command_reads_a_powershell_path_by_powershell_rules():
    assert S.is_gated_command(_PS_COMMIT, "PowerShell") is True
    assert S.is_gated_command("git status", "PowerShell") is False


def test_the_sibling_git_verb_callers_pass_tool_name_through():
    assert gated_prep_nudge._gated_start(_PS_COMMIT, "PowerShell") is not None
    assert git_commit_branch_guard._is_git_commit(_PS_COMMIT, "PowerShell") is True
    checkout = "C:" + _B + "Git" + _B + "cmd" + _B + "git.exe checkout main"
    assert reformat_md_tables._rewrites_the_tree(checkout, "PowerShell") is True
    assert reformat_md_tables._rewrites_the_tree("git status", "PowerShell") is False


# ---- a quoted Windows path on the Bash arm -----------------------------------------------------

def test_the_bash_arm_reduces_a_quoted_backslash_path_to_its_program():
    """Only a QUOTED token still carries a backslash after the Bash split - bash keeps them inside
    double quotes - so the path really is a path and the program name is its last component."""
    token = "C:" + _B + "Program Files" + _B + "Git" + _B + "cmd" + _B + "git.exe"
    assert S.basename_for_tool(token, "Bash") == "git"
    assert S.is_gated_command('"%s" commit -m x' % token, "Bash") is True
    assert S.basename_for_tool("/usr/bin/git", "Bash") == "git"


def test_a_quoted_backslash_sed_path_is_blocked_on_the_bash_arm(tmp_path):
    command = '"C:%stools%ssed.exe" -i s/a/b/ config.json' % (_B, _B)
    assert _guard("block-sed-structured-files", command, tmp_path) == 2


# ---- ANSI-C quoting ----------------------------------------------------------------------------
# Inside `$'...'` a backslash escapes, so `\'` does not close it. Read as a plain single-quoted
# string it closed early, and the quote after it opened a new span that swallowed the separator.

_ANSI = "echo $'it" + _B + "'s'; "


def test_an_ansi_c_escaped_quote_does_not_swallow_the_next_statement():
    assert S.is_gated_command(_ANSI + "git push") is True


def test_a_plain_single_quote_still_has_no_escape():
    assert S.is_gated_command("echo 'a" + _B + "'; git push") is True


def test_the_masks_close_an_ansi_c_string_where_bash_does():
    command = _ANSI + "git push"
    assert S.mask_data_regions(command).endswith("; git push")
    assert S.blank_unexpanded_text(command).endswith("; git push")
    assert len(S.mask_data_regions(command)) == len(command)


@pytest.mark.parametrize("hook,command", [
    ("block-sed-structured-files", _ANSI + "sed -i s/a/b/ config.json"),
    ("git-footgun-guard", _ANSI + "git rev-parse --short A B"),
])
def test_an_ansi_c_string_no_longer_disarms_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


# ---- a backslash-newline line continuation ------------------------------------------------------
# Bash deletes `\<newline>` before it splits words. shlex keeps the newline as part of the next
# token, so `&& \<newline>git push` put a token `<newline>git` where the program name belongs and no
# verb was recognised. Found by the corpus replay of this batch, on the Bash tool name that repo-gate
# really passes.

_CONT = " && " + _B + "\n"


@pytest.mark.parametrize("command", [
    "git status" + _CONT + "git commit -m x",
    "echo a" + _CONT + "  git push origin main",
    _B + "\ngit push origin main",
])
def test_a_line_continuation_does_not_hide_the_verb(command):
    assert S.is_gated_command(command, "Bash") is True


def test_split_for_tool_joins_a_continuation_like_bash():
    assert S.split_for_tool("git " + _B + "\n  push x", "Bash") == ["git", "push", "x"]


def test_a_continuation_inside_single_quotes_stays_literal():
    """Inside single quotes a backslash is literal, so nothing is joined and nothing is gated."""
    assert S.split_for_tool("echo 'a" + _B + "\nb'", "Bash") == ["echo", "a" + _B + "\nb"]
    assert S.is_gated_command("echo 'x" + _B + "\ngit push'", "Bash") is False


@pytest.mark.parametrize("hook,command", [
    ("git-footgun-guard", "echo a" + _CONT + "git rev-parse --short A B"),
    ("block-sed-structured-files", "echo a" + _CONT + "sed -i s/a/b/ config.json"),
])
def test_a_line_continuation_no_longer_disarms_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


# ---- dead regexes ------------------------------------------------------------------------------

def test_the_unused_commit_and_push_regexes_are_gone():
    """They read `-C`'s value as the verb, and nothing called them; git_verb_operands is the one
    answer to what git command a statement is."""
    assert not hasattr(S, "COMMIT_RE")
    assert not hasattr(S, "PUSH_RE")
