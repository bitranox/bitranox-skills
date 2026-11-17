#!/usr/bin/env python3
"""The closed topic list of one knowledge tree, and what each level was tagged from.

One JSON file beside the fact bodies, `<anchor>/.claude-memory/topics.json`:

    {"version": 1, "tagger": "jev", "topics": {"python": "Python code and its tooling"},
     "levels": {"projects/libs": "<digest of the descriptor its topics were chosen from>"}}

`topics` is the list a fact or a level may be tagged from; a tag outside it is refused by the
engine, so the list is closed until someone replaces it. `levels` lets a later run see that a
level's descriptor changed since its topics were chosen. No file means the tree has no topic
list, and nothing is placed by topic there. Written only through memory_engine.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

import self_improve_signals as sig
import topic_placement as tp
import uuid_store as us

__all__ = ["FORMAT_VERSION", "MAX_LIST", "MAX_MEANING", "TAGGERS", "Tagger", "TopicFile",
           "TopicStoreError", "level_key", "load", "record_level", "save_list", "store_path"]

MAX_LIST = 64
"""Most topics a tree's list may hold: every one becomes a question about every fact."""
MAX_MEANING = 200
FORMAT_VERSION = 1
"""The one file format this module reads and writes; a file naming another is refused."""


class Tagger(StrEnum):
    """Who chose a tree's topics: the closed vocabulary of the file's `tagger` field."""

    JEV = "jev"
    OPUS = "opus"


TAGGERS = tuple(t.value for t in Tagger)
_KEYS = frozenset({"version", "tagger", "topics", "levels"})


@dataclass(frozen=True)
class TopicFile:
    """One topic file as `load` parsed it: every field checked, nothing else carried.

    `topics` maps a stored tag to its one-line meaning, `levels` a `level_key` to the digest of
    the descriptor that level's topics were chosen from. `load` hands both out as read-only
    views, so a reader cannot change what a later `record_level` writes back."""

    tagger: Tagger
    topics: Mapping[str, str]
    levels: Mapping[str, str]
    version: int = FORMAT_VERSION

    def to_json(self) -> dict[str, object]:
        """The file's JSON object, the one shape `_write` serialises."""
        return {"version": self.version, "tagger": self.tagger.value,
                "topics": dict(self.topics), "levels": dict(self.levels)}


class TopicStoreError(ValueError):
    """The topic file cannot be used as it is, or a new list is not acceptable."""


def store_path(anchor) -> Path:
    """`<anchor>/.claude-memory/topics.json`."""
    return Path(anchor) / us.STORE_DIRNAME / "topics.json"


def level_key(anchor, level) -> str:
    """A level as the file records it: its path below the anchor with `/` separators, and the
    empty string for the anchor itself. Computed LEXICALLY (absolute paths, symlinks not followed),
    as `resolve_anchor` finds the anchor: a level reached through a symlink to a directory outside
    the tree is still the level its path names. Raises TopicStoreError for a level that is not
    below the anchor (or on another drive)."""
    try:
        rel = os.path.relpath(os.path.abspath(os.fspath(level)), os.path.abspath(os.fspath(anchor)))
    except ValueError as exc:                         # Windows: a different drive
        raise TopicStoreError("%s is not below the tree top %s (%s)" % (level, anchor, exc)) from exc
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        raise TopicStoreError("%s is not below the tree top %s" % (level, anchor))
    return "" if rel == os.curdir else Path(rel).as_posix()


_REMEDY = ("repair it by hand, or delete it and write the list again with memory_engine.py "
           "topics-set-list (every level then reads as stale until its topics are chosen again)")


def _unusable(anchor, why) -> TopicStoreError:
    return TopicStoreError("%s %s - %s" % (store_path(anchor), why, _REMEDY))


def _meaning_problem(name, meaning) -> str | None:
    """Why `meaning` cannot be the meaning of `name`, or None. One line, as given (a trailing
    line break is a second line), of 1 to MAX_MEANING characters once trimmed: the trimmed text
    is what is stored, so it is what is measured."""
    if not isinstance(meaning, str) or meaning.splitlines() != [meaning] \
            or not 0 < len(meaning.strip()) <= MAX_MEANING:
        return "the meaning of %r must be one line of 1 to %d characters" % (name, MAX_MEANING)
    return None


def _content_problem(topics) -> str | None:
    """Why a stored `topics` object is not a list `save_list` could have written, or None. Each
    tag is judged by topic_placement's own grammar and must be stored in the form it normalises
    to, so the file follows that grammar whatever it becomes."""
    if len(topics) > MAX_LIST:
        return "holds %d topics, over the limit of %d" % (len(topics), MAX_LIST)
    for name, meaning in topics.items():
        try:
            if tp.normalise_topics([name]) != (name,):
                return "holds the tag %r, which is not in its stored form" % (name,)
        except tp.InvalidTopic as exc:
            return "holds a tag that is not one: %s" % exc
        why = _meaning_problem(name, meaning)
        if why:
            return "holds a bad meaning: %s" % why
    return None


def _parse(anchor, data) -> TopicFile:
    """The TopicFile a decoded JSON value holds, or TopicStoreError naming the first field that
    is not what `_write` puts there. Every key is judged: an unknown one, a `version` other than
    FORMAT_VERSION (a bool is no version), a `tagger` outside Tagger, or a `levels` value that is
    not a string would otherwise be carried through and written back by `record_level`."""
    if not (isinstance(data, dict) and isinstance(data.get("topics"), dict)):
        raise _unusable(anchor, "is not a topic file (no 'topics' object)")
    unknown = sorted(set(data) - _KEYS)
    if unknown:
        raise _unusable(anchor, "holds keys this format has none of: %s"
                        % ", ".join(repr(k) for k in unknown))
    version = data.get("version", FORMAT_VERSION)
    if type(version) is not int or version != FORMAT_VERSION:
        raise _unusable(anchor, "names format version %r; this module reads version %d"
                        % (version, FORMAT_VERSION))
    tagger = data.get("tagger", Tagger.OPUS.value)
    if not isinstance(tagger, str) or tagger not in TAGGERS:
        raise _unusable(anchor, "names the tagger %r, not one of %s" % (tagger, ", ".join(TAGGERS)))
    levels = data.get("levels", {})
    if not isinstance(levels, dict):
        raise _unusable(anchor, "holds a 'levels' value that is not an object")
    for key, digest in levels.items():
        if not isinstance(digest, str):
            raise _unusable(anchor, "records the level %r with a digest that is not a string" % (key,))
    why = _content_problem(data["topics"])
    if why:
        raise _unusable(anchor, why)
    return TopicFile(tagger=Tagger(tagger), topics=MappingProxyType(dict(data["topics"])),
                     levels=MappingProxyType(dict(levels)), version=version)


def load(anchor) -> TopicFile | None:
    """The topic file's content, or None when the tree has none. Raises TopicStoreError for a
    file that is there but empty, that is not the JSON object this module writes (any key, field
    or value `_parse` refuses), or whose list `save_list` would refuse (a tag outside
    topic_placement's grammar, a bad meaning, more than MAX_LIST topics), and TreeWalkError for
    one that cannot be read: a list read as absent would switch placement by topic off without a
    word, and one read as fine would be written back by `record_level` as if it were. A file
    without `version`, `tagger` or `levels` reads as version 1, tagger opus and no levels."""
    path = store_path(anchor)
    text = us.read_store_text(path)
    if text == "":
        # read_store_text answers "" for a file that is absent AND for one that is empty; only
        # the first means "no list". A truncated write leaves the second.
        if path.is_file():
            raise _unusable(anchor, "is empty (0 bytes)")
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise _unusable(anchor, "is not valid JSON (%s)" % exc) from exc
    return _parse(anchor, data)


def _write(anchor, record: TopicFile) -> bool:
    text = json.dumps(record.to_json(), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    json.loads(text)                                  # what is written must load again
    return us.write_if_changed(store_path(anchor), text)


def save_list(anchor, topics: Mapping[str, str], tagger: str) -> bool:
    """Replace the tree's topic list, keeping what the file records per level. True if written.

    Raises TopicStoreError for a tagger outside TAGGERS, more than MAX_LIST topics, two names
    that trim to the same tag, or a meaning that is not one line of at most MAX_MEANING
    characters; InvalidTopic for a name that is not a plain tag. Whether a dropped topic is
    still in use is the caller's question: this module never reads a fact."""
    sig.refuse_if_memory_writes_off()
    if not isinstance(tagger, str) or tagger not in TAGGERS:
        raise TopicStoreError("unknown tagger %r - use one of %s" % (tagger, ", ".join(TAGGERS)))
    if len(topics) > MAX_LIST:
        raise TopicStoreError("%d topics, over the limit of %d" % (len(topics), MAX_LIST))
    clean = {}
    for raw, meaning in topics.items():
        # One name at a time: normalise_topics caps a list at tp.MAX_TOPICS, the per-fact
        # limit, while a tree's list is capped by MAX_LIST above. It also trims, so the
        # trimmed name is the key, and two names trimming to one tag are refused, not merged.
        (name,) = tp.normalise_topics([raw])
        if name in clean:
            raise TopicStoreError("the topic %r is named twice" % (name,))
        why = _meaning_problem(name, meaning)
        if why:
            raise TopicStoreError(why)
        clean[name] = meaning.strip()
    with sig.memory_lock(store_path(anchor)):
        old = load(anchor)
        return _write(anchor, TopicFile(tagger=Tagger(tagger), topics=clean,
                                        levels=old.levels if old else {}))


def record_level(anchor, level, digest: str, before: Callable[[], object] | None = None) -> bool:
    """Record the descriptor digest `level`'s topics were chosen from. True if written.

    Raises TopicStoreError when the tree has no list, the file cannot be used, or `level` is not
    below `anchor`. `before`, when given, runs under the file's lock once all of that is checked
    and ahead of this write: a caller whose own write (the descriptor) must not happen unless this
    one can puts it there, so a refusal here leaves both files as they were."""
    sig.refuse_if_memory_writes_off()
    with sig.memory_lock(store_path(anchor)):
        data = load(anchor)
        if data is None:
            raise TopicStoreError("this tree has no topic list yet")
        key = level_key(anchor, level)
        if before is not None:
            before()
        return _write(anchor, TopicFile(tagger=data.tagger, topics=data.topics,
                                        levels={**data.levels, key: digest}))
