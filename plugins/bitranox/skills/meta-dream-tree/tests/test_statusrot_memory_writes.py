"""BITRANOX_MEMORY_WRITES=off: `statusrot clear` refuses before it writes the baseline.

The baseline sits inside the shared store (`<anchor>/.claude-memory/statusrot-baseline.json`), so
an A/B arm that runs `clear` would otherwise record verdicts into the user's store. `clear` is the
only statusrot verb that writes; `scan` reads the baseline and git history only.

Each OFF arm has an ON control on the same input, run as a real process, so a test that passes
because `clear` is broken for another reason cannot pass both.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import self_improve_signals as sig
import statusrot

TOOL = Path(statusrot.__file__).resolve()

SHIPPED = "- [T](mem:alpha) - When you need X, know it is DEPLOYED to the host and shipped."
OTHER = "- [T2](mem:beta) - When you need Y, know it was shipped in the last release."


def _tree(root: Path, *lines: str) -> Path:
    """A tree anchor (CLAUDE.md + .claude-memory store, as the engine requires) with its level."""
    (root / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
    (root / ".claude-memory" / "facts").mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.local.md").write_text(
        "# Memory index\n\n## Memory index\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return root


def _baseline(root: Path) -> Path:
    return root / ".claude-memory" / "statusrot-baseline.json"


def _run(*args: str, off: bool) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != sig.MEMORY_WRITES_ENV}
    if off:
        env[sig.MEMORY_WRITES_ENV] = "off"
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, check=False)


def test_clear_refuses_when_off_and_writes_when_on(tmp_path: Path):
    root = _tree(tmp_path, SHIPPED, OTHER)
    out = _run("clear", "--chain", str(root), "--note", "checked", off=True)
    assert out.returncode == 2, out.stderr
    assert out.stderr.strip().splitlines() == [f"error: {sig.MEMORY_WRITES_OFF_LINE}"]
    assert out.stdout == ""
    assert not _baseline(root).exists(), "the refusal must come before the baseline is written"

    control = _run("clear", "--chain", str(root), "--note", "checked", off=False)
    assert control.returncode == 0, control.stderr
    rec = json.loads(_baseline(root).read_text(encoding="utf-8"))
    assert set(rec["cleared"]) == {"alpha", "beta"}, "control: the same clear records both"


def test_clear_leaves_an_existing_baseline_byte_identical_when_off(tmp_path: Path):
    root = _tree(tmp_path, SHIPPED)
    assert _run("clear", "--chain", str(root), off=False).returncode == 0
    before = _baseline(root).read_bytes()
    _tree(root, SHIPPED, OTHER)  # a new candidate, so an ON clear would rewrite the file

    out = _run("clear", "--chain", str(root), "--slug", "beta", off=True)
    assert out.returncode == 2, out.stderr
    assert _baseline(root).read_bytes() == before

    assert _run("clear", "--chain", str(root), "--slug", "beta", off=False).returncode == 0
    assert _baseline(root).read_bytes() != before, "control: the same clear rewrites it when on"


def test_clear_refusal_under_json_is_the_error_envelope(tmp_path: Path):
    root = _tree(tmp_path, SHIPPED)
    out = _run("clear", "--chain", str(root), "--json", off=True)
    assert out.returncode == 2, out.stderr
    env = json.loads(out.stdout)
    assert env["ok"] is False and env["command"] == "clear"
    assert env["error"] == sig.MEMORY_WRITES_OFF_LINE
    assert not _baseline(root).exists()


def test_scan_still_runs_when_off(tmp_path: Path):
    root = _tree(tmp_path, SHIPPED)
    out = _run("scan", "--chain", str(root), "--json", off=True)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["data"]["distinct_flagged"] == 1
    assert not _baseline(root).exists()
