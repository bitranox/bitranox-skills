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
`split_frontmatter` hands back the body too, and `scalar_text` decodes a value's quotes or block
header, for a consumer that reads a third-party skill or command file rather than linting one.
Pure standard library; ASCII.
"""
import re
from pathlib import Path

__all__ = ["description", "field", "frontmatter_block", "name", "read_frontmatter", "read_text",
           "scalar_text", "split_frontmatter"]

_FIELD_RX = {}
# A YAML block-scalar header: `|` or `>`, an optional chomping sign and indentation digit in
# either order, then the end of the header.
_BLOCK_HEADER = re.compile(r"^[|>](?:[1-9][+-]?|[+-][1-9]?)?(?:\s+|$)")


def _field_rx(key):
    rx = _FIELD_RX.get(key)
    if rx is None:
        rx = re.compile(r"^%s:[ \t]*(.*(?:\n[ \t]+.*)*)" % re.escape(key), re.M)
        _FIELD_RX[key] = rx
    return rx


def split_frontmatter(text):
    """(front-matter block, body) of a SKILL.md's contents. With no block the first is None and
    the body is the whole text; a block that never closes leaves an empty body."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return None, text
    parts = text.split("---", 2)
    return parts[1], parts[2] if len(parts) > 2 else ""


def frontmatter_block(text):
    """The front-matter text of a SKILL.md's contents, or None when it opens with none."""
    return split_frontmatter(text)[0]


def read_text(path):
    """The contents of the file at `path` decoded as every reader here decodes it, or None."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return data.decode("utf-8-sig", errors="replace")


def read_frontmatter(path):
    """The front-matter text of the SKILL.md at `path`, or None (no block, or unreadable)."""
    text = read_text(path)
    return None if text is None else frontmatter_block(text)


def field(block, key):
    """`key`'s value in a front-matter block, collapsed to one line; None when absent or empty."""
    if block is None:
        return None
    match = _field_rx(key).search(block)
    if not match:
        return None
    value = " ".join(match.group(1).split())
    return value or None


def scalar_text(value):
    """The text a `field` value means as a YAML scalar: a block-scalar header (`>-`, `|`) dropped,
    one pair of enclosing quotes removed with their escapes undone. None stays None, and so does a
    value that is only a header.

    `field` itself keeps the value as written, because the commit gate rejects a quoted or
    block-scalar description by its first character; this is for a consumer that offers a
    third-party skill's text, where both forms are common.
    """
    if value is None:
        return None
    header = _BLOCK_HEADER.match(value)
    if header:
        return value[header.end():] or None
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'") or None
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\") or None
    return value


def description(path):
    """The `description:` of the SKILL.md at `path`, or None."""
    return field(read_frontmatter(path), "description")


def name(path):
    """The `name:` of the SKILL.md at `path`, or None."""
    return field(read_frontmatter(path), "name")
