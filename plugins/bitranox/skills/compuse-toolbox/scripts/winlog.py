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

Exit: 0 ok (or --grep matched), 1 --grep matched nothing, 2 error (unreadable file, a --grep
that is not a valid regex, a negative --tail).
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

_WIDE_LF = b"\n\x00"

# An ASCII-heavy UTF-16 line is ~50% NUL; narrow log text is 0%. A third settles it at once,
# and a stray NUL in an otherwise narrow line stays far below it.
_NUL_SHARE_FOR_WIDE = 3


def _strip_bom(data: bytes) -> tuple[bytes, str | None]:
    for bom, enc in _BOMS:
        if data.startswith(bom):
            return data[len(bom):], enc
    return data, None


def _aligned_wide_end(data: bytes, pos: int) -> int:
    """End of the UTF-16LE line starting at pos: just past its LF code unit, or EOF.

    Only a 0A 00 pair at an EVEN offset from the line start is the LF character. A bare 0x0A
    byte is also the low byte of U+xx0A (U+4E0A, U+040A, U+200A), so cutting there loses the
    rest of the line.
    """
    k = pos
    while True:
        i = data.find(_WIDE_LF, k)
        if i < 0:
            return len(data)
        if (i - pos) % 2 == 0:
            return i + 2
        k = i + 1


class _Segmenter:
    """Cut bytes into (chunk, is_wide) lines. Narrow text never holds a NUL byte; UTF-16LE
    holds one at least in its LF (0A 00), and in every ASCII character besides."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self._nul = -1  # cached index of the next NUL at or after the scan position

    def _next_nul(self, start: int) -> int:
        if self._nul < start:
            found = self.data.find(b"\x00", start)
            self._nul = len(self.data) if found < 0 else found
        return self._nul

    def _wide_without_nul_before_lf(self, pos: int, lf: int) -> bool:
        """A UTF-16LE line of non-Latin text (Cyrillic, CJK) has no NUL before its first 0x0A.

        It is wide when that 0x0A is a low byte (even offset), the next NUL is a high byte
        (odd offset), and every 0x0A in between is a low byte too. A narrow line followed by a
        UTF-16 segment always fails one of those parity tests, whatever the line lengths.
        """
        if (lf - pos) % 2:
            return False
        nul = self._next_nul(lf + 1)
        if nul >= len(self.data) or (nul - pos) % 2 == 0:
            return False
        k = lf + 1
        while True:
            i = self.data.find(b"\n", k, nul)
            if i < 0:
                return True
            if (i - pos) % 2:
                return False
            k = i + 1

    def _plausibly_wide(self, pos: int, narrow_end: int) -> bool:
        """Is the NUL-bearing line at pos UTF-16LE, or narrow text with a stray NUL?

        An ASCII-heavy UTF-16 line is about half NUL, so a third settles it at once. A mostly
        CJK line can hold far fewer, so then it must read as UTF-16 up to an aligned LF
        (0A 00 at an even offset) and every other 0x0A must be a low byte (even offset). A
        stray NUL in narrow text fails that: narrow text has no 0A 00 pair, and its LFs land
        on both parities.
        """
        candidate = self.data[pos:narrow_end]
        if candidate.count(0) * _NUL_SHARE_FOR_WIDE >= len(candidate):
            return True
        end = _aligned_wide_end(self.data, pos)
        if self.data[end - 2:end] != _WIDE_LF:
            return False
        body_end = end - 2
        k = pos
        while True:
            i = self.data.find(b"\n", k, body_end)
            if i < 0:
                break
            if (i - pos) % 2:
                return False
            k = i + 1
        return True  # the aligned terminator's own NUL is the high byte required

    def chunks(self) -> list[tuple[bytes, bool]]:
        out: list[tuple[bytes, bool]] = []
        data, pos = self.data, 0
        while pos < len(data):
            lf = data.find(b"\n", pos)
            narrow_end = len(data) if lf < 0 else lf + 1
            has_nul = self._next_nul(pos) < narrow_end
            if has_nul:
                wide = self._plausibly_wide(pos, narrow_end)
            else:
                wide = lf >= 0 and self._wide_without_nul_before_lf(pos, lf)
            if not wide:
                out.append((data[pos:narrow_end], False))
                pos = narrow_end
                continue
            end = _aligned_wide_end(data, pos)
            out.append((data[pos:end], True))
            pos = end
        return out


def _decode_wide(chunk: bytes, encoding: str) -> str:
    """Decode an aligned UTF-16 chunk; a truncated final byte is dropped, not guessed."""
    body = chunk[:-1] if len(chunk) % 2 else chunk
    return body.decode(encoding, errors="replace")


def _decode_narrow(chunk: bytes) -> str:
    try:
        return chunk.decode("utf-8")
    except UnicodeDecodeError:
        # cp1252, not latin-1: a German Windows tool writes umlauts there, and latin-1 would
        # decode every byte without complaint while silently producing the wrong characters.
        return chunk.decode("cp1252", errors="replace")


def _analyze(data: bytes) -> tuple[list[tuple[bytes, bool]], str | None, bool, bool]:
    """(chunks, bom_encoding, saw_wide, saw_narrow) - the shared front half of decode/describe."""
    body, bom = _strip_bom(data)
    if bom in ("utf-16-le", "utf-16-be"):
        return [(body, True)], bom, True, False
    chunks = _Segmenter(body).chunks()
    saw_wide = any(wide for _, wide in chunks)
    saw_narrow = any(c.strip(b"\r\n") and not wide for c, wide in chunks)
    return chunks, bom, saw_wide, saw_narrow


def decode_windows_text(data: bytes) -> str:
    """Decode bytes written by any Windows tool, segment by segment. PURE."""
    chunks, bom, _, _ = _analyze(data)
    wide_encoding = bom if bom in ("utf-16-le", "utf-16-be") else "utf-16-le"
    parts = [_decode_wide(c, wide_encoding) if wide else _decode_narrow(c) for c, wide in chunks]
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


def _log_lines(text: str) -> list[str]:
    """Split on LF only: splitlines() also cuts at a form feed, U+2028 and U+0085, which a log
    line may carry, and would then report one line as two. The text is LF-normalized already."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _select(text: str, rx: re.Pattern[str] | None, tail: int | None) -> tuple[list[str], bool]:
    lines = _log_lines(text)
    matched = True
    if rx is not None:
        lines = [ln for ln in lines if rx.search(ln)]
        matched = bool(lines)
    if tail is not None:
        lines = lines[-tail:] if tail > 0 else []
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
        rx = re.compile(args.grep) if args.grep else None
    except re.error as exc:
        # Exit 1 means "no line matched"; a pattern that cannot compile answered nothing.
        _emit(args.json, False, None, f"winlog: invalid --grep regex {args.grep!r}: {exc}")
        return 2
    try:
        raw = Path(args.file).read_bytes()
    except OSError as exc:
        _emit(args.json, False, None, f"winlog: cannot read {args.file}: {exc}")
        return 2
    encoding = describe_encoding(raw)
    # Advisory on STDERR, never in the parsed stream: --json stdout must stay pure JSON.
    if encoding.startswith("MIXED"):
        print(f"winlog: {args.file}: {encoding}", file=sys.stderr)
    lines, matched = _select(decode_windows_text(raw), rx, args.tail)
    _emit(args.json, True, {"path": str(args.file), "encoding": encoding, "lines": lines}, None)
    return 0 if matched else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd_name", required=True)
    r = sub.add_parser("read", help="decode a Windows-written log and print it")
    r.add_argument("file")
    r.add_argument("--grep", help="print only lines matching this regex (exit 1 if none)")
    r.add_argument("--tail", type=_non_negative_int, help="print only the last N lines (N >= 0)")
    r.add_argument("--json", action="store_true", help="emit a JSON envelope on stdout")
    r.set_defaults(func=cmd_read)
    return p


def _non_negative_int(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {n}")
    return n


def _tolerate_console_encoding() -> None:
    """A cp1252 console cannot encode U+FFFD or most non-Latin text; escape it, never crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="backslashreplace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _tolerate_console_encoding()
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
