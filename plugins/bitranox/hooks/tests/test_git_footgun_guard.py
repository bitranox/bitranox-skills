"""Tests for git-footgun-guard.py (blocks `git rev-parse --short` with 2+ revs).

Pure-function tests on broken_revparse plus end-to-end tests that drive main()
with a stdin payload, and a subprocess smoke test through run-python.sh.
"""

import io
import json
import os
import subprocess
import sys
import pytest
from pathlib import Path

import git_footgun_guard as G

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "git-footgun-guard.py"
SHIM = HOOKS_DIR / "run-python.sh"


# broken_revparse: the broken form is --short with 2+ revisions.
def test_two_revs_with_short_is_broken():
    assert G.broken_revparse("git rev-parse --short feat origin/feat") is True


def test_two_revs_with_short_and_dash_c():
    assert G.broken_revparse("git -C /repo rev-parse --short A B") is True


def test_short_eq_len_form_is_broken():
    assert G.broken_revparse("git rev-parse --short=12 A B") is True


def test_single_rev_with_short_is_ok():
    assert G.broken_revparse("git rev-parse --short HEAD") is False


def test_two_revs_without_short_is_ok():
    assert G.broken_revparse("git rev-parse HEAD~1 HEAD") is False


def test_short_with_other_flags_single_rev_ok():
    assert G.broken_revparse("git rev-parse --short --verify HEAD") is False


def test_neighbour_segment_not_conflated():
    # rev-parse here has one rev; the two refs are a separate piped command.
    assert G.broken_revparse("git rev-parse --short HEAD | grep A B") is False


def test_non_git_command_ignored():
    assert G.broken_revparse("echo rev-parse --short A B") is False


def test_redirection_not_counted_as_operand():
    # the bug: a redirection target was miscounted as a second revision -> false block
    assert G.broken_revparse("git rev-parse --short origin/master 2>/dev/null") is False
    assert G.broken_revparse("git rev-parse --short HEAD 2> /dev/null") is False
    assert G.broken_revparse("git rev-parse --short HEAD >out 2>&1") is False


def test_redirection_does_not_mask_real_breakage():
    # two genuine revisions are still broken even with a trailing redirection
    assert G.broken_revparse("git rev-parse --short A B 2>/dev/null") is True


# A heredoc BODY is data, not a command. Documenting the footgun (in a memory
# entry, a doc, a commit message) must not be blocked by the guard that warns
# about it - that recursion makes the footgun impossible to write about.
RP = "git rev-parse --short"  # assembled so this test file is not its own trigger


def test_heredoc_body_prose_not_treated_as_command():
    cmd = "cat > f.md <<'EOF'\nnever use " + RP + " A B here\nEOF"
    assert G.broken_revparse(cmd) is False


def test_heredoc_body_unquoted_delimiter():
    cmd = "cat > f.md <<EOF\nbad: " + RP + " A B\nEOF"
    assert G.broken_revparse(cmd) is False


def test_heredoc_body_dash_delimiter():
    cmd = "cat > f.md <<-EOF\nbad: " + RP + " A B\nEOF"
    assert G.broken_revparse(cmd) is False


def test_rev_parse_inside_a_commit_message_not_a_subcommand():
    assert G.broken_revparse('git commit -m "avoid ' + RP + ' A B"') is False


def test_heredoc_does_not_mask_a_real_command_after_it():
    # the body is skipped, but a genuine broken invocation AFTER the terminator
    # must still be caught - stripping must end at the delimiter line
    cmd = "cat > f.md <<'EOF'\nharmless prose\nEOF\n" + RP + " A B"
    assert G.broken_revparse(cmd) is True


def test_quoted_operands_still_blocked():
    # quoted args are real operands here; only heredoc bodies are data
    assert G.broken_revparse('git rev-parse --short "$A" "$B"') is True


def _run(monkeypatch, command):
    payload = {"tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return G.main()


def test_main_blocks_broken(monkeypatch):
    assert _run(monkeypatch, "git rev-parse --short A B") == 2


def test_main_allows_ok(monkeypatch):
    assert _run(monkeypatch, "git rev-parse --short HEAD") == 0


def test_main_bad_payload_is_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_shim_smoke():
    payload = json.dumps({"tool_input": {"command": "git rev-parse --short A B"}})
    r = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True,
        encoding="utf-8",
    )
    assert r.returncode == 2
    assert "Needed a single revision" in r.stderr


def test_command_substitution_is_a_real_command():
    # $( ) opens a new statement, so the rev-parse inside it is a command like any
    # other. Splitting on SEP alone left `A=$(git` as one token, no verb was found,
    # and the BLOCKING guard stayed quiet on a shape its own advisory nudge fires on.
    assert G.broken_revparse("A=$(git rev-parse --short HEAD HEAD~1)") is True


def test_backtick_substitution_is_a_real_command():
    assert G.broken_revparse("A=`git rev-parse --short HEAD HEAD~1`") is True


def test_command_substitution_single_rev_still_ok():
    assert G.broken_revparse("A=$(git rev-parse --short HEAD)") is False


def test_a_windows_path_separator_does_not_hide_a_broken_revparse():
    """This guard BLOCKS, so the tool-keyed escape matters here as much as in the gate: under
    PowerShell `\\` is a path separator, and reading it as an escape swallows the `;` that ends
    the previous statement."""
    cmd = r"cd C:\; git rev-parse --short HEAD HEAD~1"
    assert G.broken_revparse(cmd, tool_name="PowerShell") is True


def test_a_posix_escape_is_still_honoured_by_the_guard():
    assert G.broken_revparse(r"echo a\; git rev-parse --short A B", tool_name="Bash") is False


def test_an_event_without_a_tool_name_takes_the_stricter_reading(monkeypatch):
    """An event that names no tool is unexpected, so it must not silently get the reading that can
    HIDE a command. Coercing a missing tool_name to "Bash" put the miss-prone semantics in the
    fallback: under Bash the `\\` escapes the `;`, the two statements merge, and the broken
    rev-parse behind it is never seen. Escaping nothing keeps the separator and the guard fires."""
    payload = {"tool_input": {"command": r"cd C:\; git rev-parse --short A B"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert G.main() == 2


def test_a_trailing_ampersand_is_backgrounding_not_a_revision():
    # A lone `&` ends the statement (shell_text splits there), so it never reaches the operand
    # list: `--short HEAD &` is one revision run in the background. The operand filter used to
    # carry its own `t != "&"` clause for this, which segmentation had made unreachable.
    assert G.broken_revparse("git rev-parse --short HEAD &") is False
    assert G.broken_revparse("git rev-parse --short HEAD & git log -1") is False
    assert G.broken_revparse("git rev-parse --short A B &") is True        # control
    assert G.broken_revparse("git rev-parse --short HEAD &", "PowerShell") is False


# --- a pathspec commit over a STAGED-ONLY change (contrib #35) ------------------------------------
#
# `git commit -- <paths>` records the WORKTREE copy of each named path. Measured in temp repos (git
# 2.x): a staged `rm --cached` is re-added when another path rides the same pathspec (exit 0), a
# staged `update-index --chmod=+x` under core.fileMode=false reverts to 100644, and a partial stage
# is replaced by the whole file. Fixtures are written as bytes so CRLF conversion cannot differ.

_GIT_SCOPE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CONFIG")


def _git(repo, *args):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_SCOPE}
    env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@e")
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, encoding="utf-8", env=env)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "core.fileMode", "false")
    _git(r, "config", "core.autocrlf", "false")
    (r / "f.txt").write_bytes(b"one\n")
    (r / "other.txt").write_bytes(b"x\n")
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "base")
    return r


def _advise(monkeypatch, capsys, command, cwd):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}})))
    assert G.main() == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else None


def test_a_staged_untrack_named_in_a_pathspec_commit_is_advised(repo, monkeypatch, capsys):
    _git(repo, "rm", "--cached", "-q", "f.txt")
    (repo / "other.txt").write_bytes(b"y\n")
    text = _advise(monkeypatch, capsys, "git commit -m x -- other.txt f.txt", repo)
    assert text and "PATHSPEC COMMIT" in text and "f.txt" in text and "untrack" in text
    assert "other.txt" not in text.split("discard")[-1]


def test_a_staged_mode_change_named_in_a_pathspec_commit_is_advised(repo, monkeypatch, capsys):
    _git(repo, "update-index", "--chmod=+x", "f.txt")
    text = _advise(monkeypatch, capsys, 'git commit -F msg.txt -- f.txt', repo)
    assert text and "f.txt" in text and "100755" in text


def test_a_partial_stage_named_in_a_pathspec_commit_is_advised(repo, monkeypatch, capsys):
    (repo / "f.txt").write_bytes(b"two\n")
    _git(repo, "add", "f.txt")
    (repo / "f.txt").write_bytes(b"three\n")
    text = _advise(monkeypatch, capsys, "git commit -m x f.txt", repo)
    assert text and "f.txt" in text and "partial" in text


def test_a_staged_change_equal_to_the_worktree_is_silent(repo, monkeypatch, capsys):
    """Control: the normal pathspec commit loses nothing, so it says nothing."""
    (repo / "f.txt").write_bytes(b"two\n")
    _git(repo, "add", "f.txt")
    assert _advise(monkeypatch, capsys, "git commit -m x -- f.txt", repo) is None


def test_a_commit_without_a_pathspec_is_silent(repo, monkeypatch, capsys):
    """Control: without a pathspec the index IS what gets committed."""
    _git(repo, "rm", "--cached", "-q", "f.txt")
    assert _advise(monkeypatch, capsys, "git commit -m x", repo) is None


def test_an_untrack_in_the_same_command_is_advised_without_reading_state(repo, monkeypatch, capsys):
    """PreToolUse runs before `git rm --cached` does, so the index cannot show it yet."""
    text = _advise(monkeypatch, capsys,
                   "git rm --cached f.txt && git commit -m x -- .gitignore f.txt", repo)
    assert text and "f.txt" in text


def test_the_repo_is_the_one_the_commit_runs_in(repo, tmp_path, monkeypatch, capsys):
    _git(repo, "update-index", "--chmod=+x", "f.txt")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    text = _advise(monkeypatch, capsys, "cd %s && git commit -m x -- f.txt" % repo.as_posix(), elsewhere)
    assert text and "f.txt" in text


def test_outside_a_repository_it_is_silent(tmp_path, monkeypatch, capsys):
    assert _advise(monkeypatch, capsys, "git commit -m x -- f.txt", tmp_path) is None


def test_the_rev_parse_block_still_wins(repo, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_name": "Bash", "cwd": str(repo), "tool_input": {"command": "git rev-parse --short A B"}})))
    assert G.main() == 2
