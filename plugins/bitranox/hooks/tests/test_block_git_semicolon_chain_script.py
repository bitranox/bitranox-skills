"""Tests for block-git-semicolon-chain.py's second rule: a heredoc script, then git, across `;`.

The shape (OPEN-WORK [500]): a `python3 - <<'EOF'` edit whose assertion fails, a line break, and
`git add f && git rebase --continue` - the line break runs the git step anyway, so the unedited
files (conflict markers included, on 2026-10-08) are staged and committed, exit 0.

The rule is the NARROW arm the user chose after a corpus replay: only a heredoc fed to a script
runner (python/bash/perl/node/uv) counts as the earlier step, and only a git verb that records
something. A `cd`, `cat >` or `printf >` before git was measured at 12x the firings for no extra
confirmed catch, so those must stay quiet here.
"""

import io
import json
import sys

import block_git_semicolon_chain as G

NL = "\n"


def _heredoc(runner="python3 -", body="assert False", tail=""):
    return f"{runner} <<'EOF'{tail}{NL}{body}{NL}EOF{NL}"


# --- fires ----------------------------------------------------------------------------------------


def test_the_incident_shape_fires():
    command = _heredoc() + "git add f && GIT_EDITOR=true git rebase --continue"
    assert G.git_after_script(command) == ("python3", "add")


def test_a_semicolon_after_the_heredoc_terminator_fires():
    command = _heredoc(body="print(1)") + "true ; git commit -F msg.txt"
    assert G.git_after_script(command) == ("python3", "commit")


def test_a_bash_heredoc_fires():
    assert G.git_after_script(_heredoc(runner="bash -s") + "git push") == ("bash", "push")


def test_an_env_prefixed_runner_fires():
    command = _heredoc(runner="PYTHONUTF8=1 python3 -") + "git add -A"
    assert G.git_after_script(command) == ("python3", "add")


# --- stays quiet ----------------------------------------------------------------------------------


def test_and_on_the_heredoc_opener_line_is_the_correct_form():
    command = _heredoc(tail=" && git add f")
    assert G.git_after_script(command) is None


def test_errexit_before_the_script_exempts_it():
    assert G.git_after_script("set -e" + NL + _heredoc() + "git add f") is None


def test_a_failure_handler_on_the_script_exempts_it():
    assert G.git_after_script(_heredoc(tail=" || exit 1") + "git add f") is None


def test_a_script_without_a_heredoc_is_outside_the_rule():
    assert G.git_after_script("python3 edit.py" + NL + "git add f") is None


def test_a_cat_heredoc_is_outside_the_rule():
    assert G.git_after_script(_heredoc(runner="cat > msg.txt") + "git commit -F msg.txt") is None


def test_a_cd_before_git_is_outside_the_rule():
    assert G.git_after_script("cd /repo ; git add f") is None


def test_a_read_only_git_step_is_not_judged():
    assert G.git_after_script(_heredoc() + "git status --porcelain") is None
    assert G.git_after_script(_heredoc() + "git add -n f") is None


def test_a_git_verb_outside_the_recording_list_is_not_judged():
    assert G.git_after_script(_heredoc() + "git fetch -q origin") is None


def test_a_heredoc_string_inside_a_quoted_argument_is_not_a_script():
    command = "echo 'python3 - <<EOF'" + NL + "git add f"
    assert G.git_after_script(command) is None


# --- main(): one refusal per command, the pair rule first -----------------------------------------


def _run_main(command, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    rc = G.main()
    return rc, capsys.readouterr().err


def test_main_blocks_the_incident_and_names_the_fix(monkeypatch, capsys):
    rc, err = _run_main(_heredoc() + "git add f && git rebase --continue", monkeypatch, capsys)
    assert rc == 2
    assert "python3" in err and "git add" in err
    assert "&&" in err and "opener line" in err


def test_main_allows_the_opener_line_form(monkeypatch, capsys):
    rc, err = _run_main(_heredoc(tail=" && git add f"), monkeypatch, capsys)
    assert rc == 0 and err == ""


def test_main_reports_the_pair_rule_when_both_apply(monkeypatch, capsys):
    rc, err = _run_main(_heredoc() + "git commit -m x ; git push", monkeypatch, capsys)
    assert rc == 2
    assert "`git commit` and `git push`" in err
