"""Tests for reformat-md-tables.py (auto-realign markdown tables on edit, Mode A).

Drives main() with a PostToolUse event JSON on stdin pointing at a temp file. Uses the real
reformat_tables.py shipped in the docs-md-table-formatting skill (resolved via the hook's own location).
All content is ASCII.
"""

import io
import json
import sys

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


def run_bash(monkeypatch, cwd, command="cat > doc.md", tool_name="Bash"):
    """Drive main() with a Bash event, which declares no file_path at all."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    event = {"tool_name": tool_name, "cwd": str(cwd), "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return H.main()


@pytest.mark.parametrize("tool_name", ["Bash", "PowerShell", "Monitor"])
def test_every_command_carrying_tool_the_matcher_admits_is_realigned(tmp_path, monkeypatch, tool_name):
    """hooks.json registers this hook for Bash|PowerShell|Monitor, and all three carry a command.

    Monitor was added to that matcher for the sibling hook in the same group, and this one kept
    testing the tool NAME against the two shell tools - so it fired on a Monitor event and did
    nothing, a registration wider than the behaviour. The scan never parses the command, so
    carrying one is the whole requirement.
    """
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path, tool_name=tool_name) == 0

    assert "| longer | z   |" in f.read_text(encoding="utf-8"), tool_name


@pytest.mark.parametrize("stem", ["reformat-md-tables", "tell-sweep"])
def test_a_file_hook_that_never_reads_notebook_path_is_not_registered_for_notebookedit(stem):
    """Neither hook reads `notebook_path`, so a NotebookEdit registration only spawned a no-op.

    Both docstrings used to admit it ("the registration is a no-op for that tool"), and every
    notebook edit still paid two interpreter starts for nothing. The PostToolUse group is split so
    these two run for Write|Edit|MultiEdit only; the hooks that DO read `notebook_path`
    (validate-structured-files, touched-paths) keep NotebookEdit. Control: they still have it.
    """
    from pathlib import Path

    hooks_json = Path(H.__file__).resolve().parent / "hooks.json"
    groups = json.loads(hooks_json.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]

    def tools_for(name):
        found = set()
        for group in groups:
            for handler in group["hooks"]:
                if handler["command"].endswith('/hooks/%s.py"' % name):
                    found |= set((group.get("matcher") or "").split("|"))
        return found

    assert {"Write", "Edit", "MultiEdit"} <= tools_for(stem)
    assert "NotebookEdit" not in tools_for(stem)
    assert "NotebookEdit" in tools_for("validate-structured-files")
    assert "NotebookEdit" in tools_for("touched-paths")


def test_an_event_carrying_no_command_is_left_alone(tmp_path, monkeypatch):
    """Control: the widening keys on the command, so an event without one still does nothing."""
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    event = {"tool_name": "Monitor", "cwd": str(tmp_path), "tool_input": {"shellCommand": "cat > doc.md"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    assert H.main() == 0

    assert f.read_text(encoding="utf-8") == MISALIGNED


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


def _isolate_home(tmp_path, monkeypatch):
    """The git-rewrite marker lives under Path.home(); isolate it so a test run never reads or
    writes the real machine's ~/.claude/self-improve-audit."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def test_a_git_rewrite_is_not_reformatted_by_the_next_unrelated_bash_call(tmp_path, monkeypatch):
    """The gap: `_rewrites_the_tree` only protects the SAME event's own scan. A git checkout
    restamps the file's mtime, and the NEXT, unrelated, non-git Bash call within the 120 s window
    re-scans by mtime with no memory of the git event, so it reformats a file it never wrote -
    measured on a mirrored SKILL.md, where the mirror gate then blocked the commit.
    """
    _isolate_home(tmp_path, monkeypatch)
    cwd = tmp_path / "repo"
    cwd.mkdir()
    f = cwd / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, cwd, command="git checkout -B x origin/main") == 0
    assert f.read_text(encoding="utf-8") == MISALIGNED  # the git event itself: already covered

    assert run_bash(monkeypatch, cwd, command="true") == 0  # unrelated, non-git, same window

    assert f.read_text(encoding="utf-8") == MISALIGNED, (
        "the next unrelated Bash call must not reformat a file git just restamped")


def test_a_git_rewrite_marker_does_not_leak_across_a_different_cwd(tmp_path, monkeypatch):
    """The marker is keyed per cwd: a git rewrite in one project must not suppress a genuine
    table write in an unrelated one running in the same window."""
    _isolate_home(tmp_path, monkeypatch)
    other = tmp_path / "other"
    other.mkdir()
    mine = tmp_path / "mine"
    mine.mkdir()

    assert run_bash(monkeypatch, other, command="git checkout -B x origin/main") == 0

    f = mine / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    assert run_bash(monkeypatch, mine, command="true") == 0

    assert "| longer | z   |" in f.read_text(encoding="utf-8")


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


# ---- one bad target must not cost the others ---------------------------------------------------

def test_an_unreadable_markdown_file_does_not_stop_the_next_target(tmp_path, monkeypatch):
    """`return 0` inside the target loop meant one non-UTF-8 file cancelled the reformat of every
    file after it. The bad file sits at the top so the walk reaches it before the good one."""
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe| a | b |\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    good = sub / "good.md"
    good.write_text(MISALIGNED, encoding="utf-8")

    assert run_bash(monkeypatch, tmp_path) == 0

    assert "| longer | z   |" in good.read_text(encoding="utf-8")
    assert bad.read_bytes() == b"\xff\xfe| a | b |\n"


def test_a_missing_reformat_script_is_still_the_one_early_return(tmp_path, monkeypatch):
    """The control: when the formatter itself cannot be imported there is nothing to do per file,
    so giving up at once is right and the file is left as it was."""
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    event = {"tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {"command": "cat > doc.md"}}
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "no-plugin-here"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    assert H.main() == 0

    assert f.read_text(encoding="utf-8") == MISALIGNED


# ---- the scan's bounds -------------------------------------------------------------------------

def _scan(tmp_path):
    event = {"tool_name": "Bash", "cwd": str(tmp_path), "tool_input": {"command": "true"}}
    return H._markdown_paths_from_a_command(event)


def test_the_scan_stops_at_the_file_cap(tmp_path):
    """Both breaks: the per-file one inside a directory, and the per-directory one that stops the
    walk from descending once the cap is reached."""
    for i in range(H._BASH_FILE_CAP + 1):
        (tmp_path / f"f{i:03d}.md").write_text("x\n", encoding="utf-8")
    later = tmp_path / "zz-later"
    later.mkdir()
    (later / "late.md").write_text("x\n", encoding="utf-8")

    found = _scan(tmp_path)

    assert len(found) == H._BASH_FILE_CAP
    assert str(later / "late.md") not in found


def test_a_file_that_cannot_be_stat_ed_is_skipped(tmp_path):
    """A dangling symlink named like markdown makes stat() raise; the scan must step over it and
    keep the real file beside it."""
    real = tmp_path / "real.md"
    real.write_text("x\n", encoding="utf-8")
    try:
        (tmp_path / "dangling.md").symlink_to(tmp_path / "gone.md")
    except (OSError, NotImplementedError):
        pytest.skip("this platform cannot create a symlink unprivileged")

    found = _scan(tmp_path)

    assert found == [str(real)]


def test_the_scan_lists_only_markdown(tmp_path):
    (tmp_path / "notes.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "doc.md").write_text("x\n", encoding="utf-8")
    assert _scan(tmp_path) == [str(tmp_path / "doc.md")]


def test_the_scan_of_a_cwd_that_does_not_exist_is_empty(tmp_path):
    assert _scan(tmp_path / "gone") == []
