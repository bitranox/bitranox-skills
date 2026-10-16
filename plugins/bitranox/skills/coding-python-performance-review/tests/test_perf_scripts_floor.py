"""This skill's scripts run under the PROFILED project's interpreter, so they keep its floor.

The plugin's own floor is 3.14, but SKILL.md runs every finder as `"$PYTHON_CMD" <script>` with
the interpreter setup_env.py recorded for the project, which it accepts from MIN_PYTHON up. Each
shipped script must therefore still parse at that grammar and declare no higher floor.
"""

import ast
import re
from pathlib import Path

import pytest

import setup_env as se

SKILL = Path(__file__).resolve().parent.parent
_HEADER_FLOOR = re.compile(r'^# requires-python = ">=(\d+)\.(\d+)"$', re.M)
_NEWER = re.compile(r"^\s*import tomllib\b|\bdatetime\.UTC\b|from datetime import [^\n]*\bUTC\b", re.M)


def test_min_python_is_below_the_plugin_floor():
    assert se.MIN_PYTHON < (3, 14)


@pytest.mark.parametrize("path", sorted(SKILL.glob("*.py")), ids=lambda p: p.name)
def test_a_script_still_loads_on_the_project_floor(path):
    text = path.read_text(encoding="utf-8")
    ast.parse(text, feature_version=se.MIN_PYTHON)
    assert not _NEWER.search(text), _NEWER.search(text).group(0)
    header = _HEADER_FLOOR.search(text)
    assert header is None or (int(header.group(1)), int(header.group(2))) <= se.MIN_PYTHON
