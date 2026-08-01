"""Tests for venv-guard.py. ASCII only.

The load-bearing property is that it stays SILENT in normal work: a guard that fires on ordinary
commands gets ignored, and then it is not a guard.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import venv_guard as G

HOOK = Path(__file__).resolve().parent.parent / "venv-guard.py"


def _project(tmp_path, with_venv=True):
    proj = tmp_path / "proj"
    proj.mkdir()
    if with_venv:
        (proj / ".venv").mkdir()
    return proj


# ---- when it must fire -------------------------------------------------------------------------

def test_fires_when_ambient_venv_differs_from_the_project_venv(tmp_path):
    proj = _project(tmp_path)
    other = tmp_path / "other-venv"
    other.mkdir()
    notice = G.build_notice("pytest -q", proj, str(other))
    assert notice and "WRONG VENV" in notice
    assert str(other) in notice and str(proj / ".venv") in notice


def test_names_the_symptoms_so_the_failure_is_recognisable(tmp_path):
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    notice = G.build_notice("make test", proj, str(other))
    assert "ModuleNotFoundError" in notice and "pip-audit" in notice
    assert "env -u VIRTUAL_ENV" in notice


def test_fires_for_a_gate_run_hidden_behind_a_separator(tmp_path):
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    assert G.build_notice("cd sub && pytest", proj, str(other))


# ---- when it must stay silent ------------------------------------------------------------------

def test_silent_when_the_ambient_venv_is_the_projects_own(tmp_path):
    proj = _project(tmp_path)
    assert G.build_notice("pytest", proj, str(proj / ".venv")) is None


def test_silent_when_the_venv_matches_through_a_symlink(tmp_path):
    """The same venv reached by two paths is not a mismatch."""
    proj = _project(tmp_path)
    link = tmp_path / "link-to-venv"
    try:
        link.symlink_to(proj / ".venv", target_is_directory=True)
    except (OSError, NotImplementedError):
        return                                        # unprivileged Windows cannot symlink; skip
    assert G.build_notice("pytest", proj, str(link)) is None


def test_silent_when_no_virtual_env_is_set(tmp_path):
    proj = _project(tmp_path)
    assert G.build_notice("pytest", proj, None) is None
    assert G.build_notice("pytest", proj, "") is None


def test_silent_when_the_project_has_no_venv(tmp_path):
    proj = _project(tmp_path, with_venv=False)
    assert G.build_notice("pytest", proj, str(tmp_path / "elsewhere")) is None


def test_silent_for_a_command_that_is_not_a_gate_run(tmp_path):
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    for cmd in ("ls -la", "git status", "make docs"):
        assert G.build_notice(cmd, proj, str(other)) is None, cmd


def test_silent_when_a_tool_name_is_only_MENTIONED(tmp_path):
    """The tool must be in COMMAND position, not merely present as a word.

    An earlier version matched the token anywhere, so `echo pytest is great` and a commit message
    naming a test file both fired. A guard that goes off on prose about the thing it guards is the
    failure that gets guards ignored. Caught by a side-by-side probe, not by these unit tests - the
    original case here used a hyphenated token that could never have matched.
    """
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    for cmd in ("echo pytest is great",
                'git commit -m "fix pytest config"',
                "grep -rn pytest docs/",
                "cat notes-about-ruff.md"):
        assert G.build_notice(cmd, proj, str(other)) is None, cmd


def test_still_fires_through_a_launcher(tmp_path):
    """Command position must not mean literally token zero: launchers stand in front."""
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    for cmd in ("uv run pytest -q",
                "python -m pytest",
                "env -u VIRTUAL_ENV uv run pyright",
                "PYTHONPATH=. pytest",
                "timeout 300 pytest"):
        assert G.build_notice(cmd, proj, str(other)), cmd


def test_make_fires_only_on_pipeline_targets(tmp_path):
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    assert G.build_notice("make test", proj, str(other))
    assert G.build_notice("make docs", proj, str(other)) is None


def test_looks_like_a_gate_run_matches_a_path_qualified_tool():
    assert G.looks_like_a_gate_run("./.venv/bin/pytest -q")
    assert G.looks_like_a_gate_run("echo hello") is False


# ---- the hook contract -------------------------------------------------------------------------

def _run(payload, env=None):
    e = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=e)


def test_hook_emits_additional_context_not_bare_stderr(tmp_path):
    """additionalContext is what reaches the model; an exit-0 hook's stderr does not."""
    proj = _project(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    r = _run({"tool_input": {"command": "pytest"}, "cwd": str(proj)},
             env={"VIRTUAL_ENV": str(other)})
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "WRONG VENV" in payload["hookSpecificOutput"]["additionalContext"]


def test_hook_is_silent_and_exits_zero_on_a_clean_run(tmp_path):
    proj = _project(tmp_path)
    r = _run({"tool_input": {"command": "pytest"}, "cwd": str(proj)},
             env={"VIRTUAL_ENV": str(proj / ".venv")})
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_hook_never_wedges_a_turn_on_bad_input():
    for bad in ("", "not json at all", "[]"):
        r = subprocess.run([sys.executable, str(HOOK)], input=bad, capture_output=True, text=True)
        assert r.returncode == 0, bad
