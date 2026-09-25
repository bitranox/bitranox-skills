#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Full-text search over raw Claude Code transcripts.

The curated fact store answers "what rule applies here". This answers "what did
we actually do about X", which does not depend on a fact having been written at
the time. No LLM in the write path: index narrated prose, grep it later.

Coverage: only string message content and the "text" parts of list content are
indexed. tool_use, tool_result and thinking blocks contribute no text and are
NOT indexed, so a session where the work happened through tool calls with no
narrating sentence is invisible to search. A miss means "not narrated in
prose", not "never happened" - corroborate with the raw transcript before
concluding something did not occur.

Query: each whitespace-separated word is matched LITERALLY and all of them must
occur (in any order), so a filename, a flag or error text is searchable as
typed: `search anchor_edit.py`, `search ssh-keygen`. Pass --fts to write raw
SQLite FTS5 syntax instead (OR, NEAR, "exact phrase", prefix*).

Usage:
    transcript_index.py index
    transcript_index.py search "zpool scrub" --limit 5
    transcript_index.py search "zpool scrub" --json
    transcript_index.py search --fts '"zpool scrub" OR resilver'

Exit: 0 hits (or index done), 1 no match, 2 error (a malformed --fts query, an
empty query, a directory or file that could not be read while indexing).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import sys

__all__ = ["QueryError", "ensure_schema", "fts_literal", "index_dir", "search", "main"]

DB_PATH = pathlib.Path.home() / ".claude" / "transcript-index.db"
ROOT = pathlib.Path.home() / ".claude" / "projects"

NO_MATCH_CAVEAT = (
    "tool calls, tool results and thinking blocks are not indexed - a miss "
    "means it was not narrated in prose, not that it never happened"
)


class QueryError(ValueError):
    """The query could not be run, so it answered nothing - never report it as a miss."""


def ensure_schema(db: sqlite3.Connection) -> None:
    """Create the FTS5 table and the seen-line registry if absent."""
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS messages "
        "USING fts5(project, path, role, text, tokenize='porter unicode61')"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS seen (key TEXT PRIMARY KEY)"
    )
    db.commit()


def _text_of(obj: dict) -> str:
    """Flatten a transcript message to searchable text."""
    msg = obj.get("message")
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
    return ""


def _transcripts(root: pathlib.Path, errors: list[str]) -> list[pathlib.Path]:
    """Every .jsonl under root, recording each directory that could not be listed.

    Recursive, not `*/*.jsonl`: a SUBAGENT's transcript sits two levels deeper, at
    <project>/<session>/subagents/agent-*.jsonl. The shallow walk reached only the main-session
    files - 878 of 2,090 on the machine this was measured on - so work a subagent narrated came
    back as no match, which reads exactly like "it never happened". That is the one conclusion
    this tool's own docstring warns a reader not to draw from a miss. For the same reason an
    unreadable directory is reported, never skipped in silence.
    """
    found: list[pathlib.Path] = []

    def onerror(exc: OSError) -> None:
        errors.append(f"cannot list {exc.filename}: {exc.strerror or exc}")

    for dirpath, _dirs, files in os.walk(root, onerror=onerror):
        found.extend(pathlib.Path(dirpath) / f for f in files if f.endswith(".jsonl"))
    return sorted(found)


def _index_file(path: pathlib.Path, project: str, db: sqlite3.Connection) -> int:
    added = 0
    # utf-8-sig: a BOM would otherwise make the first record unparseable and drop it unseen.
    with path.open(encoding="utf-8-sig", errors="replace") as fh:
        for lineno, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = _text_of(obj)
            # strip(): a list of only tool parts joins to bare separators, which is no text.
            if not text.strip():
                continue
            key = f"{path}:{lineno}"
            cur = db.execute("SELECT 1 FROM seen WHERE key = ?", (key,))
            if cur.fetchone():
                continue
            db.execute("INSERT INTO seen(key) VALUES (?)", (key,))
            db.execute(
                "INSERT INTO messages(project, path, role, text) "
                "VALUES (?, ?, ?, ?)",
                (project, str(path), obj.get("type", ""), text),
            )
            added += 1
    return added


def index_dir(root: pathlib.Path, db: sqlite3.Connection,
              errors: list[str] | None = None) -> int:
    """Index every .jsonl under root. Returns the count of NEW messages.

    Directories and files that could not be read are appended to `errors` (when given) and
    the rest is still indexed.
    """
    errors = [] if errors is None else errors
    added = 0
    for path in _transcripts(root, errors):
        # The label is the PROJECT, so take the component directly under root, never the parent
        # dir: for a nested transcript that parent is `subagents`, which names no project.
        project = path.relative_to(root).parts[0]
        try:
            added += _index_file(path, project, db)
        except OSError as exc:
            errors.append(f"cannot read {path}: {exc.strerror or exc}")
    db.commit()
    return added


def fts_literal(query: str) -> str:
    """Turn plain words into an FTS5 query that matches each word literally, all required.

    Raw FTS5 reads `.`, `-` and `:` as syntax, so `anchor_edit.py` was a syntax error and
    `ssh-keygen` a column filter, and both came back as "no matches". Quoting each word as a
    phrase makes its punctuation plain text while keeping the implicit AND between words.
    """
    words = query.split()
    if not words:
        raise QueryError("empty query")
    return " ".join('"' + w.replace('"', '""') + '"' for w in words)


def search(db: sqlite3.Connection, query: str, limit: int = 10,
           raw: bool = False) -> list[dict]:
    """Return matching messages, newest rowid first.

    `query` is plain words (see fts_literal) unless `raw`, when it is FTS5 syntax as typed.
    Raises QueryError when the query cannot be run, so a caller can tell it from a miss.
    """
    match = query if raw else fts_literal(query)
    try:
        rows = db.execute(
            "SELECT project, path, role, text FROM messages "
            "WHERE messages MATCH ? ORDER BY rowid DESC LIMIT ?",
            (match, limit),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise QueryError(str(exc)) from exc
    return [
        {"project": r[0], "path": r[1], "role": r[2], "text": r[3]}
        for r in rows
    ]


def _tolerate_console_encoding() -> None:
    """A cp1252 console cannot encode most transcript text; escape it, never crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="backslashreplace")
            except (ValueError, OSError):
                pass


def _run_index(db: sqlite3.Connection) -> int:
    errors: list[str] = []
    n = index_dir(ROOT, db, errors)
    print(f"indexed {n} new message(s)")
    for e in errors:
        print(f"transcript_index: {e}", file=sys.stderr)
    return 2 if errors else 0


def _query_failed(exc: QueryError, as_json: bool) -> int:
    message = f"query error: {exc}"
    if as_json:
        print(json.dumps({"ok": False, "command": "search", "data": [], "error": message}))
    else:
        print(message, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    _tolerate_console_encoding()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="index every transcript")
    s = sub.add_parser("search", help="full-text search")
    s.add_argument("query", help="words to find, each literally, all required")
    s.add_argument("--fts", action="store_true",
                   help="treat the query as raw SQLite FTS5 syntax (OR, NEAR, phrases)")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    ensure_schema(db)

    if args.cmd == "index":
        return _run_index(db)

    try:
        hits = search(db, args.query, args.limit, raw=args.fts)
    except QueryError as exc:
        return _query_failed(exc, args.as_json)
    if args.as_json:
        payload: dict[str, object] = {"ok": True, "command": "search", "data": hits}
        if not hits:
            payload["caveat"] = NO_MATCH_CAVEAT
        print(json.dumps(payload))
        return 0 if hits else 1
    for h in hits:
        print(f"[{h['project']}] {h['role']}: {h['text'][:200]}")
    if not hits:
        print("no matches", file=sys.stderr)
        print(NO_MATCH_CAVEAT, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
