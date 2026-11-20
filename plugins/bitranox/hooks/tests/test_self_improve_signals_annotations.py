"""Every function and method self_improve_signals defines carries a full signature.

The module is imported by the hooks, the memory engine and the skill scripts, and those type-check
strictly. An unannotated parameter or return here reaches each caller as "partially unknown", so
none of them can be clean, and the gap stays invisible to the module's own behaviour tests.

Read from the source with ast rather than through inspect, so a function nested inside another
(resolve_transcript's sort key) is held to the same rule as a module-level one: pyright checks
both, and inspect cannot reach the inner one.
"""

import ast
import inspect

import pytest
import self_improve_signals as S

_EXEMPT = frozenset({"self", "cls"})    # the checker types these from the class


def _missing(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """The parameters of `fn` with no annotation, plus "return" when it has no return annotation."""
    a = fn.args
    params = [*a.posonlyargs, *a.args, *a.kwonlyargs]
    params += [p for p in (a.vararg, a.kwarg) if p is not None]
    missing = [p.arg for p in params if p.annotation is None and p.arg not in _EXEMPT]
    if fn.returns is None:
        missing.append("return")
    return missing


def _defs(tree: ast.AST, prefix: str = "") -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """(qualified name, node) for every function definition in `tree`, nested ones included."""
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + node.name
            found.append((name, node))
            found.extend(_defs(node, name + "."))
        elif isinstance(node, ast.ClassDef):
            found.extend(_defs(node, prefix + node.name + "."))
        else:
            found.extend(_defs(node, prefix))
    return found


_DEFS = sorted(_defs(ast.parse(inspect.getsource(S))), key=lambda item: item[0])


def test_the_scan_reaches_public_private_nested_and_method_definitions() -> None:
    names = {name for name, _node in _DEFS}
    expected = {"proj_key", "load_config", "save_config", "add_contribution", "inert_snippet",
                "skill_usage", "_reclaim_stale_lock", "resolve_transcript._mtime",
                "_FixtureScan.__init__", "_FixtureScan.is_data", "ClaimHeld.__init__", "memory_lock"}
    assert expected <= names, sorted(expected - names)
    assert len(names) > 190


def test_the_check_reports_an_unannotated_definition() -> None:
    """A known negative: the same scan must name what it exists to catch, nested and in a class."""
    planted = ast.parse("def f(a, b: int): pass\nclass C:\n    def m(self, x) -> None:\n"
                        "        def inner(): pass\n")
    report = {name: _missing(node) for name, node in _defs(planted)}
    assert report == {"f": ["a", "return"], "C.m": ["x"], "C.m.inner": ["return"]}


@pytest.mark.parametrize(("name", "node"), _DEFS, ids=[name for name, _node in _DEFS])
def test_every_function_is_fully_annotated(name: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
    assert _missing(node) == [], name
