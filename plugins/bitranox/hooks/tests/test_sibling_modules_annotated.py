"""Every function in the store's sibling modules stays fully annotated.

memory_engine is type-checked strictly and calls uuid_store, topic_store and tell_chars. Strict
pyright reads every unannotated function as partially unknown, and everything built from its
result inherits that, so a caller can only be strict-clean while these modules stay annotated. CI
runs no type checker, so this pins the property itself: a new function, or an edited one that
loses a parameter or return annotation, fails here.

The check reads the SOURCE with `ast`, not the imported module: `typing.overload` stubs and
annotations evaluated lazily are both invisible to `inspect`, and an unannotated parameter has no
runtime trace at all.
"""
import ast
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
MODULES = ("uuid_store.py", "topic_store.py", "tell_chars.py")


def _gaps(source: str) -> list[str]:
    """`<function>: <what is missing>` for every def in `source` lacking an annotation. The first
    parameter of a method (`self`, `cls`) is exempt, as type checkers infer it; a staticmethod has
    no such parameter."""
    gaps: list[str] = []
    for owner in ast.walk(ast.parse(source)):
        body = getattr(owner, "body", None)
        if not isinstance(body, list):
            continue
        for node in body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            name = node.name
            if isinstance(owner, ast.ClassDef):
                name = "%s.%s" % (owner.name, node.name)
                static = any(isinstance(d, ast.Name) and d.id == "staticmethod"
                             for d in node.decorator_list)
                params = params if static else params[1:]
            params += [a for a in (args.vararg, args.kwarg) if a is not None]
            gaps += ["%s: parameter %s" % (name, a.arg) for a in params if a.annotation is None]
            if node.returns is None:
                gaps.append("%s: return" % name)
    return gaps


@pytest.mark.parametrize("module", MODULES)
def test_every_function_is_annotated(module: str) -> None:
    source = (HOOKS / module).read_text(encoding="utf-8")
    assert _gaps(source) == []


def test_the_check_finds_a_missing_parameter_and_return() -> None:
    source = ("def f(a: int, b, *rest, **kw: str):\n    return a\n"
              "class C:\n    def m(self, x) -> None:\n        pass\n"
              "    def ok(self) -> int:\n        def inner(y):\n            return y\n"
              "        return inner(1)\n"
              "    @staticmethod\n    def s(z) -> None:\n        pass\n")
    assert _gaps(source) == ["f: parameter b", "f: parameter rest", "f: return",
                             "C.m: parameter x", "C.s: parameter z",
                             "inner: parameter y", "inner: return"]


def test_the_check_passes_a_fully_annotated_source() -> None:
    source = ("class C:\n    def m(self, x: int, *a: int, k: str = '', **kw: int) -> None:\n"
              "        pass\n"
              "def f(a: int, /, b: int) -> int:\n    return a + b\n")
    assert _gaps(source) == []
