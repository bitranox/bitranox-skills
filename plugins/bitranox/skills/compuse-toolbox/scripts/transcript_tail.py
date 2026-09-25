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

Most `user` records in a real session are tool OUTPUT (a tool_result block), not something a
person typed, so each `--all` row carries a `kind`: `prompt` (a user record with no tool_result),
`tool_result`, or `text` (an assistant turn). "What did the user ask" is
`--all --role user --prompts-only`.

Run:
  `uv run scripts/transcript_tail.py <transcript.jsonl> [--role user|assistant|both] [--json]`
  `uv run scripts/transcript_tail.py <transcript.jsonl> --all [--role user [--prompts-only]] [--json]`
  `uv run scripts/transcript_tail.py <transcript.jsonl> --tool Agent [--json]`

Exit codes: 0 = a result, 1 = the whole-transcript mode matched nothing, 2 = usage error or an
unreadable transcript. The default tail mode exits 0 on any readable file (a role never seen is
reported as empty, not as no-match).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:                                                     # fast path when available (uv run installs it)
    import orjson

    def _loads(raw):
        return orjson.loads(raw)

    def _dumps(obj):
        return orjson.dumps(obj).decode()
except ModuleNotFoundError:                              # stdlib fallback so the script runs anywhere
    def _loads(raw):
        return json.loads(raw)

    def _dumps(obj):
        return json.dumps(obj, ensure_ascii=False)

_BOM = b"\xef\xbb\xbf"


def _envelope(obj) -> str:
    """The --json envelope, ASCII-escaped so any console encoding can carry it unchanged."""
    return json.dumps(obj)


def _content(obj):
    """A record's message content, or None when `message` is not an object (a bare string)."""
    msg = obj.get("message")
    return msg.get("content") if isinstance(msg, dict) else None


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
            if lineno == 1 and raw.startswith(_BOM):
                raw = raw[len(_BOM):]                    # orjson refuses a BOM outright
            if not raw:
                continue
            try:
                obj = _loads(raw)
            except ValueError:                           # bad JSON AND invalid UTF-8, either backend
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


def tail_messages(path, *, skip_sidechain: bool = True, skip_meta: bool = True,
                  malformed=None) -> dict:
    """Return {"user": <last user text>, "assistant": <last assistant text>} from a JSONL transcript.

    Only visible text is returned (assistant thinking/tool_use blocks are dropped). A role never
    seen stays "". A malformed line is skipped, not fatal; when `malformed` is a list its line
    number is appended there, as in iter_records.
    """
    last = {"user": "", "assistant": ""}
    for _lineno, obj in iter_records(path, skip_sidechain=skip_sidechain, skip_meta=skip_meta,
                                     malformed=malformed):
        role = obj.get("type")
        if role not in ("user", "assistant"):
            continue
        text = _flatten(_content(obj))
        if text.strip():
            last[role] = text
    return last


def _row_kind(role: str, content) -> str:
    """`text` for an assistant turn; for a user turn, `tool_result` when it carries tool output."""
    if role != "user":
        return "text"
    if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return "tool_result"
    return "prompt"


def all_messages(path, *, role=None, prompts_only: bool = False, skip_sidechain: bool = True,
                 skip_meta: bool = True, malformed=None) -> list[dict]:
    """Every user/assistant turn that has visible text, in file order.

    Each row is {"line": <1-based JSONL line>, "role": "user"|"assistant", "kind":
    "prompt"|"tool_result"|"text", "text": <flattened>}. One row per RECORD, not per block: a
    record's text blocks all come from the same line, so splitting them would repeat the line
    number without telling the reader anything new. `role` narrows to one side; None (the
    default) keeps both. `prompts_only` drops the tool_result rows, which in a real session are
    most user records, so what remains of the user side is what a person typed.
    """
    rows = []
    for lineno, obj in iter_records(path, skip_sidechain=skip_sidechain, skip_meta=skip_meta,
                                    malformed=malformed):
        who = obj.get("type")
        if who not in ("user", "assistant"):
            continue
        if role is not None and who != role:
            continue
        content = _content(obj)
        kind = _row_kind(who, content)
        if prompts_only and kind == "tool_result":
            continue
        text = _flatten(content)
        if text.strip():
            rows.append({"line": lineno, "role": who, "kind": kind, "text": text})
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
        content = _content(obj)
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
            # Only a tool_result row is labelled, so a prompt's header stays as it always was.
            label = row["role"] + (" tool_result" if row["kind"] == "tool_result" else "")
            print("== line %d %s ==\n%s" % (row["line"], label, row["text"]))


def _tolerate_console_encoding() -> None:
    """A cp1252 console cannot encode most transcript text; escape it, never crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="backslashreplace")
            except (ValueError, OSError):
                pass


def _warn_malformed(malformed: list[int]) -> None:
    # Always to stderr, --json included, so stdout stays a clean parseable stream.
    if malformed:
        print("transcript_tail: skipped %d unparseable line(s): %s"
              % (len(malformed), ", ".join(str(n) for n in malformed)), file=sys.stderr)


def _run_tail(args, skip_sidechain: bool, skip_meta: bool) -> int:
    malformed: list[int] = []
    out = tail_messages(args.transcript, skip_sidechain=skip_sidechain, skip_meta=skip_meta,
                        malformed=malformed)
    _warn_malformed(malformed)
    sides = [r for r in ("user", "assistant") if args.role in (r, "both")]
    if args.json:
        data = {r: out[r] for r in sides}
        print(_envelope({"ok": True, "command": "tail_messages", "skipped": malformed, "data": data}))
        return 0
    for r in sides:
        print("== last %s ==\n%s" % (r, out[r]))
    return 0


def _run_rows(args, skip_sidechain: bool, skip_meta: bool) -> int:
    malformed: list[int] = []
    if args.tool is not None:
        command = "tool_uses"
        rows = tool_uses(args.transcript, args.tool, skip_sidechain=skip_sidechain,
                         skip_meta=skip_meta, malformed=malformed)
    else:
        command = "all_messages"
        role = args.role if args.role in ("user", "assistant") else None
        rows = all_messages(args.transcript, role=role, prompts_only=args.prompts_only,
                            skip_sidechain=skip_sidechain, skip_meta=skip_meta, malformed=malformed)
    _warn_malformed(malformed)
    if args.json:
        print(_envelope({"ok": bool(rows), "command": command, "skipped": malformed, "data": rows}))
    else:
        _print_rows(rows, command)
    return 0 if rows else 1


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Read a Claude Code JSONL transcript: the last texts, "
                                             "every text turn, or every call of one tool.")
    ap.add_argument("transcript", type=Path, help="path to a *.jsonl transcript")
    ap.add_argument("--role", choices=["user", "assistant", "both"], default="both")
    ap.add_argument("--include-sidechain", action="store_true", help="do not skip subagent (sidechain) records")
    ap.add_argument("--include-meta", action="store_true", help="do not skip meta records")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    ap.add_argument("--prompts-only", action="store_true",
                    help="with --all: drop user rows that are tool output (kind tool_result)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="EVERY text turn, with its JSONL line number")
    mode.add_argument("--tool", metavar="NAME", help="every tool_use of NAME, with its line number and input")
    return ap


def main(argv=None) -> int:
    _tolerate_console_encoding()
    ap = _build_parser()
    args = ap.parse_args(argv)
    if args.prompts_only and not args.all:
        ap.error("--prompts-only needs --all")
    skip_sidechain, skip_meta = not args.include_sidechain, not args.include_meta
    run = _run_tail if not args.all and args.tool is None else _run_rows
    try:
        return run(args, skip_sidechain, skip_meta)
    except OSError as exc:
        # Exit 1 means "matched nothing"; a transcript that could not be read answered nothing.
        message = "transcript_tail: cannot read %s: %s" % (args.transcript, exc.strerror or exc)
        print(message, file=sys.stderr)
        if args.json:
            print(_envelope({"ok": False, "command": "transcript_tail", "skipped": [], "data": [],
                             "error": message}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
