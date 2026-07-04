"""Tests for run-python.sh: the fail-open (hook) vs fail-loud (strict) degrade paths."""

import os
import subprocess
from pathlib import Path

import pytest

SHIM = Path(__file__).resolve().parents[1] / "run-python.sh"


def _run(args, strict=False):
    env = dict(os.environ)
    if strict:
        env["BITRANOX_RUN_PYTHON_STRICT"] = "1"
    else:
        env.pop("BITRANOX_RUN_PYTHON_STRICT", None)
    return subprocess.run(["bash", str(SHIM), *args], capture_output=True, text=True, env=env)


@pytest.mark.skipif(os.name == "nt", reason="bash shim exercised on POSIX CI")
def test_missing_script_fail_open_by_default():
    r = _run(["/no/such/script.py"])
    assert r.returncode == 0                       # hook path: never wedge a turn
    assert "not found" in r.stderr


def test_missing_script_fail_loud_when_strict():
    r = _run(["/no/such/script.py"], strict=True)
    assert r.returncode == 3                        # deliberate call: loud, non-zero
    assert "not found" in r.stderr


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
    env = dict(os.environ, BITRANOX_HOOKS_OFF="1")
    p = subprocess.run(["bash", str(SHIM), str(script)], capture_output=True, text=True, env=env)
    assert p.returncode == 0
    assert not marker.exists()                       # the hook body never executed
    assert "BITRANOX_HOOKS_OFF" in (p.stderr or "")  # one loud notice line


def test_hooks_off_unset_runs_normally(tmp_path):
    marker = tmp_path / "ran.txt"
    script = tmp_path / "s.py"
    script.write_text("open(%r, 'w').write('x')\n" % str(marker), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "BITRANOX_HOOKS_OFF"}
    p = subprocess.run(["bash", str(SHIM), str(script)], capture_output=True, text=True, env=env)
    assert p.returncode == 0 and marker.exists()
