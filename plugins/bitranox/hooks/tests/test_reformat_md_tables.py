"""Tests for reformat-md-tables.py (auto-realign markdown tables on edit, Mode A).

Drives main() with a PostToolUse event JSON on stdin pointing at a temp file. Uses the real
reformat_tables.py shipped in the docs-md-table-formatting skill (resolved via the hook's own location).
All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import reformat_md_tables as H

MISALIGNED = "# t\n\n| A | Bee |\n|---|---|\n| x | y |\n| longer | z |\n"


def run(monkeypatch, path):
    # Resolve the reformat script against THIS repo (the hook's own location), not the ambient
    # CLAUDE_PLUGIN_ROOT (which during a commit points at the installed plugin cache - a different,
    # possibly older version that may not have the docs-md-table-formatting skill dir).
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"file_path": str(path)}})))
    return H.main()


def test_realigns_markdown_table_and_is_idempotent(tmp_path, monkeypatch):
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    out1 = f.read_text(encoding="utf-8")
    assert out1 != MISALIGNED            # it actually reformatted
    assert "| longer | z   |" in out1    # padded to the widest cell per column
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == out1  # idempotent (no oscillation)


def test_skips_non_markdown(tmp_path, monkeypatch):
    f = tmp_path / "code.py"
    original = "x = 1  |  y = 2\n"
    f.write_text(original, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == original


def test_markdown_without_tables_unchanged(tmp_path, monkeypatch):
    f = tmp_path / "plain.md"
    original = "# Title\n\nJust prose, no tables here.\n"
    f.write_text(original, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == original


def test_missing_file_returns_zero(tmp_path, monkeypatch):
    assert run(monkeypatch, tmp_path / "nope.md") == 0


def test_missing_file_path_returns_zero(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {}})))
    assert H.main() == 0


def test_malformed_stdin_returns_zero(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert H.main() == 0


def run_bash(monkeypatch, cwd, command="cat > doc.md"):
    """Drive main() with a Bash event, which declares no file_path at all."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    event = {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return H.main()


def test_rewrites_the_tree_ignores_a_git_verb_appearing_as_data():
    """A heredoc that DOCUMENTS `git merge` must not disable the path-guessing fallback.

    The predicate matched the subcommand anywhere in the raw command, so writing a doc whose body
    explains how to recover from a merge turned the fallback off for that very write, and the
    table it wrote shipped misaligned. The last assertion is the control: a real tree-writing git
    call must still be detected, or this test would pass against a predicate that never fires.
    """
    assert not H._rewrites_the_tree("cat > doc.md <<'EOF'\nrecover with `git merge --abort`\nEOF")
    assert not H._rewrites_the_tree("git log --oneline  # after the rebase")
    assert H._rewrites_the_tree("git merge --no-ff topic")  # control: a real merge still matches


@pytest.mark.xfail(
    reason="KNOWN GAP: heredoc bodies are stripped, so a script written and run by one command "
           "is not seen. Not stripping reinstates the prose false positive above, because a "
           "quoted delimiter makes backticks literal while the segment walk reads them as a "
           "command substitution. Needs write-vs-execute ordering, open against gated-prep-nudge.",
    strict=True,
)
def test_rewrites_the_tree_sees_a_git_write_in_a_script_this_command_then_runs():
    """Records the residual measured on the corpus: 8 of the 360 firings the walk removes.

    Kept as a failing expectation rather than deleted, because the cost of the miss is concrete -
    the hook restyles files git itself just wrote, which is how a re-cut merge once aborted with
    "your local changes would be overwritten".
    """
    written_then_run = "cat > recut.sh <<'SHEOF'\ngit merge --no-ff origin/topic\nSHEOF\nbash recut.sh"
    assert H._rewrites_the_tree(written_then_run)


def test_a_git_command_that_rewrites_the_tree_is_skipped(tmp_path, monkeypatch):
    """Verify markdown restamped by a git operation is left alone.

    checkout, merge, rebase and friends rewrite tracked files wholesale, so every
    markdown they touch looks just-written to an mtime scan. Reformatting there is
    never what the operator asked for, and doing it MID-OPERATION is destructive:
    a `git merge` mid-sequence aborted with "your local changes would be
    overwritten" because the hook had modified the very files the next merge
    needed, leaving a half-assembled branch.
    """
    for command in (
        "git merge --no-ff --no-edit origin/topic",
        "git checkout -B integration upstream/main",
        "cd /repo && git rebase --onto main base",
        "git -C /repo pull --ff-only",
    ):
        f = tmp_path / "doc.md"
        f.write_text(MISALIGNED, encoding="utf-8")
        assert run_bash(monkeypatch, tmp_path, command=command) == 0
        assert f.read_text(encoding="utf-8") == MISALIGNED, command


def test_a_read_only_git_command_still_realigns(tmp_path, monkeypatch):
    """Verify the skip is scoped to git commands that WRITE the working tree.

    `git log`/`status`/`diff` change nothing, so a markdown file written beside
    them in the same command is the operator's, and skipping it would quietly
    give back the gap the Bash fallback exists to close.
    """
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path, command="git log --oneline -1 > doc.md") == 0

    assert "| longer | z   |" in f.read_text(encoding="utf-8")


def test_a_table_written_by_bash_is_realigned(tmp_path, monkeypatch):
    """Verify the formatter reaches markdown a shell command wrote.

    Write and Edit announce their target; Bash does not. A heredoc, a `python3 -`
    script or `sed -i` therefore slipped past the formatter entirely, which is how
    a misaligned table shipped from a session that never called Write.
    """
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path) == 0

    out = f.read_text(encoding="utf-8")
    assert out != MISALIGNED
    assert "| longer | z   |" in out


def test_bash_reaches_a_nested_file_it_was_not_told_about(tmp_path, monkeypatch):
    """Verify the path is found by what changed, not by parsing the command.

    A command can build its target at runtime, so the command text is not a
    reliable source for the path.
    """
    nested = tmp_path / "docs" / "deep"
    nested.mkdir(parents=True)
    f = nested / "ref.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path, command="python3 - <<'EOF'") == 0

    assert "| longer | z   |" in f.read_text(encoding="utf-8")


def test_bash_ignores_vendored_trees(tmp_path, monkeypatch):
    """Verify a virtualenv or node_modules is never rewritten."""
    vendored = tmp_path / ".venv" / "pkg"
    vendored.mkdir(parents=True)
    f = vendored / "README.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path) == 0

    assert f.read_text(encoding="utf-8") == MISALIGNED


def test_bash_never_rewrites_a_nested_repository(tmp_path, monkeypatch):
    """Verify markdown belonging to a DIFFERENT repo checked out under cwd is left alone.

    A vendored upstream checkout is someone else's source. The Bash fallback finds
    files by mtime, and a plain `git checkout` or `git merge` in that checkout
    restamps every file it touches, so the fallback read hundreds of upstream docs
    as "just written" and realigned the ones whose tables were not in our house
    style. Measured 2026-08-07: seven docs in a vendored microsoft/openvmm mirror
    sat modified with alignment-only churn until a fast-forward refused to run.
    """
    (tmp_path / ".git").mkdir()  # cwd is itself a repo, which must stay in scope
    ours = tmp_path / "ours.md"
    ours.write_text(MISALIGNED, encoding="utf-8")

    vendored = tmp_path / "public" / "openvmm"
    (vendored / ".git").mkdir(parents=True)
    (vendored / "Guide").mkdir()
    theirs = vendored / "Guide" / "cli.md"
    theirs.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path) == 0

    assert theirs.read_text(encoding="utf-8") == MISALIGNED  # their repo, untouched
    assert "| longer | z   |" in ours.read_text(encoding="utf-8")  # ours still realigned


def test_bash_leaves_untouched_markdown_alone(tmp_path, monkeypatch):
    """Verify only files changed inside the window are considered."""
    import os
    import time

    f = tmp_path / "old.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    stale = time.time() - (H._BASH_WINDOW_SECONDS + 60)
    os.utime(f, (stale, stale))

    assert run_bash(monkeypatch, tmp_path) == 0

    assert f.read_text(encoding="utf-8") == MISALIGNED


def test_bash_with_no_cwd_returns_zero(monkeypatch):
    """Verify a malformed Bash event never wedges the turn."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Bash", "cwd": "/nonexistent-xyz"})))
    assert H.main() == 0
