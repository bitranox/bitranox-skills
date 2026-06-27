"""Tests for reformat-md-tables.py (auto-realign markdown tables on edit, Mode A).

Drives main() with a PostToolUse event JSON on stdin pointing at a temp file. Uses the real
reformat_tables.py shipped in the docs-md-table-formatting skill (resolved via the hook's own location).
All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import reformat_md_tables as H

MISALIGNED = "# t\n\n| A | Bee |\n|---|---|\n| x | y |\n| longer | z |\n"


def run(monkeypatch, path):
    # Resolve the reformat script against THIS repo (the hook's own location), not the ambient
    # CLAUDE_PLUGIN_ROOT (which during a commit points at the installed plugin cache - a different,
    # possibly older version that may not have the docs-md-table-formatting skill dir).
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"file_path": str(path)}})))
    return H.main()


def test_realigns_markdown_table_and_is_idempotent(tmp_path, monkeypatch):
    f = tmp_path / "doc.md"
    f.write_text(MISALIGNED, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    out1 = f.read_text(encoding="utf-8")
    assert out1 != MISALIGNED            # it actually reformatted
    assert "| longer | z   |" in out1    # padded to the widest cell per column
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == out1  # idempotent (no oscillation)


def test_skips_non_markdown(tmp_path, monkeypatch):
    f = tmp_path / "code.py"
    original = "x = 1  |  y = 2\n"
    f.write_text(original, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == original


def test_markdown_without_tables_unchanged(tmp_path, monkeypatch):
    f = tmp_path / "plain.md"
    original = "# Title\n\nJust prose, no tables here.\n"
    f.write_text(original, encoding="utf-8")
    assert run(monkeypatch, f) == 0
    assert f.read_text(encoding="utf-8") == original


def test_missing_file_returns_zero(tmp_path, monkeypatch):
    assert run(monkeypatch, tmp_path / "nope.md") == 0


def test_missing_file_path_returns_zero(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {}})))
    assert H.main() == 0


def test_malformed_stdin_returns_zero(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert H.main() == 0
