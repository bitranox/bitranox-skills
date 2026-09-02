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

Usage:
    transcript_index.py index
    transcript_index.py search "zpool scrub" --limit 5
    transcript_index.py search "zpool scrub" --json
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys

__all__ = ["ensure_schema", "index_dir", "search", "main"]

DB_PATH = pathlib.Path.home() / ".claude" / "transcript-index.db"
ROOT = pathlib.Path.home() / ".claude" / "projects"

NO_MATCH_CAVEAT = (
    "tool calls, tool results and thinking blocks are not indexed - a miss "
    "means it was not narrated in prose, not that it never happened"
)


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


def index_dir(root: pathlib.Path, db: sqlite3.Connection) -> int:
    """Index every .jsonl under root. Returns the count of NEW messages."""
    added = 0
    for path in sorted(root.glob("*/*.jsonl")):
        project = path.parent.name
        with path.open(encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = _text_of(obj)
                if not text:
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
    db.commit()
    return added


def search(db: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    """Return matching messages, newest rowid first."""
    try:
        rows = db.execute(
            "SELECT project, path, role, text FROM messages "
            "WHERE messages MATCH ? ORDER BY rowid DESC LIMIT ?",
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {"project": r[0], "path": r[1], "role": r[2], "text": r[3]}
        for r in rows
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="index every transcript")
    s = sub.add_parser("search", help="full-text search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    ensure_schema(db)

    if args.cmd == "index":
        n = index_dir(ROOT, db)
        print(f"indexed {n} new message(s)")
        return 0

    hits = search(db, args.query, args.limit)
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
