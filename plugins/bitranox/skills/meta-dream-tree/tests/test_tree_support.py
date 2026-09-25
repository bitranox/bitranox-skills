"""Tests for tree_support.py - the engine's anchor, and a stdout that survives cp1252. ASCII only.

The anchor tests use the REAL engine resolver from the plugin's hooks dir, never a stand-in: the
whole point of the module is that the tools agree with the engine, and a copy of the rule would be
a second source of truth.
"""
from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

import tree_support as TS
import uuid_store  # tests/conftest.py puts the plugin's hooks dir on sys.path


def decoy_tree(root: Path) -> Path:
    """The real top (CLAUDE.md + store) with a leftover store lower down the same chain."""
    (root / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    (root / ".claude-memory" / "facts").mkdir(parents=True)
    proj = root / "proj"
    (proj / ".claude-memory" / "facts").mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    return proj


def test_a_decoy_store_lower_down_the_chain_does_not_win(tmp_path):
    proj = decoy_tree(tmp_path)
    assert TS.store_anchor(proj, uuid_store.resolve_anchor) == tmp_path.resolve()


def test_without_a_decoy_the_nearest_store_is_the_top(tmp_path):
    """Control: the same call answers the obvious dir when there is only one store."""
    (tmp_path / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    (tmp_path / ".claude-memory").mkdir()
    (tmp_path / "a" / "b").mkdir(parents=True)
    assert TS.store_anchor(tmp_path / "a" / "b", uuid_store.resolve_anchor) == tmp_path.resolve()


def test_it_agrees_with_the_engine_tree_top(tmp_path):
    proj = decoy_tree(tmp_path)
    engine_top = Path(uuid_store.resolve_anchor(str(proj)))
    assert TS.store_anchor(proj, uuid_store.resolve_anchor) == engine_top.resolve()


def test_with_no_claude_md_anywhere_the_start_is_its_own_anchor(tmp_path):
    """The engine's fallback: a store at the start dir itself, with no CLAUDE.md above it."""
    (tmp_path / ".claude-memory").mkdir()
    assert TS.store_anchor(tmp_path, uuid_store.resolve_anchor) == tmp_path.resolve()


def test_a_nearer_store_without_claude_md_is_not_adopted(tmp_path):
    """A store the engine would not read must not be guessed at: None, not the nearest store."""
    (tmp_path / ".claude-memory").mkdir()
    (tmp_path / "sub").mkdir()
    assert TS.store_anchor(tmp_path / "sub", uuid_store.resolve_anchor) is None


def test_utf8_stdio_turns_a_cp1252_crash_into_replacement(monkeypatch):
    buf = io.BytesIO()
    stream = io.TextIOWrapper(buf, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)
    TS.utf8_stdio()
    print("path 日本")
    stream.flush()
    assert "日本".encode("utf-8") in buf.getvalue()


def test_utf8_stdio_leaves_a_stream_without_reconfigure_alone(monkeypatch):
    class Plain:
        def write(self, s):
            return len(s)

    monkeypatch.setattr(sys, "stdout", Plain())
    TS.utf8_stdio()                                     # must not raise


_SIBLING_USERS = ("dream_state", "dedup_scan", "factedit", "statusrot", "store_manifest")


@pytest.mark.parametrize("stem", _SIBLING_USERS)
def test_a_script_loaded_by_path_from_elsewhere_finds_tree_support(stem, tmp_path):
    """A hook test loads dream_state.py with spec_from_file_location, which does not put the
    script's dir on sys.path the way `python dream_state.py` does. Run that load in an ISOLATED
    interpreter (-I: no PYTHONPATH, no cwd on the path) from a foreign cwd, so this suite's own
    conftest cannot supply the dir the script forgot."""
    script = Path(__file__).resolve().parents[1] / f"{stem}.py"
    loader = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('probe_{stem}', {str(script)!r})\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "sys.modules[spec.name] = mod\n"
        "spec.loader.exec_module(mod)\n"
        "print('loaded')\n"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-c", loader],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "loaded"
