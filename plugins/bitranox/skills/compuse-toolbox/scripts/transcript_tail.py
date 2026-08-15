# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Read a Claude Code JSONL transcript: the last user/assistant text, or the WHOLE thing.

Why this exists: a transcript record's content shape varies - user `content` is a plain string
OR a list of tool_result blocks; assistant `content` is a list of thinking/text/tool_use blocks.
An ad-hoc one-line parser flattens them wrong and silently returns empty (hit twice by hand).
This flattens each shape correctly, keeps only visible text (drops thinking/tool_use), and skips
sidechain (subagent) and meta records by default.

The whole-transcript modes exist because the tail alone is not enough to mine a finished session:
answering "what did the user ask over the run?" or "which Agent dispatches went out, with what
input?" from the tail leaves you hand-rolling an extractor per question, and a raw JSONL field
dump hands back block JSON rather than the text. Every row carries the 1-based JSONL LINE NUMBER
it came from, so a finding can be pointed at (`sed -n '<line>p'`) instead of re-searched.

Run:
  `uv run scripts/transcript_tail.py <transcript.jsonl> [--role user|assistant|both]`
  `uv run scripts/transcript_tail.py <transcript.jsonl> --all [--role user] [--json]`
  `uv run scripts/transcript_tail.py <transcript.jsonl> --tool Agent [--json]`

Exit codes: 0 = a result, 1 = the whole-transcript mode matched nothing, 2 = usage error.
The default tail mode always exits 0 (a role never seen is reported as empty, not as no-match).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:                                                     # fast path when available (uv run installs it)
    import orjson

    def _loads(raw):
        return orjson.loads(raw)

    _JSONDecodeError = orjson.JSONDecodeError

    def _dumps(obj):
        return orjson.dumps(obj).decode()
except ModuleNotFoundError:                              # stdlib fallback so the script runs anywhere
    import json as _json

    def _loads(raw):
        return _json.loads(raw)

    _JSONDecodeError = _json.JSONDecodeError

    def _dumps(obj):
        return _json.dumps(obj, ensure_ascii=False)


def _flatten(content) -> str:
    """A record's content -> its visible text. str stays; a block list keeps text + tool_result."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif kind == "tool_result":
                parts.append(_flatten(block.get("content")))
        return "\n".join(p for p in parts if p)
    return ""


def iter_records(path, *, skip_sidechain: bool = True, skip_meta: bool = True, malformed=None):
    """Yield `(line_number, record)` for every usable record, line numbers 1-based.

    The line number counts EVERY physical line in the file, blank and unparseable ones included,
    so it addresses the file directly (`sed -n '<n>p'`). A line that is blank, is not JSON, or is
    JSON but not an object is skipped; when `malformed` is a list, the non-blank skipped line
    numbers are appended to it, so a caller can report them instead of dropping them silently.
    """
    with open(path, "rb") as handle:
        for lineno, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = _loads(raw)
            except _JSONDecodeError:
                obj = None
            if not isinstance(obj, dict):
                if malformed is not None:
                    malformed.append(lineno)
                continue
            if skip_sidechain and obj.get("isSidechain"):
                continue
            if skip_meta and obj.get("isMeta"):
                continue
            yield lineno, obj


def tail_messages(path, *, skip_sidechain: bool = True, skip_meta: bool = True) -> dict:
    """Return {"user": <last user text>, "assistant": <last assistant text>} from a JSONL transcript.

    Only visible text is returned (assistant thinking/tool_use blocks are dropped). A role never
    seen stays "". A malformed line is skipped, not fatal.
    """
    last = {"user": "", "assistant": ""}
    for _lineno, obj in iter_records(path, skip_sidechain=skip_sidechain, skip_meta=skip_meta):
        role = obj.get("type")
        if role not in ("user", "assistant"):
            continue
        text = _flatten((obj.get("message") or {}).get("content"))
        if text.strip():
            last[role] = text
    return last


def all_messages(path, *, role=None, skip_sidechain: bool = True, skip_meta: bool = True,
                 malformed=None) -> list[dict]:
    """Every user/assistant turn that has visible text, in file order.

    Each row is {"line": <1-based JSONL line>, "role": "user"|"assistant", "text": <flattened>}.
    One row per RECORD, not per block: a record's text blocks all come from the same line, so
    splitting them would repeat the line number without telling the reader anything new. `role`
    narrows to one side; None (the default) keeps both.
    """
    rows = []
    for lineno, obj in iter_records(path, skip_sidechain=skip_sidechain, skip_meta=skip_meta,
                                    malformed=malformed):
        kind = obj.get("type")
        if kind not in ("user", "assistant"):
            continue
        if role is not None and kind != role:
            continue
        text = _flatten((obj.get("message") or {}).get("content"))
        if text.strip():
            rows.append({"line": lineno, "role": kind, "text": text})
    return rows


def tool_uses(path, name, *, skip_sidechain: bool = True, skip_meta: bool = True,
              malformed=None) -> list[dict]:
    """Every `tool_use` block invoking tool `name`, in file order.

    Each row is {"line": <1-based JSONL line>, "name": <tool>, "input": <the block's input>}.
    Several calls in one record each get their own row, all carrying that record's line number.
    """
    rows = []
    for lineno, obj in iter_records(path, skip_sidechain=skip_sidechain, skip_meta=skip_meta,
                                    malformed=malformed):
        content = (obj.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != name:
                continue
            rows.append({"line": lineno, "name": block.get("name"), "input": block.get("input")})
    return rows


def _print_rows(rows, command: str) -> None:
    """Human form: a `== line N <label> ==` header per row, then the text or the tool input."""
    for row in rows:
        if command == "tool_uses":
            print("== line %d %s ==\n%s" % (row["line"], row["name"], _dumps(row["input"])))
        else:
            print("== line %d %s ==\n%s" % (row["line"], row["role"], row["text"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read a Claude Code JSONL transcript: the last texts, "
                                             "every text turn, or every call of one tool.")
    ap.add_argument("transcript", type=Path, help="path to a *.jsonl transcript")
    ap.add_argument("--role", choices=["user", "assistant", "both"], default="both")
    ap.add_argument("--include-sidechain", action="store_true", help="do not skip subagent (sidechain) records")
    ap.add_argument("--include-meta", action="store_true", help="do not skip meta records")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope (--all / --tool)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="EVERY text turn, with its JSONL line number")
    mode.add_argument("--tool", metavar="NAME", help="every tool_use of NAME, with its line number and input")
    args = ap.parse_args(argv)
    skip_sidechain, skip_meta = not args.include_sidechain, not args.include_meta

    if not args.all and args.tool is None:
        out = tail_messages(args.transcript, skip_sidechain=skip_sidechain, skip_meta=skip_meta)
        if args.json:
            print(_dumps({"ok": True, "command": "tail_messages", "skipped": [], "data": out}))
            return 0
        if args.role in ("user", "both"):
            print("== last user ==\n" + out["user"])
        if args.role in ("assistant", "both"):
            print("== last assistant ==\n" + out["assistant"])
        return 0

    malformed: list[int] = []
    if args.tool is not None:
        command = "tool_uses"
        rows = tool_uses(args.transcript, args.tool, skip_sidechain=skip_sidechain,
                         skip_meta=skip_meta, malformed=malformed)
    else:
        command = "all_messages"
        role = args.role if args.role in ("user", "assistant") else None
        rows = all_messages(args.transcript, role=role, skip_sidechain=skip_sidechain,
                            skip_meta=skip_meta, malformed=malformed)
    if malformed:
        # Always to stderr, --json included, so stdout stays a clean parseable stream.
        print("transcript_tail: skipped %d unparseable line(s): %s"
              % (len(malformed), ", ".join(str(n) for n in malformed)), file=sys.stderr)
    if args.json:
        print(_dumps({"ok": bool(rows), "command": command, "skipped": malformed, "data": rows}))
    else:
        _print_rows(rows, command)
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
