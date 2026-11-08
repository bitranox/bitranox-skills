"""Tests for claude_paths: the plugin's state follows CLAUDE_CONFIG_DIR, with no fallback.

A/B arms and install tests run Claude Code with CLAUDE_CONFIG_DIR set to a throwaway dir; the
plugin's audit state must follow it, or a sandbox reads and writes the real ~/.claude state.
"""

import ast
from pathlib import Path

import pytest

import claude_paths
import self_improve_signals as sig

PLUGIN = Path(__file__).resolve().parents[2]


@pytest.fixture
def homes(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return home, tmp_path / "arm-config"


def test_unset_resolves_under_home(homes):
    home, _ = homes
    assert claude_paths.config_dir() == home / ".claude"
    assert claude_paths.audit_dir() == home / ".claude" / "self-improve-audit"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_value_counts_as_unset(homes, monkeypatch, value):
    home, _ = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", value)
    assert claude_paths.audit_dir() == home / ".claude" / "self-improve-audit"


def test_set_wins_and_never_falls_back_to_home(homes, monkeypatch):
    # No fallback: the real state must stay invisible to a sandbox even when it exists and the
    # sandbox's own dir does not.
    home, arm = homes
    real = home / ".claude" / "self-improve-audit"
    real.mkdir(parents=True)
    (real / "x.nap-owed").write_text("1", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert claude_paths.audit_dir() == arm / "self-improve-audit"
    assert not claude_paths.audit_dir().exists()


def test_the_shared_audit_dir_follows_the_variable(homes, monkeypatch):
    # self_improve_signals._audit_dir is what most hooks and skill scripts call.
    _, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert sig._audit_dir() == arm / "self-improve-audit"                  # noqa: SLF001
    assert sig.audit_file("/proj/x").parent == arm / "self-improve-audit"
    assert sig.last_dream_file("/proj/x").parent == arm / "self-improve-audit"


def _home_audit_paths(tree):
    """Every `Path.home() / ".claude" / ...` expression in a module's AST."""
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        left = node.left
        if (isinstance(left, ast.Call) and isinstance(left.func, ast.Attribute)
                and left.func.attr == "home" and isinstance(node.right, ast.Constant)
                and node.right.value == ".claude"):
            hits.append(node.lineno)
    return hits


def test_no_shipped_python_builds_the_audit_path_from_home_by_hand():
    # Every site resolves through claude_paths. A new `Path.home() / ".claude"` followed by
    # "self-improve-audit" would reopen the leak, so the whole shipped tree is scanned.
    offenders = []
    scanned = 0
    for py in PLUGIN.rglob("*.py"):
        if "tests" in py.parts or py.name == "claude_paths.py":
            continue
        text = py.read_text(encoding="utf-8")
        scanned += 1
        if "self-improve-audit" not in text:
            continue
        for line in _home_audit_paths(ast.parse(text)):
            src = text.splitlines()[line - 1]
            if "self-improve-audit" in src:
                offenders.append("%s:%d" % (py.relative_to(PLUGIN), line))
    assert scanned > 100, scanned                                     # the scan really ran
    assert offenders == []
