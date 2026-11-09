# /// script
# requires-python = ">=3.10"
# ///
"""Did a subagent's quote-back really come from the text it cites? Substring-check quotes against a dir.

Why: a probe or reviewer subagent asked to quote the sentence that governs its answer returns a
verdict-shaped quote whether or not the sentence exists - a paraphrase, a merge of two lines, or a
sentence from the OTHER arm's text. Asserting is cheaper than quoting, so the quote is checked, not
believed. This check was hand-written four times in one fold campaign before it became a tool.

A quote is split into parts at an ellipsis (three dots or the single character), " / ", "|" and
newlines - the ways an agent joins non-adjacent sentences - and each part is normalised (backticks,
** and escaped quotes removed, whitespace collapsed, surrounding quotes stripped, case-folded) and
looked up in the normalised text of every *.md file under the cited dir (.skillwriter/ excluded).

Verdicts per quote:
  OK         every part was found
  MISMATCH   at least one part was not found (the missing parts are listed)
  NONE       the agent answered NONE (it found no governing sentence) - nothing to check
  TOO-SHORT  every part was shorter than --min-part, so nothing was checked; never counted as OK

Two modes:
  text     one or more quotes (--quote repeats) against one dir
  journal  every row of every result in a Workflow journal.jsonl whose agent label matches --label;
           each row's dir is looked up by its key (--key, default slug) in --rows files (JSON lists
           of row objects) under --dir-field, or is the single --dir for all rows

Run:
  uv run scripts/quotecheck.py text --dir SKILL_DIR --quote "the sentence"
  uv run scripts/quotecheck.py journal journal.jsonl --label '^RED ' --rows h1.json h2.json \
      --dir-field pre_snapshot_dir [--key slug] [--quote-field quote] [--json]

Exit 0 when every checked quote is OK or NONE, 1 when any is MISMATCH or TOO-SHORT, 2 when it could
not run - including a journal run that examined no row (a check that examined nothing is a refusal).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, NoReturn

ELLIPSIS = chr(0x2026)
SPLIT = re.compile(r"\.\.\.|" + ELLIPSIS + r"| / |\||\n")
WHITESPACE = re.compile(r"\s+")
DEFAULT_MIN_PART = 12


class UsageError(Exception):
    """The run could not start or examined nothing (exit 2)."""


@dataclass
class Verdict:
    """One quote's outcome."""

    verdict: str
    missing: list[str] = field(default_factory=list)


def normalise(text: str) -> str:
    """Normalise text for a substring match: markup out, whitespace collapsed, case-folded.

    >>> normalise('  Use `x`   **now**\\n"done" ')
    'use x now "done"'
    """
    text = text.replace("`", "").replace("**", "").replace('\\"', '"')
    return WHITESPACE.sub(" ", text).strip().strip('"').strip().casefold()


def dir_text(path: Path) -> str:
    """Normalised text of every *.md under a dir (or of the one file named), .skillwriter excluded."""
    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = [f for f in sorted(path.rglob("*.md")) if ".skillwriter" not in f.parts]
    else:
        raise UsageError(f"no such dir or file: {path}")
    if not files:
        raise UsageError(f"no *.md file under {path}")
    return normalise("\n".join(f.read_text(encoding="utf-8") for f in files))


def quote_parts(quote: str, min_part: int) -> list[str]:
    """The normalised parts of a quote that are long enough to check."""
    parts = (normalise(p) for p in SPLIT.split(quote))
    return [p for p in parts if len(p) >= min_part]


def check_quote(quote: str, text: str, min_part: int = DEFAULT_MIN_PART) -> Verdict:
    """Check one quote against already-normalised text."""
    if quote.strip().upper() == "NONE":
        return Verdict("NONE")
    parts = quote_parts(quote, min_part)
    if not parts:
        return Verdict("TOO-SHORT")
    missing = [p for p in parts if p not in text]
    return Verdict("MISMATCH", missing) if missing else Verdict("OK")


def load_journal(path: Path) -> list[dict[str, object]]:
    """Every JSON record of a journal.jsonl (blank and non-JSON lines skipped)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise UsageError(f"cannot read journal {path}: {exc}") from exc
    records = []
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            records.append(rec)
    return records


def labelled_results(records: list[dict[str, object]], label: re.Pattern[str]) -> list[tuple[str, list[object]]]:
    """[(label, rows)] for each result whose agent's started-label matches."""
    labels = {r.get("agentId"): str(r.get("label", "")) for r in records if r.get("type") == "started"}
    out = []
    for rec in records:
        if rec.get("type") != "result":
            continue
        name = labels.get(rec.get("agentId"), "")
        result = rec.get("result")
        if label.search(name) and isinstance(result, dict) and isinstance(result.get("rows"), list):
            out.append((name, result["rows"]))
    return out


def load_dir_map(rows_files: list[Path], key: str, dir_field: str) -> dict[str, Path]:
    """{key value: dir} from JSON row-list files."""
    mapping: dict[str, Path] = {}
    for path in rows_files:
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise UsageError(f"cannot read rows file {path}: {exc}") from exc
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict) and key in row and dir_field in row:
                mapping[str(row[key])] = Path(str(row[dir_field]))
    if not mapping:
        raise UsageError(f"no row in {[str(p) for p in rows_files]} has both {key!r} and {dir_field!r}")
    return mapping


class DirTexts:
    """Normalised dir texts, read once each."""

    def __init__(self) -> None:
        self._cache: dict[Path, str] = {}

    def get(self, path: Path) -> str:
        if path not in self._cache:
            self._cache[path] = dir_text(path)
        return self._cache[path]


@dataclass
class ReportRow:
    """One checked quote in the report."""

    label: str
    key: str
    verdict: str
    missing: list[str] = field(default_factory=list)


def check_journal(args: argparse.Namespace) -> list[ReportRow]:
    """One report row per journal row checked."""
    label = re.compile(args.label)
    results = labelled_results(load_journal(Path(args.journal)), label)
    dir_map = load_dir_map([Path(p) for p in args.rows], args.key, args.dir_field) if args.rows else {}
    texts = DirTexts()
    report: list[ReportRow] = []
    for name, rows in results:
        for row in rows:
            if isinstance(row, dict):
                report.append(_check_row(row, name, args, dir_map, texts))
    if not report:
        raise UsageError(f"no result row from an agent whose label matches {args.label!r}")
    return report


def _check_row(row: dict[str, object], name: str, args: argparse.Namespace,
               dir_map: dict[str, Path], texts: DirTexts) -> ReportRow:
    key = str(row.get(args.key, ""))
    base = Path(args.dir) if args.dir else dir_map.get(key)
    if base is None:
        return ReportRow(name, key, "UNKNOWN-KEY")
    verdict = check_quote(str(row.get(args.quote_field, "")), texts.get(base), args.min_part)
    return ReportRow(name, key, verdict.verdict, verdict.missing)


def tally(report: list[ReportRow]) -> dict[str, int]:
    """Count of each verdict."""
    counts: dict[str, int] = {}
    for row in report:
        counts[row.verdict] = counts.get(row.verdict, 0) + 1
    return counts


def failed(report: list[ReportRow]) -> bool:
    """True when any row is neither OK nor NONE."""
    return any(row.verdict not in ("OK", "NONE") for row in report)


def render_text(report: list[ReportRow]) -> str:
    """Human report: the tally, then every row that is not OK."""
    lines = [f"rows checked: {len(report)}  {tally(report)}"]
    for row in report:
        if row.verdict == "OK":
            continue
        lines.append(f"{row.verdict:11} {row.label}  {row.key}")
        lines.extend(f"    missing: {part}" for part in row.missing)
    return "\n".join(lines)


class EnvelopeParser(argparse.ArgumentParser):
    """An ArgumentParser whose usage error prints a JSON envelope when the run asked for --json."""

    def __init__(self, *args: Any, json_requested: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.json_requested = json_requested

    def error(self, message: str) -> NoReturn:
        if self.json_requested:
            print(json.dumps({"ok": False, "command": "quotecheck", "error": message}))
            raise SystemExit(2)
        super().error(message)


def build_parser(json_requested: bool = False) -> argparse.ArgumentParser:
    parser = EnvelopeParser(prog="quotecheck", json_requested=json_requested,
                            description="Substring-check quote-backs against the text they cite.")
    sub = parser.add_subparsers(dest="mode", required=True,
                                parser_class=partial(EnvelopeParser, json_requested=json_requested))
    text = sub.add_parser("text", help="one or more quotes against one dir")
    text.add_argument("--dir", required=True)
    # append, not store: a repeated --quote must not silently keep only the last one.
    text.add_argument("--quote", required=True, action="append", help="repeatable, one row each")
    journal = sub.add_parser("journal", help="every row of matching results in a Workflow journal")
    journal.add_argument("journal")
    journal.add_argument("--label", required=True, help="regex on the agent's started-label")
    journal.add_argument("--rows", nargs="+", help="JSON row-list files mapping --key to --dir-field")
    journal.add_argument("--dir-field", help="row field holding the dir to check against")
    journal.add_argument("--dir", help="one dir for every row instead of --rows/--dir-field")
    journal.add_argument("--key", default="slug")
    journal.add_argument("--quote-field", default="quote")
    for p in (text, journal):
        p.add_argument("--min-part", type=int, default=DEFAULT_MIN_PART)
        p.add_argument("--json", action="store_true", help="print a JSON envelope")
    return parser


def run(args: argparse.Namespace) -> list[ReportRow]:
    """The report for either mode."""
    if args.mode == "text":
        text = dir_text(Path(args.dir))
        verdicts = (check_quote(q, text, args.min_part) for q in args.quote)
        return [ReportRow("", str(i), v.verdict, v.missing) for i, v in enumerate(verdicts, 1)]
    if not args.dir and not (args.rows and args.dir_field):
        raise UsageError("journal mode needs --dir, or --rows with --dir-field")
    return check_journal(args)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser("--json" in argv).parse_args(argv)
    try:
        report = run(args)
    except UsageError as exc:
        if args.json:
            print(json.dumps({"ok": False, "command": "quotecheck", "error": str(exc)}))
        else:
            print(f"quotecheck: {exc}", file=sys.stderr)
        return 2
    if args.json:
        data = {"tally": tally(report), "rows": [asdict(r) for r in report]}
        print(json.dumps({"ok": True, "command": "quotecheck", "data": data}, indent=2))
    else:
        print(render_text(report))
    return 1 if failed(report) else 0


if __name__ == "__main__":
    sys.exit(main())
