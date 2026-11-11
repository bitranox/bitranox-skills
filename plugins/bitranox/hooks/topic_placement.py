#!/usr/bin/env python3
"""Where a topic-bound fact's pointer lines go: the pure rules, no file access.

A fact tagged with topics is read only where its topics are: its pointer is rendered at every
level that has one of its topics and no ancestor that has one. A level HAS a topic when its
descriptor declares it (the `TOPICS:` line) or when it has two or more child levels and every
one of them has it, in which case one line at the parent replaces a copy per child. Nothing
here opens a file; memory_engine reads the tree and asks.

Decisions:
    - The tree top's topics are only the ones its descriptor declares; a topic every child has
      does not roll up into it. Why: the top's block is read by every session of the tree, so
      what it holds is the user's choice and never a computed consequence of what sits below.
      Evidence: argued (the design's safeguard that a change to the top's topics is proposed,
      never applied). Reopen if: a tree keeps one topic at every child of the top and the
      per-child copies are measured to cost more than one line at the top would.
      Pinned by: tests/test_topic_placement.py::test_a_topic_every_child_has_does_not_roll_up_into_the_top
    - A level with ONE child level takes nothing from it. Why: rolling up exists to replace
      several copies by one line, and with one child there is one copy either way, while the
      parent's own sessions would start reading a rule nobody placed there. Evidence: the
      design's example (/a/python and /b/python keep their lines, /a and /b get none).
      Reopen if: never for cost; only if a single-child container should read its child's rules.
      Pinned by: tests/test_topic_placement.py::test_a_single_child_does_not_roll_up
    - A fact whose topics no level has is placed at the top. Why: a rule nobody reads is lost,
      and a rule read too widely only costs bytes. Reopen if: never - it is the safeguard.
      Pinned by: tests/test_topic_placement.py::test_a_fact_whose_topic_no_level_has_falls_back_to_the_top
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping

__all__ = [
    "MAX_TOPICS",
    "TOP",
    "InvalidTopic",
    "Level",
    "LevelMap",
    "descriptor_digest",
    "descriptor_topics",
    "format_topics",
    "normalise_topics",
    "parse_topics",
    "with_descriptor_topics",
]

Level = tuple[str, ...]
"""A level as its path parts below the tree top; the top itself is the empty tuple."""

TOP: Level = ()
MAX_TOPICS = 12
"""Most topics one fact or one descriptor may carry: a bound on a field, so one item cannot make
a pointer line or a descriptor arbitrarily long."""

_TOPIC_RX = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
_TOPICS_LINE_RX = re.compile(r"(?m)^TOPICS:[ \t]*([^\r\n]*)$")


class InvalidTopic(ValueError):
    """A topic that is not a plain tag, or more topics than one item may carry."""


def normalise_topics(raw: Iterable[str]) -> tuple[str, ...]:
    """`raw` as a sorted tuple without repeats. Raises InvalidTopic for a tag that is not lower
    case letters, digits and dashes (at most 32 characters, starting with a letter or digit), and
    for more than MAX_TOPICS tags."""
    seen: set[str] = set()
    for item in raw:
        tag = item.strip() if isinstance(item, str) else item
        if not isinstance(tag, str) or not _TOPIC_RX.fullmatch(tag):
            raise InvalidTopic("invalid topic %r - use lower case letters, digits and dashes, "
                               "at most 32 characters" % (item,))
        seen.add(tag)
        if len(seen) > MAX_TOPICS:
            raise InvalidTopic("more than %d topics" % MAX_TOPICS)
    return tuple(sorted(seen))


def parse_topics(value: str) -> tuple[str, ...]:
    """The topics in a stored value: `[a, b]`, `a, b` or an empty list `[]`."""
    inner = value.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    return normalise_topics(part for part in inner.split(",") if part.strip())


def format_topics(topics: Iterable[str]) -> str:
    """The stored form of a topic list: `[a, b]`, and `[]` for none."""
    return "[%s]" % ", ".join(normalise_topics(topics))


def descriptor_topics(scope: str) -> tuple[str, ...] | None:
    """The topics a level's descriptor declares on its `TOPICS:` line; None when it has no such
    line (the level was never tagged), an empty tuple when the line is there and empty."""
    m = _TOPICS_LINE_RX.search(scope or "")
    return None if m is None else parse_topics(m.group(1))


def with_descriptor_topics(scope: str, topics: Iterable[str]) -> str:
    """`scope` with its `TOPICS:` line set. A descriptor without the line gains it after the
    `STACK:` line, or at the end when it has none; every other line is kept as it is."""
    line = "TOPICS: %s" % ", ".join(normalise_topics(topics))
    text = (scope or "").strip("\n")
    if _TOPICS_LINE_RX.search(text):
        return _TOPICS_LINE_RX.sub(lambda _m: line, text, count=1)
    out, placed = [], False
    for row in text.split("\n") if text else []:
        out.append(row)
        if not placed and row.startswith("STACK:"):
            out.append(line)
            placed = True
    if not placed:
        out.append(line)
    return "\n".join(out)


def descriptor_digest(scope: str) -> str:
    """A digest of what a descriptor SAYS, its `TOPICS:` line left out and blank lines and line
    ends ignored: equal digests mean the text the topics were chosen from has not changed."""
    rows = [row.strip() for row in _TOPICS_LINE_RX.sub("", scope or "").split("\n")]
    return hashlib.sha256("\n".join(row for row in rows if row).encode("utf-8")).hexdigest()


class LevelMap:
    """The levels of one tree and the topics each one has. Holds one small record per level."""

    def __init__(self, declared: Mapping[Level, Iterable[str]]) -> None:
        self._declared = {tuple(level): frozenset(normalise_topics(topics))
                          for level, topics in declared.items()}
        self._declared.setdefault(TOP, frozenset())
        self._children: dict[Level, list[Level]] = {level: [] for level in self._declared}
        for level in self._declared:
            parent = self.parent(level)
            if parent is not None:
                self._children[parent].append(level)
        self._effective: dict[Level, frozenset[str]] = {}
        for level in sorted(self._declared, key=len, reverse=True):   # children before parents
            self._effective[level] = self._declared[level] | self._rolled_up(level)

    def parent(self, level: Level) -> Level | None:
        """The nearest level above `level` that is in the map; None for the top."""
        for cut in range(len(level) - 1, -1, -1):
            if level[:cut] in self._declared:
                return level[:cut]
        return None

    def _rolled_up(self, level: Level) -> frozenset[str]:
        children = self._children[level]
        if level == TOP or len(children) < 2:
            return frozenset()
        return frozenset.intersection(*(self._effective[child] for child in children))

    def levels(self) -> list[Level]:
        """Every level, the top first, then by path."""
        return sorted(self._declared, key=lambda level: (len(level), level))

    def topics(self, level: Level) -> frozenset[str]:
        """The topics `level` has: declared there, or had by every one of its two or more
        child levels."""
        return self._effective[tuple(level)]

    def placements(self, topics: Iterable[str]) -> tuple[Level, ...]:
        """The levels a fact with `topics` gets a pointer line at: each level that has one of the
        topics while no level above it does. `(TOP,)` when no level has any of them."""
        wanted = frozenset(topics)
        hit = {level for level in self._declared if self._effective[level] & wanted}
        out = [level for level in hit if not self._has_ancestor_in(level, hit)]
        return tuple(sorted(out, key=lambda level: (len(level), level))) or (TOP,)

    def placed_at(self, level: Level, topics: Iterable[str]) -> bool:
        """True when a fact with `topics` gets a pointer line at `level`."""
        return tuple(level) in self.placements(topics)

    def _has_ancestor_in(self, level: Level, hit: set[Level]) -> bool:
        parent = self.parent(level)
        while parent is not None:
            if parent in hit:
                return True
            parent = self.parent(parent)
        return False
