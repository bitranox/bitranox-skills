"""OPEN-WORK.md as data: list, add and close backlog items without hand-editing the file.

The backlog's own header states its rules: one item per line, a rank no other line holds, a solved
item's line deleted. This module enforces the mechanical ones, so a tool call cannot split a bullet,
reuse a number another line holds or cites, or delete any line but the one it closes. Nothing here
chooses a rank; the one ordering it refuses is a FOUND item above an open USER item. A `- [x]` line
written by an older release still parses as closed and still holds its rank.

Decisions:
    A FOUND item ranked above an open USER item is REFUSED, not warned about. Why: the backlog's
    first ranking rule has no exception, a warning arrives after the line is written so the caller
    still has to move it by hand, and a rank below the last open USER item always exists. Reopen
    if a real backlog needs a FOUND item above a USER one and the hand edit is too costly. Pinned
    by test_add_refuses_a_found_item_above_an_open_user_item.
    The reverse direction (a USER item added below a FOUND one) is not refused: when a FOUND item
    holds rank 1 no rank above it exists, so a refusal could leave no legal number.
"""
import datetime
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import self_improve_signals as sig

FILENAME = "OPEN-WORK.md"


class Origin(StrEnum):
    """Who raised an item: the backlog's two origins, spelled as a line writes them."""

    USER = "USER"
    FOUND = "FOUND"


class ItemState(StrEnum):
    """An item line's checkbox: `- [ ]` is open, `- [x]` (an older release's solved line) closed."""

    OPEN = "open"
    CLOSED = "closed"


ORIGINS = tuple(Origin)
STATES = ("open", "closed", "all")
#: the largest rank a line may carry: a bound keeps the free-tens suggestion finite
MAX_RANK = 999999

HEADER = (
    "# Open work\n\n"
    "The standing backlog: everything that outlives a single session. An item leaves it only when\n"
    "it is SOLVED, and then its line is deleted; an unsolved item is never dropped.\n\n"
    "One item per line:\n\n"
    "```\n"
    "- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why it is "
    "still open | next: the concrete next action\n"
    "```\n\n"
    "A solved item's line is deleted. Delete it in the commit that records the solving work and\n"
    "put the reason in that commit message: git history keeps the old line.\n\n"
)

#: The `(date)` is optional: a ranked line written without one (by hand, or by an older tool) is
#: still an item. Read as no item, close reported its rank "not found" while the line stood there.
_ITEM_RX = re.compile(r"-\s*\[([ xX])\]\s*(?:\(([^)]*)\)\s*)?\[(\d+)\]\s*(.*)$")
_ORIGIN_RX = re.compile(r"(USER|FOUND):\s*(.*)$")
_FIELD_RX = re.compile(r"(?<!\s)\s+\|\s+(size|open|next|closed):\s*")
_FENCE_RX = re.compile(r" {0,3}(`{3,}|~{3,})")
_CHECKBOX_RX = re.compile(r"-\s*\[([ xX])\]\s")
#: a rank an item's text cites, e.g. "same blocker as [60]"; at most MAX_RANK's six digits
_CITED_RX = re.compile(r"\[(\d{1,6})\]")


@dataclass(frozen=True, slots=True)
class Item:
    """One backlog line as data. A field the line does not carry is None.

    `open` and `next` keep the line's own label names: they are the keys `to_data` writes, which
    the backlog_list tool relays as its `items`."""

    rank: int
    raised: str
    state: ItemState
    origin: Origin | None
    what: str
    size: str | None
    open: str | None
    next: str | None
    closed: str | None

    def to_data(self) -> dict[str, object]:
        """The item as the backlog_list JSON carries it: keys in this order, enum values as strings."""
        return {"rank": self.rank, "raised": self.raised, "state": self.state.value,
                "origin": None if self.origin is None else self.origin.value, "what": self.what,
                "size": self.size, "open": self.open, "next": self.next, "closed": self.closed}


@dataclass(frozen=True, slots=True)
class Added:
    """What add_item wrote: the new item's rank and its line exactly as written."""

    rank: int
    line: str

    def to_data(self) -> dict[str, object]:
        """The report as the backlog_add JSON carries it, keys in this order."""
        return {"rank": self.rank, "line": self.line}


@dataclass(frozen=True, slots=True)
class Closed:
    """What close_item deleted: the line as it stood, and the caller's reason for closing it.

    `reason` is for the caller to record where it lasts (the commit message that ships the
    change), since the file keeps no trace of it."""

    rank: int
    line: str
    reason: str

    def to_data(self) -> dict[str, object]:
        """The report as the backlog_close JSON carries it; `deleted` is always true, because a
        close that deletes nothing raises instead of returning."""
        return {"rank": self.rank, "line": self.line, "reason": self.reason, "deleted": True}


#: a path argument the backlog functions accept
PathArg = str | os.PathLike[str]


class BacklogError(ValueError):
    """A request the backlog refuses; the class name is the `kind` a caller sees."""


class NotARepo(BacklogError):
    pass


class RankTaken(BacklogError):
    pass


class RankOrder(BacklogError):
    pass


class UnknownRank(BacklogError):
    pass


class AlreadyClosed(BacklogError):
    pass


class AmbiguousRank(BacklogError):
    pass


class MalformedField(BacklogError):
    pass


class BacklogElsewhere(BacklogError):
    pass


def parse_line(line: str) -> Item | None:
    """The item a line holds, or None for anything that is not an item line."""
    m = _ITEM_RX.match(line.strip())
    if not m:
        return None
    box, raised, rank, rest = m.groups()
    parts = _FIELD_RX.split(rest)
    fields: dict[str, str] = {}
    current = ""
    for label, text in zip(parts[1::2], parts[2::2]):
        if label in fields:
            # the label's own words inside an earlier field: keep them there, never drop them
            fields[current] += " | %s: %s" % (label, text)
            continue
        fields[label] = text.strip()
        current = label
    head = parts[0].strip()
    om = _ORIGIN_RX.match(head)
    return Item(rank=int(rank), raised=(raised or "").strip(),
                state=ItemState.OPEN if box == " " else ItemState.CLOSED,
                origin=Origin(om.group(1)) if om else None,
                what=(om.group(2) if om else head).strip(),
                size=fields.get("size"), open=fields.get("open"), next=fields.get("next"),
                closed=fields.get("closed"))


def item_text(line: str) -> str:
    """Everything after an item line's `[rank]`, as written (origin and fields included), or ""
    for a line that is not an item. A listing shows this rather than a rebuilt line, so it quotes
    the backlog in the author's own field order and wording."""
    m = _ITEM_RX.match(line.strip())
    return m.group(4).strip() if m else ""


def _outside_fences(lines: list[str]) -> Iterator[tuple[int, str]]:
    """(index, line) for every line outside a fenced code block."""
    fence: str | None = None
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
        yield i, line


def iter_items(lines: list[str]) -> Iterator[tuple[int, Item]]:
    """(index, item) for every item line outside a fenced code block."""
    for i, line in _outside_fences(lines):
        item = parse_line(line)
        if item is not None:
            yield i, item


def list_items(path: PathArg, state: str = "open") -> list[Item]:
    """The items of the backlog at `path` in file order; [] when the file does not exist."""
    if state not in STATES:
        raise MalformedField("state must be one of %s, got %r" % (", ".join(STATES), state))
    backlog = Path(path)
    if not backlog.is_file():
        return []
    lines = backlog.read_text(encoding="utf-8").split("\n")
    return [it for _, it in iter_items(lines) if state == "all" or it.state == state]


def unranked_lines(path: PathArg, state: str = "open") -> list[str]:
    """Checkbox lines of the backlog at `path` that are NOT items because they carry no `[rank]`.

    A backlog in an older shape ("- [ ] (date) ORIGIN: ...") parses to no items at all, and an empty
    list reads as an empty backlog. The caller reports these so that cannot happen. The unfenced
    format template (its literal `[rank]`) is not a line of work and is left out."""
    if state not in STATES:
        raise MalformedField("state must be one of %s, got %r" % (", ".join(STATES), state))
    backlog = Path(path)
    if not backlog.is_file():
        return []
    wanted = {"open": " ", "closed": "xX", "all": " xX"}[state]
    lines = backlog.read_text(encoding="utf-8").split("\n")
    found: list[str] = []
    for _, line in _outside_fences(lines):
        bare = line.strip()
        m = _CHECKBOX_RX.match(bare)
        if m and m.group(1) in wanted and parse_line(line) is None and "[rank]" not in bare:
            found.append(bare)
    return found


def enclosing_backlog(toplevel: PathArg) -> Path | None:
    """The nearest OPEN-WORK.md in a directory above `toplevel`, or None."""
    for parent in Path(toplevel).parents:
        candidate = parent / FILENAME
        if candidate.is_file():
            return candidate
    return None


def backlog_path(cwd: PathArg) -> Path:
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


def main_checkout_of(cwd: PathArg) -> Path | None:
    """The main checkout when `cwd` is inside a LINKED worktree, else None.

    A linked worktree carries its own OPEN-WORK.md, and a line written there is not in the main
    checkout's copy until the commit reaches it - a reader looking there finds nothing. The main
    checkout is the directory holding the common git dir; a bare or unusual layout (common dir not
    named .git) answers None rather than guessing."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    r = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute",
                        "--git-dir", "--git-common-dir"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    parts = r.stdout.split("\n")
    if r.returncode != 0 or len(parts) < 2:
        return None
    git_dir, common = Path(parts[0].strip()), Path(parts[1].strip())
    if git_dir == common or common.name != ".git":
        return None
    return common.parent


_RAISED_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})\??", re.ASCII)


def require_one_line(value: object, name: str) -> str:
    """`value` unchanged when it is one non-empty line of text a UTF-8 file can hold, else
    MalformedField naming the field.

    Control characters (category Cc) and the line and paragraph separators (Zl, Zp) are refused,
    which covers every character str.splitlines() breaks on, so no reader can see two lines."""
    if not isinstance(value, str) or not value.strip():
        raise MalformedField("%s must be a non-empty string" % name)
    if any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in value):
        raise MalformedField("%s must be one line of plain text: no line break or other control "
                             "character" % name)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise MalformedField("%s must be text a UTF-8 file can hold (a lone surrogate cannot)"
                             % name) from None
    return value


def require_line(value: object, name: str) -> str:
    """`value` as one non-empty backlog field, stripped, or MalformedField naming the field."""
    text = require_one_line(value, name)
    if _FIELD_RX.search(" " + text + " "):
        raise MalformedField("%s contains a ' | <label>: ' separator, which would split the "
                             "line into the wrong fields" % name)
    return text.strip()


def _require_rank(rank: object) -> int:
    # bool is an int subclass: True would otherwise be accepted as rank 1
    if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= MAX_RANK:
        raise MalformedField("rank must be a positive integer up to %d, got %r" % (MAX_RANK, rank))
    return rank


def _require_raised(raised: object, today: datetime.date | None) -> str:
    if raised is None:
        # never an inferred date: an admitted unknown is today's date with a question mark
        return (today or datetime.date.today()).isoformat() + "?"
    if raised == "unknown":
        return "unknown"
    m = _RAISED_RX.fullmatch(raised) if isinstance(raised, str) else None
    if not m:
        raise MalformedField("raised must be YYYY-MM-DD, YYYY-MM-DD? or unknown, got %r" % (raised,))
    try:
        datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise MalformedField("raised is not a calendar date: %r" % raised) from None
    return m.group(0)


def _free_tens_near(rank: int, taken: set[int]) -> list[int]:
    base = rank - rank % 10
    below = next((r for r in range(base, 0, -10) if r not in taken and r != rank), None)
    above = next(r for r in range(base + 10, base + 10 ** 6, 10) if r not in taken)
    return [r for r in (below, above) if r is not None]


def _free_ten_after(rank: int, taken: set[int]) -> int:
    return next(r for r in range(rank - rank % 10 + 10, MAX_RANK + 10 ** 6, 10) if r not in taken)


def _read(path: Path) -> tuple[str, str]:
    """(text with LF line ends, the file's line end) of the backlog at `path`.

    The line end is kept so a rewrite does not turn a CRLF checkout (Windows, core.autocrlf) into
    a whole-file diff. read_text() would fold every CRLF to LF and hide which the file used."""
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), eol


def _write(path: Path, lines: list[str], eol: str = "\n") -> None:
    tmp = path.with_name("%s.tmp-%d" % (path.name, os.getpid()))
    try:
        with open(tmp, "w", encoding="utf-8", newline=eol) as fh:
            fh.write("\n".join(lines))
            # the rename below is durable only if the data it points at reached the disk first
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        # a failed write must not leave OPEN-WORK.md.tmp-<pid> beside the backlog
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def add_item(path: PathArg, rank: object, origin: object, what: object, size: object,
             open_: object, next_: object, raised: object = None,
             today: datetime.date | None = None) -> Added:
    """Insert one open item and report what was written. Refuses before writing anything.

    The fields are `object` because they arrive from a tool call's JSON unchecked: each is
    validated here, which is the boundary."""
    number = _require_rank(rank)
    if not isinstance(origin, str) or origin not in ORIGINS:
        raise MalformedField("origin must be USER or FOUND, got %r" % (origin,))
    who = Origin(origin)
    fields = [require_line(v, n) for v, n in ((what, "what"), (size, "size"),
                                              (open_, "open"), (next_, "next"))]
    line = "- [ ] (%s) [%d] %s: %s | size: %s | open: %s | next: %s" % (
        (_require_raised(raised, today), number, who) + tuple(fields))
    backlog = Path(path)
    with sig.memory_lock(backlog):
        text, eol = _read(backlog) if backlog.is_file() else ("", "\n")
        if not text.strip():
            text = HEADER                       # a missing or empty file starts from the header
        lines = text.split("\n")
        items = list(iter_items(lines))
        # a cited number is taken too: the citing line would otherwise point at the new item
        taken = {it.rank for _, it in items} | {int(n) for ln in lines for n in _CITED_RX.findall(ln)}
        if number in taken:
            raise RankTaken("rank %d is already held or cited by a line (closed lines count); free "
                            "tens nearby: %s"
                            % (number, ", ".join(map(str, _free_tens_near(number, taken)))))
        users = [it.rank for _, it in items
                 if it.state == ItemState.OPEN and it.origin == Origin.USER]
        if who == Origin.FOUND and users and number < max(users):
            raise RankOrder("rank %d would put a FOUND item above open USER item %d; a USER item "
                            "outranks every FOUND one. Next free ten below it: %d"
                            % (number, max(users), _free_ten_after(max(users), taken)))
        smaller = [(it.rank, i) for i, it in items if it.rank < number]
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
        _write(backlog, new, eol)
    return Added(rank=number, line=line)


def close_item(path: PathArg, rank: object, reason: object) -> Closed:
    """Delete one open item's line: the item is solved. Nothing else in the file changes.

    Returns the deleted line and the reason (see Closed); a rank that names no open line raises.
    """
    number = _require_rank(rank)
    why = require_line(reason, "reason")
    backlog = Path(path)
    with sig.memory_lock(backlog):
        if not backlog.is_file():
            raise UnknownRank("no %s here, so there is no rank %d" % (FILENAME, number))
        text, eol = _read(backlog)
        lines = text.split("\n")
        hits = [(i, it) for i, it in iter_items(lines) if it.rank == number]
        if not hits:
            raise UnknownRank("no line holds rank %d" % number)
        open_hits = [(i, it) for i, it in hits if it.state == ItemState.OPEN]
        if not open_hits:
            raise AlreadyClosed("rank %d is already closed" % number)
        if len(open_hits) > 1:
            raise AmbiguousRank("rank %d labels %d open lines; give one a free number before "
                                "closing either" % (number, len(open_hits)))
        i = open_hits[0][0]
        removed = lines[i]
        _write(backlog, lines[:i] + lines[i + 1:], eol)
    return Closed(rank=number, line=removed, reason=why)
