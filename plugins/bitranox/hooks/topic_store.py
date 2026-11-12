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
from pathlib import Path

import self_improve_signals as sig
import topic_placement as tp
import uuid_store as us

__all__ = ["MAX_LIST", "MAX_MEANING", "TAGGERS", "TopicStoreError", "level_key", "load",
           "record_level", "save_list", "store_path"]

MAX_LIST = 64
"""Most topics a tree's list may hold: every one becomes a question about every fact."""
MAX_MEANING = 200
TAGGERS = ("jev", "opus")
_EMPTY = {"version": 1, "tagger": "opus", "topics": {}, "levels": {}}


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


def load(anchor) -> dict | None:
    """The topic file's content, or None when the tree has none. Raises TopicStoreError for a
    file that is not the JSON object this module writes, and TreeWalkError for one that cannot
    be read: a list read as absent would switch placement by topic off without a word."""
    text = us.read_store_text(store_path(anchor))
    if text == "":
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise TopicStoreError("%s is not valid JSON (%s)" % (store_path(anchor), exc)) from exc
    if not (isinstance(data, dict) and isinstance(data.get("topics"), dict)
            and isinstance(data.get("levels", {}), dict)):
        raise TopicStoreError("%s is not a topic file (no 'topics' object)" % store_path(anchor))
    data.setdefault("levels", {})
    data.setdefault("tagger", "opus")
    return data


def _write(anchor, data) -> bool:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    json.loads(text)                                  # what is written must load again
    return us.write_if_changed(store_path(anchor), text)


def save_list(anchor, topics: Mapping[str, str], tagger: str) -> bool:
    """Replace the tree's topic list, keeping what the file records per level. True if written.

    Raises TopicStoreError for a tagger outside TAGGERS, more than MAX_LIST topics, two names
    that trim to the same tag, or a meaning that is not one line of at most MAX_MEANING
    characters; InvalidTopic for a name that is not a plain tag. Whether a dropped topic is
    still in use is the caller's question: this module never reads a fact."""
    sig.refuse_if_memory_writes_off()
    if tagger not in TAGGERS:
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
        if not isinstance(meaning, str) or not meaning.strip() or len(meaning) > MAX_MEANING \
                or meaning.splitlines() != [meaning]:
            raise TopicStoreError("the meaning of %r must be one line of 1 to %d characters"
                                  % (name, MAX_MEANING))
        clean[name] = meaning.strip()
    with sig.memory_lock(store_path(anchor)):
        data = load(anchor) or dict(_EMPTY)
        return _write(anchor, {"version": 1, "tagger": tagger, "topics": clean,
                               "levels": dict(data["levels"])})


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
        levels = dict(data["levels"])
        levels[key] = digest
        return _write(anchor, {**data, "levels": levels})
