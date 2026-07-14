"""Tests for block-partial-typecheck.py (PreToolUse(Bash) narrowed-pyright guard).

Contract: reads a PreToolUse event JSON on stdin. Exit 2 (with stderr) blocks only
when pyright is given positional paths, the project has a test directory, and none
of those paths covers it. Every other path exits 0.

All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import block_partial_typecheck as B

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "block-partial-typecheck.py"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project laid out with src/ and tests/."""
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    return tmp_path


def run_main(monkeypatch, command, cwd: Path | None = None) -> int:
    payload = {"tool_input": {"command": command}}
    if cwd is not None:
        payload["cwd"] = str(cwd)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return B.main()


# --- allowed: not a narrowed check -----------------------------------------


def test_unrelated_command_passes(monkeypatch, project):
    assert run_main(monkeypatch, "ls -la && echo done", project) == 0


def test_bare_pyright_passes(monkeypatch, project):
    """No paths: pyright uses its config's include list, i.e. the whole project."""
    assert run_main(monkeypatch, "pyright", project) == 0


def test_bare_pyright_with_flags_passes(monkeypatch, project):
    assert run_main(monkeypatch, "pyright --outputjson", project) == 0


def test_version_passes(monkeypatch, project):
    assert run_main(monkeypatch, "pyright --version", project) == 0


def test_paths_covering_tests_pass(monkeypatch, project):
    assert run_main(monkeypatch, "pyright src tests", project) == 0


def test_dot_covers_everything(monkeypatch, project):
    assert run_main(monkeypatch, "pyright .", project) == 0


def test_checking_only_tests_passes(monkeypatch, project):
    """Naming the tests is explicit about scope, not a false 'all clean'."""
    assert run_main(monkeypatch, "pyright tests", project) == 0


def test_file_inside_tests_passes(monkeypatch, project):
    assert run_main(monkeypatch, "pyright tests/test_x.py", project) == 0


def test_project_without_tests_passes(monkeypatch, tmp_path):
    """Nothing to miss when the project has no test directory."""
    (tmp_path / "src").mkdir()
    assert run_main(monkeypatch, "pyright src", tmp_path) == 0


def test_missing_cwd_passes(monkeypatch):
    assert run_main(monkeypatch, "pyright src") == 0


def test_value_flag_argument_is_not_a_path(monkeypatch, project):
    """`--pythonversion 3.10` must not read 3.10 as a positional path."""
    assert run_main(monkeypatch, "pyright --pythonversion 3.10 tests", project) == 0


def test_word_containing_pyright_passes(monkeypatch, project):
    assert run_main(monkeypatch, "echo pyrightish", project) == 0


def test_unbalanced_quotes_passes(monkeypatch, project):
    assert run_main(monkeypatch, 'pyright "src', project) == 0


def test_pyright_as_another_tools_flag_value_passes(monkeypatch, project):
    """`find -name pyright` names a FILE to look for; it invokes nothing.

    Observed false positive: the guard took the quoted "pyright" for the
    executable and read the rest of find's own arguments as its paths, blocking
    with the nonsense "paths given: 4 2>/dev/null".
    """
    assert run_main(monkeypatch, "find .venv -name 'pyright' -maxdepth 4 2>/dev/null", project) == 0
    assert run_main(monkeypatch, "grep -rn -e pyright src", project) == 0


def test_real_invocation_after_a_flag_value_still_blocks(monkeypatch, project):
    """Skipping a flag-value match must not skip a real run later in the line.

    Returning at the first token spelled "pyright" would let the genuine
    narrowed invocation through unchecked.
    """
    assert run_main(monkeypatch, "find . -name pyright; python -m pyright src", project) == 2


def test_redirect_ends_the_invocation(monkeypatch, project):
    """`2>/dev/null` is a redirection, not a path handed to pyright.

    shlex keeps the fd prefix in one token, so a plain `>` comparison misses it
    and the redirect target gets counted as a positional.
    """
    assert run_main(monkeypatch, "pyright tests 2>/dev/null", project) == 0
    assert B._pyright_positionals("pyright src 2>/dev/null") == ["src"]


# --- blocked: narrowed away from the tests ---------------------------------


def test_src_only_blocks(monkeypatch, project, capsys):
    assert run_main(monkeypatch, "pyright src", project) == 2
    err = capsys.readouterr().err
    assert "BLOCKED" in err
    assert "tests/" in err


def test_src_trailing_slash_blocks(monkeypatch, project):
    assert run_main(monkeypatch, "pyright src/", project) == 2


def test_individual_files_block(monkeypatch, project, capsys):
    """The exact shape that hid 7 strict errors in a new test file."""
    assert run_main(monkeypatch, "pyright src/pkg/a.py src/pkg/b.py", project) == 2
    assert "src/pkg/a.py src/pkg/b.py" in capsys.readouterr().err


def test_blocks_via_uv_run(monkeypatch, project):
    assert run_main(monkeypatch, "uv run pyright src", project) == 2


def test_blocks_with_flags_before_paths(monkeypatch, project):
    assert run_main(monkeypatch, "pyright --outputjson --pythonversion 3.10 src", project) == 2


def test_message_names_the_fix(monkeypatch, project, capsys):
    run_main(monkeypatch, "pyright src", project)
    err = capsys.readouterr().err
    assert "pyright src tests" in err


def test_test_dir_named_test_is_honoured(monkeypatch, tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "test").mkdir()
    assert run_main(monkeypatch, "pyright src", tmp_path) == 2


# --- contract ---------------------------------------------------------------


def test_broken_stdin_never_wedges_a_turn(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert B.main() == 0


def test_script_exists_and_is_ascii():
    text = SCRIPT.read_text(encoding="utf-8")
    text.encode("ascii")  # raises if a tell slipped in
    assert text.startswith("#!/usr/bin/env python3")
