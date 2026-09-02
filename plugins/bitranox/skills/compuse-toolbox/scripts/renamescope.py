# /// script
# requires-python = ">=3.10"
# ///
r"""I am substituting an identifier across a file - which FUNCTIONS do the hits land in, and which
of those was I not refactoring?

A rename by pattern is a bulk action, and the rule for a bulk action is that its target list comes
from the work you did, never from a predicate that merely overlaps it. A regex is a predicate. It
finds every occurrence of the name, including the ones in functions you never opened, and there
the substitution does not break - it changes MEANING. So this takes the EXPLICIT list of functions
you set out to change, resolves each match's innermost enclosing function by AST, and reports the
hits that fall OUTSIDE that list. Those are the finding.

The measured case it is built from (2026-08-31). Swapping a `windows: bool` parameter for a
`GuestOS` enum, the signature `_guest_new_iface(ip, mac, key, guest_os)` was substituted across a
file. One hit landed inside `_no_nic_was_stranded`, a function that was NOT being refactored,
whose loop reads `for mac in other_nic_macs(conf, spare_mac)`. The rewrite silently repointed that
guard at `target.spare_mac` - the SPARE NIC, inside a loop whose entire purpose is checking the
OTHER NICs. The spare is address-less by design, so the guard would have gone on looking like a
working check while interrogating the one NIC that can never answer.

Nothing in the test suite covered that function. It was caught only because the substituted name
happened to be UNDEFINED in that scope, so pyright rejected it. Had `target` been in scope there,
it would have shipped green.

That is why the report leads with HOW THE NAME IS BOUND at each site, not just where it is. The
same identifier was a PARAMETER in the function being changed and a LOOP VARIABLE in the one next
to it. A pattern matches both; only one of them is your work, and the difference between those two
bindings is the entire defect. `binding` is how the name is bound in that enclosing scope
(parameter, loop variable, assignment target, imported, or free); `site_kind` is what this
particular occurrence is (the parameter declaration itself, a loop target, an attribute, a plain
load, a string, a comment).

Three things it deliberately does rather than the easy version:

* **AST, never indentation or a regex for the enclosing function.** Nested functions and methods
  report the INNERMOST enclosing function with its qualified name (`Class.method.inner`), because
  a rename inside a closure is a different edit from one in its parent.
* **Module-level hits get their own bucket rather than being dropped.** A match with no enclosing
  function is still a hit your list did not name, so it counts as a finding. Bless it deliberately
  by passing `--intended '<module>'` if module scope really is part of the work.
* **Zero matches is an ERROR, not a pass.** A pattern that matches nothing cannot answer the
  question, and exiting 0 there would be a green that means "I examined nothing".

THE INDENTATION TRAP, which this warns about but cannot fix for you: an indent-bearing literal is
a SUBSTRING of a deeper-indented occurrence, so a 4-space pattern silently rewrites the 8-space
one as well. `--regex` is compiled with `re.MULTILINE` precisely so you can anchor it
(`(?m)^(\s*)if x:$`) instead of leading it with spaces; a pattern that starts with whitespace and
is not anchored gets a warning naming the depths its matches actually landed at.

KNOWN LIMITS, and they are the honest ones. This reads the files you hand it and nothing else, so
a file-wide rename that also touches a sibling module is invisible unless you pass that module
too. A bare `--intended` name that matches two qualified names (the same method on two classes)
blesses BOTH, and warns rather than choosing - an unwarned choice there is how a hit in the wrong
class reads as intended. Names bound dynamically (`globals()[...]`, `setattr`, `exec`) are not
visible to any AST. And this reports where a substitution LANDS; whether the replacement is
correct in a scope that legitimately owns the name is still yours to read.

Run: uv run tools/renamescope.py src/net.py --name mac \
       --intended _guest_new_iface --intended _apply_iface
     uv run tools/renamescope.py src/*.py --regex '(?m)^(\s*)if x:$' --intended run --json
Exit 0 = every hit is inside a function you named; 1 = hits fall OUTSIDE that list (the finding);
2 = error - no such file, unparseable source, or a pattern that matched nothing.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import sys
import tokenize
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path

__all__ = [
    "Binding",
    "Bucket",
    "RenamescopeError",
    "Scan",
    "Site",
    "SiteKind",
    "Unparseable",
    "indent_trap_warning",
    "main",
    "name_pattern",
    "resolve_intended",
    "scan_paths",
    "scan_source",
]

MODULE_SCOPE = "<module>"
"""The pseudo-name for module scope, both in the report and in `--intended`."""


class RenamescopeError(Exception):
    """Base for every refusal: the question was not answered, so do not read silence as a pass."""


class Unparseable(RenamescopeError):
    """The source does not parse, so no enclosing function can be resolved for any hit."""


class NothingMatched(RenamescopeError):
    """The pattern matched nowhere. A scan that examined nothing must not report "no findings"."""


class Bucket(Enum):
    """Which side of the mandate a hit falls on."""

    INTENDED = "intended"
    """Inside a function the caller explicitly named. This is the work."""
    OUTSIDE = "outside"
    """Inside a function the caller did NOT name. This is the finding - meaning changes here."""
    MODULE = "module"
    """No enclosing function at all. Its own bucket so it is never silently dropped."""


class Binding(Enum):
    """How the name is bound in the enclosing scope - the axis the measured defect turned on."""

    PARAMETER = "parameter"
    LOOP_VAR = "loop_var"
    COMPREHENSION_VAR = "comprehension_var"
    WITH_VAR = "with_var"
    EXCEPT_VAR = "except_var"
    ASSIGNED = "assigned"
    IMPORTED = "imported"
    DEFINED = "defined"
    GLOBAL_DECL = "global_decl"
    NONLOCAL_DECL = "nonlocal_decl"
    FREE = "free"
    """Read here, bound somewhere else - a global, a closure cell, or a builtin."""


_BINDING_PRIORITY = (
    Binding.PARAMETER,
    Binding.LOOP_VAR,
    Binding.COMPREHENSION_VAR,
    Binding.WITH_VAR,
    Binding.EXCEPT_VAR,
    Binding.ASSIGNED,
    Binding.IMPORTED,
    Binding.DEFINED,
    Binding.GLOBAL_DECL,
    Binding.NONLOCAL_DECL,
    Binding.FREE,
)


class SiteKind(Enum):
    """What THIS occurrence is, which is a separate question from how the name is bound."""

    PARAMETER_DECL = "parameter_decl"
    LOOP_TARGET = "loop_target"
    COMP_TARGET = "comp_target"
    WITH_TARGET = "with_target"
    ASSIGN_TARGET = "assign_target"
    AUGASSIGN_TARGET = "augassign_target"
    DEL_TARGET = "del_target"
    DEF_NAME = "def_name"
    IMPORT_ALIAS = "import_alias"
    ATTRIBUTE = "attribute"
    """`x.name` - a different name in a different namespace that the regex cannot tell apart."""
    KEYWORD_ARG = "keyword_arg"
    LOAD = "load"
    STRING = "string"
    COMMENT = "comment"
    UNCLASSIFIED = "unclassified"
    """Matched text no AST node and no token covers. Reported, never silently called a load."""


@dataclass(frozen=True)
class Site:
    """One match, placed."""

    path: str
    line: int
    col: int
    text: str
    enclosing: str | None
    """Innermost enclosing FUNCTION qualname, or None at module or bare class-body scope."""
    scope: str
    """Innermost enclosing scope of any kind, so a class body is not reported as `<module>`."""
    bucket: Bucket
    site_kind: SiteKind
    binding: Binding
    bindings: tuple[Binding, ...]
    in_decorator: bool
    """The hit sits on a decorator line above the `def`, which is evaluated in the OUTER scope."""


@dataclass(frozen=True)
class Scan:
    """Everything one run looked at, including what it could not place."""

    sites: tuple[Site, ...] = ()
    functions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    skipped: tuple[str, ...] = field(default=())

    def bucket(self, which: Bucket) -> tuple[Site, ...]:
        return tuple(s for s in self.sites if s.bucket is which)

    @property
    def findings(self) -> tuple[Site, ...]:
        """Everything the caller's list did not account for: OUTSIDE plus unblessed MODULE."""
        return tuple(s for s in self.sites if s.bucket in (Bucket.OUTSIDE, Bucket.MODULE))


# --------------------------------------------------------------------------------------------
# scopes
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Scope:
    qualname: str
    parent: str | None
    start: int
    """Decorator-INCLUSIVE first line: a diff hunk on a decorator reads as part of that function."""
    end: int
    def_line: int
    depth: int
    is_function: bool
    node: ast.AST


def _scope_start(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    """Decorators come BEFORE `node.lineno`, so a naive start silently orphans them."""
    if not node.decorator_list:
        return node.lineno
    return min(node.lineno, min(d.lineno for d in node.decorator_list))


def _scopes(tree: ast.Module) -> list[_Scope]:
    """Every def/class in the file with its span, innermost-resolvable."""
    found: list[_Scope] = []

    def visit(node: ast.AST, stack: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                qual = ".".join([*stack, child.name])
                found.append(
                    _Scope(
                        qualname=qual,
                        parent=".".join(stack) if stack else None,
                        start=_scope_start(child),
                        end=child.end_lineno or child.lineno,
                        def_line=child.lineno,
                        depth=len(stack),
                        is_function=not isinstance(child, ast.ClassDef),
                        node=child,
                    )
                )
                visit(child, [*stack, child.name])
            else:
                visit(child, stack)

    visit(tree, [])
    return found


def _innermost(scopes: list[_Scope], line: int, *, functions_only: bool) -> _Scope | None:
    """Deepest scope containing `line`; ties break to the tighter span."""
    candidates = [
        s for s in scopes if s.start <= line <= s.end and (s.is_function or not functions_only)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda s: (s.depth, -(s.end - s.start)))


# --------------------------------------------------------------------------------------------
# how the name is bound in a scope
# --------------------------------------------------------------------------------------------


def _stored_names(target: ast.AST | None) -> list[ast.Name]:
    """Names a binding target actually binds, unwrapping tuple/list/starred unpacking.

    `for mac, ip in pairs:` binds both, and missing that is how a loop variable gets classified
    as a free read.
    """
    if target is None:
        return []
    return [n for n in ast.walk(target) if isinstance(n, ast.Name)]


def _own_nodes(scope: ast.AST):
    """Nodes belonging to THIS scope, not descending into nested def/class bodies.

    A nested function's `for mac in ...` binds `mac` in the NESTED scope, so folding it into the
    parent would report a binding the parent does not have.
    """
    body = getattr(scope, "body", [])
    stack: list[ast.AST] = list(body)
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _parameter_names(node: ast.AST) -> set[str]:
    args = getattr(node, "args", None)
    if not isinstance(args, ast.arguments):
        return set()
    every = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg:
        every.append(args.vararg)
    if args.kwarg:
        every.append(args.kwarg)
    return {a.arg for a in every}


def _bindings_in(scope: ast.AST, name: str) -> tuple[Binding, ...]:
    """Every way `name` is bound in this scope, strongest first. Empty means FREE."""
    found: set[Binding] = set()
    if name in _parameter_names(scope):
        found.add(Binding.PARAMETER)

    for node in _own_nodes(scope):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            if any(n.id == name for n in _stored_names(node.target)):
                found.add(Binding.LOOP_VAR)
        elif isinstance(node, ast.comprehension):
            if any(n.id == name for n in _stored_names(node.target)):
                found.add(Binding.COMPREHENSION_VAR)
        elif isinstance(node, ast.withitem):
            if any(n.id == name for n in _stored_names(node.optional_vars)):
                found.add(Binding.WITH_VAR)
        elif isinstance(node, ast.ExceptHandler):
            if node.name == name:
                found.add(Binding.EXCEPT_VAR)
        elif isinstance(node, ast.Assign):
            if any(n.id == name for t in node.targets for n in _stored_names(t)):
                found.add(Binding.ASSIGNED)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            if any(n.id == name for n in _stored_names(node.target)):
                found.add(Binding.ASSIGNED)
        elif isinstance(node, ast.alias):
            bound = node.asname or node.name.split(".")[0]
            if bound == name:
                found.add(Binding.IMPORTED)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                found.add(Binding.DEFINED)
        elif isinstance(node, ast.Global):
            if name in node.names:
                found.add(Binding.GLOBAL_DECL)
        elif isinstance(node, ast.Nonlocal):
            if name in node.names:
                found.add(Binding.NONLOCAL_DECL)
        elif isinstance(node, ast.MatchAs) and node.name == name:
            found.add(Binding.ASSIGNED)

    if not found:
        return (Binding.FREE,)
    return tuple(b for b in _BINDING_PRIORITY if b in found)


# --------------------------------------------------------------------------------------------
# what each occurrence is
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Occ:
    line: int
    col: int
    end_col: int
    kind: SiteKind


def _byte_col_to_char(line_text: str, byte_col: int) -> int:
    """AST `col_offset` is a UTF-8 BYTE offset; a regex match offset is a CHARACTER offset.

    On a file with any non-ASCII line these disagree, and every site kind on that line would be
    attributed to the wrong column - silently, as `unclassified`.
    """
    raw = line_text.encode("utf-8")[:byte_col]
    return len(raw.decode("utf-8", "ignore"))


def _target_kinds(tree: ast.Module) -> dict[int, SiteKind]:
    """Map `id(Name node)` to the kind of binding target it is, by the construct that owns it."""
    kinds: dict[int, SiteKind] = {}

    def mark(target: ast.AST | None, kind: SiteKind) -> None:
        for n in _stored_names(target):
            kinds[id(n)] = kind

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            mark(node.target, SiteKind.LOOP_TARGET)
        elif isinstance(node, ast.comprehension):
            mark(node.target, SiteKind.COMP_TARGET)
        elif isinstance(node, ast.withitem):
            mark(node.optional_vars, SiteKind.WITH_TARGET)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                mark(t, SiteKind.ASSIGN_TARGET)
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
            mark(node.target, SiteKind.ASSIGN_TARGET)
        elif isinstance(node, ast.AugAssign):
            mark(node.target, SiteKind.AUGASSIGN_TARGET)
        elif isinstance(node, ast.Delete):
            for t in node.targets:
                mark(t, SiteKind.DEL_TARGET)
    return kinds


def _def_name_occ(node: ast.AST, lines: list[str], name: str) -> _Occ | None:
    """Locate the NAME token on a `def`/`class` line. `node.col_offset` points at the keyword."""
    line_no = getattr(node, "lineno", 0)
    if not 1 <= line_no <= len(lines):
        return None
    text = lines[line_no - 1]
    found = re.search(r"\b(?:def|class)\s+(" + re.escape(name) + r")\b", text)
    if found is None:
        return None
    return _Occ(line_no, found.start(1), found.end(1), SiteKind.DEF_NAME)


def _occurrences(tree: ast.Module, lines: list[str], name: str) -> list[_Occ]:
    """Every position the AST knows this identifier appears at, with what it is there."""
    targets = _target_kinds(tree)
    out: list[_Occ] = []

    def line_of(n: int) -> str:
        return lines[n - 1] if 1 <= n <= len(lines) else ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == name:
            kind = targets.get(id(node))
            if kind is None:
                kind = SiteKind.DEL_TARGET if isinstance(node.ctx, ast.Del) else (
                    SiteKind.ASSIGN_TARGET if isinstance(node.ctx, ast.Store) else SiteKind.LOAD
                )
            text = line_of(node.lineno)
            start = _byte_col_to_char(text, node.col_offset)
            out.append(_Occ(node.lineno, start, start + len(name), kind))
        elif isinstance(node, ast.arg) and node.arg == name:
            text = line_of(node.lineno)
            start = _byte_col_to_char(text, node.col_offset)
            out.append(_Occ(node.lineno, start, start + len(name), SiteKind.PARAMETER_DECL))
        elif isinstance(node, ast.Attribute) and node.attr == name:
            end_line = node.end_lineno or node.lineno
            text = line_of(end_line)
            end = _byte_col_to_char(text, node.end_col_offset or 0)
            out.append(_Occ(end_line, max(end - len(name), 0), end, SiteKind.ATTRIBUTE))
        elif isinstance(node, ast.keyword) and node.arg == name:
            text = line_of(node.lineno)
            start = _byte_col_to_char(text, node.col_offset)
            out.append(_Occ(node.lineno, start, start + len(name), SiteKind.KEYWORD_ARG))
        elif isinstance(node, ast.alias):
            bound = node.asname or node.name.split(".")[0]
            if bound == name and getattr(node, "lineno", None):
                text = line_of(node.lineno)
                found = re.search(r"\b" + re.escape(name) + r"\b", text)
                if found:
                    out.append(
                        _Occ(node.lineno, found.start(), found.end(), SiteKind.IMPORT_ALIAS)
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                occ = _def_name_occ(node, lines, name)
                if occ is not None:
                    out.append(occ)
    return out


def _token_spans(source: str) -> list[tuple[tuple[int, int], tuple[int, int], SiteKind]]:
    """Comment and string token spans, so a hit in a docstring is named rather than guessed at."""
    spans: list[tuple[tuple[int, int], tuple[int, int], SiteKind]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                spans.append((tok.start, tok.end, SiteKind.COMMENT))
            elif tok.type == tokenize.STRING:
                spans.append((tok.start, tok.end, SiteKind.STRING))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # A tokenize failure costs precision on string/comment hits, never correctness of the
        # enclosing-function answer, which comes from the AST.
        return spans
    return spans


def _kind_at(
    line: int, col: int, occs: list[_Occ], spans: list[tuple[tuple[int, int], tuple[int, int], SiteKind]]
) -> SiteKind:
    for occ in occs:
        if occ.line == line and occ.col <= col < occ.end_col:
            return occ.kind
    for start, end, kind in spans:
        if start <= (line, col) < end:
            return kind
    return SiteKind.UNCLASSIFIED


# --------------------------------------------------------------------------------------------
# patterns and the intended list
# --------------------------------------------------------------------------------------------


def name_pattern(name: str) -> re.Pattern[str]:
    """A word-anchored pattern for a bare identifier, which is what a rename actually substitutes."""
    return re.compile(r"\b" + re.escape(name) + r"\b", re.MULTILINE)


_INLINE_FLAGS = ("(?m)", "(?s)", "(?i)", "(?x)", "(?a)")


def indent_trap_warning(pattern: str) -> str | None:
    """Warn when a pattern LEADS with indentation and is not line-anchored.

    `"    if x:"` is a substring of `"        if x:"`, so the shallow pattern rewrites the deeper
    occurrence too and the diff looks fine.
    """
    body = pattern
    changed = True
    while changed:
        changed = False
        for flag in _INLINE_FLAGS:
            if body.startswith(flag):
                body = body[len(flag) :]
                changed = True
    if body.startswith("^"):
        return None
    if body[:1] in (" ", "\t") or body.startswith(("\\s", "\\t")):
        return (
            "the pattern leads with indentation and is not line-anchored: an indent-bearing "
            "literal is a SUBSTRING of a deeper-indented occurrence, so a 4-space pattern "
            "silently rewrites the 8-space one too. Anchor it as (?m)^(\\s*)... instead."
        )
    return None


def resolve_intended(
    wanted: list[str], functions: tuple[str, ...]
) -> tuple[set[str], bool, list[str]]:
    """Turn the caller's list of function names into qualnames, warning rather than choosing.

    Returns the resolved qualnames, whether module scope was blessed, and warnings. A bare name
    matching two qualnames blesses BOTH - the alternative is picking one silently, which is how a
    hit in the wrong class reads as intended.
    """
    resolved: set[str] = set()
    module_blessed = False
    notes: list[str] = []
    for want in wanted:
        if want == MODULE_SCOPE:
            module_blessed = True
            continue
        if want in functions:
            resolved.add(want)
            continue
        matches = [q for q in functions if q.rsplit(".", 1)[-1] == want]
        if not matches:
            notes.append(
                f"--intended {want!r} matches no function in the scanned files; your mandate "
                "names something that is not there (typo, or the wrong file)"
            )
            continue
        if len(matches) > 1:
            notes.append(
                f"--intended {want!r} is ambiguous and blesses ALL of {sorted(matches)}; "
                "pass the qualified name to mean just one"
            )
        resolved.update(matches)
    return resolved, module_blessed, notes


# --------------------------------------------------------------------------------------------
# the scan
# --------------------------------------------------------------------------------------------


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _position(starts: list[int], offset: int) -> tuple[int, int]:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1, offset - starts[lo]


def scan_source(
    source: str,
    *,
    pattern: re.Pattern[str],
    intended: list[str] | None = None,
    path: str = "<source>",
) -> Scan:
    """Place every match of `pattern` in `source` against the caller's intended function list."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise Unparseable(f"{path}: {exc.msg} (line {exc.lineno})") from exc

    lines = source.splitlines()
    scopes = _scopes(tree)
    scope_nodes = {s.qualname: s.node for s in scopes}
    functions = tuple(s.qualname for s in scopes if s.is_function)
    resolved, module_blessed, notes = resolve_intended(list(intended or []), functions)

    starts = _line_starts(source)
    spans = _token_spans(source)
    binding_cache: dict[str, tuple[Binding, ...]] = {}
    occ_cache: dict[str, list[_Occ]] = {}

    sites: list[Site] = []
    for match in pattern.finditer(source):
        line, col = _position(starts, match.start())
        text = lines[line - 1] if 1 <= line <= len(lines) else ""
        token = match.group(0)
        word = token if token.isidentifier() else _word_at(text, col)

        if word not in occ_cache:
            occ_cache[word] = _occurrences(tree, lines, word) if word else []
        kind = _kind_at(line, col, occ_cache[word], spans)

        fn = _innermost(scopes, line, functions_only=True)
        any_scope = _innermost(scopes, line, functions_only=False)
        enclosing = fn.qualname if fn else None
        scope_name = any_scope.qualname if any_scope else MODULE_SCOPE

        # `enclosing` is TEXTUAL - the innermost span holding the line, which is the question
        # "which hunk of my diff is this". The BINDING is a different question, and for two site
        # kinds the answer is one scope OUT: a `def x` line opens x's scope but binds `x` in the
        # enclosing one, and a decorator expression is evaluated before the function exists. Read
        # in the inner scope both come back FREE or, worse, pick up a same-named parameter and
        # report a binding that is not the one this occurrence has.
        on_decorator = any_scope is not None and line < any_scope.def_line
        binds_outward = kind is SiteKind.DEF_NAME or on_decorator
        if any_scope is None:
            holder, holder_key = tree, MODULE_SCOPE
        elif binds_outward:
            holder_key = any_scope.parent or MODULE_SCOPE
            holder = scope_nodes.get(holder_key, tree)
        else:
            holder, holder_key = any_scope.node, any_scope.qualname

        cache_key = f"{holder_key}\0{word}"
        if cache_key not in binding_cache:
            binding_cache[cache_key] = _bindings_in(holder, word) if word else (Binding.FREE,)
        bindings = binding_cache[cache_key]

        if enclosing is None:
            bucket = Bucket.INTENDED if module_blessed else Bucket.MODULE
        elif enclosing in resolved:
            bucket = Bucket.INTENDED
        else:
            bucket = Bucket.OUTSIDE

        sites.append(
            Site(
                path=path,
                line=line,
                col=col,
                text=text.rstrip(),
                enclosing=enclosing,
                scope=scope_name,
                bucket=bucket,
                site_kind=kind,
                binding=bindings[0],
                bindings=bindings,
                in_decorator=on_decorator,
            )
        )
    return Scan(sites=tuple(sites), functions=functions, warnings=tuple(notes))


def _word_at(text: str, col: int) -> str:
    """The identifier a non-identifier match landed on, so `--regex` still gets binding analysis."""
    found = re.search(r"[A-Za-z_][A-Za-z0-9_]*", text[col:])
    return found.group(0) if found and found.start() == 0 else ""


def scan_paths(
    paths: list[Path], *, pattern: re.Pattern[str], intended: list[str] | None = None
) -> Scan:
    """Scan several files as one mandate, so a per-file green cannot hide a cross-file hit."""
    sites: list[Site] = []
    functions: list[str] = []
    skipped: list[str] = []
    per_file: list[Scan] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            skipped.append(f"{path}: {exc}")
            continue
        one = scan_source(source, pattern=pattern, intended=None, path=str(path))
        per_file.append(one)
        functions.extend(one.functions)

    resolved, module_blessed, notes = resolve_intended(list(intended or []), tuple(functions))
    for one in per_file:
        for site in one.sites:
            if site.enclosing is None:
                bucket = Bucket.INTENDED if module_blessed else Bucket.MODULE
            elif site.enclosing in resolved:
                bucket = Bucket.INTENDED
            else:
                bucket = Bucket.OUTSIDE
            sites.append(replace(site, bucket=bucket))
    return Scan(
        sites=tuple(sites),
        functions=tuple(functions),
        warnings=tuple(notes),
        skipped=tuple(skipped),
    )


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _site_json(site: Site) -> dict[str, object]:
    return {
        **asdict(site),
        "bucket": site.bucket.value,
        "site_kind": site.site_kind.value,
        "binding": site.binding.value,
        "bindings": [b.value for b in site.bindings],
    }


def _render(scan: Scan, pattern: str) -> str:
    out = [f"pattern {pattern!r}: {len(scan.sites)} match(es) in {len(scan.functions)} function(s)"]
    for which in (Bucket.OUTSIDE, Bucket.MODULE, Bucket.INTENDED):
        group = scan.bucket(which)
        if not group:
            continue
        head = {
            Bucket.OUTSIDE: "OUTSIDE your list - the rename changes MEANING here, read every one",
            Bucket.MODULE: "MODULE scope - no enclosing function, and your list named none",
            Bucket.INTENDED: "intended - inside a function you named",
        }[which]
        out.append(f"\n{which.value.upper()} ({len(group)}): {head}")
        for s in group:
            where = s.enclosing or s.scope
            deco = " [decorator line, evaluated in the OUTER scope]" if s.in_decorator else ""
            out.append(
                f"  {s.path}:{s.line}:{s.col}  in {where}  "
                f"bound as {s.binding.value}, here a {s.site_kind.value}{deco}"
            )
            out.append(f"      {s.text.strip()}")
    return "\n".join(out)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="renamescope.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("paths", nargs="+", type=Path, help="Python file(s) the rename would touch")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="a bare identifier; matched word-anchored")
    group.add_argument("--regex", help="a pattern; compiled with re.MULTILINE so ^ anchors a line")
    p.add_argument(
        "--intended",
        action="append",
        default=[],
        metavar="FUNC",
        help=f"a function you set out to change; repeatable. Use {MODULE_SCOPE!r} for module scope",
    )
    p.add_argument(
        "--intended-file",
        type=Path,
        help="read the intended function names from a file, one per line",
    )
    p.add_argument("--json", dest="json_", action="store_true", help="emit a JSON envelope")
    return p


def _fail(message: str, *, as_json: bool, command: str = "renamescope") -> int:
    if as_json:
        print(json.dumps({"ok": False, "command": command, "data": {"error": message},
                          "skipped": []}, indent=1))
    print(f"renamescope: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    intended = list(args.intended)
    if args.intended_file:
        try:
            intended += [
                ln.strip()
                for ln in args.intended_file.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
        except OSError as exc:
            return _fail(f"--intended-file: {exc}", as_json=args.json_)

    raw = args.regex if args.regex is not None else None
    try:
        pattern = name_pattern(args.name) if raw is None else re.compile(raw, re.MULTILINE)
    except re.error as exc:
        return _fail(f"bad --regex: {exc}", as_json=args.json_)
    shown = raw if raw is not None else args.name

    missing = [str(p) for p in args.paths if not p.exists()]
    if missing:
        return _fail(f"no such file: {', '.join(missing)}", as_json=args.json_)

    try:
        scan = scan_paths(args.paths, pattern=pattern, intended=intended)
    except Unparseable as exc:
        return _fail(str(exc), as_json=args.json_)

    warnings = list(scan.warnings)
    trap = indent_trap_warning(raw) if raw is not None else None
    if trap:
        depths = sorted({len(s.text) - len(s.text.lstrip()) for s in scan.sites})
        warnings.append(f"{trap} Matched lines sit at indent depths {depths}.")

    if not scan.sites:
        for note in warnings:
            print(f"renamescope: warning: {note}", file=sys.stderr)
        return _fail(
            f"pattern {shown!r} matched nothing in {len(args.paths)} file(s); a scan that "
            "examined nothing cannot report 'no findings'",
            as_json=args.json_,
        )

    findings = scan.findings
    if args.json_:
        print(
            json.dumps(
                {
                    "ok": True,
                    "command": "renamescope",
                    "data": {
                        "pattern": shown,
                        "intended": intended,
                        "matches": len(scan.sites),
                        "verdict": "outside_hits" if findings else "clean",
                        "counts": {b.value: len(scan.bucket(b)) for b in Bucket},
                        "sites": [_site_json(s) for s in scan.sites],
                        "warnings": warnings,
                    },
                    "skipped": list(scan.skipped),
                },
                indent=1,
            )
        )
    else:
        print(_render(scan, shown))

    for note in warnings:
        print(f"renamescope: warning: {note}", file=sys.stderr)
    for note in scan.skipped:
        print(f"renamescope: skipped: {note}", file=sys.stderr)

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
