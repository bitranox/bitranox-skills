"""Every function and method memory_engine defines carries a full signature.

The engine is imported by hooks and skill scripts that type-check strictly. An unannotated
parameter or return here reaches each of those callers as "partially unknown", so none of them
can be clean, and the gap stays invisible to the engine's own behaviour tests.
"""

import inspect
from collections.abc import Callable, Iterator
from types import FunctionType
from typing import TypeIs

import memory_engine as E
import pytest


def _unannotated(fn: Callable[..., object]) -> list[str]:
    """The parameters of `fn` (unwrapped past a decorator) with no annotation, plus "return".
    `self` and `cls` are exempt: the checker types them from the class."""
    sig = inspect.signature(inspect.unwrap(fn))
    missing = [name for name, p in sig.parameters.items()
               if p.annotation is inspect.Parameter.empty and name not in ("self", "cls")]
    if sig.return_annotation is inspect.Signature.empty:
        missing.append("return")
    return missing


_ENGINE_FILE = inspect.getsourcefile(E)

# Written by the interpreter rather than in the source: the lazy-annotation function Python 3.14
# compiles for every annotated module and class.
_GENERATED = frozenset({"__annotate__", "__annotate_func__"})


def _written_here(obj: object, name: str) -> TypeIs[FunctionType]:
    """True for a function whose code is in memory_engine.py itself, looked up past a decorator
    (placement_lock is a contextmanager). Members a dataclass, NamedTuple, enum or Protocol
    generates (__eq__, _make, __subclasshook__) are compiled elsewhere, so they are not the
    engine's to annotate."""
    if name in _GENERATED or not inspect.isfunction(obj):
        return False
    return inspect.getsourcefile(inspect.unwrap(obj)) == _ENGINE_FILE


def _methods(cls: type) -> Iterator[tuple[str, Callable[..., object]]]:
    """Each method `cls` itself defines, a property's accessors included. Read through the class,
    a staticmethod comes back as its function and a classmethod as a method bound to it."""
    for name, member in vars(cls).items():
        if isinstance(member, property):
            parts: list[object] = [member.fget, member.fset, member.fdel]
        else:
            found = getattr(cls, name)
            parts = [found.__func__ if inspect.ismethod(found) else found]
        for part in parts:
            if _written_here(part, name):
                yield name, part


def _engine_callables() -> list[tuple[str, Callable[..., object]]]:
    """(qualified name, function) for every function and method the module itself defines;
    names it re-exports from a sibling module (slugify, read_store_text) are that module's."""
    found: list[tuple[str, Callable[..., object]]] = []
    for name, obj in vars(E).items():
        if _written_here(obj, name):
            found.append((name, obj))
        elif inspect.isclass(obj) and inspect.getmodule(obj) is E:
            found.extend(("%s.%s" % (name, method), fn) for method, fn in _methods(obj))
    return sorted(found, key=lambda item: item[0])


_CALLABLES = _engine_callables()


def test_the_scan_sees_the_public_api_and_the_cli_handlers() -> None:
    names = {name for name, _fn in _CALLABLES}
    expected = {"add_or_update_entry", "read_store", "move_entry", "render_topics",
                "set_fact_topics", "heal", "main", "_main", "_topic_read", "_topic_write",
                "placement_lock", "Entry.__init__", "_Placer.__call__"}
    assert expected <= names, sorted(expected - names)
    assert len(names) > 200


@pytest.mark.parametrize(("name", "fn"), _CALLABLES, ids=[name for name, _fn in _CALLABLES])
def test_every_engine_function_is_fully_annotated(name: str, fn: Callable[..., object]) -> None:
    assert _unannotated(fn) == [], name
