"""docs/architecture.md's hook table must list every script hooks.json registers, and nothing else.

The table is the one place a reader learns what each hook is for. Written by hand, it fell behind the
registrations as hooks were added: 31 of 65 registered scripts had no row. These tests pin both
directions (a registered script with no row, a row naming a script nothing registers) and check
that each row's Event column names only events its scripts are registered under. Each scan also
asserts it read the table at all, because a heading or column change would otherwise leave every
comparison empty and green.
"""

import json
import re
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
REPO = HOOKS_DIR.parents[2]
ARCHITECTURE = REPO / "docs" / "architecture.md"
SECTION = "## The hook pipeline"
SCRIPT = re.compile(r"`([A-Za-z0-9_.-]+\.py)`")
EVENT = re.compile(r"`([A-Z][A-Za-z]+)`")


def _registered():
    """{script file name: set of events} for every hook command in hooks.json."""
    hooks = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    found = {}
    for event, groups in hooks.items():
        for group in groups:
            for handler in group["hooks"]:
                for script in re.findall(r"([A-Za-z0-9_.-]+\.py)", handler.get("command", "")):
                    found.setdefault(script, set()).add(event)
    return found


def _table_rows():
    """[(events named, scripts named)] for every body row of the hook pipeline table."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    out = []
    for line in rows[2:]:  # header and separator
        cells = line.split("|")
        out.append((set(EVENT.findall(cells[1])), set(SCRIPT.findall(cells[2]))))
    return out


def test_the_table_and_the_registrations_were_both_read():
    assert len(_registered()) >= 60
    assert len(_table_rows()) >= 20


def test_every_registered_hook_script_has_a_row():
    named = set().union(*(scripts for _, scripts in _table_rows()))
    missing = sorted(set(_registered()) - named)
    assert not missing, (
        "registered in hooks.json but given no row in the hook table of docs/architecture.md "
        "(section %r): %s - add a row per script from its module docstring" % (SECTION, ", ".join(missing)))


def test_every_script_in_the_table_is_registered():
    named = set().union(*(scripts for _, scripts in _table_rows()))
    stale = sorted(named - set(_registered()))
    assert not stale, "docs/architecture.md lists hooks that hooks.json does not register: %s" % ", ".join(stale)


def test_each_row_names_only_events_its_scripts_are_registered_under():
    registered = _registered()
    wrong = []
    for events, scripts in _table_rows():
        for script in sorted(scripts & set(registered)):
            extra = events - registered[script]
            if extra:
                wrong.append("%s: row says %s, registered %s" % (script, sorted(extra), sorted(registered[script])))
    assert not wrong, wrong
