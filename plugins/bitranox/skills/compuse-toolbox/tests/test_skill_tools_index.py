"""The Tools table in SKILL.md and its full entries in references/tools.md name the same tools.

SKILL.md keeps a one-line summary and the launch command per tool; the full text of each entry
lives in references/tools.md under a `## `name`` heading. A tool added to one and not the other
leaves a row with no detail behind it, or an entry nothing routes to.
"""

import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
_ROW = re.compile(r"^\| `(?P<name>[^`]+)` \|")
_HEADING = re.compile(r"^## `(?P<name>[^`]+)`$")


def _table_tools(text: str) -> list[str]:
    lines = text.split("\n")
    start = lines.index("## Tools")
    names: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        m = _ROW.match(line)
        if m:
            names.append(m.group("name"))
    return names


def _page_tools(text: str) -> list[str]:
    return [m.group("name") for line in text.split("\n") if (m := _HEADING.match(line))]


def test_every_tools_row_has_one_entry_in_the_page_and_no_entry_lacks_a_row():
    table = _table_tools((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    page = _page_tools((SKILL_DIR / "references" / "tools.md").read_text(encoding="utf-8"))
    assert len(table) >= 40, "the Tools table did not parse: %d rows" % len(table)
    assert len(page) == len(set(page)), "an entry heading is repeated"
    assert table == page


def test_each_entry_has_body_text():
    text = (SKILL_DIR / "references" / "tools.md").read_text(encoding="utf-8")
    sections = re.split(r"^## `[^`]+`$", text, flags=re.M)[1:]
    assert sections
    assert all(len(s.strip()) > 40 for s in sections)


def test_the_table_points_at_the_page():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "references/tools.md" in text
