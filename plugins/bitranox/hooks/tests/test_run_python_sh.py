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


# ---------------------------------------------------------------------------
# Stub binaries first on PATH stand in for a platform this Linux runner is not: a fake `uname`
# for another shell, a fake `cygpath` for Git Bash, a wrapping `python3` for a file that vanishes
# between the shim's check and the interpreter's open.

def _stub_dir(tmp_path, name, **scripts):
    """A directory holding executable /bin/sh stubs, to be put FIRST on PATH."""
    d = tmp_path / name
    d.mkdir()
    for tool, body in scripts.items():
        f = d / tool
        f.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        f.chmod(0o755)
    return {"PATH": str(d) + os.pathsep + os.environ.get("PATH", "")}


def _marker_script(tmp_path, name="s.py"):
    marker = tmp_path / (name + ".ran")
    s = tmp_path / name
    s.write_text("open(%r, 'w').write('x')\n" % str(marker), encoding="utf-8")
    return s, marker


def _assert_degraded(r, hook, fragment):
    assert r.returncode == (0 if hook else 3), (r.returncode, r.stderr)
    last = r.stderr.splitlines()[-1]               # a failing cygpath may print its own line first
    assert last.startswith("run-python.sh: "), r.stderr
    assert fragment in last, r.stderr


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                    reason="root reads a mode-000 file, so it cannot be made unreadable")
def test_unreadable_script_degrades_and_never_returns_the_block_code(tmp_path):
    s, marker = _marker_script(tmp_path)
    s.chmod(0)
    try:
        _assert_degraded(_run(["--hook", str(s)]), True, str(s))
        _assert_degraded(_run([str(s)]), False, str(s))
        assert _run(["--hook", str(s)], strict=True).returncode == 3
    finally:
        s.chmod(0o644)
    assert not marker.exists()


def test_script_that_vanishes_after_the_check_degrades(tmp_path):
    # the stub deletes the script during the interpreter probe, which runs after the shim's -f check
    real = sys.executable
    for hook in (True, False):
        s, marker = _marker_script(tmp_path, "vanish%d.py" % hook)
        env = _stub_dir(tmp_path, "vbin%d" % hook, python3=(
            'if [ "$1" = "-c" ] && [ -n "$VANISH" ]; then rm -f "$VANISH"; fi\n'
            'exec "%s" "$@"\n' % real))
        env["VANISH"] = str(s)
        r = _run((["--hook"] if hook else []) + [str(s)], env_extra=env)
        _assert_degraded(r, hook, str(s))
        assert not marker.exists()


def test_converted_script_path_python_cannot_open_degrades(tmp_path):
    # the -f check sees the POSIX path; python opens the cygpath result. A conversion python
    # cannot open must degrade like a missing file, never surface python's own exit 2.
    s, marker = _marker_script(tmp_path)
    env = _stub_dir(tmp_path, "cbin", cygpath='printf "C:%s\\n" "$2"\n')
    _assert_degraded(_run(["--hook", str(s)], env_extra=env), True, "C:")
    _assert_degraded(_run([str(s)], env_extra=env), False, "C:")
    assert not marker.exists()


def test_cygpath_converts_only_the_script_path(tmp_path):
    # Stub cygpath prefixes "CYG"; a CYG symlink to / in the cwd makes the converted script path
    # openable, so the run shows both halves: $1 WAS converted, the later arguments were not.
    (tmp_path / "CYG").symlink_to("/")
    log = tmp_path / "cygpath.log"
    env = _stub_dir(tmp_path, "cbin", cygpath='echo "$2" >> "%s"\nprintf "CYG%%s\\n" "$2"\n' % log)
    s = tmp_path / "argv.py"
    s.write_text("import sys; print(repr(__file__)); print(sys.argv[1:])\n", encoding="utf-8")
    r = subprocess.run(["bash", str(SHIM), "--hook", str(s), "/regex/", "/abs/path", "rel/x"],
                       capture_output=True, text=True, cwd=str(tmp_path),
                       env={**os.environ, **env})
    assert r.returncode == 0, r.stderr
    file_line, argv_line = r.stdout.strip().splitlines()
    assert "CYG" in file_line                                  # the script ran from the converted path
    assert argv_line == "['/regex/', '/abs/path', 'rel/x']"    # later arguments untouched
    assert log.read_text(encoding="utf-8").splitlines() == [str(s)]


def test_cygpath_failure_degrades_with_a_labelled_line(tmp_path):
    s, marker = _marker_script(tmp_path)
    env = _stub_dir(tmp_path, "cbin", cygpath='echo "cygpath: boom" >&2\nexit 1\n')
    _assert_degraded(_run(["--hook", str(s)], env_extra=env), True, "cygpath failed")
    _assert_degraded(_run([str(s)], env_extra=env), False, "cygpath failed")
    assert _run(["--hook", str(s)], strict=True, env_extra=env).returncode == 3
    assert not marker.exists()


def test_unexpected_shell_degrades(tmp_path):
    s, marker = _marker_script(tmp_path)
    env = _stub_dir(tmp_path, "ubin", uname="echo FreeBSD\n")
    _assert_degraded(_run(["--hook", str(s)], env_extra=env), True, "unexpected shell 'FreeBSD'")
    _assert_degraded(_run([str(s)], env_extra=env), False, "unexpected shell 'FreeBSD'")
    assert _run(["--hook", str(s)], strict=True, env_extra=env).returncode == 3
    assert not marker.exists()


@pytest.mark.parametrize("kernel", ["CYGWIN_NT-10.0-19045", "MINGW64_NT-10.0-19045", "MSYS_NT-10.0"])
def test_windows_shells_are_accepted(tmp_path, kernel):
    # Git Bash is the supported Windows shell; Cygwin is accepted best-effort
    s, marker = _marker_script(tmp_path)
    env = _stub_dir(tmp_path, "ubin", uname="echo %s\n" % kernel)
    r = _run(["--hook", str(s)], env_extra=env)
    assert r.returncode == 0 and r.stderr == "", r.stderr
    assert marker.exists()


_FIDELITY = '''\
import json, os, pickle, sys
class Probe:
    pass
data = {
    "argv": sys.argv,
    "file": __file__,
    "name": __name__,
    "path0": sys.path[0],
    "stdin": sys.stdin.read(),
    "pickled": type(pickle.loads(pickle.dumps(Probe()))).__name__,
    "leaked": sorted(k for k in os.environ if k.startswith("_BITRANOX")),
}
if __name__ == "__main__":
    print(json.dumps(data))
'''


def test_script_sees_what_a_direct_python_launch_gives_it(tmp_path):
    # the shim must be invisible to the script: same argv, __file__, __name__, sys.path[0], stdin
    import json
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    s = real_dir / "probe.py"
    s.write_text(_FIDELITY, encoding="utf-8")
    link = tmp_path / "link.py"                     # python resolves a symlinked script's dir
    link.symlink_to(s)
    for script in (s, link):
        stdin = '{"hook_event_name": "PreToolUse"}'
        via_shim = subprocess.run(["bash", str(SHIM), "--hook", str(script), "a", "-b", "/c"],
                                  input=stdin, capture_output=True, text=True)
        direct = subprocess.run([sys.executable, str(script), "a", "-b", "/c"],
                                input=stdin, capture_output=True, text=True)
        assert via_shim.returncode == 0, via_shim.stderr
        got, want = json.loads(via_shim.stdout), json.loads(direct.stdout)
        assert got == want
        assert got["stdin"] == stdin and got["name"] == "__main__" and got["leaked"] == []


def test_a_script_traceback_names_the_scripts_file_and_line(tmp_path):
    s = tmp_path / "boom.py"
    s.write_text("x = 1\n\nraise ValueError('kaboom')\n", encoding="utf-8")
    r = _run(["--hook", str(s)])
    assert r.returncode == 1                          # an uncaught exception, as python gives it
    assert 'File "%s", line 3' % s in r.stderr, r.stderr
    assert "ValueError: kaboom" in r.stderr


def test_an_oserror_raised_by_the_script_itself_is_not_mistaken_for_an_unopenable_script(tmp_path):
    s = tmp_path / "oserr.py"
    s.write_text("open('/no/such/file/at/all')\n", encoding="utf-8")
    for args in (["--hook", str(s)], [str(s)]):
        r = _run(args)
        assert r.returncode == 1, r.stderr            # the script's own failure, not the degrade
        assert "FileNotFoundError" in r.stderr
        assert not r.stderr.startswith("run-python.sh: ")


def test_a_script_calling_sys_exit_2_still_blocks(tmp_path):
    s = tmp_path / "block.py"
    s.write_text("import sys\nsys.stderr.write('denied')\nsys.exit(2)\n", encoding="utf-8")
    r = _run(["--hook", str(s)])
    assert r.returncode == 2 and r.stderr == "denied"


def test_the_bootstrap_survives_msys_argument_conversion():
    # Git Bash rewrites a slash-bearing argument handed to a native python.exe unless whitespace
    # comes first (msys2_path_conv.cc convert()); a bootstrap that trips that rule arrives mangled
    # on Windows only, where this suite cannot run the shim.
    text = SHIM.read_text(encoding="utf-8")
    code = text.split("_bootstrap='", 1)[1].split("\n'\n", 1)[0]
    first = next(i for i, ch in enumerate(code) if ch.isspace() or ch in "/\\")
    assert code[first].isspace(), code[:first + 1]
