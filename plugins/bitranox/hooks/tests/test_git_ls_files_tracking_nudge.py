"""Tests for git-ls-files-tracking-nudge: a bare `git ls-files <path>` used as a tracking test."""

import io
import json
import subprocess
import sys

import pytest

import git_ls_files_tracking_nudge as G


@pytest.mark.parametrize("command", [
    "git ls-files CLAUDE.md && echo TRACKED",
    "git ls-files CLAUDE.md >/dev/null && echo TRACKED || echo UNTRACKED",
    "git ls-files CLAUDE.md 2>/dev/null || echo 'not tracked'",
    "if git ls-files CLAUDE.md; then echo tracked; fi",
    "if git ls-files -- CLAUDE.md >/dev/null; then echo tracked; fi",
    "while git ls-files x; do sleep 1; done",
    "! git ls-files CLAUDE.md && echo missing",
    "cd /repo && git -C /repo ls-files docs/a.md && echo yes",
    "git ls-files --cached a.md && echo yes",
    "git ls-files -x '*.tmp' a.md && echo yes",
    "git ls-files CLAUDE.md && printf 'tracked\\n'",
    "git ls-files a.md && exit 0",
    # Output thrown away, so the exit status is the only thing anything downstream acts on.
    "git ls-files a.md >/dev/null && git rm --cached a.md",
    "git ls-files a.md > /dev/null 2>&1 && git commit -m x",
])
def test_fires_on_a_bare_ls_files_used_as_a_test(command):
    assert G.notice(command) is not None


@pytest.mark.parametrize("command", [
    # --error-unmatch is the fix the notice teaches.
    "git ls-files --error-unmatch CLAUDE.md && echo TRACKED",
    "git ls-files --error-unmatch -- CLAUDE.md >/dev/null 2>&1 || echo untracked",
    # Listing output, not testing the status.
    "git ls-files CLAUDE.md",
    "git ls-files src/ | head",
    "git ls-files; git status",
    # No pathspec: nothing about one path's tracking is asked.
    "git ls-files && echo listed",
    "git ls-files -o --exclude-standard && echo done",
    # Output tested, not the status: the correct idiom.
    '[ -n "$(git ls-files CLAUDE.md)" ] && echo TRACKED',
    'test -n "$(git ls-files CLAUDE.md)" && echo TRACKED',
    "git ls-files CLAUDE.md | grep -q . && echo TRACKED",
    "x=$(git ls-files a.md) && echo $x",
    # Chained steps whose listing the reader sees: the `&&` sequences work, it decides nothing.
    "git ls-files a.md && cat a.md",
    "git ls-files -s f.py && git add f.py",
    "git ls-files --eol x.txt && git diff --numstat",
    "git ls-files 'src/*.py' > files.txt && wc -l files.txt",
    "git status --short && git ls-files CLAUDE.md && ls docs/",
    # Failure swallowed, not tested.
    "git ls-files a.md || true",
    "git ls-files a.md || :",
    # Data, not a command.
    "cat <<'EOF' > note.md\ngit ls-files a.md && echo TRACKED\nEOF",
    "echo 'git ls-files a.md && echo TRACKED'",
    # Another verb.
    "git status a.md && echo ok",
])
def test_quiet_on_listing_and_correct_idioms(command):
    assert G.notice(command) is None


def test_notice_names_the_fix():
    text = G.notice("git ls-files a.md && echo TRACKED")
    assert "--error-unmatch" in text
    assert "check-ignore" in text


def test_non_string_input_is_quiet():
    assert G.notice(None) is None
    assert G.notice(["git", "ls-files"]) is None


def _run_main(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    rc = G.main()
    return rc, capsys.readouterr().out


def test_main_emits_additional_context_and_never_blocks(monkeypatch, capsys):
    rc, out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": "git ls-files a.md && echo TRACKED"}})
    assert rc == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "--error-unmatch" in payload["additionalContext"]
    assert "permissionDecision" not in payload


def test_main_ignores_other_tools(monkeypatch, capsys):
    rc, out = _run_main(monkeypatch, capsys, {
        "tool_name": "Write", "tool_input": {"command": "git ls-files a.md && echo TRACKED"}})
    assert (rc, out) == (0, "")


def test_main_survives_garbage_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0
    assert capsys.readouterr().out == ""


def test_the_premise_bare_ls_files_exits_zero_for_an_untracked_path(tmp_path):
    # The nudge's whole claim, checked against the real git rather than restated.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    bare = subprocess.run(["git", "-C", str(tmp_path), "ls-files", "nope"], capture_output=True)
    strict = subprocess.run(["git", "-C", str(tmp_path), "ls-files", "--error-unmatch", "nope"],
                            capture_output=True)
    assert bare.returncode == 0 and bare.stdout == b""
    assert strict.returncode != 0
