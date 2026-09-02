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
is compared to it, or control flow branches on it - enforcement by refusal) and CLAMP (min()/max()
caps a value with it - enforcement by truncation, which bounds without ever branching). The rest do
not: DECLARATION, CONFIG, TEST, DOCSTRING, COMMENT and plain REFERENCE. Both empty is the answer.

It follows ONE alias hop inside a function: `ceiling = self.policy.tokens_per_row.get(row)` then a
decision on `ceiling` counts, reported as "via local `ceiling`". One hop and one scope on purpose -
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

Run: `uv run scripts/enforced.py planner_kinds --root src/`
     `uv run scripts/enforced.py on_auth_failure --root . --json`
Exit 0 = enforced (a decision exists), 1 = parsed but never enforced, 2 = not found or unreadable.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

__all__ = ["Hit", "HitKind", "Verdict", "classify_source", "classify_tree", "verdict_of"]

_PY_SUFFIXES = frozenset({".py", ".pyi"})
_CONFIG_SUFFIXES = frozenset({".yaml", ".yml", ".toml", ".json", ".ini", ".cfg", ".env"})
_CLAMP_CALLS = frozenset({"min", "max"})
"""Builtins that BOUND a value. Only these - treating any call as enforcement would make every
argument of every function a bound."""

_SKIP_DIRS = frozenset({".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".ruff_cache"})


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
    parts = {p.lower() for p in path.parts}
    return bool(parts & {"tests", "test"}) or path.name.startswith("test_")


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
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            return False
        current = parent


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
    hits: list[Hit] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc and identifier in doc:
            body = node.body[0] if node.body else None
            line = getattr(body, "lineno", 1)
            hits.append(Hit(HitKind.DOCSTRING, line, str(path), _line_text(lines, line)))
    return hits


def _comment_hits(identifier: str, path: Path, lines: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for number, raw in enumerate(lines, start=1):
        comment = raw.split("#", 1)[1] if "#" in raw else ""
        if identifier in comment:
            hits.append(Hit(HitKind.COMMENT, number, str(path), raw.strip()))
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
    """If this mention is the VALUE of `name = <...node...>`, return that local name and its line."""
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


def classify_source(source: str, identifier: str, *, path: Path) -> list[Hit]:
    """Classify every mention of ``identifier`` in one Python source string.

    Args:
        source: The file's text.
        identifier: The exact name to look for; substrings of longer names never match.
        path: Where it came from, used for the text of each hit and to spot a test path.

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
    lines = source.splitlines()
    table = _parents(tree)
    in_test = _is_test_path(path)
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
    doc_and_comment = _docstring_hits(tree, identifier, path, lines) + _comment_hits(identifier, path, lines)
    if in_test:
        doc_and_comment = [Hit(HitKind.TEST, h.line, h.path, h.text) for h in doc_and_comment]
    hits.extend(doc_and_comment)
    return sorted(hits, key=lambda h: (h.line, h.kind.value))


def classify_tree(root: Path, identifier: str) -> tuple[list[Hit], list[str]]:
    """Classify every mention under ``root``. Returns the hits and the files that could not be read."""
    hits: list[Hit] = []
    unreadable: list[str] = []
    targets = [root] if root.is_file() else sorted(root.rglob("*"))
    for path in targets:
        if not path.is_file() or _SKIP_DIRS & set(path.parts):
            continue
        if path.suffix in _CONFIG_SUFFIXES:
            hits.extend(_config_hits(path, identifier))
            continue
        if path.suffix not in _PY_SUFFIXES:
            continue
        try:
            hits.extend(classify_source(path.read_text(encoding="utf-8"), identifier, path=path))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            unreadable.append(f"{path}: {type(exc).__name__}")
    return hits, unreadable


def _config_hits(path: Path, identifier: str) -> list[Hit]:
    """Mentions in a config file, always CONFIG - a value's home, never its enforcer."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    return [
        Hit(HitKind.CONFIG, number, str(path), raw.strip())
        for number, raw in enumerate(lines, start=1)
        if identifier in raw
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("identifier", help="the exact name to classify (a config key, a field, a flag)")
    parser.add_argument("--root", default=".", help="file or directory to scan [.]")
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope on stdout")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.exists():
        # JSON mode must still emit JSON when it FAILS, or a caller parsing stdout gets an empty
        # string and reports "no hits" for what was actually a bad path.
        if args.json:
            print(json.dumps({"ok": False, "command": "enforced",
                              "data": {"identifier": args.identifier, "error": f"no such root: {root}"},
                              "skipped": []}, indent=1))
        else:
            print(f"no such root: {root}", file=sys.stderr)
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
        print(f"\nincomplete: {len(unreadable)} file(s) unread; treat the verdict as unproven", file=sys.stderr)
        return 2
    if not verdict.found:
        return 2
    return 0 if verdict.enforced else 1


if __name__ == "__main__":
    raise SystemExit(main())
