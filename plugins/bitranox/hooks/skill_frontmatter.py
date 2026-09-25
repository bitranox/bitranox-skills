"""The ONE reader of a SKILL.md front matter's `name:` and `description:` values.

The commit gate lints a description, the trigger-map builder turns it into router keywords, the
catalog builder prints it, the mirror audit matches twins by it, the listing-budget hook measures
it and the Jev router catalogue offers it. Each of them used to parse it with its own regex, so a
malformation one reader forgave the other read differently - the gate passed a description whose
following `# comment` line the builder shipped as keywords. Every one of them reads through here,
so they cannot disagree.

A value is the rest of its key's line plus any INDENTED continuation lines (a YAML plain scalar
may also begin on the next indented line). A line at column 0 - the next key of any shape, a
comment - ends it, and a key with nothing after it reads as absent rather than capturing the next
line. A leading UTF-8 BOM is dropped, and undecodable bytes are replaced rather than raised.

The block is everything between the opening `---` and the next `---`, the split every reader
already used; `harness_checks` separately reports a delimiter glued to a value and a second block.
Pure standard library; ASCII.
"""
import re
from pathlib import Path

__all__ = ["description", "field", "frontmatter_block", "name", "read_frontmatter"]

_FIELD_RX = {}


def _field_rx(key):
    rx = _FIELD_RX.get(key)
    if rx is None:
        rx = re.compile(r"^%s:[ \t]*(.*(?:\n[ \t]+.*)*)" % re.escape(key), re.M)
        _FIELD_RX[key] = rx
    return rx


def frontmatter_block(text):
    """The front-matter text of a SKILL.md's contents, or None when it opens with none."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None
    return text.split("---", 2)[1]


def read_frontmatter(path):
    """The front-matter text of the SKILL.md at `path`, or None (no block, or unreadable)."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return frontmatter_block(data.decode("utf-8-sig", errors="replace"))


def field(block, key):
    """`key`'s value in a front-matter block, collapsed to one line; None when absent or empty."""
    if block is None:
        return None
    match = _field_rx(key).search(block)
    if not match:
        return None
    value = " ".join(match.group(1).split())
    return value or None


def description(path):
    """The `description:` of the SKILL.md at `path`, or None."""
    return field(read_frontmatter(path), "description")


def name(path):
    """The `name:` of the SKILL.md at `path`, or None."""
    return field(read_frontmatter(path), "name")
