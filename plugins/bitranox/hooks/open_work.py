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


_RAISED_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})\??", re.ASCII)


def require_line(value, name):
    """`value` as one non-empty line, or MalformedField naming the field."""
    if not isinstance(value, str) or not value.strip():
        raise MalformedField("%s must be a non-empty string" % name)
    if "\n" in value or "\r" in value:
        raise MalformedField("%s must be one line: the backlog holds one item per line" % name)
    if _FIELD_RX.search(" " + value + " "):
        raise MalformedField("%s contains a ' | <label>: ' separator, which would split the "
                             "line into the wrong fields" % name)
    return value.strip()


def _require_rank(rank):
    # bool is an int subclass: True would otherwise be accepted as rank 1
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise MalformedField("rank must be a positive integer, got %r" % (rank,))
    return rank


def _require_raised(raised, today):
    if raised is None:
        # never an inferred date: an admitted unknown is today's date with a question mark
        return (today or datetime.date.today()).isoformat() + "?"
    if raised == "unknown":
        return raised
    m = _RAISED_RX.fullmatch(raised) if isinstance(raised, str) else None
    if not m:
        raise MalformedField("raised must be YYYY-MM-DD, YYYY-MM-DD? or unknown, got %r" % (raised,))
    try:
        datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise MalformedField("raised is not a calendar date: %r" % raised) from None
    return raised


def _free_tens_near(rank, taken):
    base = rank - rank % 10
    below = next((r for r in range(base, 0, -10) if r not in taken and r != rank), None)
    above = next(r for r in range(base + 10, base + 10 ** 6, 10) if r not in taken)
    return [r for r in (below, above) if r is not None]


def _write(path, lines):
    tmp = path.with_name("%s.tmp-%d" % (path.name, os.getpid()))
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    os.replace(tmp, path)


def add_item(path, rank, origin, what, size, open_, next_, raised=None, today=None):
    """Insert one open item; returns {"rank", "line"}. Refuses before writing anything."""
    rank = _require_rank(rank)
    if not isinstance(origin, str) or origin not in ORIGINS:
        raise MalformedField("origin must be USER or FOUND, got %r" % (origin,))
    fields = [require_line(v, n) for v, n in ((what, "what"), (size, "size"),
                                              (open_, "open"), (next_, "next"))]
    line = "- [ ] (%s) [%d] %s: %s | size: %s | open: %s | next: %s" % (
        (_require_raised(raised, today), rank, origin) + tuple(fields))
    path = Path(path)
    with sig.memory_lock(path):
        text = path.read_text(encoding="utf-8") if path.is_file() else HEADER
        lines = text.split("\n")
        items = list(iter_items(lines))
        taken = {it["rank"] for _, it in items}
        if rank in taken:
            raise RankTaken("rank %d is already held by a line (closed lines count); free tens "
                            "nearby: %s" % (rank, ", ".join(map(str, _free_tens_near(rank, taken)))))
        smaller = [(it["rank"], i) for i, it in items if it["rank"] < rank]
        if smaller:
            at = max(smaller)[1] + 1
        elif items:
            at = items[0][0]
        else:
            # no item yet: after the last non-empty line, so the file keeps one trailing newline
            at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
        new = lines[:at] + [line] + lines[at:]
        if new[-1] != "":
            new.append("")
        if len(new) != len(lines) + 1 + (0 if lines[-1] == "" else 1):
            raise BacklogError("internal: an add must grow the file by exactly one line")
        _write(path, new)
    return {"rank": rank, "line": line}


def close_item(path, rank, reason):
    """Mark one open item closed with its reason; the line stays. Returns {"rank", "line"}."""
    rank = _require_rank(rank)
    reason = require_line(reason, "reason")
    path = Path(path)
    with sig.memory_lock(path):
        if not path.is_file():
            raise UnknownRank("no %s here, so there is no rank %d" % (FILENAME, rank))
        lines = path.read_text(encoding="utf-8").split("\n")
        hits = [(i, it) for i, it in iter_items(lines) if it["rank"] == rank]
        if not hits:
            raise UnknownRank("no line holds rank %d" % rank)
        open_hits = [(i, it) for i, it in hits if it["state"] == "open"]
        if not open_hits:
            raise AlreadyClosed("rank %d is already closed" % rank)
        if len(open_hits) > 1:
            raise AmbiguousRank("rank %d labels %d open lines; give one a free number before "
                                "closing either" % (rank, len(open_hits)))
        i = open_hits[0][0]
        # edit the raw line rather than re-rendering it, so an older line keeps its exact text
        lines[i] = re.sub(r"^(\s*-\s*\[) \]", r"\1x]", lines[i], count=1) + " | closed: " + reason
        _write(path, lines)
    return {"rank": rank, "line": lines[i]}
