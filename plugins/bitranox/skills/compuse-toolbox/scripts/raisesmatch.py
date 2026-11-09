# /// script
# requires-python = ">=3.10"
# ///
"""Does a pytest.raises / warns match= pattern really pin the refusal, or would ANY refusal pass it?

Why: `pytest.raises(X, match=...)` passes on the first X raised for ANY reason, and most validators
quote the offending input in their message. A pattern that is only a number, a single word or a
key name is therefore satisfied by a refusal for a different reason - a fixture defect, an unknown
field refused by `extra="forbid"` before the field even exists - and the test is green before the
feature it guards is written. Hit three times (2026-09-20 twice in lsdsk, 2026-10-29 in datamax-dpl,
`match="10"` passing on pydantic's echoed input), so the rule moved from a note into a check.

It parses each file (AST, never imports it) and judges every literal pattern of:
  pytest.raises / pytest.warns (any alias, or `from pytest import raises`), keyword match=
  self.assertRaisesRegex / assertWarnsRegex, second argument or expected_regex=

Kinds flagged:
  number        only a number (anchors and escapes ignored): "10", r"0\\.5", "^-1$"
  single-token  one token without whitespace: "offset_along", "Invalid", "--bottom"
  empty         "" matches every message
  no-match      no pattern at all (only with --require-match)

A pattern that is not a string literal (a variable, an f-string) is counted as not judged, never
as clean. A deliberate single-token pattern (a KeyError carries only the key) is waived with a
comment on the call's first line or the pattern's line: `# raisesmatch: ok - <reason>`; a waiver
without a reason does not count.

Run:
  uv run scripts/raisesmatch.py tests/            # text report
  uv run scripts/raisesmatch.py --json src tests  # {"ok","command","data","skipped"} envelope

Exit 0 nothing flagged, 1 at least one finding, 2 no .py file found or bad usage (a scan that
examined nothing is a refusal, not a pass). A file that does not parse is listed under skipped.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PYTEST_CALLS = frozenset({"raises", "warns"})
UNITTEST_CALLS = frozenset({"assertRaisesRegex", "assertWarnsRegex"})
SKIP_DIRS = frozenset({"__pycache__", ".git", "node_modules", ".tox", ".nox", "build", "dist"})
WAIVER = re.compile(r"#\s*raisesmatch:\s*ok\b[\s:-]*(?P<reason>.*)$")
NUMBER = re.compile(r"[-+]?[0-9]+(?:[.,][0-9]+)?")
# regex pieces that stand for a gap between words, so "Bad\s+key" or "Bad.*key" reads as two words
WORD_GAP = re.compile(r"\\s[+*?]?|\.[*+?]")
ESCAPED = re.compile(r"\\([^A-Za-z0-9])")


@dataclass
class Finding:
    """One arm whose pattern does not pin the refusal."""

    path: str
    line: int
    kind: str
    pattern: str
    call: str


@dataclass
class Report:
    """What one file (or a whole run) examined and found."""

    findings: list[Finding] = field(default_factory=list)
    calls: int = 0
    judged: int = 0
    unjudged: int = 0
    waived: int = 0

    def merge(self, other: Report) -> None:
        """Add another report's counts and findings to this one."""
        self.findings.extend(other.findings)
        self.calls += other.calls
        self.judged += other.judged
        self.unjudged += other.unjudged
        self.waived += other.waived


def classify(pattern: str) -> str | None:
    """Name the weakness of a literal pattern, or None when it reads as a phrase.

    >>> classify("10"), classify("offset_along"), classify("less than or equal to 10")
    ('number', 'single-token', None)
    """
    text = pattern
    for prefix in ("^", "\\A"):
        text = text.removeprefix(prefix)
    for suffix in ("$", "\\Z"):
        text = text.removesuffix(suffix)
    text = ESCAPED.sub(r"\1", WORD_GAP.sub(" ", text)).strip()
    if not text:
        return "empty"
    if NUMBER.fullmatch(text):
        return "number"
    if not any(ch.isspace() for ch in text):
        return "single-token"
    return None


class _Aliases:
    """The names under which this file reaches pytest and its raises/warns."""

    def __init__(self, tree: ast.Module) -> None:
        self.modules: set[str] = set()
        self.functions: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.modules.update(a.asname or a.name for a in node.names if a.name == "pytest")
            elif isinstance(node, ast.ImportFrom) and node.module == "pytest":
                self.functions.update(
                    {a.asname or a.name: a.name for a in node.names if a.name in PYTEST_CALLS}
                )

    def call_name(self, call: ast.Call) -> str | None:
        """'pytest.raises', 'assertRaisesRegex' ... for an arm, None for any other call."""
        func = call.func
        if isinstance(func, ast.Name) and func.id in self.functions:
            return f"pytest.{self.functions[func.id]}"
        if not isinstance(func, ast.Attribute):
            return None
        if func.attr in UNITTEST_CALLS:
            return func.attr
        if func.attr in PYTEST_CALLS and isinstance(func.value, ast.Name) and func.value.id in self.modules:
            return f"pytest.{func.attr}"
        return None


def _pattern_node(call: ast.Call, name: str) -> ast.expr | None:
    keyword = "match" if name.startswith("pytest.") else "expected_regex"
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    if not name.startswith("pytest.") and len(call.args) >= 2:
        return call.args[1]
    return None


def _waived(lines: list[str], *linenos: int) -> bool:
    for lineno in linenos:
        found = WAIVER.search(lines[lineno - 1]) if 0 < lineno <= len(lines) else None
        if found and found.group("reason").strip():
            return True
    return False


def scan_source(source: str, path: str, *, require_match: bool = False) -> Report:
    """Judge every raises/warns arm in one file's source text.

    Raises:
        SyntaxError: the source does not parse.
    """
    tree = ast.parse(source, filename=path)
    aliases = _Aliases(tree)
    lines = source.splitlines()
    report = Report()
    for node in ast.walk(tree):
        name = aliases.call_name(node) if isinstance(node, ast.Call) else None
        if name is None or not isinstance(node, ast.Call):
            continue
        report.calls += 1
        pattern = _pattern_node(node, name)
        if pattern is None:
            if require_match:
                report.findings.append(Finding(path, node.lineno, "no-match", "", name))
            continue
        if not (isinstance(pattern, ast.Constant) and isinstance(pattern.value, str)):
            report.unjudged += 1
            continue
        report.judged += 1
        kind = classify(pattern.value)
        if kind is None:
            continue
        if _waived(lines, node.lineno, pattern.lineno):
            report.waived += 1
            continue
        report.findings.append(Finding(path, node.lineno, kind, pattern.value, name))
    report.findings.sort(key=lambda f: f.line)
    return report


def python_files(paths: list[Path]) -> list[Path]:
    """Every .py file named or under the named dirs, skipping caches and virtualenvs."""
    found: list[Path] = []
    for root in paths:
        if root.is_file():
            found.append(root)
            continue
        for py in sorted(root.rglob("*.py")):
            parts = py.relative_to(root).parts[:-1]
            if any(p in SKIP_DIRS or p.startswith(".venv") for p in parts):
                continue
            found.append(py)
    return found


def run(paths: list[Path], *, require_match: bool) -> tuple[Report, list[dict[str, str]], int]:
    """Scan every file; return the merged report, the files skipped and how many were examined."""
    files = python_files(paths)
    total = Report()
    skipped: list[dict[str, str]] = []
    for py in files:
        try:
            total.merge(scan_source(py.read_text(encoding="utf-8"), str(py), require_match=require_match))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            skipped.append({"path": str(py), "reason": f"{type(exc).__name__}: {exc}"})
    return total, skipped, len(files)


def _text(report: Report, skipped: list[dict[str, str]], files: int) -> str:
    out = [f"{f.path}:{f.line}: {f.kind} match={f.pattern!r} ({f.call})" for f in report.findings]
    out += [f"skipped {s['path']}: {s['reason']}" for s in skipped]
    out.append(
        f"{files} file(s), {report.calls} arm(s) ({report.judged} judged, {report.unjudged} not a literal,"
        f" {report.waived} waived): {len(report.findings)} finding(s)"
    )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("tests")], help="files or dirs (default: tests)")
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope")
    parser.add_argument("--require-match", action="store_true", help="also flag raises/warns with no match=")
    args = parser.parse_args(argv)
    missing = [str(p) for p in args.paths if not p.exists()]
    if missing:
        print(f"raisesmatch: no such path: {', '.join(missing)}", file=sys.stderr)
        return 2
    report, skipped, files = run(args.paths, require_match=args.require_match)
    if files == 0:
        print(f"raisesmatch: no .py file under {', '.join(map(str, args.paths))}", file=sys.stderr)
        return 2
    if args.json:
        data = {"files": files, **{k: v for k, v in asdict(report).items()}}
        print(json.dumps({"ok": True, "command": "raisesmatch", "data": data, "skipped": skipped}, indent=2))
    else:
        print(_text(report, skipped, files))
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
