"""Find regex patterns used without re.compile(), and patterns whose search is quadratic.

Two reports.

Uncompiled calls: calls like re.match(r'pattern', ...) inside a function body where the pattern
is a string literal. These should be re.compile()'d at module level: the re module caches
compiled patterns (512 by default), so such a call pays a cache lookup on every call, and a real
recompile only when more distinct patterns cycle than the cache holds. A call at module or class
level runs once, so it is not reported.

Quadratic starts: a pattern (compiled or not, in any scope) whose search can START at every
position of one long run and then read to the run's end before it fails, so N characters cost
about N squared steps under search, finditer, findall, sub, subn and split. The pattern SOURCE is
parsed with the re module's own parser; the shape is a leading unbounded repeat of one character
class (``[\\w./-]+``, ``\\s*``, ``.*``) whose starts no guard holds back inside a run of its own
characters (a ``^`` without MULTILINE, a negative lookbehind of the same class), followed by more
pattern. Whether a start inside the run then fails is confirmed by running the compiled pattern
once on a short witness run of each character the class accepts; the report names those runs, so
a growth test (the same run at N and 8N) can be built from it. Two shapes are named:

- ``class-run-before-suffix``: ``[\\w./-]+\\.(?:py|sh)\\b`` over a long token with no suffix.
  Fix: a negative lookbehind of the SAME class before the repeat.
- ``newline-start-then-blanks``: a start alternative that matches after every newline
  (``(?<=[;&|\\n])``, ``(?m)^``) followed by ``\\s*``, over many blank lines. Fix: ``[^\\S\\n]*``
  after the anchor, so each newline is a start of its own.

A compiled pattern bound to a name the file only ever calls ``.match`` or ``.fullmatch`` on is not
reported: those try one start. Patterns built by ``+`` from module-level string constants are
resolved. Not modelled: a leading literal before the repeat, a mixed run under ``\\b`` beyond one
word/non-word pair, and flags passed through a variable (inline flags are read).

Recognised spellings: ``re.match(...)``, ``import re as X`` then ``X.match(...)``,
``from re import match [as m]`` then ``match(...)``, and the ``pattern=`` keyword.

Usage: python find_uncompiled_regex.py FILE [FILE ...]

Exit codes: 0 every file was scanned (whether or not calls were found), 2 at least one
path was missing or could not be read or parsed (its ERROR line goes to stderr; the report
for the files that were scanned is still printed), or the arguments were invalid.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import os
import re
import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol, TypedDict, cast

# re module functions that accept a pattern string
RE_FUNCTIONS = frozenset({
    'match', 'search', 'findall', 'finditer',
    'sub', 'subn', 'split', 'fullmatch',
})

# Functions whose pattern is searched from many starts, with the position of their flags argument.
# match and fullmatch try one start, so they cannot rescan a run from every position.
_MULTI_START_FLAGS_INDEX = {
    'compile': 1, 'search': 2, 'finditer': 2, 'findall': 2, 'split': 3, 'sub': 4, 'subn': 4,
}
_SINGLE_START_METHODS = frozenset({'match', 'fullmatch'})

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


class UncompiledFinding(TypedDict):
    file: str
    line: int
    call: str
    suggestion: str


class QuadraticFinding(TypedDict):
    file: str
    line: int
    call: str
    shape: str
    witnesses: list[str]
    suggestion: str


# --- typed facade over the re module's parser ----------------------------------------------
# The parser is private (re._parser from 3.11, the public sre_parse on 3.10, deprecated since),
# so it is reached through a Protocol and every value it returns is narrowed with isinstance.

class _ParseState(Protocol):
    @property
    def flags(self) -> int: ...


class _ParsedPattern(Protocol):
    @property
    def state(self) -> _ParseState: ...

    @property
    def data(self) -> list[object]: ...


class _ParserModule(Protocol):
    MAXREPEAT: int

    def parse(self, pattern: str | bytes, flags: int = 0, /) -> _ParsedPattern: ...


def _load_parser() -> _ParserModule:
    try:
        module = importlib.import_module('re._parser')
    except ImportError:  # Python 3.10: the parser is the public sre_parse module
        module = importlib.import_module('sre_parse')
    return cast(_ParserModule, module)


_PARSER = _load_parser()


class _Unsupported(Exception):
    """A parse-tree shape this checker does not model; the pattern is skipped, not reported."""


@dataclass(frozen=True)
class _Chars:
    """One character out of *members* (a subset of the probe alphabet)."""
    members: frozenset[str]


@dataclass(frozen=True)
class _Repeat:
    low: int
    high: int | None  # None: unbounded
    body: tuple[_Node, ...]


@dataclass(frozen=True)
class _Group:
    body: tuple[_Node, ...]


@dataclass(frozen=True)
class _Branch:
    alts: tuple[tuple[_Node, ...], ...]


@dataclass(frozen=True)
class _At:
    code: str


@dataclass(frozen=True)
class _Look:
    behind: bool
    negative: bool
    body: tuple[_Node, ...]


@dataclass(frozen=True)
class _Opaque:
    op: str


_Node = _Chars | _Repeat | _Group | _Branch | _At | _Look | _Opaque

# Characters each class is evaluated on: all of ASCII plus a few non-ASCII ones a str class may
# hold (a non-breaking space, a Latin letter, a line separator, a CJK letter).
_STR_PROBES = tuple(chr(i) for i in range(128)) + tuple(chr(c) for c in (0xA0, 0xE9, 0x2028, 0x4E2D))
_BYTES_PROBES = tuple(chr(i) for i in range(256))  # bytes as latin-1 characters

_CATEGORY_SOURCE = {
    'CATEGORY_DIGIT': r'\d', 'CATEGORY_NOT_DIGIT': r'\D',
    'CATEGORY_SPACE': r'\s', 'CATEGORY_NOT_SPACE': r'\S',
    'CATEGORY_WORD': r'\w', 'CATEGORY_NOT_WORD': r'\W',
}
_CLASS_FLAGS = re.IGNORECASE | re.DOTALL | re.ASCII | re.LOCALE


@dataclass(frozen=True)
class _Context:
    """How one pattern's classes are evaluated: its flags and whether it is a bytes pattern."""
    flags: int
    is_bytes: bool

    @property
    def probes(self) -> tuple[str, ...]:
        return _BYTES_PROBES if self.is_bytes else _STR_PROBES


def _op_name(op: object) -> str:
    name = getattr(op, 'name', None)
    if not isinstance(name, str):
        raise _Unsupported(repr(op))
    return name


def _pairs(subpattern: object) -> list[tuple[str, object]]:
    """The (opcode name, argument) items of a parser SubPattern or of an IN item list."""
    data = getattr(subpattern, 'data', subpattern)
    if not isinstance(data, list):
        raise _Unsupported(type(subpattern).__name__)
    out: list[tuple[str, object]] = []
    for entry in cast(list[object], data):
        op, arg = _tuple(entry, 2)
        out.append((_op_name(op), arg))
    return out


def _tuple(arg: object, size: int) -> tuple[object, ...]:
    kind = type(arg).__name__
    if isinstance(arg, tuple):
        items = cast(tuple[object, ...], arg)
        if len(items) == size:
            return items
    raise _Unsupported(f'expected a {size}-tuple, got {kind}')


def _int(arg: object) -> int:
    if not isinstance(arg, int):
        raise _Unsupported(repr(arg))
    return arg


def _class_item_source(op: str, arg: object) -> str:
    if op == 'LITERAL':
        return re.escape(chr(_int(arg)))
    if op == 'RANGE':
        low, high = _tuple(arg, 2)
        return f'{re.escape(chr(_int(low)))}-{re.escape(chr(_int(high)))}'
    if op == 'CATEGORY' and _op_name(arg) in _CATEGORY_SOURCE:
        return _CATEGORY_SOURCE[_op_name(arg)]
    if op == 'NEGATE':
        return '^'
    raise _Unsupported(op)


def _single_char_source(op: str, arg: object) -> str:
    """Regex source matching exactly the one character the (op, arg) item matches."""
    if op == 'LITERAL':
        return re.escape(chr(_int(arg)))
    if op == 'NOT_LITERAL':
        return f'[^{re.escape(chr(_int(arg)))}]'
    if op == 'ANY':
        return '.'
    return '[' + ''.join(_class_item_source(o, a) for o, a in _pairs(arg)) + ']'


def _members(source: str, ctx: _Context) -> frozenset[str]:
    flags = ctx.flags & _CLASS_FLAGS
    if ctx.is_bytes:
        compiled_b = re.compile(source.encode('latin-1'), flags)
        return frozenset(c for c in ctx.probes if compiled_b.fullmatch(c.encode('latin-1')))
    compiled = re.compile(source, flags & ~re.LOCALE)
    return frozenset(c for c in ctx.probes if compiled.fullmatch(c))


def _convert(subpattern: object, ctx: _Context) -> tuple[_Node, ...]:
    return tuple(_convert_item(op, arg, ctx) for op, arg in _pairs(subpattern))


def _repeat(arg: object, ctx: _Context) -> _Node:
    low, high, body = _tuple(arg, 3)
    unbounded = _int(high) == _PARSER.MAXREPEAT
    return _Repeat(_int(low), None if unbounded else _int(high), _convert(body, ctx))


def _branch(arg: object, ctx: _Context) -> _Node:
    alts = _tuple(arg, 2)[1]
    if not isinstance(alts, list):
        raise _Unsupported('BRANCH')
    return _Branch(tuple(_convert(alt, ctx) for alt in cast(list[object], alts)))


def _look(arg: object, ctx: _Context, *, negative: bool) -> _Node:
    direction, body = _tuple(arg, 2)
    return _Look(_int(direction) < 0, negative, _convert(body, ctx))


_CONVERTERS: dict[str, Callable[[object, _Context], _Node]] = {
    'MAX_REPEAT': _repeat,
    'MIN_REPEAT': _repeat,
    'POSSESSIVE_REPEAT': _repeat,
    'SUBPATTERN': lambda arg, ctx: _Group(_convert(_tuple(arg, 4)[3], ctx)),
    'ATOMIC_GROUP': lambda arg, ctx: _Group(_convert(arg, ctx)),
    'BRANCH': _branch,
    'AT': lambda arg, _ctx: _At(_op_name(arg)),
    'ASSERT': lambda arg, ctx: _look(arg, ctx, negative=False),
    'ASSERT_NOT': lambda arg, ctx: _look(arg, ctx, negative=True),
}
_CHAR_OPS = frozenset({'LITERAL', 'NOT_LITERAL', 'ANY', 'IN'})


def _convert_item(op: str, arg: object, ctx: _Context) -> _Node:
    if op in _CHAR_OPS:
        return _Chars(_members(_single_char_source(op, arg), ctx))
    converter = _CONVERTERS.get(op)
    return converter(arg, ctx) if converter else _Opaque(op)


# --- where a match can start -----------------------------------------------------------------

@dataclass(frozen=True)
class _Start:
    """A leading unbounded class repeat: the guards before it, its class, the pattern after it."""
    guards: tuple[_Node, ...]
    chars: frozenset[str]
    rest: tuple[_Node, ...]


_MAX_STARTS = 32


def _is_guard(node: _Node) -> bool:
    if isinstance(node, (_At, _Look)):
        return True
    return isinstance(node, _Branch) and all(all(_is_guard(n) for n in alt) for alt in node.alts)


def _repeat_class(node: _Node) -> frozenset[str] | None:
    """The class of an unbounded repeat of ONE character, else None."""
    if not isinstance(node, _Repeat) or node.high is not None or len(node.body) != 1:
        return None
    (body,) = node.body
    if isinstance(body, _Group) and len(body.body) == 1:
        (body,) = body.body
    return body.members if isinstance(body, _Chars) else None


def _starts(seq: tuple[_Node, ...], guards: tuple[_Node, ...] = ()) -> Iterator[_Start]:
    if not seq:
        return
    head, tail = seq[0], seq[1:]
    if isinstance(head, _Look) and not head.behind:
        yield from _starts(tail, guards)  # a lookahead holds back no start inside a run
    elif _is_guard(head):
        yield from _starts(tail, (*guards, head))
    elif isinstance(head, _Group):
        yield from _starts((*head.body, *tail), guards)
    elif isinstance(head, _Branch):
        for alt in head.alts:
            yield from _starts((*alt, *tail), guards)
    else:
        chars = _repeat_class(head)
        if chars:
            yield _Start(guards, chars, tail)


# --- guards, evaluated on a concrete witness text ---------------------------------------------

def _is_word(ch: str, ctx: _Context) -> bool:
    ascii_only = ctx.is_bytes or bool(ctx.flags & re.ASCII)
    return (ch.isalnum() or ch == '_') and (ch.isascii() or not ascii_only)


def _at_holds(code: str, text: str, i: int, ctx: _Context) -> bool:
    multiline = bool(ctx.flags & re.MULTILINE)
    prev_word = i > 0 and _is_word(text[i - 1], ctx)
    next_word = i < len(text) and _is_word(text[i], ctx)
    holds = {
        'AT_BEGINNING': i == 0 or (multiline and text[i - 1] == '\n'),
        'AT_BEGINNING_STRING': i == 0,
        'AT_BOUNDARY': prev_word != next_word,
        'AT_NON_BOUNDARY': prev_word == next_word,
        'AT_END': i == len(text) or (text[i] == '\n' and (multiline or i == len(text) - 1)),
        'AT_END_STRING': i == len(text),
    }
    return holds.get(code, False)


def _behind_matches(body: tuple[_Node, ...], text: str, i: int) -> bool | None:
    """Whether a lookbehind of fixed single characters matches before *i*; None if not modelled."""
    chars = [n for n in body if not isinstance(n, _At)]
    if not all(isinstance(n, _Chars) for n in chars):
        return None
    if i < len(chars):
        return False
    window = text[i - len(chars):i]
    return all(ch in cast(_Chars, n).members for ch, n in zip(window, chars, strict=True))


def _guard_holds(node: _Node, text: str, i: int, ctx: _Context) -> bool:
    if isinstance(node, _At):
        return _at_holds(node.code, text, i, ctx)
    if isinstance(node, _Branch):
        return any(all(_guard_holds(n, text, i, ctx) for n in alt) for alt in node.alts)
    if isinstance(node, _Look) and node.behind:
        matched = _behind_matches(node.body, text, i)
        # A lookbehind this checker cannot evaluate counts as holding every start back.
        return matched is not None and matched != node.negative
    return True


# --- the witness search -----------------------------------------------------------------------

_RUN = 16
_TERMINATOR_PREFERENCE = ('\n', ' ', 'x', '#', '\x00')


def _unit_order(ch: str) -> tuple[bool, bool, str]:
    # Letters and digits first, then other printable characters: the report shows the first few.
    return (not ch.isalnum(), not ch.isprintable(), ch)


def _units(start: _Start, ctx: _Context) -> list[str]:
    """Run units to try: each class character alone, plus one word/non-word pair under \\b."""
    units = sorted(start.chars, key=_unit_order)
    if any(isinstance(g, _At) and g.code == 'AT_BOUNDARY' for g in start.guards):
        words = [c for c in units if _is_word(c, ctx)]
        others = [c for c in units if not _is_word(c, ctx)]
        if words and others:
            units.append(words[0] + others[0])
    return units


def _terminators(chars: frozenset[str]) -> list[str]:
    return ['', *[t for t in _TERMINATOR_PREFERENCE if t not in chars][:3]]


def _admits_inner_starts(start: _Start, run: str, ctx: _Context) -> bool:
    admitted = sum(all(_guard_holds(g, run, i, ctx) for g in start.guards) for i in range(1, len(run)))
    return admitted >= len(run) // 2


def _inner_starts_fail(compiled: re.Pattern[str] | re.Pattern[bytes], text: str, run_len: int,
                       ctx: _Context) -> bool:
    if ctx.is_bytes:
        found_b = cast('re.Pattern[bytes]', compiled).search(text.encode('latin-1'), 1)
        first = found_b.start() if found_b else None
    else:
        found = cast('re.Pattern[str]', compiled).search(text, 1)
        first = found.start() if found else None
    return first is None or first >= run_len


def _witness(start: _Start, unit: str, compiled: re.Pattern[str] | re.Pattern[bytes],
             ctx: _Context) -> str | None:
    run = unit * (_RUN // len(unit))
    if not _admits_inner_starts(start, run, ctx):
        return None
    for terminator in _terminators(start.chars):
        if _inner_starts_fail(compiled, run + terminator, len(run), ctx):
            end = f' + {terminator!r}' if terminator else ' (end of text)'
            return f'{unit!r} * N{end}'
    return None


@dataclass(frozen=True)
class QuadraticVerdict:
    shape: str
    witnesses: tuple[str, ...]


_NEWLINE_SHAPE = 'newline-start-then-blanks'
_CLASS_SHAPE = 'class-run-before-suffix'


def _witnesses(starts: list[_Start], compiled: re.Pattern[str] | re.Pattern[bytes],
               ctx: _Context) -> list[str]:
    found: list[str] = []
    for start in starts:
        if not start.rest:
            continue  # a bare class repeat consumes the whole run: one start per run
        for unit in _units(start, ctx):
            witness = _witness(start, unit, compiled, ctx)
            if witness and witness not in found:
                found.append(witness)
    return found


def quadratic_verdict(pattern: str | bytes, flags: int = 0) -> QuadraticVerdict | None:
    """Return the quadratic-start shape of *pattern*, or None when no witness run was found.

    Raises re.error when the pattern does not compile.

    >>> quadratic_verdict(r'[\\w./-]+\\.py').shape
    'class-run-before-suffix'
    >>> quadratic_verdict(r'(?<![\\w./-])[\\w./-]+\\.py') is None
    True
    """
    compiled = re.compile(pattern, flags)
    parsed = _PARSER.parse(pattern, flags)
    ctx = _Context(parsed.state.flags, isinstance(pattern, bytes))
    try:
        starts = list(_starts(_convert(parsed, ctx)))[:_MAX_STARTS]
    except _Unsupported:
        return None
    found = _witnesses(starts, compiled, ctx)
    if not found:
        return None
    only_newline = all(w.startswith("'\\n' * N") for w in found)
    guarded = any(s.guards for s in starts)
    shape = _NEWLINE_SHAPE if only_newline and guarded else _CLASS_SHAPE
    return QuadraticVerdict(shape, tuple(found))


_SHAPE_FIX = {
    _CLASS_SHAPE: 'Anchor the start with a negative lookbehind of the SAME class as the leading '
                  'repeat, e.g. (?<![\\w./-])[\\w./-]+',
    _NEWLINE_SHAPE: 'After the newline start, use [^\\S\\n]* instead of \\s*, so each newline is a '
                    'start of its own',
}


# --- source scanning ----------------------------------------------------------------------

def _re_names(tree: ast.AST) -> tuple[set[str], dict[str, str]]:
    """Return (names bound to the re module, {local name: re function} from-imports)."""
    wanted = RE_FUNCTIONS | {'compile'}
    modules: set[str] = {'re'}
    functions: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.asname for a in node.names if a.name == 're' and a.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == 're' and not node.level:
            functions.update((a.asname or a.name, a.name) for a in node.names if a.name in wanted)
    return modules, functions


def _re_function(call: ast.Call, modules: set[str], functions: dict[str, str]) -> str | None:
    """The re function *call* invokes (e.g. 'match'), or None when it is not an re call."""
    func = call.func
    if isinstance(func, ast.Attribute):
        is_re = isinstance(func.value, ast.Name) and func.value.id in modules
        return func.attr if is_re else None
    if isinstance(func, ast.Name):
        return functions.get(func.id)
    return None


def _pattern_arg(call: ast.Call) -> ast.expr | None:
    if call.args:
        return call.args[0]
    return next((kw.value for kw in call.keywords if kw.arg == 'pattern'), None)


def _finding(file_path: str, call: ast.Call, name: str) -> UncompiledFinding | None:
    pattern = _pattern_arg(call)
    if not isinstance(pattern, (ast.Constant, ast.JoinedStr)):
        return None
    if isinstance(pattern, ast.JoinedStr):
        pattern_repr = '<f-string>'
        suggestion = 'Dynamic pattern  - cannot compile at module level; consider caching or restructuring'
    else:
        pattern_repr = repr(pattern.value)
        suggestion = f'Compile at module level: _RE = re.compile({pattern_repr})'
    return {
        'file': file_path,
        'line': call.lineno,
        'call': f're.{name}({pattern_repr}, ...)',
        'suggestion': suggestion,
    }


def _scoped_children(node: ast.AST, in_function: bool) -> list[tuple[ast.AST, bool]]:
    """(child, runs inside a function body) for each child of *node*.

    Only a function's BODY runs on every call. Its decorators, default values and annotations
    run where the def or lambda itself runs - once at module level, once per call of an
    enclosing function - so they keep the enclosing scope's answer."""
    if not isinstance(node, _FUNCTION_NODES):
        return [(child, in_function) for child in ast.iter_child_nodes(node)]
    body: Sequence[ast.AST] = node.body if isinstance(node.body, list) else [node.body]
    body_ids = {id(stmt) for stmt in body}
    return [(child, in_function or id(child) in body_ids) for child in ast.iter_child_nodes(node)]


def _calls_in_function_bodies(tree: ast.AST) -> Iterator[ast.Call]:
    """Yield every Call that runs each time a def, async def or lambda body runs."""
    def walk(node: ast.AST, in_function: bool) -> Iterator[ast.Call]:
        for child, inside in _scoped_children(node, in_function):
            if inside and isinstance(child, ast.Call):
                yield child
            yield from walk(child, inside)
    yield from walk(tree, False)


def _parse(file_path: str) -> ast.Module:
    # Bytes, not text: ast.parse then honours a UTF-8 BOM and a PEP 263 coding cookie
    # exactly as the interpreter does.
    with open(file_path, 'rb') as f:
        return ast.parse(f.read(), filename=file_path)


def find_uncompiled_regex(file_path: str) -> list[UncompiledFinding]:
    """Return list of uncompiled regex call sites in *file_path*.

    Raises OSError, SyntaxError or ValueError when the file cannot be read or parsed, so a
    caller can tell "no findings" from "not scanned".
    """
    tree = _parse(file_path)
    modules, functions = _re_names(tree)
    findings: list[UncompiledFinding] = []
    for call in _calls_in_function_bodies(tree):
        name = _re_function(call, modules, functions)
        finding = _finding(file_path, call, name) if name in RE_FUNCTIONS else None
        if finding:
            findings.append(finding)
    findings.sort(key=lambda f: f['line'])
    return findings


# --- quadratic-start scan -------------------------------------------------------------------

def _module_constants(tree: ast.Module) -> dict[str, str | bytes]:
    """Module-level names bound ONCE to a string built from literals, other such names and +."""
    assigned: dict[str, list[ast.expr]] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            assigned.setdefault(stmt.targets[0].id, []).append(stmt.value)
    constants: dict[str, str | bytes] = {}
    for name, values in assigned.items():
        value = _fold(values[0], constants) if len(values) == 1 else None
        if value is not None:
            constants[name] = value
    return constants


def _fold(node: ast.expr, constants: dict[str, str | bytes]) -> str | bytes | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _fold(node.left, constants), _fold(node.right, constants)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, bytes) and isinstance(right, bytes):
            return left + right
    return None


def _flags_value(node: ast.expr | None, modules: set[str]) -> int:
    """The int value of a flags argument built from re.X attributes, | and ints; 0 if unknown."""
    if node is None:
        return 0
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in modules:
        flag = getattr(re, node.attr, None)
        return int(flag) if isinstance(flag, re.RegexFlag) else 0
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _flags_value(node.left, modules) | _flags_value(node.right, modules)
    return 0


def _flags_arg(call: ast.Call, name: str) -> ast.expr | None:
    keyword = next((kw.value for kw in call.keywords if kw.arg == 'flags'), None)
    index = _MULTI_START_FLAGS_INDEX[name]
    return keyword if keyword is not None else (call.args[index] if len(call.args) > index else None)


def _single_start_names(tree: ast.Module) -> set[str]:
    """Names whose every load is a .match/.fullmatch call target: a pattern bound to one never
    searches from many starts."""
    loads: dict[str, int] = {}
    single: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            loads[node.id] = loads.get(node.id, 0) + 1
        elif (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
              and node.attr in _SINGLE_START_METHODS):
            single[node.value.id] = single.get(node.value.id, 0) + 1
    return {name for name, count in single.items() if loads.get(name) == count}


def _compile_targets(tree: ast.Module) -> dict[int, str]:
    """{id of a call node: the single Name it is assigned to}."""
    targets: dict[int, str] = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            targets[id(node.value)] = node.targets[0].id
    return targets


@dataclass(frozen=True)
class _ScanContext:
    modules: set[str]
    functions: dict[str, str]
    constants: dict[str, str | bytes]
    single_start: set[str]
    targets: dict[int, str]


def _scan_context(tree: ast.Module) -> _ScanContext:
    modules, functions = _re_names(tree)
    return _ScanContext(modules, functions, _module_constants(tree), _single_start_names(tree),
                        _compile_targets(tree))


_CALL_TEXT_WIDTH = 70


def _call_text(call: ast.Call, name: str, pattern: ast.expr) -> str:
    source = ast.unparse(pattern)
    if len(source) > _CALL_TEXT_WIDTH:
        source = source[:_CALL_TEXT_WIDTH - 3] + '...'
    return f're.{name}({source}, ...)'


def _quadratic_finding(file_path: str, call: ast.Call, scan: _ScanContext) -> QuadraticFinding | None:
    name = _re_function(call, scan.modules, scan.functions)
    pattern_node = _pattern_arg(call)
    if name not in _MULTI_START_FLAGS_INDEX or pattern_node is None:
        return None
    if scan.targets.get(id(call)) in scan.single_start:
        return None
    pattern = _fold(pattern_node, scan.constants)
    if pattern is None:
        return None
    try:
        verdict = quadratic_verdict(pattern, _flags_value(_flags_arg(call, name), scan.modules))
    except (re.error, ValueError, TypeError, OverflowError):
        return None  # a pattern that does not compile is not this checker's finding
    if verdict is None:
        return None
    return {'file': file_path, 'line': call.lineno, 'call': _call_text(call, name, pattern_node),
            'shape': verdict.shape, 'witnesses': list(verdict.witnesses),
            'suggestion': _SHAPE_FIX[verdict.shape]}


def find_quadratic_regex(file_path: str) -> list[QuadraticFinding]:
    """Return the regex call sites in *file_path* whose search can rescan one run from every start.

    Raises OSError, SyntaxError or ValueError when the file cannot be read or parsed.
    """
    tree = _parse(file_path)
    scan = _scan_context(tree)
    findings: list[QuadraticFinding] = []
    for node in ast.walk(tree):
        finding = _quadratic_finding(file_path, node, scan) if isinstance(node, ast.Call) else None
        if finding:
            findings.append(finding)
    findings.sort(key=lambda f: f['line'])
    return findings


# --- CLI ------------------------------------------------------------------------------------

def _utf8_output() -> None:
    # A cp1252 console cannot encode most non-ASCII paths; the report is read back as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding='utf-8', errors='backslashreplace')


def _scan(paths: list[str]) -> tuple[list[UncompiledFinding], list[QuadraticFinding], int]:
    """Scan *paths*; return (uncompiled, quadratic, number of paths that could not be scanned)."""
    found: list[UncompiledFinding] = []
    quadratic: list[QuadraticFinding] = []
    failed = 0
    for filepath in paths:
        if not os.path.exists(filepath):
            print(f"ERROR not found: {filepath}", file=sys.stderr)
            failed += 1
            continue
        try:
            found.extend(find_uncompiled_regex(filepath))
            quadratic.extend(find_quadratic_regex(filepath))
        except (OSError, SyntaxError, ValueError) as e:
            print(f"ERROR parsing {filepath}: {e}", file=sys.stderr)
            failed += 1
    return found, quadratic, failed


_WITNESSES_SHOWN = 6


def _print_quadratic(findings: list[QuadraticFinding]) -> None:
    print("# Quadratic Regex Starts\n")
    print(f"Found {len(findings)} patterns whose search can rescan one run from every start\n")
    for f in findings:
        shown = ', '.join(f['witnesses'][:_WITNESSES_SHOWN])
        more = len(f['witnesses']) - _WITNESSES_SHOWN
        extra = f' (+{more} more)' if more > 0 else ''
        print(f"{f['file']}:{f['line']} - {f['call']} [{f['shape']}]")
        print(f"  Runs that fail from every start: {shown}{extra}")
        print(f"  Fix: {f['suggestion']}\n")


def main(argv: list[str] | None = None) -> int:
    _utf8_output()
    parser = argparse.ArgumentParser(
        description="Find regex calls inside a function that pass a literal pattern, and "
                    "patterns whose search is quadratic in one long run.")
    parser.add_argument('files', nargs='+', metavar='FILE', help="Python source files to scan")
    args = parser.parse_args(argv)

    all_findings, quadratic, failed = _scan(cast(list[str], args.files))

    print("# Uncompiled Regex Analysis\n")
    print(f"Found {len(all_findings)} uncompiled regex calls\n")

    for f in all_findings:
        print(f"{f['file']}:{f['line']} - {f['call']}")
        print(f"  Fix: {f['suggestion']}\n")
    _print_quadratic(quadratic)
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
