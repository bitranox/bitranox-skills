"""Tests for the generate_schematic.py thin wrapper (stdlib only).

The wrapper's logic lives in main(): it validates the API key, locates the AI
script, builds an argv, and shells out via subprocess.run. We drive main() with
a crafted argv and monkeypatch subprocess.run so nothing is actually executed.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _run_main(mod, argv, monkeypatch, env_key="env-key"):
    """Invoke wrapper main() capturing the subprocess cmd and exit code."""
    captured = {}

    def fake_run(cmd, check=False, env=None):
        captured["cmd"] = cmd
        captured["env"] = env

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    monkeypatch.setattr(mod.sys, "argv", ["generate_schematic.py"] + argv)
    if env_key is None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENROUTER_API_KEY", env_key)

    with pytest.raises(SystemExit) as exc:
        mod.main()
    captured["exit"] = exc.value.code
    return captured


def test_missing_api_key_exits_1(gen_wrapper, monkeypatch):
    out = _run_main(gen_wrapper, ["a diagram", "-o", "x.png"], monkeypatch, env_key=None)
    assert out["exit"] == 1
    assert "cmd" not in out  # never reached subprocess


def test_builds_command_with_defaults(gen_wrapper, gen_ai, monkeypatch):
    out = _run_main(gen_wrapper, ["a flowchart", "-o", "f.png"], monkeypatch)
    cmd = out["cmd"]
    assert cmd[1].endswith("generate_schematic_ai.py")
    child = gen_ai.build_parser().parse_args(cmd[2:])
    assert (child.prompt, child.output) == ("a flowchart", "f.png")
    # default doc-type is not forwarded, default iterations (2) not forwarded.
    assert "--doc-type" not in cmd
    assert "--iterations" not in cmd
    assert out["exit"] == 0


def test_forwards_doc_type(gen_wrapper, monkeypatch):
    out = _run_main(
        gen_wrapper, ["x", "-o", "f.png", "--doc-type", "journal"], monkeypatch
    )
    cmd = out["cmd"]
    i = cmd.index("--doc-type")
    assert cmd[i + 1] == "journal"


def test_iterations_clamped_to_two(gen_wrapper, monkeypatch):
    # Request 5 iterations; wrapper enforces max 2 and, since clamped value == 2
    # (the default), it is NOT forwarded as a flag.
    out = _run_main(
        gen_wrapper, ["x", "-o", "f.png", "--iterations", "5"], monkeypatch
    )
    assert "--iterations" not in out["cmd"]


def test_iterations_one_forwarded(gen_wrapper, monkeypatch):
    out = _run_main(
        gen_wrapper, ["x", "-o", "f.png", "--iterations", "1"], monkeypatch
    )
    cmd = out["cmd"]
    i = cmd.index("--iterations")
    assert cmd[i + 1] == "1"


def test_api_key_passed_via_env_not_argv(gen_wrapper, monkeypatch):
    # Security: the key must go through the child env, never onto the argv.
    out = _run_main(gen_wrapper, ["x", "-o", "f.png"], monkeypatch, env_key="FAKE-KEY-NOT-REAL")
    assert "FAKE-KEY-NOT-REAL" not in out["cmd"]
    assert out["env"]["OPENROUTER_API_KEY"] == "FAKE-KEY-NOT-REAL"


def test_api_key_flag_is_refused(gen_wrapper, monkeypatch, capsys):
    # A key on the wrapper's own argv sits in the process list for the whole child run.
    out = _run_main(
        gen_wrapper, ["x", "-o", "f.png", "--api-key", "FAKE-KEY-NOT-REAL"], monkeypatch, env_key=None
    )
    err = capsys.readouterr().err
    assert out["exit"] == 2
    assert "cmd" not in out
    assert "OPENROUTER_API_KEY" in err
    assert "FAKE-KEY-NOT-REAL" not in err


def test_help_does_not_offer_a_key_flag(gen_wrapper, monkeypatch, capsys):
    monkeypatch.setattr(gen_wrapper.sys, "argv", ["generate_schematic.py", "--help"])
    with pytest.raises(SystemExit):
        gen_wrapper.main()
    assert "--api-key" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "argv,prompt,output",
    [
        (["block diagram", "-o=-draft.png"], "block diagram", "-draft.png"),
        (["-o", "x.png", "--", "-->"], "-->", "x.png"),
        (["--output=--weird.png", "--", "--help"], "--help", "--weird.png"),
    ],
)
def test_dash_prefixed_values_reach_the_child_intact(gen_wrapper, gen_ai, monkeypatch, argv, prompt, output):
    # Parse the child argv with the AI script's own parser: that is what the child does.
    out = _run_main(gen_wrapper, argv, monkeypatch)
    child = gen_ai.build_parser().parse_args(out["cmd"][2:])
    assert (child.prompt, child.output) == (prompt, output)


def test_launch_error_exits_1(gen_wrapper, monkeypatch):
    def refuse(*args, **kwargs):
        raise OSError("cannot launch")

    monkeypatch.setattr(gen_wrapper.subprocess, "run", refuse)
    monkeypatch.setattr(gen_wrapper.sys, "argv", ["generate_schematic.py", "x", "-o", "f.png"])
    monkeypatch.setenv("OPENROUTER_API_KEY", "FAKE-KEY-NOT-REAL")
    with pytest.raises(SystemExit) as exc:
        gen_wrapper.main()
    assert exc.value.code == 1


def _copy_wrapper(tmp_path, child_source):
    shutil.copy(SCRIPTS_DIR / "generate_schematic.py", tmp_path / "generate_schematic.py")
    if child_source is not None:
        (tmp_path / "generate_schematic_ai.py").write_text(child_source, encoding="utf-8")
    return tmp_path / "generate_schematic.py"


def _run_copy(wrapper, tmp_path, encoding="utf-8"):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["OPENROUTER_API_KEY"] = "FAKE-KEY-NOT-REAL"
    env["PYTHONIOENCODING"] = encoding
    return subprocess.run(
        [sys.executable, str(wrapper), "x", "-o", str(tmp_path / "o.png")],
        capture_output=True, cwd=tmp_path, env=env, timeout=60,
    )


def test_child_exit_code_is_propagated(tmp_path):
    wrapper = _copy_wrapper(tmp_path, "import sys\nsys.exit(3)\n")
    assert _run_copy(wrapper, tmp_path).returncode == 3


def test_missing_ai_script_exits_1(tmp_path):
    wrapper = _copy_wrapper(tmp_path, None)
    proc = _run_copy(wrapper, tmp_path)
    assert proc.returncode == 1
    assert b"not found" in proc.stdout + proc.stderr


def test_cp1252_console_with_non_ascii_path_prints_its_error(tmp_path):
    home = tmp_path / (chr(0x65E5) + chr(0x672C))  # a CJK directory cp1252 cannot encode
    home.mkdir()
    wrapper = _copy_wrapper(home, None)
    proc = _run_copy(wrapper, home, encoding="cp1252")
    assert proc.returncode == 1
    assert b"Traceback" not in proc.stderr
    assert b"not found" in proc.stdout
