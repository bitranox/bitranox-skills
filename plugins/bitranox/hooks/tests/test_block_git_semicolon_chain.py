"""Tests for block-git-semicolon-chain.py.

The guard blocks a single Bash command that joins two or more state-changing git verbs with `;`
(or a newline) rather than `&&`, because `;` runs the later steps after an earlier one failed and
the later steps then report their no-op as success.

Pure-function tests on `chained_state_changes` plus end-to-end tests that drive `main()` with a
stdin payload, and a subprocess smoke test through run-python.sh.
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


# --- fires: two state-changing verbs reachable across a `;` ------------------------------------


def test_commit_then_push_via_semicolon():
    assert G.chained_state_changes("git commit -m x ; git push") == ["commit", "push"]


def test_intervening_harmless_statement_still_fires():
    # The real failure: an `echo RC=$?` between the two hid nothing, because `;` still let the
    # push run after the commit had failed.
    assert G.chained_state_changes("git commit -F m.txt ; echo RC=$? ; git push") == [
        "commit",
        "push",
    ]


def test_mixed_separators_fire_when_the_path_crosses_a_semicolon():
    # commit && merge is safe, but merge ; push is not - the pair that crosses `;` is what counts.
    verbs = G.chained_state_changes("git commit -m x && git merge --ff-only b ; git push")
    assert verbs == ["merge", "push"]


def test_newline_separator_is_a_semicolon():
    assert G.chained_state_changes("git commit -m x\ngit push") == ["commit", "push"]


def test_global_dash_c_form_is_recognised():
    assert G.chained_state_changes("git -C /repo commit -F f ; git -C /repo push") == [
        "commit",
        "push",
    ]


def test_checkout_then_merge_fires():
    # Branch position is load-bearing: a failed checkout means the merge lands on the wrong branch.
    assert G.chained_state_changes("git checkout master ; git merge topic") == [
        "checkout",
        "merge",
    ]


def test_env_assignment_prefix_does_not_hide_the_verb():
    assert G.chained_state_changes("GIT_EDITOR=true git commit ; git push") == ["commit", "push"]


def test_the_command_that_motivated_this_guard():
    """The real 2026-08-16 command, verbatim.

    `git commit -F` refused with rc 1 because nothing was staged. The `;` let the rest run, and
    `git merge --ff-only` then printed `Bereits aktuell` and `git push` printed
    `Everything up-to-date`, both exit 0, so the sequence read as a successful ship.
    """
    command = (
        "cd ~/wt-capsys && git commit -F /tmp/msg.txt > /tmp/commit.log 2>&1; "
        'echo "COMMIT_RC=$?"; tail -3 /tmp/commit.log\n'
        'cd "$MAIN" && git checkout master > /dev/null 2>&1 '
        "&& git merge --ff-only capsys-fix > /tmp/merge.log 2>&1; "
        'echo "MERGE_RC=$?"\n'
        "git push origin master > /tmp/push.log 2>&1; "
        'echo "PUSH_RC=$?"'
    )
    assert G.chained_state_changes(command) is not None


# --- does not fire ------------------------------------------------------------------------------


def test_and_separator_is_the_correct_form():
    assert G.chained_state_changes("git commit -m x && git push") is None


def test_single_state_changing_verb_never_fires():
    assert G.chained_state_changes("git commit -m x ; echo done ; git status") is None


def test_read_only_verbs_never_fire():
    assert G.chained_state_changes("git status ; git log ; git diff") is None


def test_heredoc_body_is_data_not_commands():
    command = "cat <<'EOF' > note.md\ngit commit -m x ; git push\nEOF\ngit status"
    assert G.chained_state_changes(command) is None


def test_single_quoted_prose_is_data():
    assert G.chained_state_changes("echo 'git commit -m x ; git push'") is None


def test_double_quoted_prose_is_data():
    # A `;` inside a double-quoted message is not a separator, and the words after it are not a
    # command. Without blanking, this splits into a phantom `git push origin"` statement.
    command = 'git commit -m "wip; git push origin" ; echo ok'
    assert G.chained_state_changes(command) is None


def test_comment_is_not_a_command():
    assert G.chained_state_changes("git commit -m x  # ; git push") is None


def test_set_e_makes_semicolon_behave_like_and():
    assert G.chained_state_changes("set -e ; git commit -m x ; git push") is None


def test_set_euo_pipefail_also_counts():
    assert G.chained_state_changes("set -euo pipefail\ngit commit -m x\ngit push") is None


def test_set_o_errexit_also_counts():
    assert G.chained_state_changes("set -o errexit ; git commit -m x ; git push") is None


def test_explicit_or_true_marks_deliberate_continuation():
    command = "git tag -d v1 || true ; git push --delete origin v1"
    assert G.chained_state_changes(command) is None


def test_explicit_or_colon_marks_deliberate_continuation():
    command = "git tag -d v1 || : ; git push --delete origin v1"
    assert G.chained_state_changes(command) is None


def test_or_true_only_exempts_the_boundary_it_marks():
    # The `|| true` exempts tag -> push and nothing else. The very next gap, push ; commit, is
    # unmarked, so that is the pair reported - the FIRST offending gap, not the last.
    command = "git tag -d v1 || true ; git push --delete origin v1 ; git commit -m x ; git push"
    assert G.chained_state_changes(command) == ["push", "commit"]


def test_a_word_ending_in_git_is_not_git():
    assert G.chained_state_changes("mygit commit ; mygit push") is None


def test_pipe_is_not_a_semicolon_separator():
    # A pipe does not continue-after-failure in the way `;` does; it is a different shape.
    assert G.chained_state_changes("git log | head -3 ; git status") is None


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


def test_main_survives_malformed_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0


def test_main_survives_a_missing_command_field(monkeypatch, capsys):
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
