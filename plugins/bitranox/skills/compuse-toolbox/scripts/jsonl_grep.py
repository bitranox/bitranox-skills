# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Filter a JSONL stream (a Claude Code transcript or any JSONL) by top-level type / message.role,
extract a dotted field, or regex over the raw line - the general form of transcript_tail's parsing.

Why: reading a JSONL by hand (`for line in open(...): json.loads(line)`) and picking fields is a
recurring chore in probe/self-mining work; an ad-hoc parser gets the varied content shapes wrong.

Run:
  `uv run scripts/jsonl_grep.py <file> [--type assistant] [--role user] [--field message.model]
                                     [--pattern REGEX]`
"""
from __future__ import annotations

import argparse
import sys

import orjson


def _get(obj, dotted: str):
    cur = obj
    for key in dotted.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur


def filter_records(text: str, *, type_=None, role=None, field=None, pattern=None):
    """Return matching records (list of dicts), or - when `field` is set - the extracted values.

    `pattern` is a regex tested against the RAW line (fast pre-filter); `type_` matches the
    top-level `type`; `role` matches `message.role`. Malformed lines are skipped.
    """
    import re
    rx = re.compile(pattern) if pattern else None
    out = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        if rx and not rx.search(raw):
            continue
        try:
            obj = orjson.loads(raw)
        except orjson.JSONDecodeError:
            continue
        if type_ is not None and obj.get("type") != type_:
            continue
        if role is not None and _get(obj, "message.role") != role:
            continue
        if field:
            val = _get(obj, field)
            if val is not None:
                out.append(val)
        else:
            out.append(obj)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Filter/extract from a JSONL stream.")
    ap.add_argument("jsonl", nargs="?", help="path to a *.jsonl file (default: stdin)")
    ap.add_argument("--type", dest="type_")
    ap.add_argument("--role")
    ap.add_argument("--field", help="dotted path to extract (e.g. message.model)")
    ap.add_argument("--pattern", help="regex over the raw line")
    args = ap.parse_args(argv)
    text = open(args.jsonl, encoding="utf-8", errors="replace").read() if args.jsonl else sys.stdin.read()
    for rec in filter_records(text, type_=args.type_, role=args.role, field=args.field, pattern=args.pattern):
        print(rec if isinstance(rec, str) else orjson.dumps(rec).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
