#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) hook: auto-realign markdown tables after an edit.

Formatter-on-save for markdown tables (Mode A). When a markdown file is written or edited, reuse the
md-table-formatting skill's `reformat_tables.reformat_file()` to realign its tables in place, so a
table can never ship misaligned and the "reformat after editing a table" rule cannot be skipped.

Silent by design: it just fixes the file. `reformat_tables` is safe-by-design (it bails on tables
with inconsistent column counts and skips non-markdown fenced code blocks), so a normal edit is left
alone. Pure standard library plus the shipped reformat script. Every failure path exits 0, so a
broken hook never wedges a turn.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

_MD_SUFFIXES = (".md", ".markdown", ".mdown", ".mkd")


def _reformat_file_fn():
    """Import reformat_file() from the md-table-formatting skill (resolved from the plugin root)."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    base = Path(root) if root else Path(__file__).resolve().parent.parent
    script = base / "skills" / "md-table-formatting" / "reformat_tables.py"
    spec = importlib.util.spec_from_file_location("_bx_reformat_tables", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.reformat_file


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if not path or not path.lower().endswith(_MD_SUFFIXES):
        return 0  # not a markdown file -> nothing to align
    if not Path(path).is_file():
        return 0
    try:
        _reformat_file_fn()(path)  # in-place realign; bails safely on malformed tables
    except Exception:  # noqa: BLE001 - reformat/import failure must never wedge a turn
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
