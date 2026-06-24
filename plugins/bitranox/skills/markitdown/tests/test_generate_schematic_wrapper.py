"""Tests for the generate_schematic.py thin wrapper (stdlib only).

The wrapper's logic lives in main(): it validates the API key, locates the AI
script, builds an argv, and shells out via subprocess.run. We drive main() with
a crafted argv and monkeypatch subprocess.run so nothing is actually executed.
"""

import pytest


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


def test_builds_command_with_defaults(gen_wrapper, monkeypatch):
    out = _run_main(gen_wrapper, ["a flowchart", "-o", "f.png"], monkeypatch)
    cmd = out["cmd"]
    assert cmd[1].endswith("generate_schematic_ai.py")
    assert "a flowchart" in cmd
    assert "-o" in cmd and "f.png" in cmd
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
    out = _run_main(
        gen_wrapper, ["x", "-o", "f.png", "--api-key", "secret-key"], monkeypatch
    )
    assert "secret-key" not in out["cmd"]
    assert out["env"]["OPENROUTER_API_KEY"] == "secret-key"
