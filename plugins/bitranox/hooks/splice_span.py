"""The one detector for a file region spliced between two FOUND anchors: `s[:a] + new + s[b:]`
after two `.index()` / `.find()` calls, written back.

Two hooks ask about this shape and must not disagree about what it is, so both read it from
here. `toolbox-nudge.py` uses the textual `SPAN_SHAPE` on anything authored - a Write body, an
Edit, a heredoc - and only points at `anchor_edit`. `block-index-splice.py` REFUSES, so it asks
the narrower question `runs_an_unchecked_splice`: is a Python program that does this splice, and
does not assert every anchor unique, being RUN by this Bash call? It starts from the same `SPAN_SHAPE` and then confirms it in the parsed code,
because a refusal on text that merely describes the trap (a test fixture, a memory note, a commit
message) blocks the writing of the guidance itself.

Why the shape is worth a refusal: every way it goes wrong is silent. `str.find` returns -1 on a
miss, which slices from the END of the string; an end marker that also occurs inside a deeper-
indented line matches early and leaves the rest of the old region behind as dead code that still
parses. The splice writes, the program exits 0, and the damage shows up later, somewhere else.

Pure standard library.
"""

import ast
import re
import warnings

import shell_text

__all__ = ["SPAN_SHAPE", "every_anchor_checked", "programs_run_by", "runs_an_unchecked_splice",
           "splices_between_found_anchors", "unchecked_splices"]

# Every part is required (two finds, a head slice glued with `+`, a tail slice, a write), so
# reading a span, or prose describing one, is not a match. `\A` anchors the lookaheads:
# unanchored, `search` retries them at every offset and an 880 KB Write cost minutes per call.
SPAN_SHAPE = re.compile(r"(?s)\A(?=.*\.r?(?:index|find)\(.*\.r?(?:index|find)\()"
                        r"(?=.*\b\w+\[\s*:[^\]\n]+\]\s*\+)"
                        r"(?=.*\+\s*\w+\[[^\]\n:]+:\s*\])"
                        r"(?=.*(?:write_text\(|\.write\())")

_FINDERS = frozenset({"find", "rfind", "index", "rindex"})
_WRITERS = frozenset({"write_text", "write", "write_bytes"})


def _add_operands(node):
    """The leaves of a chain of `+`: `a + b + c` parses as `(a + b) + c`."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        yield from _add_operands(node.left)
        yield from _add_operands(node.right)
    else:
        yield node


def _cut(operand):
    """(sliced expression, "head" or "tail", the bound) for `x[:b]` / `x[b:]`, else None."""
    if not (isinstance(operand, ast.Subscript) and isinstance(operand.slice, ast.Slice)):
        return None
    lower, upper, step = operand.slice.lower, operand.slice.upper, operand.slice.step
    if step is not None or (lower is None) == (upper is None):
        return None
    base = ast.unparse(operand.value)
    return (base, "head", ast.unparse(upper)) if lower is None else (base, "tail", ast.unparse(lower))


class _Facts(ast.NodeVisitor):
    """What the program does, outside any `assert`: an assert that rebuilds the expected result
    with a splice is a CHECK of an edit made some other way, not the edit."""

    def __init__(self):
        self.finds = 0
        self.writes = 0
        self.anchors = []                                # one _anchor_key per find/index call
        self.cuts = {}                                   # base -> {"head": set, "tail": set}

    def visit_Assert(self, node):
        return None

    def visit_Call(self, node):
        name = node.func.attr if isinstance(node.func, ast.Attribute) else None
        self.finds += name in _FINDERS
        self.writes += name in _WRITERS
        if name in _FINDERS:
            self.anchors.append(_anchor_key(node.args[0]) if node.args else None)
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Add):
            for operand in _add_operands(node):
                cut = _cut(operand)
                if cut:
                    base, kind, bound = cut
                    self.cuts.setdefault(base, {"head": set(), "tail": set()})[kind].add(bound)
        self.generic_visit(node)

    def spans(self):
        """True when one expression is cut at a head bound and at a DIFFERENT tail bound. The same
        bound on both sides is an insert at one anchor - anchor_edit `insert` - not a span."""
        return any(head != tail for cut in self.cuts.values()
                   for head in cut["head"] for tail in cut["tail"])


def splices_between_found_anchors(program):
    """True when the Python `program` splices a region between two found anchors and writes.

    Starts from `SPAN_SHAPE`, so it never says yes where the nudge's shape says no, and confirms
    each part in the parsed code: at least two find/index calls, one expression cut at a head and
    at a different tail bound inside a `+` chain, and a write call - none of it counted inside a
    string or an `assert`. A program that does not parse (a heredoc whose `$VAR`s the shell would
    expand, a fragment) is not judged: the guard fails open and the nudge still speaks.

    Examples:
        >>> splices_between_found_anchors(
        ...     "s = p.read_text()\\na = s.index('A')\\nb = s.index('B')\\n"
        ...     "p.write_text(s[:a] + new + s[b:])\\n")
        True
        >>> splices_between_found_anchors("x = 'p.write_text(s[:a] + n + s[b:]) s.index( s.index('")
        False
    """
    return _splice_facts(program) is not None


def _splice_facts(program):
    """(tree, facts) when `program` is a span splice, else None."""
    if not SPAN_SHAPE.search(program or ""):
        return None
    try:
        # A heredoc often carries an escape Python warns about (`\``); in a hook that warning
        # would print on stderr for a call that is let through.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(program)
    except (SyntaxError, ValueError):
        return None
    facts = _Facts()
    facts.visit(tree)
    if facts.finds >= 2 and facts.writes >= 1 and facts.spans():
        return tree, facts
    return None


def _anchor_key(node):
    """A comparable key for an anchor argument: a bare name or a string literal. Anything else
    (an f-string, a concatenation, an attribute) cannot be paired with its count, so None."""
    if isinstance(node, ast.Name):
        return ("name", node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return ("const", node.value)
    return None


def _count_key(node, op):
    """The anchor key of `X.count(A) <op> 1` or `1 <op> X.count(A)`, else None."""
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], op)):
        return None
    for call, other in ((node.left, node.comparators[0]), (node.comparators[0], node.left)):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "count" and len(call.args) == 1
                and isinstance(other, ast.Constant) and other.value == 1
                and not isinstance(other.value, bool)):
            return _anchor_key(call.args[0])
    return None


def _asserted_unique(test):
    """Keys an `assert test` proves unique: `X.count(A) == 1`, alone or in an `and` chain."""
    parts = test.values if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And) else [test]
    return {key for key in (_count_key(part, ast.Eq) for part in parts) if key}


def _refused_when_not_unique(test):
    """Keys whose non-uniqueness makes `if test:` true: `X.count(A) != 1` or
    `not X.count(A) == 1`, alone or in an `or` chain. An `and` chain stops only when EVERY
    anchor is wrong, so it guards none of them."""
    parts = test.values if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or) else [test]
    keys = set()
    for part in parts:
        if isinstance(part, ast.UnaryOp) and isinstance(part.op, ast.Not):
            key = _count_key(part.operand, ast.Eq)
        else:
            key = _count_key(part, ast.NotEq)
        if key:
            keys.add(key)
    return keys


_STOPPERS = frozenset({"exit", "quit", "_exit"})


def _stops(body):
    """True when a block raises or exits: `raise ...`, `sys.exit(...)`, `exit(...)`."""
    for stmt in body:
        if isinstance(stmt, ast.Raise):
            return True
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        if isinstance(call, ast.Call):
            func = call.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name in _STOPPERS:
                return True
    return False


def _checked_anchors(tree):
    """Every anchor key the program asserts unique, or stops on when it is not."""
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            keys |= _asserted_unique(node.test)
        elif isinstance(node, ast.If) and _stops(node.body):
            keys |= _refused_when_not_unique(node.test)
    return keys


def every_anchor_checked(program):
    """True when `program` is a span splice and EVERY find/index anchor it uses is checked unique.

    A check is `assert X.count(A) == 1` (or `1 == ...`, or several joined by `and`), or an `if`
    whose test is true when A is not unique (`X.count(A) != 1`, `not X.count(A) == 1`, joined by
    `or`) and whose body raises or exits. The anchor is paired with its count by the argument
    alone - the same name, or the same string literal. An anchor that is neither (an f-string, a
    concatenation, a value built in a loop) cannot be paired and leaves the program unchecked:
    the exemption errs toward refusing. Where the check sits relative to the cut is not judged.

    Examples:
        >>> every_anchor_checked(
        ...     "s = p.read_text()\\nassert s.count(A) == 1 and s.count(B) == 1\\n"
        ...     "a = s.index(A)\\nb = s.index(B)\\np.write_text(s[:a] + new + s[b:])\\n")
        True
        >>> every_anchor_checked(
        ...     "s = p.read_text()\\nassert s.count(A) == 1\\n"
        ...     "a = s.index(A)\\nb = s.index(B)\\np.write_text(s[:a] + new + s[b:])\\n")
        False
    """
    found = _splice_facts(program)
    if found is None:
        return False
    tree, facts = found
    checked = _checked_anchors(tree)
    return bool(facts.anchors) and all(key is not None and key in checked for key in facts.anchors)


# The interpreter word, by basename: python, python3, python3.14, pypy3, py (the Windows
# launcher), with or without `.exe`.
_INTERPRETER = re.compile(r"(?:^|[\\/])(?:python(?:3(?:\.\d+)?)?|pypy3?|py)(?:\.exe)?$")
# Options that take a separate value. `-c` and `-m` make something else the program, so the
# heredoc is stdin DATA; they are handled before this set is consulted.
_VALUE_OPTIONS = frozenset({"-W", "-X", "-Q"})
_REDIRECTION = re.compile(r"^\d*[<>]")


def _feeds_python(prefix):
    """True when the simple command ending at a heredoc opener runs Python ON ITS STDIN.

    `prefix` is the opener line up to the `<<`. `python3 - args <<EOF` and `python3 <<EOF` run the
    body; `python3 tool.py <<EOF`, `python3 -m mod <<EOF` and `python3 -c '...' <<EOF` hand it to
    another program as data, and `cat > f.py <<EOF` authors a file - the Write tool's case.
    """
    command = re.split(r"&&|\|\||[;|&(]", prefix)[-1]
    words = command.split()
    at = next((i for i, word in enumerate(words) if _INTERPRETER.search(word.strip("'\""))), None)
    if at is None:
        return False
    rest = iter(words[at + 1:])
    for word in rest:
        if word == "-" or _REDIRECTION.match(word):
            return True
        if word in ("-c", "-m") or not word.startswith("-"):
            return False
        if word in _VALUE_OPTIONS:
            next(rest, None)
    return True


def programs_run_by(command):
    """The heredoc bodies of `command` that a Python interpreter reads as its program.

    Examples:
        >>> programs_run_by("python3 - <<'PY'\\nprint(1)\\nPY\\n")
        ['print(1)']
        >>> programs_run_by("cat > /tmp/x.py <<'PY'\\nprint(1)\\nPY\\n")
        []
    """
    lines = (command or "").split("\n")
    return ["\n".join(lines[start:end])
            for line, opener, (start, end) in shell_text.iter_heredocs(command or "")
            if _feeds_python(lines[line][:opener.start()])]


def unchecked_splices(command):
    """The programs `command` runs that splice between found anchors without checking every
    anchor unique - what block-index-splice refuses."""
    return [program for program in programs_run_by(command)
            if splices_between_found_anchors(program) and not every_anchor_checked(program)]


def runs_an_unchecked_splice(command):
    """True when this shell `command` runs a span splice whose anchors are not all checked."""
    return bool(unchecked_splices(command))
