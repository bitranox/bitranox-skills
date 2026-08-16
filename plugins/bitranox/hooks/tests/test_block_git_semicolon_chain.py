"""Tests for block-git-semicolon-chain.py.

The guard blocks a single Bash command that joins two or more state-changing git verbs with `;`
(or a newline) rather than `&&`, because `;` runs the later steps after an earlier one failed and
the later steps then report their no-op as success.

Most of the cases below came from two adversarial reviews of the first implementation, which found
five Criticals between them. They are kept as tests rather than summarised, because each one is a
concrete shell shape the flat-split parser got wrong once and can get wrong again.

The decisive question for any case here: WOULD `&&` BE CORRECT ADVICE? The guard's message tells
the author to use `&&`, so a command where that advice is wrong must not be blocked.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import block_git_semicolon_chain as G

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "block-git-semicolon-chain.py"
SHIM = HOOKS_DIR / "run-python.sh"


# --- fires: state-changing verbs reachable across an unguarded `;` -------------------------------


def test_commit_then_push_via_semicolon():
    assert G.chained_state_changes("git commit -m x ; git push") == ["commit", "push"]


def test_intervening_harmless_statement_still_fires():
    assert G.chained_state_changes("git commit -F m.txt ; echo RC=$? ; git push") == [
        "commit",
        "push",
    ]


def test_mixed_separators_fire_when_the_path_crosses_a_semicolon():
    verbs = G.chained_state_changes("git commit -m x && git merge --ff-only b ; git push")
    assert verbs == ["merge", "push"]


def test_newline_separator_is_a_semicolon():
    assert G.chained_state_changes("git commit -m x\ngit push") == ["commit", "push"]


def test_env_assignment_prefix_does_not_hide_the_verb():
    assert G.chained_state_changes("GIT_EDITOR=true git commit ; git push") == ["commit", "push"]


def test_the_command_that_motivated_this_guard():
    """The real 2026-08-16 command, including the `$(...)` line the first version choked on.

    `git commit -F` refused with rc 1 because nothing was staged. The `;` let the rest run, and
    `git merge --ff-only` then printed `Bereits aktuell` and `git push` printed
    `Everything up-to-date`, both exit 0, so the sequence read as a successful ship.
    """
    command = (
        "cd ~/wt-capsys && git commit -F /tmp/msg.txt > /tmp/commit.log 2>&1; "
        'echo "COMMIT_RC=$?"; tail -3 /tmp/commit.log\n'
        "MAIN=$(git worktree list | head -1 | awk '{print $1}')\n"
        'cd "$MAIN" && git checkout master > /dev/null 2>&1 '
        "&& git merge --ff-only capsys-fix > /tmp/merge.log 2>&1; "
        'echo "MERGE_RC=$?"\n'
        "git push origin master > /tmp/push.log 2>&1; "
        'echo "PUSH_RC=$?"'
    )
    assert G.chained_state_changes(command) is not None


# --- fires: shapes the FIRST implementation missed (from the false-negative review) --------------


def test_quoted_dash_c_value_does_not_hide_the_verb():
    """Masking must consume the quote characters too.

    Blanking only the CONTENT leaves `"$MAIN"` as two bare `"` tokens, `-C` eats the first, the
    parser stops on the second, and the whole statement reads as a non-git command. The unquoted
    form kept working throughout, so a test using it reads as covering this and does not.
    """
    assert G.chained_state_changes('git -C "$MAIN" commit -F f ; git -C "$MAIN" push') == [
        "commit",
        "push",
    ]


def test_single_quoted_dash_c_value():
    assert G.chained_state_changes("git -C '/repo' commit -F f ; git -C '/repo' push") == [
        "commit",
        "push",
    ]


def test_unquoted_dash_c_form_is_still_recognised():
    assert G.chained_state_changes("git -C /repo commit -F f ; git -C /repo push") == [
        "commit",
        "push",
    ]


def test_errexit_after_the_chain_does_not_protect_it():
    assert G.chained_state_changes("git commit -m x ; git push ; set -e") == ["commit", "push"]


def test_errexit_switched_back_off_does_not_protect():
    assert G.chained_state_changes("set -e ; set +e ; git commit -m x ; git push") == [
        "commit",
        "push",
    ]


def test_or_true_on_an_unrelated_statement_does_not_excuse_the_gap():
    """The `;` right after the commit is the hazard; a `|| true` two statements later is not it."""
    assert G.chained_state_changes("git commit -m x ; rm -f /tmp/log || true ; git push") == [
        "commit",
        "push",
    ]


def test_stash_pop_or_true_between_checkout_and_merge():
    command = "git checkout master ; git stash pop || true ; git merge topic"
    assert G.chained_state_changes(command) == ["checkout", "merge"]


def test_ampersand_backgrounding_is_a_separator():
    assert G.chained_state_changes("git commit -m x & git push") == ["commit", "push"]


def test_redirection_ampersands_are_not_separators():
    assert G.chained_state_changes("git commit -m x > log 2>&1 && git push &>out") is None


def test_wrapper_prefixes_do_not_hide_the_verb():
    assert G.chained_state_changes("sudo git commit -m x ; sudo git push") == ["commit", "push"]


def test_timeout_wrapper_with_a_duration():
    assert G.chained_state_changes("timeout 60 git push ; git tag -a v1 -m x") == ["push", "tag"]


def test_sudo_with_a_user_option():
    assert G.chained_state_changes("sudo -u git git commit -m x ; sudo -u git git push") == [
        "commit",
        "push",
    ]


def test_fetch_then_ff_merge_fires():
    """A failed fetch leaves origin/master stale, and the ff-merge then prints the very string
    this guard exists to distrust."""
    assert G.chained_state_changes("git fetch ; git merge --ff-only origin/master") == [
        "fetch",
        "merge",
    ]


def test_update_index_then_commit_fires():
    assert G.chained_state_changes("git update-index --chmod=+x f ; git commit -m x") == [
        "update-index",
        "commit",
    ]


# --- does not fire: correct forms (from the false-positive review) -------------------------------


def test_and_separator_is_the_correct_form():
    assert G.chained_state_changes("git commit -m x && git push") is None


def test_newline_after_and_is_a_line_continuation():
    """The worst defect the reviews found: this is ALREADY the form the guard demands.

    Blocking it printed a message saying "join them with &&", which the author had done, so no
    edit could satisfy the guard - the fastest way to train someone to route around one.
    """
    assert G.chained_state_changes("git checkout main &&\ngit merge --ff-only origin/main") is None


def test_backslash_continuation_after_and():
    assert G.chained_state_changes("git commit -m x && \\\n  git push") is None


def test_multi_line_and_chain():
    command = "cd /repo &&\ngit add -A &&\ngit commit -F /tmp/m.txt &&\ngit push origin main"
    assert G.chained_state_changes(command) is None


def test_blank_line_inside_an_and_chain():
    assert G.chained_state_changes("git checkout main &&\n\ngit merge origin/main") is None


def test_comment_line_inside_an_and_chain():
    assert G.chained_state_changes("git checkout main &&\n# now merge\ngit merge origin/main") is None


def test_checkout_with_double_dash_is_a_path_restore():
    """`git checkout -- Makefile` moves no branch, so its failure invalidates nothing after it.

    This was the largest single false-positive class measured against real command history, and it
    comes straight from this repo's own workflow of dropping bmk's Makefile regen before a commit.
    """
    command = "git checkout -- Makefile 2>/dev/null\ngit commit -q -m x"
    assert G.chained_state_changes(command) is None


def test_two_independent_path_restores():
    assert G.chained_state_changes("git checkout -- README.md; git checkout -- CHANGELOG.md") is None


def test_abort_forms_are_cleanup():
    command = "git merge --abort 2>/dev/null; git reset --hard origin/main"
    assert G.chained_state_changes(command) is None


def test_tag_listing_forms_are_read_only():
    assert G.chained_state_changes("git tag -l 'v5.*' ; git push") is None
    assert G.chained_state_changes("git tag --list ; git push") is None
    assert G.chained_state_changes("git tag ; git push") is None


def test_repeated_verb_is_parallel_work_not_a_pipeline():
    """`&&` would be WRONG advice here: you want branch two pushed even if branch one fails."""
    assert G.chained_state_changes("git push origin main ; git push origin topic") is None
    assert G.chained_state_changes("git commit --allow-empty -m a ; git commit -m b") is None


def test_any_or_handler_marks_deliberate_continuation():
    assert G.chained_state_changes("git tag -d v1 || true ; git push --delete origin v1") is None
    assert G.chained_state_changes("git tag -d v1 || : ; git push --delete origin v1") is None
    assert G.chained_state_changes("git commit -m x || exit 1; git push") is None
    assert G.chained_state_changes("git commit -am wip || echo 'nothing staged'; git push") is None


def test_errexit_before_the_chain_exempts_it():
    assert G.chained_state_changes("set -e ; git commit -m x ; git push") is None
    assert G.chained_state_changes("set -euo pipefail\ngit commit -m x\ngit push") is None
    assert G.chained_state_changes("set -o errexit ; git commit -m x ; git push") is None
    assert G.chained_state_changes("set -x -e; git commit -m x; git push") is None
    assert G.chained_state_changes("set -o pipefail -e; git commit -m x; git push") is None


def test_set_u_alone_is_not_errexit():
    assert G.chained_state_changes("set -u ; git commit -m x ; git push") == ["commit", "push"]


def test_single_state_changing_verb_never_fires():
    assert G.chained_state_changes("git commit -m x ; echo done ; git status") is None


def test_read_only_verbs_never_fire():
    assert G.chained_state_changes("git status ; git log ; git diff") is None


def test_a_word_ending_in_git_is_not_git():
    assert G.chained_state_changes("mygit commit ; mygit push") is None


def test_pipe_is_not_a_continue_after_failure_separator():
    assert G.chained_state_changes("git log | head -3 ; git status") is None


# --- does not fire: data regions ------------------------------------------------------------------


def test_heredoc_body_is_data_not_commands():
    command = "cat <<'EOF' > note.md\ngit commit -m x ; git push\nEOF\ngit status"
    assert G.chained_state_changes(command) is None


def test_single_quoted_prose_is_data():
    assert G.chained_state_changes("echo 'git commit -m x ; git push'") is None


def test_double_quoted_prose_is_data():
    assert G.chained_state_changes('git commit -m "wip; git push origin" ; echo ok') is None


def test_newline_inside_a_quoted_message_is_not_a_separator():
    assert G.chained_state_changes("git commit -m 'line one\nline two' && git push") is None


def test_comment_is_not_a_command():
    assert G.chained_state_changes("git commit -m x  # ; git push") is None


def test_semicolon_inside_command_substitution_is_not_a_separator():
    command = "git checkout -B rel/$(cd /v; git describe --tags) && git push -u origin HEAD"
    assert G.chained_state_changes(command) is None


# --- does not judge: block structure --------------------------------------------------------------


def test_if_else_branches_are_mutually_exclusive():
    """Exactly one branch runs, and `&&` cannot express that - joining them is a different program."""
    command = 'if [ -n "$X" ]; then\n  git merge --ff-only origin/main\nelse\n  git rebase origin/main\nfi'
    assert G.chained_state_changes(command) is None


def test_loop_body_semicolons_in_the_gap_are_required_syntax():
    command = "git checkout main && for r in a b c; do echo $r; done && git push --all"
    assert G.chained_state_changes(command) is None


def test_brace_group_in_the_gap():
    assert G.chained_state_changes("git commit -m x && { echo done; date; } && git push") is None


def test_two_subshells_joined_by_and():
    assert G.chained_state_changes("(cd /a; git checkout main) && (cd /b; git merge x)") is None


def test_function_definitions_are_not_executed():
    command = "a() {\n git checkout main\n}\nb() {\n git merge topic\n}"
    assert G.chained_state_changes(command) is None


def test_parameter_expansion_braces_do_not_trigger_the_scope_bail():
    """`${VAR}` is a word, not a brace GROUP - masking it keeps ordinary commands judgeable."""
    assert G.chained_state_changes("echo ${FOO} ; git commit -m x ; git push") == [
        "commit",
        "push",
    ]


# --- degenerate input -----------------------------------------------------------------------------


def test_degenerate_inputs_are_clean():
    for command in ["", " ", ";", ";;;", "\n", "||", "&&", "|", "git commit -m '", 'git commit -m "']:
        assert G.chained_state_changes(command) is None


def test_none_command_is_clean():
    assert G.chained_state_changes(None) is None


# --- main(): exit codes and message ---------------------------------------------------------------


def _run_main(command, monkeypatch, capsys):
    payload = json.dumps({"tool_input": {"command": command}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    rc = G.main()
    return rc, capsys.readouterr()


def test_main_blocks_the_chained_form(monkeypatch, capsys):
    rc, captured = _run_main("git commit -m x ; git push", monkeypatch, capsys)
    assert rc == 2
    assert "&&" in captured.err
    assert "commit" in captured.err and "push" in captured.err


def test_main_allows_the_and_form(monkeypatch, capsys):
    rc, captured = _run_main("git commit -m x && git push", monkeypatch, capsys)
    assert rc == 0
    assert captured.err == ""


def test_main_survives_malformed_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0


def test_main_survives_a_missing_command_field(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({})))
    assert G.main() == 0


def test_subprocess_through_the_shim_blocks():
    payload = json.dumps({"tool_input": {"command": "git commit -m x ; git push"}})
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 2
    assert "&&" in proc.stderr


def test_subprocess_through_the_shim_allows_the_and_form():
    payload = json.dumps({"tool_input": {"command": "git commit -m x && git push"}})
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 0
