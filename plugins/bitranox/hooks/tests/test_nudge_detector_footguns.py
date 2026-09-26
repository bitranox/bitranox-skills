"""Tests for the detector-footgun nudge.

Each test names the defect it guards. The two positives are commands that burned a real
session; the negatives are the shapes a careless matcher would fire on.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parent.parent / "nudge-detector-footguns.py"


def _load():
    spec = importlib.util.spec_from_file_location("nudge_detector_footguns", _HOOK)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()


# --- find -newermt --------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["-3 minutes", "-5 min", "+2 days", "3 minutes ago", "yesterday", "now"],
)
def test_a_relative_newermt_is_flagged(value: str, tmp_path: Path) -> None:
    # bfs rejects these outright, so the loop reports 'nothing changed' forever.
    notice = mod.build_notice(f"find /x -newermt '{value}' | wc -l", tmp_path)
    assert notice is not None and "newermt" in notice


def test_an_iso_newermt_is_not_flagged(tmp_path: Path) -> None:
    # ISO-8601 is exactly what bfs documents as supported - flagging it would be noise.
    assert mod.build_notice("find /x -newermt 2026-07-31T10:00:00", tmp_path) is None


def test_newermt_without_find_is_not_flagged(tmp_path: Path) -> None:
    # The word appearing in prose or another tool's argument is not an invocation.
    assert mod.build_notice("echo 'use -newermt -3 minutes here'", tmp_path) is None


def test_find_without_newermt_is_not_flagged(tmp_path: Path) -> None:
    assert mod.build_notice("find . -name '*.py' -type f", tmp_path) is None


# --- pyright interpreter --------------------------------------------------------------


def test_unpinned_pyright_is_flagged_when_a_venv_exists(tmp_path: Path) -> None:
    # The measured case: 9 phantom reportMissingImports from the ambient interpreter.
    (tmp_path / ".venv").mkdir()
    notice = mod.build_notice("pyright --outputjson", tmp_path)
    assert notice is not None and "pyright" in notice


def test_unpinned_pyright_is_silent_without_a_venv(tmp_path: Path) -> None:
    # No venv means no ambient/venv split to warn about; firing here would be noise.
    assert mod.build_notice("pyright --outputjson", tmp_path) is None


@pytest.mark.parametrize(
    "flag",
    ["--pythonpath .venv/bin/python", "--pythonpath=.venv/bin/python", "--venvpath .", "-p .", "--project ."],
)
def test_a_pinned_pyright_is_not_flagged(flag: str, tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice(f"pyright {flag}", tmp_path) is None


def test_python_m_pyright_is_still_pyright(tmp_path: Path) -> None:
    # The exact form that misled a session: launching via the venv does NOT pin it.
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice(".venv/bin/python -m pyright", tmp_path) is not None


# --- both, and the never-wedge contract -----------------------------------------------


def test_both_footguns_in_one_command_are_both_reported(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    notice = mod.build_notice("find . -newermt '-3 minutes'; pyright", tmp_path)
    assert notice is not None
    assert "newermt" in notice and "pyright" in notice


def test_an_unparseable_command_is_silent(tmp_path: Path) -> None:
    # shlex raises on an unbalanced quote; guessing would be worse than staying quiet.
    assert mod.build_notice("find . -newermt '-3 minutes", tmp_path) is None


def test_the_hook_exits_zero_and_emits_context(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    event = {"tool_input": {"command": "pyright"}, "cwd": str(tmp_path)}
    r = subprocess.run(
        [sys.executable, str(_HOOK)], input=json.dumps(event), capture_output=True, text=True, check=False
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "pyright" in payload["hookSpecificOutput"]["additionalContext"]


def test_garbage_stdin_exits_zero_and_says_nothing() -> None:
    # A nudge must never wedge a turn, whatever it is handed.
    r = subprocess.run(
        [sys.executable, str(_HOOK)], input="not json at all", capture_output=True, text=True, check=False
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_newermt_from_another_command_is_not_finds():
    """`-newermt` belongs to whichever invocation it follows. Scanning every token on the line
    attributes another command's flag to `find` and describes an invocation nobody wrote."""
    toks = mod._tokens("grep -rn -- -newermt '-3 minutes' docs/ && find . -name '*.md'")
    assert mod.find_newermt_relative(toks) is None


def test_a_real_relative_newermt_is_still_found():
    """The direction where it must NOT apply."""
    toks = mod._tokens("find . -newermt '-3 minutes'")
    assert mod.find_newermt_relative(toks) == "-3 minutes"


def test_a_pin_flag_from_another_command_does_not_count_as_pyright_pinned(tmp_path):
    """`mkdir -p build && pyright` is an UNPINNED pyright run. `-p` is a pyright pin flag but here
    it is mkdir's, and reading it as pyright's silences the nudge - a miss, not a false fire."""
    (tmp_path / ".venv").mkdir()
    toks = mod._tokens("mkdir -p build && pyright")
    assert mod.pyright_without_pinned_interpreter(toks, tmp_path) is True


def test_a_real_pyright_pin_still_counts(tmp_path):
    (tmp_path / ".venv").mkdir()
    toks = mod._tokens("pyright -p pyrightconfig.json")
    assert mod.pyright_without_pinned_interpreter(toks, tmp_path) is False


# --- statement boundaries: the tokeniser must see what the shell sees ------------------


def test_a_mid_word_hash_is_data_not_a_comment(tmp_path):
    """`docs#tag` is one word to the shell. Reading its `#` as a comment dropped everything after
    it, pyright included, so an unpinned run went unnudged."""
    (tmp_path / ".venv").mkdir()
    notice = mod.build_notice("curl -s http://localhost:8000/docs#tag && pyright", tmp_path)
    assert notice is not None and "pyright" in notice


def test_a_real_trailing_comment_does_not_pin_pyright(tmp_path):
    """The direction the mid-word fix must not change: a word-initial `#` still starts a comment,
    so a pin flag written only in the comment is not a pin."""
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice("pyright  # -p pyrightconfig.json", tmp_path) is not None


def test_a_newline_ends_the_pyright_statement(tmp_path):
    """shlex never emits a newline token, so the next line's `-p` was read as pyright's pin."""
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice("pyright\nmkdir -p build", tmp_path) is not None


def test_a_newline_ends_the_find_statement(tmp_path):
    """The same gap the other way: another line's `-newermt` was attributed to `find`."""
    assert mod.build_notice("find . -name x\ngrep -- -newermt '-3 minutes' f", tmp_path) is None


def test_a_relative_newermt_before_a_newline_is_still_flagged(tmp_path):
    notice = mod.build_notice("find . -newermt '-3 minutes'\nls", tmp_path)
    assert notice is not None and "newermt" in notice


def test_a_glued_separator_still_separates(tmp_path):
    """`sub&&pyright` is one shlex token, so pyright was never seen as a program."""
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice("cd sub&&pyright", tmp_path) is not None


def test_a_heredoc_body_naming_pyright_is_not_an_invocation(tmp_path):
    (tmp_path / ".venv").mkdir()
    assert mod.build_notice("cat > notes.md <<'EOF'\nrun pyright here\nEOF", tmp_path) is None


# --- PowerShell: Windows paths and the .exe suffix ------------------------------------


@pytest.mark.parametrize(
    "command",
    ["C:\\Python312\\Scripts\\pyright.exe --outputjson", "pyright.exe --outputjson", "PYRIGHT.EXE"],
)
def test_a_windows_pyright_is_recognised_on_powershell(command, tmp_path):
    (tmp_path / ".venv").mkdir()
    notice = mod.build_notice(command, tmp_path, tool_name="PowerShell")
    assert notice is not None and "pyright" in notice


def test_a_pinned_windows_pyright_is_silent_on_powershell(tmp_path):
    (tmp_path / ".venv").mkdir()
    command = "C:\\Python312\\Scripts\\pyright.exe --project ."
    assert mod.build_notice(command, tmp_path, tool_name="PowerShell") is None


def test_a_windows_find_with_a_relative_newermt_is_flagged_on_powershell(tmp_path):
    command = "C:\\Program Files\\Git\\usr\\bin\\find.exe . -newermt '-3 minutes'"
    notice = mod.build_notice(command, tmp_path, tool_name="PowerShell")
    assert notice is not None and "-3 minutes" in notice


def test_a_windows_find_with_an_iso_newermt_is_silent_on_powershell(tmp_path):
    command = "find.exe . -newermt '2026-07-31T10:00:00'"
    assert mod.build_notice(command, tmp_path, tool_name="PowerShell") is None


def test_the_hook_reads_tool_name_for_powershell(tmp_path):
    """End to end: main() must hand the event's tool_name to the tokeniser, or the PowerShell arm
    is split by POSIX rules and the backslashes are eaten."""
    (tmp_path / ".venv").mkdir()
    event = {
        "tool_name": "PowerShell",
        "tool_input": {"command": "C:\\Python312\\Scripts\\pyright.exe --outputjson"},
        "cwd": str(tmp_path),
    }
    r = subprocess.run(
        [sys.executable, str(_HOOK)], input=json.dumps(event), capture_output=True, text=True, check=False
    )
    assert r.returncode == 0
    assert "pyright" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


# --- the venv probe's error path --------------------------------------------------------


class _UnreadableTree:
    """A cwd whose venv probe raises, as `Path.is_dir` does on Python 3.10-3.13 when a parent
    directory denies search permission (EACCES is not one of the errnos it swallows there)."""

    def __truediv__(self, _other):
        return self

    def is_dir(self):
        raise PermissionError(13, "Permission denied")


def test_an_unreadable_tree_is_silent_rather_than_raising():
    statements = mod._tokens("pyright --outputjson")
    assert mod.pyright_without_pinned_interpreter(statements, _UnreadableTree()) is False
