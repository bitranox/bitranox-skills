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

A log whose writer died mid-file (a crash, a power cut) often ends in a run of NUL bytes - zeroed
clusters, not text. That run is set aside rather than decoded, and the encoding line names how
many bytes it held, since a zeroed tail is itself evidence of how the writer ended.

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
from typing import NamedTuple

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


def _wide_line_aligned(data: bytes, pos: int) -> bool:
    """Read from pos as UTF-16LE, is the NEXT `0A 00` pair a whole code unit (or EOF, evenly)?

    Only the first pair is consulted, never an aligned one further on: searching past misaligned
    pairs costs the rest of the file per call, and a file of such lines went quadratic.
    """
    first = data.find(_WIDE_LF, pos)
    return ((len(data) if first < 0 else first) - pos) % 2 == 0


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
        UTF-16 segment fails one of those parity tests - except when the segment's first
        character is U+xx00 (00 xx): the narrow LF and that NUL then read as a wide LF, and
        only what follows can tell the two apart (`_narrow_lf_before_wide`).
        """
        if (lf - pos) % 2:
            return False
        nul = self._next_nul(lf + 1)
        if nul >= len(self.data) or (nul - pos) % 2 == 0:
            return False
        if nul == lf + 1 and self._narrow_lf_before_wide(pos, lf):
            return False
        k = lf + 1
        while True:
            i = self.data.find(b"\n", k, nul)
            if i < 0:
                return True
            if (i - pos) % 2:
                return False
            k = i + 1

    def _narrow_lf_before_wide(self, pos: int, lf: int) -> bool:
        """Is `0A 00` at lf a narrow LF followed by a wide segment opening with U+xx00?

        Both readings are valid bytes, so alignment decides: the narrow reading must leave a
        wide line from lf+1 that ends on an aligned LF (or at EOF on a whole code unit), and the
        wide reading must leave a line from lf+2 that does NOT - a real wide file stays aligned
        after its LF, a misread transition does not. The line itself must read as narrow text.
        """
        if not _reads_as_narrow_text(self.data[pos:lf]):
            return False
        return _wide_line_aligned(self.data, lf + 1) and not self._line_fits(lf + 2)

    def _line_fits(self, start: int) -> bool:
        """Does a line starting at `start` read cleanly: narrow, or wide on whole code units?

        Narrow means no NUL up to and including the byte after its LF - a NUL there is the same
        ambiguous `0A 00` again, which only alignment can settle.
        """
        if start >= len(self.data):
            return True
        lf = self.data.find(b"\n", start)
        after_lf = len(self.data) if lf < 0 else lf + 2
        # A bounded find, not _next_nul: that cache only moves forward, and the caller's next
        # line starts BEFORE `start`.
        if self.data.find(b"\x00", start, after_lf) < 0:
            return True
        return _wide_line_aligned(self.data, start)

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


def _reads_as_narrow_text(chunk: bytes) -> bool:
    """Is this clean narrow log text - UTF-8 or cp1252 with no control byte but tab, CR and LF?

    UTF-16LE of Cyrillic, Greek or Arabic carries a control byte in every code unit (U+04xx is
    xx 04), and ASCII in UTF-16 carries NULs, so neither passes. Only a short run of CJK whose
    bytes all happen to be printable can, which is why this settles nothing on its own.
    """
    for encoding in ("utf-8", "cp1252"):
        try:
            text = chunk.decode(encoding)
        except UnicodeDecodeError:
            continue
        return all(ch.isprintable() or ch in "\t\r\n" for ch in text)
    return False


def _segment(body: bytes) -> tuple[list[tuple[bytes, bool]], int]:
    """(chunks, padding) - cut the text into lines, with its trailing NUL run set aside.

    A crash or power cut leaves a log ending in zeroed clusters. That run is text in neither
    encoding, and fed to the segmenter it made the narrow lines before it read as UTF-16, which
    hid the completion marker of every such log. Only the run's FIRST NUL can be content: the
    high byte of a last UTF-16LE code unit (`\\n` is 0A 00). It is kept when it closes a wide
    chunk at an odd offset, unless that chunk also reads as clean narrow text in a file with no
    other wide chunk - there the zeroed tail after a narrow log is far the likelier story.
    """
    content_end = len(body.rstrip(b"\x00"))
    if content_end == len(body):
        return _Segmenter(body).chunks(), 0
    kept = _Segmenter(body[:content_end + 1]).chunks()
    last, wide = kept[-1]
    high_byte = wide and len(last) % 2 == 0
    if high_byte and (any(w for _, w in kept[:-1]) or not _reads_as_narrow_text(last[:-1])):
        return kept, len(body) - content_end - 1
    return (_Segmenter(body[:content_end]).chunks() if content_end else []), len(body) - content_end


def _strip_wide_padding(body: bytes) -> tuple[bytes, int]:
    """A whole-file UTF-16 body minus its trailing NUL run, keeping a NUL that ends a code unit."""
    content_end = len(body.rstrip(b"\x00"))
    keep = content_end + content_end % 2
    return body[:keep], len(body) - keep


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


class _Analysis(NamedTuple):
    """The shared front half of decode/describe."""
    chunks: list[tuple[bytes, bool]]
    bom: str | None
    saw_wide: bool
    saw_narrow: bool
    padding: int  # trailing NUL bytes set aside as not-text


def _analyze(data: bytes) -> _Analysis:
    body, bom = _strip_bom(data)
    if bom in ("utf-16-le", "utf-16-be"):
        text, padding = _strip_wide_padding(body)
        return _Analysis([(text, True)], bom, True, False, padding)
    chunks, padding = _segment(body)
    saw_wide = any(wide for _, wide in chunks)
    saw_narrow = any(c.strip(b"\r\n") and not wide for c, wide in chunks)
    return _Analysis(chunks, bom, saw_wide, saw_narrow, padding)


def decode_windows_text(data: bytes) -> str:
    """Decode bytes written by any Windows tool, segment by segment. PURE."""
    found = _analyze(data)
    wide_encoding = found.bom if found.bom in ("utf-16-le", "utf-16-be") else "utf-16-le"
    parts = [_decode_wide(c, wide_encoding) if wide else _decode_narrow(c)
             for c, wide in found.chunks]
    return "".join(parts).replace("\r\n", "\n").replace("\r", "\n")


def describe_encoding(data: bytes) -> str:
    """Name what was actually found, so a MIXED file gets fixed at the writer."""
    if not data:
        return "empty"
    found = _analyze(data)
    base = _name_encoding(data, found)
    if not found.padding:
        return base
    # Said, not silently dropped: a zeroed tail is the mark of a writer that died mid-file.
    return f"{base} + {found.padding} trailing NUL bytes (padding, not text)"


def _name_encoding(data: bytes, found: _Analysis) -> str:
    if found.bom in ("utf-16-le", "utf-16-be"):
        return f"{found.bom} (BOM)"
    if found.saw_wide and found.saw_narrow:
        return ("MIXED: utf-8/ansi and utf-16-le segments in one file - the writer used more "
                "than one encoding (Set-Content then Tee-Object is the usual cause)")
    if found.saw_wide:
        return "utf-16-le (no BOM)"
    if found.bom == "utf-8":
        return "utf-8 (BOM)"
    if not any(c for c, _ in found.chunks):
        return "empty"
    try:
        b"".join(c for c, _ in found.chunks).decode("utf-8")
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
