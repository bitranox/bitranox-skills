# /// script
# requires-python = ">=3.14"
# ///
"""Follow a log and report only lines that START with a marker the producer owns.

A wait loop that greps a log for "the run finished" fires early in ways that all look like
success: the start banner shares the decoration (`==== `), the waiter's own output lands in the
log it reads, a transcript quotes the marker, an echoed `run:` line repeats it, and a
case-insensitive `FAIL` matches an unrelated `FailureReason`. Each needs only an UNANCHORED or
case-folded pattern. This jig takes none of those:

- a marker is a LITERAL, CASE-SENSITIVE PREFIX of the line (after an optional timestamp strip,
  `--strip-timestamp`), never a regex and never a substring; there is no ignore-case option, and
  `-i` is refused with the reason;
- a marker that is blank, starts with whitespace, starts with `^` (anchoring is already implied)
  or holds `.*` (it would be searched literally) is refused, and so is one made only of
  punctuation such as `====` or `---`, which is decoration every banner shares;
- `--calibrate FINISHED_LOG` counts each marker on a run you KNOW finished and refuses when a
  `--terminal` marker matches there zero times (it can never fire) or more than once (it already
  fires before the end).

`watch LOG` follows LOG the way `tail -F` does (waiting for it to appear, reopening it after a
truncation or a rotation), prints every line starting with a `--marker` or a `--terminal`, and
exits 0 on the first `--terminal` line. `--from start|end` is required: from `start` a log that
already finished answers at once, but an append-only log spanning several runs answers with an
OLD run's marker; from `end` a run that finished before you started never answers. Only you know
which of the two the log is.

Exit codes: 0 = a terminal marker was seen (`watch`) or every terminal marker matched exactly once
(`calibrate`), 1 = the deadline passed with no terminal marker (`watch`) or a terminal marker
matched zero or several times (`calibrate`), 2 = could not run (a refused marker, an unreadable
file, a usage error).

`--json` prints `{ok, command, data, skipped}` once at the end instead of streaming the lines.

Run:
  `uv run scripts/markerwatch.py calibrate last-good.log --terminal 'ALL GATES PASSED' --terminal 'GATE RED'`
  `uv run scripts/markerwatch.py watch gate.log --from start --terminal 'ALL GATES PASSED' --terminal 'GATE RED' --timeout 1800`
  `uv run scripts/markerwatch.py watch ci.log --from end --strip-timestamp --marker '##[group]' --terminal 'Job completed'`
"""

import argparse
import math
import os
import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded

__all__ = ["MarkerError", "Markers", "calibrate", "follow", "marker_problem", "match",
           "strip_timestamp"]

COMMAND = "markerwatch"
_POLL_S = 0.5
_KEEP_LINES = 200                  # matched lines kept for --json; the stream itself is unbounded

# An ISO-8601 date-time (GitHub Actions writes one with 7 fractional digits and a Z), or a bare
# clock time, optionally in square brackets, then whitespace.
_TIMESTAMP = re.compile(
    r"^\[?(?:\d{4}-\d{2}-\d{2}[T ])?\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?\]?\s+")
_DECORATION = re.compile(r"^[\W_]+$")


class MarkerError(Exception):
    """A marker this jig refuses, or a file it cannot read: exit 2 with one line."""


def marker_problem(marker: str) -> str | None:
    """Why `marker` cannot identify a producer's line, or None when it can. PURE."""
    if not marker.strip():
        return "a blank marker matches every line"
    if marker[0].isspace():
        return "a marker starting with whitespace is an indented quote of the real one"
    if marker.startswith("^"):
        return "anchoring is implied (a marker is a line PREFIX); drop the '^'"
    if ".*" in marker:
        return "a marker is a literal, not a regex; '.*' would be searched as the two characters"
    if _DECORATION.match(marker):
        return ("a marker made only of punctuation is decoration every banner shares; use the "
                "producer's own words after it")
    return None


def strip_timestamp(line: str) -> str:
    """`line` without one leading timestamp. PURE."""
    return _TIMESTAMP.sub("", line, count=1)


@dataclass(frozen=True)
class Markers:
    terminal: tuple[str, ...]
    progress: tuple[str, ...] = ()
    strip: bool = False

    def __post_init__(self) -> None:
        for marker in self.terminal + self.progress:
            problem = marker_problem(marker)
            if problem:
                raise MarkerError(f"refusing marker {marker!r}: {problem}")


def match(line: str, markers: Markers) -> tuple[str, str] | None:
    """("terminal"|"marker", the marker) for the first marker `line` starts with, else None.

    Terminal markers are tried first, so a terminal marker that extends a progress one wins.
    """
    text = strip_timestamp(line) if markers.strip else line
    for kind, group in (("terminal", markers.terminal), ("marker", markers.progress)):
        for marker in group:
            if text.startswith(marker):
                return kind, marker
    return None


def _read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError as exc:
        raise MarkerError(f"cannot read {path}: {exc.strerror or exc}") from exc


def calibrate(text: str, markers: Markers) -> dict[str, int]:
    """How many lines of a finished run each marker starts. PURE."""
    counts = {m: 0 for m in markers.terminal + markers.progress}
    for line in text.split("\n"):
        text_line = strip_timestamp(line) if markers.strip else line
        for marker in counts:
            if text_line.startswith(marker):
                counts[marker] += 1
    return counts


@dataclass
class _Cursor:
    pos: int = 0
    ident: tuple[int, int] | None = None
    pending: bytes = b""
    shown_tail: bytes = b""          # the stalled tail last yielded, so it is yielded once
    reopened: int = 0
    lines_read: int = 0
    notes: list[str] = field(default_factory=list)


def _stat(path: Path) -> os.stat_result | None:
    try:
        return path.stat()
    except FileNotFoundError:
        return None


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").rstrip("\r")


def _stalled_tail(cursor: _Cursor, *, stalled: bool) -> list[str]:
    """The unterminated last line, once it has stopped growing, unless already shown as it is.

    A producer may end its log with the terminal marker and no newline, and `calibrate` counts
    that line, so the follower must judge it too. It is judged only once a whole poll interval
    added nothing to it (or at the deadline): a line still being written is not judged mid-write.
    Judging a stalled half line is safe because a marker is a line PREFIX: a partial line that
    starts with a marker is a prefix of a complete line that starts with it too. If the producer
    later extends the line, the grown line is judged again, so a tail first read as the progress
    marker `GATE` still answers as the terminal `GATE RED` it becomes.
    """
    if not stalled or not cursor.pending or cursor.pending == cursor.shown_tail:
        return []
    cursor.shown_tail = cursor.pending
    return [_decode(cursor.pending)]


def _poll(path: Path, cursor: _Cursor, *, final: bool = False) -> list[str]:
    """The lines appended since the last poll, reopening after truncation or rotation; the
    unterminated last line is included once it stalls (see `_stalled_tail`)."""
    before = cursor.pos
    lines = _read_new(path, cursor)
    return lines + _stalled_tail(cursor, stalled=final or cursor.pos == before)


def _read_new(path: Path, cursor: _Cursor) -> list[str]:
    """The complete lines appended since the last poll; the unterminated rest stays pending."""
    st = _stat(path)
    if st is None:
        return []
    ident = (st.st_dev, st.st_ino)
    if cursor.ident is not None and (ident != cursor.ident or st.st_size < cursor.pos):
        # A new file under the old name, or the old one cut short: the next run's lines start
        # at offset 0, and a half line carried over from the old file belongs to neither.
        cursor.pos, cursor.pending, cursor.shown_tail = 0, b"", b""
        cursor.reopened += 1
    cursor.ident = ident
    if st.st_size <= cursor.pos:
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(cursor.pos)
            chunk = handle.read()
    except OSError as exc:
        raise MarkerError(f"cannot read {path}: {exc.strerror or exc}") from exc
    cursor.pos += len(chunk)
    data = cursor.pending + chunk
    *complete, cursor.pending = data.split(b"\n")
    if complete:
        cursor.shown_tail = b""
    cursor.lines_read += len(complete)
    return [_decode(raw) for raw in complete]


def follow(path: Path, *, start: str, deadline: float,
           clock: Callable[[], float] = time.monotonic,
           sleep: Callable[[float], None] = time.sleep,
           cursor: _Cursor | None = None) -> Iterator[str]:
    """Every line appended to `path` until `deadline` (on `clock`); an unterminated last line
    is yielded once it stops growing, and again if it grows later (see `_stalled_tail`).

    `start="end"` skips what the file already holds when the follow begins; a file that does not
    exist yet is waited for and then read from its beginning, since all of it is new.
    """
    cursor = cursor if cursor is not None else _Cursor()
    if start == "end":
        st = _stat(path)
        if st is not None:
            cursor.pos, cursor.ident = st.st_size, (st.st_dev, st.st_ino)
    while True:
        final = clock() >= deadline
        yield from _poll(path, cursor, final=final)
        if final:
            return
        sleep(_POLL_S)


def _parser() -> EnvelopeArgumentParser:
    p = EnvelopeArgumentParser(description=(__doc__ or COMMAND).splitlines()[0],
                               envelope_command=COMMAND, json_flags=("--json",))
    subs = p.add_subparsers(dest="command", required=True)
    for name in ("watch", "calibrate"):
        sub = subs.add_parser(name)
        sub.add_argument("log", help="the log file (watch: followed; calibrate: a FINISHED run)")
        sub.add_argument("--terminal", action="append", default=[], required=True,
                         metavar="PREFIX", help="a line prefix meaning the run is OVER "
                                                "(repeatable: a pass and a fail marker)")
        sub.add_argument("--marker", action="append", default=[], metavar="PREFIX",
                         help="a progress line prefix to print as it appears (repeatable)")
        sub.add_argument("--strip-timestamp", action="store_true",
                         help="drop one leading ISO-8601 or HH:MM:SS timestamp before matching")
        sub.add_argument("-i", "--ignore-case", action="store_true", help=argparse.SUPPRESS)
        sub.add_argument("--json", action="store_true", help="print one JSON envelope at the end")
        if name == "watch":
            sub.add_argument("--from", dest="start", choices=("start", "end"), required=True,
                             help="read the lines already there (start) or only new ones (end)")
            sub.add_argument("--timeout", type=_seconds, default=3600.0,
                             help="seconds to wait for a terminal line (default 3600)")
            sub.add_argument("--calibrate", metavar="FINISHED_LOG",
                             help="refuse to start unless each terminal marker matches exactly "
                                  "once in this finished run")
    return p


def _seconds(text: str) -> float:
    """An argparse type for --timeout: a finite number above zero.

    `float` alone took `nan`, under which `clock() >= deadline` is never true so the follow
    never ends, and `inf`, `0` or a negative value, none of which is a deadline.
    """
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a finite number of seconds above 0: {text!r}")
    return value


def _markers(args: argparse.Namespace) -> Markers:
    if args.ignore_case:
        raise MarkerError("-i is refused: a producer writes its marker in one case, and "
                          "case-folding is how 'FAIL' matched an unrelated 'FailureReason'")
    return Markers(tuple(args.terminal), tuple(args.marker), args.strip_timestamp)


def _calibration_failures(counts: dict[str, int], markers: Markers) -> list[str]:
    return [f"terminal marker {m!r} matched {counts[m]} line(s) in the finished run; it must "
            "match exactly once" for m in markers.terminal if counts[m] != 1]


def _do_calibrate(args: argparse.Namespace, markers: Markers) -> int:
    counts = calibrate(_read_text(Path(args.log)), markers)
    failures = _calibration_failures(counts, markers)
    code = EXIT_NO if failures else EXIT_YES
    if args.json:
        return emit(code, COMMAND, {"counts": counts, "failures": failures})
    for marker, count in counts.items():
        kind = "terminal" if marker in markers.terminal else "marker"
        print(f"{count:6d}  {kind:8s}  {marker}")
    for failure in failures:
        print(f"{COMMAND}: {failure}", file=sys.stderr)
    return code


def _do_watch(args: argparse.Namespace, markers: Markers, *,
              clock: Callable[[], float], sleep: Callable[[float], None]) -> int:
    if args.calibrate:
        failures = _calibration_failures(calibrate(_read_text(Path(args.calibrate)), markers),
                                         markers)
        if failures:
            raise MarkerError("calibration failed: " + "; ".join(failures))
    cursor = _Cursor()
    seen: list[str] = []
    terminal: str | None = None
    for line in follow(Path(args.log), start=args.start, deadline=clock() + args.timeout,
                       clock=clock, sleep=sleep, cursor=cursor):
        hit = match(line, markers)
        if hit is None:
            continue
        seen = (seen + [line])[-_KEEP_LINES:]
        if not args.json:
            print(line, flush=True)
        if hit[0] == "terminal":
            terminal = line
            break
    code = EXIT_YES if terminal is not None else EXIT_NO
    data: dict[str, Any] = {"terminal_line": terminal, "matched": seen,
                            "lines_read": cursor.lines_read, "reopened": cursor.reopened}
    if args.json:
        return emit(code, COMMAND, data)
    if terminal is None:
        print(f"{COMMAND}: no terminal marker within {args.timeout:g}s "
              f"({cursor.lines_read} line(s) read)", file=sys.stderr)
    return code


def execute(argv: list[str] | None = None, *, clock: Callable[[], float] = time.monotonic,
            sleep: Callable[[float], None] = time.sleep) -> int:
    """The whole run; the clock and sleep are seams so a test can append between polls."""
    args = _parser().parse_args(argv)
    try:
        markers = _markers(args)
        if args.command == "calibrate":
            return _do_calibrate(args, markers)
        return _do_watch(args, markers, clock=clock, sleep=sleep)
    except MarkerError as exc:
        if args.json:
            return emit(EXIT_ERROR, COMMAND, None, error=str(exc))
        print(f"{COMMAND}: {exc}", file=sys.stderr)
        return EXIT_ERROR


@guarded(COMMAND, json_flags=("--json",))
def main(argv: list[str] | None = None) -> int:
    """Run; an uncaught exception exits 2, never 1, which means 'no terminal marker'."""
    return execute(argv)


if __name__ == "__main__":
    sys.exit(main())
