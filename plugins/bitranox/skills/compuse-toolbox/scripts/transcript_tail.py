# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Extract the last user and assistant message TEXT from a Claude Code JSONL transcript.

Why this exists: a transcript record's content shape varies - user `content` is a plain string
OR a list of tool_result blocks; assistant `content` is a list of thinking/text/tool_use blocks.
An ad-hoc one-line parser flattens them wrong and silently returns empty (hit twice by hand).
This flattens each shape correctly, keeps only visible text (drops thinking/tool_use), and skips
sidechain (subagent) and meta records by default.

Run: `uv run scripts/transcript_tail.py <transcript.jsonl> [--role user|assistant|both]`
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import orjson


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


def tail_messages(path, *, skip_sidechain: bool = True, skip_meta: bool = True) -> dict:
    """Return {"user": <last user text>, "assistant": <last assistant text>} from a JSONL transcript.

    Only visible text is returned (assistant thinking/tool_use blocks are dropped). A role never
    seen stays "". A malformed line is skipped, not fatal.
    """
    last = {"user": "", "assistant": ""}
    with open(path, "rb") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = orjson.loads(raw)
            except orjson.JSONDecodeError:
                continue
            role = obj.get("type")
            if role not in ("user", "assistant"):
                continue
            if skip_sidechain and obj.get("isSidechain"):
                continue
            if skip_meta and obj.get("isMeta"):
                continue
            text = _flatten((obj.get("message") or {}).get("content"))
            if text.strip():
                last[role] = text
    return last


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Last user/assistant text from a Claude Code JSONL transcript.")
    ap.add_argument("transcript", type=Path, help="path to a *.jsonl transcript")
    ap.add_argument("--role", choices=["user", "assistant", "both"], default="both")
    ap.add_argument("--include-sidechain", action="store_true", help="do not skip subagent (sidechain) records")
    ap.add_argument("--include-meta", action="store_true", help="do not skip meta records")
    args = ap.parse_args(argv)
    out = tail_messages(args.transcript, skip_sidechain=not args.include_sidechain, skip_meta=not args.include_meta)
    if args.role in ("user", "both"):
        print("== last user ==\n" + out["user"])
    if args.role in ("assistant", "both"):
        print("== last assistant ==\n" + out["assistant"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
