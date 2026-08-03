# /// script
# requires-python = ">=3.10"
# ///
"""Read a Windows-written log as text, whatever encoding the writer used - including mixed.

Why this exists: on 2026-08-03 an install log was created by `Set-Content` (ASCII) and then
appended to by `Tee-Object` (UTF-16LE, no BOM). Read the obvious way it comes back as
"D O N E - O K", so a match on the completion marker found nothing. The watcher polling that
file reported "no marker" for a run that had plainly written one, and would have timed out on
a SUCCESSFUL install just as readily as on a failed one.

The trap is that no single decode is right for the whole file, and nothing announces it: there
is no BOM, the bytes are valid, and every layer reports success. So decode PER SEGMENT and say
out loud when a file turned out to be mixed - otherwise the next person fixes it in the reader
again instead of in the writer.

    winlog.py read D:/lcu/install.log --grep DONE-OK
    winlog.py read install.log --tail 20 --json

Exit: 0 ok (or --grep matched), 1 --grep matched nothing, 2 error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

__all__ = ["decode_windows_text", "describe_encoding", "read_windows_log", "main"]

# Ordered longest-first: the UTF-8 BOM must not be mistaken for anything shorter.
_BOMS: list[tuple[bytes, str]] = [
    (b"\xef\xbb\xbf", "utf-8"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
]

# A UTF-16 segment holding ASCII is ~50% NUL; real log text is 0%. A third is a wide margin
# either way, so a stray NUL in an otherwise narrow line cannot flip the verdict.
_NUL_SHARE_FOR_WIDE = 3


def _strip_bom(data: bytes) -> tuple[bytes, str | None]:
    for bom, enc in _BOMS:
        if data.startswith(bom):
            return data[len(bom):], enc
    return data, None


def _split_keeping_newlines(data: bytes) -> list[bytes]:
    """Split on the LF byte, keeping it. Works for UTF-16LE too, where LF is 0x0A 0x00 -
    the chunk simply ends mid-character and the next one starts with the orphan NUL."""
    out: list[bytes] = []
    start = 0
    while True:
        i = data.find(b"\n", start)
        if i < 0:
            if start < len(data):
                out.append(data[start:])
            return out
        out.append(data[start:i + 1])
        start = i + 1


def _is_wide(chunk: bytes) -> bool:
    return bool(chunk) and chunk.count(0) * _NUL_SHARE_FOR_WIDE >= len(chunk)


def _decode_wide(chunk: bytes, encoding: str) -> str:
    """Decode a UTF-16 chunk that split_keeping_newlines may have left unaligned.

    Splitting on the LF byte cuts the LF character in half, so a chunk can carry a leading
    orphan NUL from the previous line and a trailing LF whose NUL went to the next chunk.
    """
    body = chunk
    trailing_nl = body.endswith(b"\n")
    if trailing_nl:
        body = body[:-1]
    if body.startswith(b"\x00") and encoding == "utf-16-le":
        body = body[1:]
    if len(body) % 2:
        body = body[:-1]
    text = body.decode(encoding, errors="replace")
    return text + ("\n" if trailing_nl else "")


def _decode_narrow(chunk: bytes) -> str:
    try:
        return chunk.decode("utf-8")
    except UnicodeDecodeError:
        # cp1252, not latin-1: a German Windows tool writes umlauts there, and latin-1 would
        # decode every byte without complaint while silently producing the wrong characters.
        return chunk.decode("cp1252", errors="replace")


def _analyze(data: bytes) -> tuple[list[bytes], str | None, bool, bool]:
    """(chunks, bom_encoding, saw_wide, saw_narrow) - the shared front half of decode/describe."""
    body, bom = _strip_bom(data)
    if bom in ("utf-16-le", "utf-16-be"):
        return [body], bom, True, False
    chunks = _split_keeping_newlines(body)
    saw_wide = any(_is_wide(c) for c in chunks)
    saw_narrow = any(c.strip(b"\x00\r\n") and not _is_wide(c) for c in chunks)
    return chunks, bom, saw_wide, saw_narrow


def decode_windows_text(data: bytes) -> str:
    """Decode bytes written by any Windows tool, segment by segment. PURE."""
    chunks, bom, _, _ = _analyze(data)
    wide_encoding = bom if bom in ("utf-16-le", "utf-16-be") else "utf-16-le"
    parts = [
        _decode_wide(c, wide_encoding) if (bom in ("utf-16-le", "utf-16-be") or _is_wide(c))
        else _decode_narrow(c)
        for c in chunks
    ]
    return "".join(parts).replace("\r\n", "\n").replace("\r", "\n")


def describe_encoding(data: bytes) -> str:
    """Name what was actually found, so a MIXED file gets fixed at the writer."""
    if not data:
        return "empty"
    _, bom, saw_wide, saw_narrow = _analyze(data)
    if bom in ("utf-16-le", "utf-16-be"):
        return f"{bom} (BOM)"
    if saw_wide and saw_narrow:
        return ("MIXED: utf-8/ansi and utf-16-le segments in one file - the writer used more "
                "than one encoding (Set-Content then Tee-Object is the usual cause)")
    if saw_wide:
        return "utf-16-le (no BOM)"
    if bom == "utf-8":
        return "utf-8 (BOM)"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return "cp1252/ansi"
    return "utf-8"


def read_windows_log(path: str | Path) -> str:
    """Read and decode a file. Raises OSError if it cannot be read."""
    return decode_windows_text(Path(path).read_bytes())


def _select(text: str, pattern: str | None, tail: int | None) -> tuple[list[str], bool]:
    lines = text.splitlines()
    matched = True
    if pattern:
        rx = re.compile(pattern)
        lines = [ln for ln in lines if rx.search(ln)]
        matched = bool(lines)
    if tail:
        lines = lines[-tail:]
    return lines, matched


def _emit(as_json: bool, ok: bool, data: dict[str, object] | None, error: str | None) -> None:
    if as_json:
        print(json.dumps({"ok": ok, "command": "read", "data": data or {}, "error": error}))
    elif error:
        print(error, file=sys.stderr)
    elif data:
        for line in data["lines"]:  # type: ignore[index]
            print(line)


def cmd_read(args: argparse.Namespace) -> int:
    try:
        raw = Path(args.file).read_bytes()
    except OSError as exc:
        _emit(args.json, False, None, f"winlog: cannot read {args.file}: {exc}")
        if not args.json:
            pass
        return 2
    encoding = describe_encoding(raw)
    # Advisory on STDERR, never in the parsed stream: --json stdout must stay pure JSON.
    if encoding.startswith("MIXED"):
        print(f"winlog: {args.file}: {encoding}", file=sys.stderr)
    lines, matched = _select(decode_windows_text(raw), args.grep, args.tail)
    _emit(args.json, True, {"path": str(args.file), "encoding": encoding, "lines": lines}, None)
    return 0 if matched else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd_name", required=True)
    r = sub.add_parser("read", help="decode a Windows-written log and print it")
    r.add_argument("file")
    r.add_argument("--grep", help="print only lines matching this regex (exit 1 if none)")
    r.add_argument("--tail", type=int, help="print only the last N lines")
    r.add_argument("--json", action="store_true", help="emit a JSON envelope on stdout")
    r.set_defaults(func=cmd_read)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
