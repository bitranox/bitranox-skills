"""OPEN-WORK.md as data: list, add and close backlog items without hand-editing the file.

The backlog's own header states its rules: one item per line, a rank no other line holds, a closed
item kept with its reason. This module enforces the mechanical ones, so a tool call cannot split a
bullet, reuse a closed item's number or delete a line. Which item outranks which stays the
caller's judgment - nothing here chooses a rank.
"""
import datetime
import os
import re
import subprocess
from pathlib import Path

import self_improve_signals as sig

FILENAME = "OPEN-WORK.md"
ORIGINS = ("USER", "FOUND")
STATES = ("open", "closed", "all")
#: the labelled fields of a line, in the order a written line carries them
LABELS = ("size", "open", "next", "closed")

HEADER = (
    "# Open work\n\n"
    "The standing backlog: everything that outlives a single session. Items leave it by being\n"
    "CLOSED, never by being dropped.\n\n"
    "One item per line:\n\n"
    "```\n"
    "- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why it is "
    "still open | next: the concrete next action\n"
    "```\n\n"
    "Closing an item means `- [x]` plus `| closed: <reason>`. The line stays.\n\n"
)

_ITEM_RX = re.compile(r"-\s*\[([ xX])\]\s*\(([^)]*)\)\s*\[(\d+)\]\s*(.*)$")
_ORIGIN_RX = re.compile(r"(USER|FOUND):\s*(.*)$")
_FIELD_RX = re.compile(r"\s+\|\s+(size|open|next|closed):\s*")
_FENCE_RX = re.compile(r" {0,3}(`{3,}|~{3,})")


class BacklogError(ValueError):
    """A request the backlog refuses; the class name is the `kind` a caller sees."""


class NotARepo(BacklogError):
    pass


class RankTaken(BacklogError):
    pass


class UnknownRank(BacklogError):
    pass


class AlreadyClosed(BacklogError):
    pass


class AmbiguousRank(BacklogError):
    pass


class MalformedField(BacklogError):
    pass


def parse_line(line):
    """The item a line holds, or None for anything that is not an item line."""
    m = _ITEM_RX.match(line.strip())
    if not m:
        return None
    box, raised, rank, rest = m.groups()
    parts = _FIELD_RX.split(rest)
    fields, current = {}, None
    for label, text in zip(parts[1::2], parts[2::2]):
        if label in fields:
            # the label's own words inside an earlier field: keep them there, never drop them
            fields[current] += " | %s: %s" % (label, text)
            continue
        fields[label] = text.strip()
        current = label
    head = parts[0].strip()
    om = _ORIGIN_RX.match(head)
    item = {"rank": int(rank), "raised": raised.strip(),
            "state": "open" if box == " " else "closed",
            "origin": om.group(1) if om else None,
            "what": (om.group(2) if om else head).strip()}
    for label in LABELS:
        item[label] = fields.get(label)
    return item


def iter_items(lines):
    """(index, item) for every item line outside a fenced code block."""
    fence = None
    for i, line in enumerate(lines):
        if fence is not None:
            bare = line.strip()
            # a closer is the opener's character only, at least as long, nothing else on the line
            if bare and set(bare) == {fence[0]} and len(bare) >= len(fence):
                fence = None
            continue
        m = _FENCE_RX.match(line)
        if m:
            fence = m.group(1)
            continue
        item = parse_line(line)
        if item is not None:
            yield i, item


def list_items(path, state="open"):
    """The items of the backlog at `path` in file order; [] when the file does not exist."""
    if state not in STATES:
        raise MalformedField("state must be one of %s, got %r" % (", ".join(STATES), state))
    path = Path(path)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    return [it for _, it in iter_items(lines) if state == "all" or it["state"] == state]


def backlog_path(cwd):
    """OPEN-WORK.md at the git top level of `cwd`.

    Every GIT_ variable is dropped first: git reads GIT_DIR before the cwd, and a push from a
    linked worktree exports it, which would answer for some other repository."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    r = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0 or not r.stdout.strip():
        raise NotARepo("%s is not inside a git repository, so it has no OPEN-WORK.md" % cwd)
    return Path(r.stdout.strip()) / FILENAME
