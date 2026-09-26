# /// script
# requires-python = ">=3.10"
# ///
"""Is this config value actually ENFORCED, or just declared, parsed and read?

A field that is loaded, typed and schema-validated has a READER. It does not have an ENFORCER,
and only the second one bounds anything. The failure mode is silent and reads as safety: the
field is loud when malformed and mute when ignored, so the loudness gets mistaken for
enforcement, and a safety argument built on it fails open with no symptom.

Measured twice in one repo. `planner_kinds` is a typed `extra="forbid"` pydantic field listing
the node kinds a plan may emit, and a design rested "a plan cannot cause an irreversible effect"
on it; nothing compares a spec's kind to it. `escalation.on_auth_failure: fail_run` is in the
shipped policy YAML and read by no Python at all, and it was published as the mechanism that
fails a run. Both were reached by grepping the identifier and reading the HIT COUNT instead of
reading what the hits DO.

So this classifies every hit rather than counting them. Two buckets ENFORCE: DECISION (something
is compared to it, or control flow branches on it - an if/while/assert test, a conditional
expression, a `match` subject, a `case` pattern or a `case` guard - enforcement by refusal) and CLAMP (min()/max()
caps a value with it - enforcement by truncation, which bounds without ever branching). The rest do
not: DECLARATION, CONFIG, TEST, DOCSTRING, COMMENT and plain REFERENCE. Both empty is the answer.

It follows ONE alias hop inside a function: `ceiling = self.policy.tokens_per_row.get(row)` (or the
annotated `ceiling: int = ...`) then a decision on `ceiling` counts, reported as "via local
`ceiling`". One hop and one scope on purpose -
further would need real dataflow, and guessing across scopes would manufacture a decision from any
common local name, which is the worse error because it reads as safety.

Its own sweep found all three of those classes as false negatives before they were fixed, which is
the honest warning: a NOT-ENFORCED verdict is only as good as the shapes it knows. If a value
reaches its enforcer renamed, through a wrapper, or across a module boundary, this will not see it -
so treat NOT-ENFORCED as "go read these hits", not as proof.

Two things it deliberately does NOT do. It does not decide whether an enforcer is CORRECT, only
that one exists. And it never reports a non-Python file as enforcement: a YAML or TOML mention is
where a value is declared, never where it is enforced, which is exactly the confusion that makes
a shipped config line look like a mechanism.

What counts as a TEST hit: anything under a `test`/`tests` directory BELOW --root, everything
when --root itself is such a directory (or a file in one) that holds no project marker
(`pyproject.toml`, `setup.py`, `setup.cfg`, `.git`), and any `test_*.py`, `*_test.py` or
`conftest.py`. The walk skips VCS, cache and vendored trees below --root (`.git`, `__pycache__`,
`venv`, any `.venv*`, `.tox`, `site-packages`, `node_modules`), reads a `.env` / `.env.*` file as
config unless it is a `.py`/`.pyi` module, and matches comments, docstrings and config lines as
whole words, taking comments from the tokenizer so a `#` inside a string is not one. A directory
it cannot enter is listed as UNREAD like an unparsable file.

Run: `uv run scripts/enforced.py planner_kinds --root src/`
     `uv run scripts/enforced.py on_auth_failure --root . --json`
Exit 0 = enforced (a decision exists), 1 = parsed but never enforced, 2 = not found, or incomplete
(a file or directory could not be read and no decision was found elsewhere).
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import sys
import tokenize
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

__all__ = ["Hit", "HitKind", "Verdict", "classify_source", "classify_tree", "verdict_of"]

_PY_SUFFIXES = frozenset({".py", ".pyi"})
_CONFIG_SUFFIXES = frozenset({".yaml", ".yml", ".toml", ".json", ".ini", ".cfg", ".env"})
_CLAMP_CALLS = frozenset({"min", "max"})
"""Builtins that BOUND a value. Only these - treating any call as enforcement would make every
argument of every function a bound."""

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", "venv", "node_modules", ".mypy_cache", ".ruff_cache", ".tox",
    "site-packages",
})
"""Directory names never scanned, matched only BELOW --root: a project that itself lives under a
folder called venv or test is still the project."""
_SKIP_DIR_PREFIXES = (".venv",)
"""Prefix, not name: .venv-win, .venv-3.12 and .venv-bmk are venvs too, and a third-party
site-packages decision under one read as this project's enforcer."""

_TEST_DIRS = frozenset({"tests", "test"})
_PROJECT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", ".git")
"""What makes a directory a project ROOT rather than a test folder, when --root itself is named
test/tests: a project whose own top directory is called `test` keeps its enforcers."""
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
"""The line breaks Python's tokenizer and YAML/TOML count - NOT str.splitlines(), which also
breaks on a form feed, U+2028 and friends and so shifts every later line number off the AST's."""


class HitKind(str, Enum):
    """What a mention of the identifier is DOING, which is the whole question."""

    DECISION = "decision"
    """Something is compared to it, or control flow branches on it. Enforcement by REFUSAL."""
    CLAMP = "clamp"
    """It caps a value through min()/max(). Enforcement by TRUNCATION - it bounds without
    branching, so a decision-only walk would call it documentation. Kept a separate bucket
    because refusing and silently truncating are different guarantees to a reader."""
    DECLARATION = "declaration"
    """It is being defined or assigned: a model field, an annotation, an assignment target."""
    CONFIG = "config"
    """A mention in a non-Python file. Where a value is SET, never where it is enforced."""
    TEST = "test"
    """A mention under a test path. Proves the field exists; never that anything binds to it."""
    DOCSTRING = "docstring"
    COMMENT = "comment"
    REFERENCE = "reference"
    """Read, passed, logged, returned - a real reader that decides nothing."""


@dataclass(frozen=True)
class Hit:
    kind: HitKind
    line: int
    path: str
    text: str
    via: str = ""
    """The local name the value was rebound to, when the decision was found through an alias.

    Empty for a direct hit. A reader needs this: "enforced via `ceiling`" is a different claim
    from "enforced", and the alias hop is the part that could be wrong."""


@dataclass(frozen=True)
class Verdict:
    found: bool
    enforced: bool
    summary: str
    counts: dict[str, int]


def _is_test_path(path: Path) -> bool:
    """A test DIRECTORY anywhere in `path`, or a module pytest collects or loads as test code.

    Callers pass the path RELATIVE to the scan root, so a folder called test above --root does not
    turn the whole project into tests."""
    parts = {p.lower() for p in path.parts[:-1]}
    name = path.name.lower()
    return (bool(parts & _TEST_DIRS) or name.startswith("test_") or name.endswith("_test.py")
            or name == "conftest.py")


def _is_test_root(root: Path) -> bool:
    """Whether the scan root ITSELF is a test directory: named test/tests once resolved (so
    `--root .` from inside tests/ counts) and holding no project marker.

    `_is_test_path` sees only the part BELOW the root, so without this a helper module in a
    tests dir given as --root read as production code and its assert as the enforcer."""
    resolved = root.resolve()
    if resolved.name.lower() not in _TEST_DIRS:
        return False
    return not any(os.path.lexists(resolved / marker) for marker in _PROJECT_MARKERS)


def _skipped_dir(name: str) -> bool:
    return name in _SKIP_DIRS or name.startswith(_SKIP_DIR_PREFIXES)


def _word(identifier: str) -> re.Pattern[str]:
    """The identifier as a whole word, so `limit` is not found inside `rate_limit`."""
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(identifier) + r"(?![A-Za-z0-9_])")


def _lines(text: str) -> list[str]:
    return _LINE_BREAK.split(text)


def _parents(tree: ast.AST) -> dict[int, tuple[ast.AST, str]]:
    """Map id(node) -> (parent, the field name the child sits under).

    The field matters as much as the parent: an ``If``'s ``test`` is a decision and its ``body``
    is not, and a walk that only looked at node TYPES would call every mention inside an if-block
    a decision.
    """
    table: dict[int, tuple[ast.AST, str]] = {}
    for parent in ast.walk(tree):
        for field, value in ast.iter_fields(parent):
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    table[id(child)] = (parent, field)
    return table


def _is_declaration(node: ast.AST, table: dict[int, tuple[ast.AST, str]]) -> bool:
    parent_field = table.get(id(node))
    if parent_field is None:
        return False
    parent, field = parent_field
    if isinstance(parent, ast.AnnAssign) and field == "target":
        return True
    return isinstance(parent, (ast.Assign, ast.AugAssign)) and field in {"target", "targets"}


def _decides(node: ast.AST, table: dict[int, tuple[ast.AST, str]]) -> bool:
    """Walk up to the nearest scope; report whether anything on the way BRANCHES on this value."""
    current: ast.AST = node
    while True:
        parent_field = table.get(id(current))
        if parent_field is None:
            return False
        parent, field = parent_field
        if isinstance(parent, ast.Compare):
            return True
        if isinstance(parent, (ast.If, ast.While, ast.IfExp, ast.Assert)) and field == "test":
            return True
        if _branches_as_match(parent, field):
            return True
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            return False
        current = parent


def _branches_as_match(parent: ast.AST, field: str) -> bool:
    """A `match` SUBJECT, a `case` PATTERN and a `case ... if` GUARD choose a branch exactly as an
    if-test does: `case Mode.STRICT:` compares the subject to the value, `case Strict():` tests
    its class."""
    if isinstance(parent, ast.Match) and field == "subject":
        return True
    return isinstance(parent, ast.match_case) and field in {"pattern", "guard"}


def _clamps(node: ast.AST, table: dict[int, tuple[ast.AST, str]]) -> bool:
    """Whether this mention is an argument to min()/max(), which bounds it without branching."""
    parent_field = table.get(id(node))
    if parent_field is None:
        return False
    parent, field = parent_field
    return (
        isinstance(parent, ast.Call)
        and field == "args"
        and isinstance(parent.func, ast.Name)
        and parent.func.id in _CLAMP_CALLS
    )


def _named_nodes(tree: ast.AST, identifier: str) -> list[ast.AST]:
    """Every AST node that IS the identifier - never a substring of a longer name.

    `grep planner_kinds` matches `planner_kinds_extra`; this cannot, because it compares whole
    `Name.id` / `Attribute.attr` / parameter names.
    """
    found: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == identifier:
            found.append(node)
        elif isinstance(node, ast.Attribute) and node.attr == identifier:
            found.append(node)
        elif isinstance(node, ast.arg) and node.arg == identifier:
            found.append(node)
        elif isinstance(node, ast.keyword) and node.arg == identifier:
            found.append(node)
    return found


def _docstring_hits(tree: ast.AST, identifier: str, path: Path, lines: list[str]) -> list[Hit]:
    word = _word(identifier)
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc and word.search(doc):
            body = node.body[0] if node.body else None
            line = getattr(body, "lineno", 1)
            hits.append(Hit(HitKind.DOCSTRING, line, str(path), _line_text(lines, line)))
    return hits


def _comment_hits(source: str, identifier: str, path: Path, lines: list[str]) -> list[Hit]:
    """Real COMMENT tokens only: a `#` inside a string literal is not a comment."""
    word = _word(identifier)
    hits: list[Hit] = []
    try:
        # newline=None: a CR-only or CRLF file keeps the tokenizer's line numbers equal to the AST's
        tokens = list(tokenize.generate_tokens(io.StringIO(source, newline=None).readline))
    except (tokenize.TokenError, SyntaxError):
        return hits
    for token in tokens:
        if token.type == tokenize.COMMENT and word.search(token.string):
            line = token.start[0]
            hits.append(Hit(HitKind.COMMENT, line, str(path), _line_text(lines, line)))
    return hits


def _line_text(lines: list[str], line: int) -> str:
    return lines[line - 1].strip() if 0 < line <= len(lines) else ""


def _enclosing_scope(node: ast.AST, table: dict[int, tuple[ast.AST, str]]) -> ast.AST | None:
    """The FunctionDef / ClassDef / Module a node sits in - the bound for alias following."""
    current: ast.AST = node
    while True:
        parent_field = table.get(id(current))
        if parent_field is None:
            return None
        parent = parent_field[0]
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            return parent
        current = parent


def _alias_of(node: ast.AST, table: dict[int, tuple[ast.AST, str]]) -> tuple[str, int] | None:
    """If this mention is the VALUE of `name = <...node...>` or `name: T = <...node...>`, return
    that local name and its line."""
    current: ast.AST = node
    while True:
        parent_field = table.get(id(current))
        if parent_field is None:
            return None
        parent, field = parent_field
        if isinstance(parent, ast.Assign) and field == "value":
            targets = parent.targets
            if len(targets) == 1 and isinstance(targets[0], ast.Name):
                return (targets[0].id, parent.lineno)
            return None
        if isinstance(parent, ast.AnnAssign) and field == "value":
            if isinstance(parent.target, ast.Name):
                return (parent.target.id, parent.lineno)
            return None
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            return None
        current = parent


def _alias_decisions(
    node: ast.AST,
    identifier_line: int,
    table: dict[int, tuple[ast.AST, str]],
    path: Path,
    lines: list[str],
) -> list[Hit]:
    """Follow ONE hop: `x = <field>` then a decision on `x`, within the same function.

    One hop and one scope on purpose. Following further would need real dataflow analysis, and a
    tool that guesses across scopes would manufacture decisions from any common local name - the
    opposite error, and the harder one to notice. `_alias_of` also refuses a multi-target assign,
    and a decision BEFORE the binding line does not count.
    """
    alias = _alias_of(node, table)
    scope = _enclosing_scope(node, table)
    if alias is None or scope is None:
        return []
    name, assigned_at = alias
    hits: list[Hit] = []
    for candidate in ast.walk(scope):
        if not isinstance(candidate, ast.Name) or candidate.id != name:
            continue
        if candidate.lineno <= assigned_at:
            continue
        if _enclosing_scope(candidate, table) is not scope:
            continue
        if _decides(candidate, table):
            hits.append(Hit(HitKind.DECISION, candidate.lineno, str(path), _line_text(lines, candidate.lineno), via=name))
    del identifier_line
    return hits


def classify_source(source: str, identifier: str, *, path: Path, root: Path | None = None) -> list[Hit]:
    """Classify every mention of ``identifier`` in one Python source string.

    Args:
        source: The file's text.
        identifier: The exact name to look for; substrings of longer names never match.
        path: Where it came from, used for the text of each hit and to spot a test path.
        root: The scan root. When given, only the part of ``path`` BELOW it, and the root's own
            name, decide whether this is a test file, so a project under a folder called ``test``
            is not all tests while a ``tests`` dir given as the root is.

    Returns:
        One :class:`Hit` per mention, in line order.

    Raises:
        SyntaxError: ``source`` does not parse. Deliberately not swallowed - a file that cannot
            be read is an unanswered question, and reporting it as "no decisions found" would
            be the same false clean this tool exists to prevent.

    Examples:
        >>> hits = classify_source("if s.kind not in l.limit:\\n    raise E()\\n", "limit", path=Path("a.py"))
        >>> [h.kind.value for h in hits]
        ['decision']
        >>> classify_source("x = 1\\n", "limit", path=Path("a.py"))
        []
    """
    tree = ast.parse(source)
    lines = _lines(source)
    table = _parents(tree)
    in_test = _is_test_path(_below(path, root)) or (root is not None and _is_test_root(root))
    hits: list[Hit] = []
    for node in _named_nodes(tree, identifier):
        line = getattr(node, "lineno", 1)
        if in_test:
            kind = HitKind.TEST
        elif _is_declaration(node, table):
            kind = HitKind.DECLARATION
        elif _decides(node, table):
            kind = HitKind.DECISION
        elif _clamps(node, table):
            kind = HitKind.CLAMP
        else:
            kind = HitKind.REFERENCE
        hits.append(Hit(kind, line, str(path), _line_text(lines, line)))
        if kind is HitKind.REFERENCE:
            hits.extend(_alias_decisions(node, line, table, path, lines))
    doc_and_comment = (_docstring_hits(tree, identifier, path, lines)
                       + _comment_hits(source, identifier, path, lines))
    if in_test:
        doc_and_comment = [Hit(HitKind.TEST, h.line, h.path, h.text) for h in doc_and_comment]
    hits.extend(doc_and_comment)
    return sorted(hits, key=lambda h: (h.line, h.kind.value))


def _below(path: Path, root: Path | None) -> Path:
    """`path` relative to the scan root when it lies under it, else `path` unchanged."""
    if root is None:
        return path
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _is_config(path: Path) -> bool:
    """A `.env` has suffix '' and `.env.production` has suffix '.production', so name them too -
    but a Python module stays Python: `.env.py` also starts with `.env.`, and reading it as config
    would drop every decision in it."""
    if path.suffix in _PY_SUFFIXES:
        return False
    return path.suffix in _CONFIG_SUFFIXES or path.name == ".env" or path.name.startswith(".env.")


def _walk_files(root: Path, unreadable: list[str]) -> list[Path]:
    """Every file under `root`, pruning skipped directories BELOW it; an unreadable directory is
    recorded in `unreadable`, because the only enforcer could sit inside it."""
    def record(exc: OSError) -> None:
        unreadable.append(f"{exc.filename}: {type(exc).__name__} (directory not read)")

    found: list[Path] = []
    for dirpath, dirs, files in os.walk(root, onerror=record):
        dirs[:] = sorted(d for d in dirs if not _skipped_dir(d))
        found.extend(Path(dirpath) / name for name in files)
    return sorted(found)


def classify_tree(root: Path, identifier: str) -> tuple[list[Hit], list[str]]:
    """Classify every mention under ``root``. Returns the hits and what could not be read - files
    that would not decode or parse, and directories the walk could not enter."""
    hits: list[Hit] = []
    unreadable: list[str] = []
    scan_root = root.parent if root.is_file() else root
    targets = [root] if root.is_file() else _walk_files(root, unreadable)
    for path in targets:
        if _is_config(path):
            hits.extend(_config_hits(path, identifier))
            continue
        if path.suffix not in _PY_SUFFIXES:
            continue
        try:
            source = path.read_text(encoding="utf-8-sig")
            hits.extend(classify_source(source, identifier, path=path, root=scan_root))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            unreadable.append(f"{path}: {type(exc).__name__}")
    return hits, unreadable


def _config_hits(path: Path, identifier: str) -> list[Hit]:
    """Whole-word mentions in a config file, always CONFIG - a value's home, never its enforcer."""
    try:
        lines = _lines(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, OSError):
        return []
    word = _word(identifier)
    return [
        Hit(HitKind.CONFIG, number, str(path), raw.strip())
        for number, raw in enumerate(lines, start=1)
        if word.search(raw)
    ]


def verdict_of(hits: list[Hit]) -> Verdict:
    """Fold hits into the answer: is anything DECIDING on this value?

    Examples:
        >>> verdict_of([]).found
        False
        >>> verdict_of([Hit(HitKind.DECLARATION, 1, "p.py", "x: int")]).enforced
        False
        >>> verdict_of([Hit(HitKind.DECISION, 1, "p.py", "if x > 1:")]).enforced
        True
    """
    counts: dict[str, int] = {}
    for hit in hits:
        counts[hit.kind.value] = counts.get(hit.kind.value, 0) + 1
    found = bool(hits)
    decisions = counts.get(HitKind.DECISION.value, 0)
    clamps = counts.get(HitKind.CLAMP.value, 0)
    enforced = decisions > 0 or clamps > 0
    if not found:
        summary = "not found: no mention anywhere, so this tool cannot answer - check the spelling and the root"
    elif enforced:
        parts = []
        if decisions:
            parts.append(f"{decisions} decision site(s) branch on it")
        if clamps:
            parts.append(f"{clamps} clamp site(s) cap a value with it (truncates, does not refuse)")
        summary = "enforced: " + ", and ".join(parts)
    else:
        summary = (
            "parsed but never enforced: it is declared, read or documented, and nothing compares "
            "anything to it - the value is documentation"
        )
    return Verdict(found=found, enforced=enforced, summary=summary, counts=counts)


def _render(identifier: str, hits: list[Hit], verdict: Verdict, unreadable: list[str]) -> str:
    lines = [f"{identifier}: {verdict.summary}", ""]
    order = [
        HitKind.DECISION,
        HitKind.CLAMP,
        HitKind.DECLARATION,
        HitKind.CONFIG,
        HitKind.REFERENCE,
        HitKind.TEST,
        HitKind.DOCSTRING,
        HitKind.COMMENT,
    ]
    for kind in order:
        bucket = [h for h in hits if h.kind is kind]
        if not bucket:
            continue
        lines.append(f"{kind.value} ({len(bucket)})")
        for hit in bucket[:20]:
            suffix = f"   [via local `{hit.via}`]" if hit.via else ""
            lines.append(f"    {hit.path}:{hit.line}  {hit.text[:100]}{suffix}")
        if len(bucket) > 20:
            lines.append(f"    ... {len(bucket) - 20} more")
        lines.append("")
    if unreadable:
        lines.append(f"UNREAD ({len(unreadable)}) - these were not classified, so the answer is incomplete:")
        lines.extend(f"    {item}" for item in unreadable)
    return "\n".join(lines)


def _tolerate_unencodable_stdout() -> None:
    """A Windows pipe is cp1252; a hit line it cannot encode must print as '?', not crash."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        pass


def _root_problem(root: Path) -> str | None:
    """Why ``root`` cannot be scanned, or None when it can be looked at.

    Not Path.exists(): before Python 3.14 it RAISES PermissionError for a path under an
    unreadable directory, and the traceback's exit 1 means "parsed but never enforced". Since
    3.14 it answers False, which would call an unreachable root missing. Both are exit 2, and
    the message says which."""
    try:
        os.stat(root)
    except (FileNotFoundError, NotADirectoryError):
        return f"no such root: {root}"
    except (OSError, ValueError) as exc:
        return f"root cannot be accessed ({type(exc).__name__}): {root}"
    return None


def main(argv: list[str] | None = None) -> int:
    _tolerate_unencodable_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("identifier", help="the exact name to classify (a config key, a field, a flag)")
    parser.add_argument("--root", default=".", help="file or directory to scan [.]")
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope on stdout")
    args = parser.parse_args(argv)

    root = Path(args.root)
    problem = _root_problem(root)
    if problem:
        # JSON mode must still emit JSON when it FAILS, or a caller parsing stdout gets an empty
        # string and reports "no hits" for what was actually a bad path.
        if args.json:
            print(json.dumps({"ok": False, "command": "enforced",
                              "data": {"identifier": args.identifier, "error": problem},
                              "skipped": []}, indent=1))
        else:
            print(problem, file=sys.stderr)
        return 2
    hits, unreadable = classify_tree(root, args.identifier)
    verdict = verdict_of(hits)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": verdict.found,
                    "command": "enforced",
                    "data": {
                        "identifier": args.identifier,
                        "verdict": asdict(verdict),
                        "hits": [{**asdict(h), "kind": h.kind.value} for h in hits],
                    },
                    "skipped": unreadable,
                },
                indent=1,
            )
        )
    else:
        print(_render(args.identifier, hits, verdict, unreadable))
    if unreadable and not verdict.enforced:
        # An unread file could hold the only enforcer, so "never enforced" is not safe to assert.
        print(f"\nincomplete: {len(unreadable)} path(s) unread; treat the verdict as unproven", file=sys.stderr)
        return 2
    if not verdict.found:
        return 2
    return 0 if verdict.enforced else 1


if __name__ == "__main__":
    raise SystemExit(main())
