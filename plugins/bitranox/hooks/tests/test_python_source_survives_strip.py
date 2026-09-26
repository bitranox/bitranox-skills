"""No shipped Python file may hold a character that strip_typographic_tells.py rewrites.

The strip tool is the sanctioned repair for the tell-sweep hook, and it rewrites EVERY such
character in a file, string literals included. A raw BOM inside `startswith("<BOM>")` became
`startswith("")`, which is always true, so the code silently dropped the first character of every
file it rewrote; a raw U+2028 inside a string becomes a real newline and a syntax error. Written as
an escape (backslash-u-f-e-f-f) the same string survives the tool untouched, so the rule is simply:
spell these characters as escapes. ASCII only - the characters are built with chr().
"""
from pathlib import Path

import strip_typographic_tells as S

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SKIP_PARTS = {"__pycache__", "node_modules"}


def _shipped_python_files():
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        rel = path.relative_to(PLUGIN_ROOT).parts
        if any(p in _SKIP_PARTS or p.startswith(".venv") for p in rel):
            continue
        yield path


def _offenders(path, root, table):
    text = path.read_text(encoding="utf-8")
    out = []
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        for ch in line:
            if ord(ch) in table:
                out.append("%s:%d U+%04X" % (path.relative_to(root), lineno, ord(ch)))
    return out


def test_the_walk_sees_the_plugin_tree():
    """A walk rooted at the wrong directory finds nothing and passes vacuously."""
    names = {p.name for p in _shipped_python_files()}
    assert "strip_typographic_tells.py" in names and "reformat_tables.py" in names


def test_the_detector_fires_on_a_planted_raw_bom(tmp_path):
    planted = tmp_path / "planted.py"
    planted.write_text('if text.startswith("%s"):\n    pass\n' % chr(0xFEFF), encoding="utf-8")
    table = S._build_table()
    assert _offenders(planted, tmp_path, table) == ["planted.py:1 U+FEFF"]
    escaped = tmp_path / "escaped.py"
    escaped.write_text('if text.startswith("\\ufeff"):\n    pass\n', encoding="utf-8")
    assert _offenders(escaped, tmp_path, table) == []


def test_no_shipped_python_file_holds_a_character_the_strip_tool_rewrites():
    table = S._build_table()
    found = []
    for path in _shipped_python_files():
        found.extend(_offenders(path, PLUGIN_ROOT, table))
    assert found == [], "write these as escapes:\n" + "\n".join(found)
