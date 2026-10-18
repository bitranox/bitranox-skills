"""Tests for subagent-brief-pyright-nudge.py (PreToolUse on Task|Agent).

Contract: a dispatch whose brief tells the subagent to RUN pyright in command shape, and carries no
interpreter pin anywhere, gets hookSpecificOutput.additionalContext naming the pin (exit 0, NO
permissionDecision). A brief that only TALKS about pyright, pins it, or runs it through `uv run`
(which puts the venv on PATH) gets silence, and so does every non-subagent tool and bad event.

The positive and negative shapes below are taken from real briefs in the transcript corpus; the
replay that measured the hook's firing rate is described in the hook's own docstring.
"""

import io
import json
import sys

import pytest

import subagent_brief_pyright_nudge as N


def run_main(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return N.main()


@pytest.mark.parametrize("prompt", [
    "Gate: `.venv/bin/ruff check .` and `.venv/bin/pyright` (no path argument).",
    "Run `cd $REPO && .venv/bin/python -m pyright` and report filesAnalyzed.",
    "types: `.venv-win/bin/pyright src/pkg/x.py` must be clean",
    "Use .venv\\Scripts\\pyright.exe on Windows.",
    "2. `uvx pyright --pythonversion 3.11 skills/x/scripts` - must pass.",
    "then npx pyright on the changed files",
    "ruff check . && pyright --outputjson",
    "Then run\n    pyright\nfrom the repo root.",
    "$ pyright src",
    "whole-project `pyright`, `lint-imports` (11 kept, 0 broken)",
    "PYTHONPATH=$PWD/src $PY -m pyright tests/<file>",
], ids=lambda p: p[:40])
def test_command_shaped_unpinned_pyright_fires(prompt):
    assert N.unpinned_pyright_snippet(prompt)
    message = N.assess("Agent", {"prompt": prompt})
    assert message and "--pythonpath" in message


@pytest.mark.parametrize("prompt", [
    "Keep it typed (no dicts; pyright strict).",
    "pyright caught it, 114 tests did not.",
    "Add no `# type: ignore`, `# noqa`, `pyright: ignore` comments.",
    "Report the pyright/lint-imports/ruff outputs.",
    "Claims: full suite 4920 passed; pyright 0; ruff clean.",
    "Python is pyright-strict and ruff-checked.",
    "Cross-platform (each OS branch; pyright with --pythonplatform Windows).",
    "Write a pyrightconfig.json in the scratch dir.",
], ids=lambda p: p[:40])
def test_prose_about_pyright_is_silent(prompt):
    assert N.unpinned_pyright_snippet(prompt) is None


@pytest.mark.parametrize("prompt", [
    'Gate: `.venv/bin/pyright --pythonpath "$PWD/.venv/bin/python"`.',
    "Run `.venv/bin/python -m pyright --pythonpath=.venv/bin/python src`.",
    "`.venv/bin/pyright` - the config sets [tool.pyright] venvPath and venv.",
    "Run `.venv/bin/pyright` on the tests; for src use --venvpath . --venv .venv",
], ids=lambda p: p[:40])
def test_a_pin_anywhere_in_the_brief_silences_it(prompt):
    assert N.unpinned_pyright_snippet(prompt) is None


def test_uv_run_pyright_is_not_unpinned():
    # uv run puts the project venv first on PATH, where pyright finds its python: measured
    # 0 errors against bare .venv/bin/pyright's 3904 on the same 235 files.
    assert N.unpinned_pyright_snippet("Then `uv run pyright --outputjson` (0 errors).") is None
    assert N.unpinned_pyright_snippet("uv run --frozen pyright src") is None


def test_snippet_shows_the_line_it_means():
    snippet = N.unpinned_pyright_snippet("x" * 200 + " then `.venv/bin/pyright src` " + "y" * 200)
    assert ".venv/bin/pyright src" in snippet
    assert len(snippet) < 160


@pytest.mark.parametrize("tool", ["Bash", "Edit", "Write", None, 3])
def test_non_subagent_tools_are_silent(tool):
    assert N.assess(tool, {"prompt": "run `.venv/bin/pyright`"}) is None


@pytest.mark.parametrize("tool_input", [None, "x", {}, {"prompt": None}, {"prompt": 7}, {"prompt": ""}])
def test_malformed_input_is_silent(tool_input):
    assert N.assess("Agent", tool_input) is None


def test_main_emits_non_blocking_additional_context(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"prompt": "run `.venv/bin/pyright`"}})
    assert rc == 0
    hso = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "--pythonpath" in hso["additionalContext"]
    assert "permissionDecision" not in hso


def test_main_is_silent_on_a_clean_brief(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Agent", "tool_input": {"prompt": "run `uv run pyright`"}})
    assert rc == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", "null"])
def test_main_fails_open_on_bad_stdin(monkeypatch, capsys, stdin):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    assert N.main() == 0
    assert capsys.readouterr().out == ""


def test_advice_is_ascii():
    message = N.assess("Agent", {"prompt": "run `.venv/bin/pyright`"})
    assert message.isascii()
