"""Refuse a Python module that defines the same top-level function or class name twice.

A second module-level ``def _helper`` silently replaces the first for every caller in the
module, including the callers written against the first: Python binds the name at import, and
the call resolves it at run time. ruff's F811 does not flag a redefinition of a name already USED
before the second def, so no lint gate sees it. In this repo it made a grandchild-kill test call a
POSIX-only ``_gone`` on Windows, and two helper pairs in test_repo_gate.py ran tests with the
other helper's git behaviour while staying green.

Scope of the check:

* Only statements directly in the module body count. A definition inside a module-level ``if``,
  ``try`` or ``with`` block is not counted, because a platform branch
  (``if sys.platform == "win32": def x ... else: def x``) and an ``ImportError`` fallback define
  one name on each path on purpose.
* A definition decorated with ``typing.overload`` is a signature stub, not a replacement, so a
  name whose earlier definitions are all overloads is not a duplicate.
* Every ``.py`` under ``plugins/`` is walked, tests included; ``__pycache__`` and virtualenv
  directories are skipped. A file that does not parse is a failure, never a skip.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

PLUGINS_DIR = Path(__file__).resolve().parents[3]
_SKIPPED_DIRS = ("__pycache__", "node_modules")
_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _is_overload(node: ast.AST) -> bool:
    for deco in getattr(node, "decorator_list", ()):
        target = deco.func if isinstance(deco, ast.Call) else deco
        if isinstance(target, ast.Name) and target.id == "overload":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "overload":
            return True
    return False


def duplicate_top_level_names(source: str, filename: str = "<src>") -> list[tuple[str, int, int]]:
    """Return ``(name, earlier_line, later_line)`` for each top-level def/class redefined.

    Args:
        source: The module's source text.
        filename: Used only in a SyntaxError raised for unparsable source.

    Returns:
        One tuple per redefinition, in source order; empty when every name is defined once.

    Examples:
        >>> duplicate_top_level_names("def a(): pass\\ndef a(): pass\\n")
        [('a', 1, 2)]
        >>> duplicate_top_level_names("import sys\\nif sys.platform == 'x':\\n    def a(): pass\\n"
        ...                           "else:\\n    def a(): pass\\n")
        []
    """
    seen: dict[str, ast.AST] = {}
    found = []
    for node in ast.parse(source, filename=filename).body:
        if not isinstance(node, _DEFS):
            continue
        earlier = seen.get(node.name)
        if earlier is not None and not _is_overload(earlier):
            found.append((node.name, earlier.lineno, node.lineno))
        seen[node.name] = node
    return found


def _python_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _SKIPPED_DIRS and not d.startswith(".venv"))
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield Path(dirpath) / name


def scan(root: Path) -> tuple[int, list[str]]:
    """Walk ``root`` and return (files examined, one message per redefinition)."""
    examined = 0
    problems = []
    for path in _python_files(root):
        examined += 1
        rel = path.relative_to(root).as_posix()
        for name, first, second in duplicate_top_level_names(path.read_text(encoding="utf-8"),
                                                             rel):
            problems.append(f"{rel}:{second}: `{name}` redefines the one at line {first}")
    return examined, problems


def test_no_module_under_plugins_defines_a_top_level_name_twice():
    examined, problems = scan(PLUGINS_DIR)
    print(f"examined {examined} .py files under {PLUGINS_DIR}")
    assert examined > 0, f"no .py file found under {PLUGINS_DIR}: the scan checked nothing"
    assert problems == [], (
        "a later module-level def or class replaces the earlier one for every caller; "
        "give each its own name:\n" + "\n".join(problems))


@pytest.mark.parametrize("source, expected", [
    ("def a(): pass\ndef b(): pass\n", []),
    ("def a(): pass\ndef a(): pass\n", [("a", 1, 2)]),
    ("class A: pass\nclass A: pass\n", [("A", 1, 2)]),
    ("async def a(): pass\ndef a(): pass\n", [("a", 1, 2)]),
    ("def a(): pass\nclass a: pass\n", [("a", 1, 2)]),
    ("def a(): pass\na()\ndef a(): pass\n", [("a", 1, 3)]),       # used in between: F811's gap
    ("def a(): pass\ndef a(): pass\ndef a(): pass\n", [("a", 1, 2), ("a", 2, 3)]),
])
def test_duplicate_top_level_names_flags_a_redefinition(source, expected):
    assert duplicate_top_level_names(source) == expected


@pytest.mark.parametrize("source", [
    # platform branches and import fallbacks define one name on each path on purpose
    "import sys\nif sys.platform == 'win32':\n    def a(): pass\nelse:\n    def a(): pass\n",
    "try:\n    from x import a\nexcept ImportError:\n    def a(): pass\n",
    "try:\n    def a(): pass\nexcept Exception:\n    def a(): pass\n",
    # typing.overload stubs precede the implementation
    "from typing import overload\n@overload\ndef a(x: int) -> int: ...\n"
    "@overload\ndef a(x: str) -> str: ...\ndef a(x): return x\n",
    "import typing\n@typing.overload\ndef a(x: int) -> int: ...\ndef a(x): return x\n",
    # a nested def of the same name is not module level
    "def a():\n    def a(): pass\n    return a\n",
    "class A:\n    def m(self): pass\n    def m(self): pass\n",
])
def test_duplicate_top_level_names_leaves_legitimate_shapes_alone(source):
    assert duplicate_top_level_names(source) == []


def test_scan_reports_a_planted_duplicate_and_counts_the_files(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "clean.py").write_text("def a(): pass\n", encoding="utf-8")
    (tmp_path / "pkg" / "dup.py").write_text("def a(): pass\n\ndef a(): pass\n", encoding="utf-8")
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "skip.py").write_text("def a(): pass\ndef a(): pass\n",
                                                             encoding="utf-8")
    (tmp_path / ".venv-x").mkdir()
    (tmp_path / ".venv-x" / "skip.py").write_text("def a(): pass\ndef a(): pass\n",
                                                  encoding="utf-8")

    examined, problems = scan(tmp_path)

    assert examined == 2
    assert problems == ["pkg/dup.py:3: `a` redefines the one at line 1"]


def test_scan_of_an_empty_tree_examines_nothing(tmp_path):
    # The repo-level test refuses this count, so a moved plugins/ dir cannot pass vacuously.
    assert scan(tmp_path) == (0, [])


def test_scan_fails_loudly_on_a_file_that_does_not_parse(tmp_path):
    (tmp_path / "broken.py").write_text("def (:\n", encoding="utf-8")
    with pytest.raises(SyntaxError):
        scan(tmp_path)
