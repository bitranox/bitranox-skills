"""Tests for venv-guard.py. ASCII only.

The load-bearing property is that it stays SILENT in normal work: a guard that fires on ordinary
commands gets ignored, and then it is not a guard.
"""
import json
import os
import shlex
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
                "env FOO=1 uv run pyright",
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
                          capture_output=True, text=True, env=e, check=False)


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
        r = subprocess.run([sys.executable, str(HOOK)], input=bad, capture_output=True, text=True,
                           check=False)
        assert r.returncode == 0, bad


# ---- data is not a command ---------------------------------------------------------------------

def _q(path):
    """``path`` as bash reads it: a bare Windows path loses its backslashes to bash's escapes."""
    return shlex.quote(str(path))


def _other(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    return str(other)


def test_a_heredoc_body_naming_a_tool_is_data(tmp_path):
    """A doc written through a heredoc that mentions `pytest -q` runs no pytest."""
    proj = _project(tmp_path)
    cmd = "cat > doc.md <<'EOF'\npytest -q runs the suite\nEOF"
    assert G.build_notice(cmd, proj, _other(tmp_path)) is None


def test_a_real_run_after_a_heredoc_still_fires(tmp_path):
    proj = _project(tmp_path)
    cmd = "cat > doc.md <<'EOF'\nprose\nEOF\npytest -q"
    assert G.build_notice(cmd, proj, _other(tmp_path))


def test_a_quoted_separator_does_not_start_a_statement(tmp_path):
    """`;` inside quotes is data, so the text after it is not a command in its own right."""
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ('git commit -m "fix; pytest now passes"', "echo 'x; pytest -q'"):
        assert G.build_notice(cmd, proj, other) is None, cmd


def test_an_unquoted_separator_still_starts_a_statement(tmp_path):
    proj = _project(tmp_path)
    assert G.build_notice("echo x; pytest -q", proj, _other(tmp_path))


# ---- a per-statement override is honoured -------------------------------------------------------

def test_the_hooks_own_remediation_is_silent(tmp_path):
    """The notice tells the reader to run `env -u VIRTUAL_ENV uv run ...`; firing on exactly that
    command told them their fix was wrong."""
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("env -u VIRTUAL_ENV uv run pytest -q",
                "env --unset=VIRTUAL_ENV pytest",
                "env --unset VIRTUAL_ENV pytest",
                "env -uVIRTUAL_ENV pytest",
                "env -i pytest",
                'env -u VIRTUAL_ENV BMK_PYTHON_CMD="x/.venv/bin/python" make test'):
        assert G.build_notice(cmd, proj, other) is None, cmd


def test_an_explicit_virtual_env_pointing_at_the_project_venv_is_silent(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in (f"VIRTUAL_ENV={_q(proj / '.venv')} pytest -q",
                "VIRTUAL_ENV=.venv pytest -q",
                f"env VIRTUAL_ENV={_q(proj / '.venv')} pytest"):
        assert G.build_notice(cmd, proj, other) is None, cmd


def test_an_unset_earlier_in_the_command_carries_forward(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("unset VIRTUAL_ENV; pytest", "unset VIRTUAL_ENV && make test",
                f"export VIRTUAL_ENV={_q(proj / '.venv')} && pytest"):
        assert G.build_notice(cmd, proj, other) is None, cmd


def test_an_override_reaches_only_its_own_statement(tmp_path):
    """The direction the fix must not change: `env -u` on ANOTHER statement unsets nothing here."""
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("env -u VIRTUAL_ENV true && pytest",
                "env -u OTHER_VAR pytest",
                f"VIRTUAL_ENV={_q(proj / '.venv')} true; pytest"):
        assert G.build_notice(cmd, proj, other), cmd


def test_an_explicit_foreign_virtual_env_fires_even_with_none_ambient(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    notice = G.build_notice(f"VIRTUAL_ENV={_q(other)} pytest", proj, None)
    assert notice and other in notice


def test_an_unexpanded_override_is_taken_as_deliberate(tmp_path):
    """`VIRTUAL_ENV=$PWD/.venv` cannot be resolved without running the shell; guessing a mismatch
    would fire on a command that is very likely correct."""
    proj = _project(tmp_path)
    assert G.build_notice("VIRTUAL_ENV=$PWD/.venv pytest", proj, _other(tmp_path)) is None


# ---- make behind a launcher --------------------------------------------------------------------

def test_make_behind_a_launcher_fires(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("sudo make test", "time make test", "timeout 600 make test", "nice make test",
                "nice -n 19 make test", "uv run make test"):
        assert G.build_notice(cmd, proj, other), cmd


def test_make_behind_a_launcher_still_needs_a_pipeline_target(tmp_path):
    proj = _project(tmp_path)
    assert G.build_notice("sudo make docs", proj, _other(tmp_path)) is None


# ---- a path that already pins the interpreter ---------------------------------------------------

def test_a_tool_inside_the_project_venv_is_already_pinned(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("./.venv/bin/pytest -q", ".venv/bin/python -m pytest",
                f"{_q(proj / '.venv' / 'bin' / 'ruff')} check ."):
        assert G.build_notice(cmd, proj, other) is None, cmd


def test_a_tool_path_outside_the_project_venv_still_fires(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    assert G.build_notice(f"{_q(other + '/bin/pytest')} -q", proj, other)


def test_pyright_is_not_pinned_by_its_install_path(tmp_path):
    """pyright takes its environment from config and the python on PATH, never from where the
    pyright wrapper was installed, so `.venv/bin/pyright` under a foreign venv still misreads."""
    proj = _project(tmp_path)
    assert G.build_notice("./.venv/bin/pyright", proj, _other(tmp_path))


# ---- PowerShell remediation --------------------------------------------------------------------

def _snippets(notice):
    return [part for i, part in enumerate(notice.split("`")) if i % 2]


def test_powershell_gets_powershell_remediation(tmp_path):
    proj = _project(tmp_path)
    notice = G.build_notice("pytest -q", proj, _other(tmp_path), tool_name="PowerShell")
    assert notice and "Remove-Item Env:VIRTUAL_ENV" in notice
    assert "env -u" not in notice


def test_bash_keeps_its_posix_remediation(tmp_path):
    proj = _project(tmp_path)
    notice = G.build_notice("pytest -q", proj, _other(tmp_path), tool_name="Bash")
    assert notice and "env -u VIRTUAL_ENV" in notice and "Remove-Item" not in notice


def test_every_remediation_the_notice_names_is_silent_when_run(tmp_path):
    """Run the route the message names: each suggested command, filled in, must not fire again."""
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for tool in ("Bash", "PowerShell"):
        notice = G.build_notice("pytest -q", proj, other, tool_name=tool)
        snippets = _snippets(notice)
        assert len(snippets) == 2, (tool, snippets)
        for snippet in snippets:
            filled = snippet.replace("uv run ...", "uv run pytest -q").replace("make ...", "make test")
            assert G.build_notice(filled, proj, other, tool_name=tool) is None, (tool, filled)


def test_powershell_session_env_changes_are_honoured(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    for cmd in ("Remove-Item Env:VIRTUAL_ENV; pytest", "Remove-Item -Path Env:\\VIRTUAL_ENV; pytest",
                "$env:VIRTUAL_ENV = ''; pytest", "$env:VIRTUAL_ENV = $null; pytest"):
        assert G.build_notice(cmd, proj, other, tool_name="PowerShell") is None, cmd
    assert G.build_notice("Remove-Item Env:OTHER; pytest", proj, other, tool_name="PowerShell")


def test_hook_reads_tool_name_for_the_remediation(tmp_path):
    proj = _project(tmp_path)
    other = _other(tmp_path)
    r = _run({"tool_name": "PowerShell", "tool_input": {"command": "pytest"}, "cwd": str(proj)},
             env={"VIRTUAL_ENV": other})
    assert r.returncode == 0
    assert "Remove-Item Env:VIRTUAL_ENV" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


# ---- the interpreter hint, both layouts ---------------------------------------------------------

def test_interpreter_hint_posix_layout(tmp_path):
    assert G._interpreter_hint(tmp_path / ".venv", windows=False) == str(tmp_path / ".venv" / "bin/python")


def test_interpreter_hint_windows_layout(tmp_path):
    hint = G._interpreter_hint(tmp_path / ".venv", windows=True)
    assert hint == str(tmp_path / ".venv" / "Scripts/python.exe")


def test_interpreter_hint_defaults_to_this_platform(tmp_path):
    expected = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    assert G._interpreter_hint(tmp_path / ".venv") == str(tmp_path / ".venv" / expected)
