"""Typed facade over the untyped hook and store modules the Jev shadow tool uses.

`classifier`, `self_improve_signals`, `memory_engine` and `reconcile_memory_index` carry no
annotations, so under a strict type checker every call into them is partially unknown. This module
states the types the shadow tool relies on - as Protocols the imported modules are cast to - and
exposes plain typed functions. The other jev_shadow modules call these, never the hook modules.

It also puts the hooks dir on sys.path, the same setup `classifier_eval.py` uses. Standard library
only.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol, TypedDict, cast

_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
for _d in (str(_HOOKS), str(_HERE)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import classifier as _classifier
import memory_engine as _memory_engine
import self_improve_signals as _signals

import reconcile_memory_index as _reconcile

__all__ = [
    "MisplacedCandidate",
    "StoreEntry",
    "TreeWalkError",
    "curated_levels_under",
    "find_misplaced",
    "load_config",
    "memory_lock",
    "parse_frontmatter",
    "plugin_version",
    "prepare_state",
    "read_store",
]


class StoreEntry(Protocol):
    """One curated fact as `memory_engine.read_store` returns it (the fields used here)."""

    @property
    def slug(self) -> str: ...

    @property
    def hook(self) -> str: ...


class MisplacedCandidate(TypedDict):
    """One `reconcile_memory_index.find_misplaced` candidate."""

    level: str
    slug: str
    target_anchor: str
    paths: list[str]


class _Classifier(Protocol):
    def prepare_state(
        self, fields: Mapping[str, str], key: str | None = ..., cap: int = ...
    ) -> tuple[dict[str, str], int]: ...


class _Signals(Protocol):
    def load_config(self) -> dict[str, object]: ...

    def memory_lock(self, target_path: Path) -> AbstractContextManager[None]: ...


class _MemoryEngine(Protocol):
    TreeWalkError: type[Exception]

    def curated_levels_under(self, anchor: str) -> list[str]: ...

    def read_store(self, proj: str) -> tuple[str, list[StoreEntry], dict[str, str]]: ...


class _Reconcile(Protocol):
    def find_misplaced(self, anchor: str) -> list[MisplacedCandidate]: ...

    def parse_frontmatter(self, text: str) -> tuple[dict[str, str], str]: ...


_cl = cast("_Classifier", _classifier)
_sig = cast("_Signals", _signals)
_me = cast("_MemoryEngine", _memory_engine)
_rec = cast("_Reconcile", _reconcile)

# The classifier's own manifest reader, so shadow rows name the release the way its rows do. It is
# module-private there, so it is looked up by name rather than reached into as an attribute.
_PLUGIN_VERSION_READER = "_plugin_version"
_plugin_version = cast(
    "Callable[[], str]", getattr(_classifier, _PLUGIN_VERSION_READER)
)

TreeWalkError: type[Exception] = _me.TreeWalkError


def prepare_state(
    fields: Mapping[str, str], cap: int | None = None
) -> tuple[dict[str, str], int]:
    """Redact every field and cap its length (`classifier.prepare_state`); (state, redactions)."""
    if cap is None:
        return _cl.prepare_state(fields)
    return _cl.prepare_state(fields, cap=cap)


def plugin_version() -> str:
    """The version of the plugin this file shipped in, or "" when the manifest is unreadable."""
    return _plugin_version()


def load_config() -> dict[str, object]:
    """The machine-local memory config merged over its defaults (`self_improve_signals`)."""
    return _sig.load_config()


def memory_lock(target_path: Path) -> AbstractContextManager[None]:
    """The cross-platform `<target>.lock` lock; raises TimeoutError past its wait."""
    return _sig.memory_lock(target_path)


def curated_levels_under(anchor: str) -> list[str]:
    """Every curated level dir under `anchor`; raises TreeWalkError on an unreadable dir."""
    return _me.curated_levels_under(anchor)


def read_store(level: str) -> tuple[str, list[StoreEntry], dict[str, str]]:
    """(scope, entries, bodies by slug) of one level's store."""
    return _me.read_store(level)


def find_misplaced(anchor: str) -> list[MisplacedCandidate]:
    """Facts under `anchor` whose body cites only another tree's paths."""
    return _rec.find_misplaced(anchor)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """(frontmatter fields, body) of a stored fact body."""
    return _rec.parse_frontmatter(text)
