"""Tests for run-python.sh: loud by default for a CLI caller, fail-open only in explicit hook mode."""

import sys
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SHIM = Path(__file__).resolve().parents[1] / "run-python.sh"

# Every test here launches the shim through bare "bash". On a Windows runner that
# resolves to the WSL stub in System32 rather than Git Bash: with no WSL installed it
# prints a UTF-16 "install from the Store" message and exits 1, so these measure the
# stub, not the shim. The shim itself is Git Bash only by design (see its header).
pytestmark = pytest.mark.skipif(sys.platform == "win32",
                               reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')


def _run(args, strict=False, env_extra=None, bash="bash"):
    env = {k: v for k, v in os.environ.items()
           if k not in ("BITRANOX_RUN_PYTHON_STRICT", "BITRANOX_HOOKS_OFF")}
    if strict:
        env["BITRANOX_RUN_PYTHON_STRICT"] = "1"
    env.update(env_extra or {})
    return subprocess.run([bash, str(SHIM), *args], capture_output=True, text=True, env=env)


def test_missing_script_fails_loud_for_a_cli_caller():
    # a mistyped path in a gate must not read as a clean pass
    r = _run(["/no/such/script.py"])
    assert r.returncode == 3
    assert "not found" in r.stderr


def test_missing_script_fail_open_in_hook_mode():
    r = _run(["--hook", "/no/such/script.py"])
    assert r.returncode == 0                       # hook path: never wedge a turn
    assert "not found" in r.stderr


def test_missing_script_fail_loud_when_strict_in_both_modes():
    assert _run(["/no/such/script.py"], strict=True).returncode == 3
    r = _run(["--hook", "/no/such/script.py"], strict=True)
    assert r.returncode == 3                        # STRICT overrides hook mode
    assert "not found" in r.stderr


def test_no_script_argument_at_all():
    assert _run([]).returncode == 3
    assert _run(["--hook"]).returncode == 0


def test_stderr_is_labelled_with_the_shims_own_name():
    for args in (["/no/such/script.py"], ["--hook", "/no/such/script.py"]):
        err = _run(args).stderr
        assert err.startswith("run-python.sh: "), err
        assert "self-improve" not in err


def test_hook_flag_is_not_passed_to_the_script(tmp_path):
    s = tmp_path / "argv.py"
    s.write_text("import sys; print(sys.argv[1:])\n", encoding="utf-8")
    r = _run(["--hook", str(s), "a", "--hook"])
    assert r.returncode == 0
    assert r.stdout.strip() == "['a', '--hook']"


def _path_without_python(tmp_path):
    """A PATH holding only the tools the shim needs before its interpreter probe."""
    only = tmp_path / "bin"
    only.mkdir()
    (only / "uname").symlink_to(shutil.which("uname"))
    return str(only)


def test_no_interpreter_fails_loud_for_a_cli_caller_and_open_in_hook_mode(tmp_path):
    s = tmp_path / "ok.py"
    s.write_text("print('ok')\n", encoding="utf-8")
    env = {"PATH": _path_without_python(tmp_path)}
    bash = shutil.which("bash")
    cli = _run([str(s)], env_extra=env, bash=bash)
    hook = _run(["--hook", str(s)], env_extra=env, bash=bash)
    assert cli.returncode == 3, cli.stderr
    assert hook.returncode == 0, hook.stderr
    for r in (cli, hook):
        assert "no Python 3 interpreter found" in r.stderr
        assert r.stderr.startswith("run-python.sh: ")
    assert _run(["--hook", str(s)], strict=True, env_extra=env, bash=bash).returncode == 3


def test_a_hook_scripts_own_exit_2_still_passes_through(tmp_path):
    # the shim never invents a 2, but a guard's deliberate block must reach Claude Code intact
    s = tmp_path / "block.py"
    s.write_text("raise SystemExit(2)\n", encoding="utf-8")
    assert _run(["--hook", str(s)]).returncode == 2


def test_successful_script_runs_and_returns_zero(tmp_path):
    s = tmp_path / "ok.py"
    s.write_text("print('ok')\n", encoding="utf-8")
    assert _run([str(s)]).returncode == 0
    assert _run([str(s)], strict=True).returncode == 0   # strict does not change a success


def test_script_error_passes_through_even_without_strict(tmp_path):
    s = tmp_path / "bad.py"
    s.write_text("raise SystemExit(7)\n", encoding="utf-8")
    assert _run([str(s)]).returncode == 7           # python's own non-zero exit is loud already


def test_hooks_off_kill_switch_skips_execution(tmp_path):
    # BITRANOX_HOOKS_OFF=1 silences every hook launched through run-python.sh: exit 0, script NOT run.
    marker = tmp_path / "ran.txt"
    script = tmp_path / "s.py"
    script.write_text("open(%r, 'w').write('x')\n" % str(marker), encoding="utf-8")
    p = _run(["--hook", str(script)], env_extra={"BITRANOX_HOOKS_OFF": "1"})
    assert p.returncode == 0
    assert not marker.exists()                       # the hook body never executed
    assert "BITRANOX_HOOKS_OFF" in (p.stderr or "")  # one loud notice line


def test_hooks_off_does_not_skip_a_deliberate_cli_call(tmp_path):
    # the kill switch silences HOOKS; a CLI call skipped with exit 0 would read as a clean run
    marker = tmp_path / "ran.txt"
    script = tmp_path / "s.py"
    script.write_text("open(%r, 'w').write('x')\n" % str(marker), encoding="utf-8")
    p = _run([str(script)], env_extra={"BITRANOX_HOOKS_OFF": "1"})
    assert p.returncode == 0 and marker.exists()


def test_hooks_off_unset_runs_normally(tmp_path):
    marker = tmp_path / "ran.txt"
    script = tmp_path / "s.py"
    script.write_text("open(%r, 'w').write('x')\n" % str(marker), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "BITRANOX_HOOKS_OFF"}
    p = subprocess.run(["bash", str(SHIM), str(script)], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and marker.exists()
