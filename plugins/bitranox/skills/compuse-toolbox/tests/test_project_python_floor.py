"""A tool launched with the PROJECT's interpreter keeps the floor of the projects it runs in.

The plugin's own floor is 3.14, but `LAUNCH_WITH = "project-python"` means the tool runs as
`<project python> -m pytest`, and that interpreter belongs to whichever project is under test.
So the tool and every sibling module it imports must still load on 3.10: parse at that grammar,
keep annotations lazy with the __future__ import (3.10-3.13 evaluate them at def time), and use
no stdlib name newer than 3.10.
"""

import ast
import re
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
FLOOR = (3, 10)
_LAUNCH = re.compile(r'^LAUNCH_WITH = "project-python"$', re.M)
_HEADER_FLOOR = re.compile(r'^# requires-python = ">=(\d+)\.(\d+)"$', re.M)
# stdlib names that arrived after 3.10, the ones an upgrade pass reaches for
_NEWER = re.compile(r"^\s*import tomllib\b|\bdatetime\.UTC\b|from datetime import [^\n]*\bUTC\b", re.M)


def _sibling_imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
    return {n for n in names if (SCRIPTS / f"{n}.py").is_file()}


def _closure() -> list[Path]:
    todo = [p for p in sorted(SCRIPTS.glob("*.py")) if _LAUNCH.search(p.read_text(encoding="utf-8"))]
    seen: dict[str, Path] = {}
    while todo:
        path = todo.pop()
        if path.stem in seen:
            continue
        seen[path.stem] = path
        todo.extend(SCRIPTS / f"{n}.py" for n in _sibling_imports(path))
    return sorted(seen.values())


def test_the_closure_is_not_empty():
    names = {p.stem for p in _closure()}
    assert {"mutation_arm", "anchor_edit", "_cli_envelope"} <= names


@pytest.mark.parametrize("path", _closure(), ids=lambda p: p.name)
def test_a_project_python_module_still_loads_on_3_10(path):
    text = path.read_text(encoding="utf-8")
    ast.parse(text, feature_version=FLOOR)
    assert "from __future__ import annotations\n" in text
    assert not _NEWER.search(text), _NEWER.search(text).group(0)
    header = _HEADER_FLOOR.search(text)
    assert header is None or (int(header.group(1)), int(header.group(2))) <= FLOOR
