"""The dream-tree scripts run under `python -OO`, which strips every docstring.

Each built its argument parser's description from `__doc__.splitlines()[0]`; under -OO `__doc__` is
None, so every invocation, `--help` included, died with AttributeError before parsing an argument.
Each test runs the real script in a child interpreter with -OO: once with --help, once with a real
subcommand over a small tree.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import memory_engine as ME
import topic_store
import uuid_store as us

SKILL_DIR = Path(__file__).resolve().parent.parent


def _tree(tmp_path: Path) -> Path:
    """A one-level tree with two facts, rooted below its own CLAUDE.md."""
    root = tmp_path / "tree"
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    ME.add_or_update_entry(str(root), "Alpha rule", "When alpha, do alpha.", body="Alpha prose.",
                           slug="alpha-rule")
    ME.add_or_update_entry(str(root), "Beta rule", "When beta, do beta.", body="Beta prose.",
                           slug="beta-rule")
    return root


def _run_oo(tmp_path: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run `script` under -OO with a throwaway HOME, so nothing it writes lands in a real one."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
               CLAUDE_CONFIG_DIR=str(home / ".claude"), PYTHONUTF8="1")
    return subprocess.run([sys.executable, "-OO", str(SKILL_DIR / script), *args],
                          capture_output=True, encoding="utf-8", env=env, cwd=str(tmp_path))


@pytest.mark.parametrize("script", ["dedup_scan.py", "factedit.py", "store_manifest.py",
                                    "topic_tagging.py"])
def test_help_works_under_oo(tmp_path: Path, script: str) -> None:
    r = _run_oo(tmp_path, script, "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: %s" % script), r.stdout
    assert "AttributeError" not in r.stderr


def test_dedup_scan_runs_under_oo(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    r = _run_oo(tmp_path, "dedup_scan.py", "--from", str(root), "--json")
    assert r.returncode in (0, 1), r.stderr
    envelope = json.loads(r.stdout)
    assert envelope["command"] == "dedup_scan", envelope


def test_factedit_show_runs_under_oo(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    r = _run_oo(tmp_path, "factedit.py", "show", "--slug", "alpha-rule", "--from", str(root))
    assert r.returncode == 0, r.stderr
    assert "When alpha, do alpha." in r.stdout


def test_store_manifest_backup_and_verify_run_under_oo(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    out = tmp_path / "backup"
    r = _run_oo(tmp_path, "store_manifest.py", "backup", "--from", str(root), "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert (out / "manifest.json").is_file()
    r = _run_oo(tmp_path, "store_manifest.py", "verify", "--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr


def test_topic_tagging_items_runs_under_oo(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    topic_store.save_list(root, {"python": "Python code and its tooling"}, "jev")
    out = tmp_path / "items.jsonl"
    r = _run_oo(tmp_path, "topic_tagging.py", "items", "--from", str(root), "--facts-at",
                str(root), "--out", str(out))
    assert r.returncode == 0, r.stderr
    assert "alpha-rule" in out.read_text(encoding="utf-8")


def test_dream_state_help_prints_its_usage_not_none_under_oo(tmp_path: Path) -> None:
    """dream_state's --help printed `__doc__` before its usage: under -OO the first line was
    the word None."""
    r = _run_oo(tmp_path, "dream_state.py", "--help")
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("usage: dream_state.py"), r.stdout
    assert "None" not in r.stdout.splitlines()[0]
