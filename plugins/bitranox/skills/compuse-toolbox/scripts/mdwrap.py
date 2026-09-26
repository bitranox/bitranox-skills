# /// script
# requires-python = ">=3.10"
# ///
"""Rewrap exactly ONE paragraph of a markdown file, and prove nothing else moved.

Why: reflowing a paragraph in a long prose document (a TODO, a design note, a CLAUDE.md) is a
chore that keeps being hand-rolled as a throwaway `textwrap` slice, and the hand-rolled form has
two failure modes that both look fine in the output.

1. **The blast radius.** Written as a PREDICATE ("every line longer than N"), it matches unrelated
   content everywhere in the file. Measured 2026-08-31: reflowing one paragraph of a 4000-line
   TODO.md that way rewrapped 38 lines, 35 of them in unrelated sections, turning a 9-line change
   into a 153-line diff nobody could review. The lines are individually correct, so only the diff
   SIZE reveals it. See the memory fact
   `feedback-build-a-bulk-action-s-target-list-from-the-work-you-did-not-from-a-state-query`.
2. **The stray block marker.** `textwrap` knows nothing about markdown, so a wrap point falling
   just before a " - " clause puts a dash at the start of a line, which CommonMark then renders as
   a bullet - silently splitting the paragraph in two when the file is viewed. A " # " or " > "
   does the same as a heading or a blockquote, a " ``` " or " <tag>" as a code fence or an HTML
   block, and a " --- " or " === " left alone on a line underlines the text above it as a setext
   heading (or, as "---", "***" or "___", becomes a thematic break). Hit in the same session.

So this takes an ANCHOR (a substring that identifies the paragraph) rather than a rule, refuses
when the anchor is missing or matches more than one paragraph, and reports the changed line range
and the line delta so the caller can check the radius against the change they meant to make.

Paragraph = the maximal run of non-blank lines around the anchor, stopping at an ATX heading or a
thematic break (a heading directly above or below prose is its own block). It is REFUSED rather
than reflowed when rewrapping would corrupt it: a table row, a fence line, a paragraph that sits
inside a fenced code block, a blockquote (any line starting with '>'), a heading (ATX or setext),
a list (the first line is an item, two or more lines start one, one follows a lead-in line
ending in ':', or one is a '* ', '+ ', '1. ' or '1) ' item), or a Markdown hard line break (a line
ending in two spaces or a backslash). A SINGLE continuation line starting with '- ' is the damage
a previous bad wrap leaves, and is repaired; a wrap never ends a line in a backslash, which would
create a hard break. The paragraph's own leading indent is taken from its first line and preserved. A wrap
that would still leave a block marker alone on a line after the repair is refused, never written.

`--width` is the TOTAL line length including the paragraph's leading indent, matching how the
file is read and how a linter counts it - not the prose width alone.

It is a target, not a hard cap, in exactly one case: repairing a stray marker pulls the marker
token up onto the previous line, which can leave that line a few characters over (measured 99
against a requested 98). A paragraph that renders wrong is the worse failure and it is silent,
so the overflow wins - and every over-width line is listed in `notes` so it is never hidden.
If you need the width as an absolute guarantee, check `notes` and fix those lines by hand.

The file's own line endings (LF, CRLF) and a leading BOM are kept, on every platform. The write
is atomic (a temp file beside it, then a rename), so a failed write leaves it untouched - except
for a file with more than one hard link, or one in a directory that refuses the temp file or the
rename: that file is overwritten IN PLACE, which keeps its links and needs no directory write, and
the JSON `write` field (and a stderr note) says "in-place" rather than "atomic".

Dry-run by DEFAULT: it prints what would change and writes nothing until `--apply`. That is the
point of the tool, so the safe direction is the default one.

Run: `uv run scripts/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --width 98`
     `uv run scripts/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --width 98 --apply`
     `uv run scripts/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --json`

Exit codes: 0 = rewrapped (or would be), 1 = refused (anchor not found, ambiguous, or a paragraph
that must not be reflowed), 2 = error (unreadable or non-UTF-8 file, a failed write, bad
arguments, an internal error).
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Result", "rewrap", "main"]

# A paragraph holding any of these is structure, not prose: reflowing it corrupts it.
_TABLE = "|"
_FENCES = ("```", "~~~")
_LIST_MARKERS = ("- ", "* ", "+ ")
_EOL = re.compile(r"\r\n|\r|\n")
_BOM = "\ufeff"
# Matched on the lstripped line: this tool's documents indent prose, and treating an indented
# heading as a boundary is the safe error (a refusal or a smaller paragraph, never a merge).
_ATX = re.compile(r"#{1,6}(?:[ \t]|$)")
_THEMATIC = re.compile(r"(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$")
_SETEXT = re.compile(r"(?:=+|-+)[ \t]*$")
_FENCE_OPEN = re.compile(r"(`{3,}|~{3,})(.*)$")


@dataclass
class Result:
    ok: bool
    text: str = ""
    reason: str = ""
    start_line: int = 0          # 1-based, inclusive, in the ORIGINAL file
    end_line: int = 0            # 1-based, inclusive, in the ORIGINAL file
    line_delta: int = 0          # lines added (positive) or removed (negative)
    changed: bool = False
    notes: list[str] = field(default_factory=list)


def _split_lines(text: str) -> tuple[list[str], list[str]]:
    """`(bodies, endings)`: each line's text and its own terminator ("" for an unterminated end).

    Splitting on the terminator and keeping it is what lets a CRLF file come back CRLF: a plain
    `split("\\n")` left the '\\r' on each body and the rewrapped lines without one.
    """
    bodies, endings, pos = [], [], 0
    for m in _EOL.finditer(text):
        bodies.append(text[pos:m.start()])
        endings.append(m.group())
        pos = m.end()
    bodies.append(text[pos:])
    endings.append("")
    return bodies, endings


def _is_heading(line: str) -> bool:
    return bool(_ATX.match(line.lstrip()))


def _is_boundary(line: str) -> bool:
    """A line that ends a paragraph without being part of it: an ATX heading, a thematic break,
    or a setext underline (a run of '=' or '-' alone on its line)."""
    s = line.lstrip()
    return bool(_ATX.match(s) or _THEMATIC.match(s) or _SETEXT.match(s))


def _paragraph_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    """Maximal run of non-blank, non-boundary lines containing `idx`, as 0-based [lo, hi]."""
    if _is_boundary(lines[idx]):
        return idx, idx
    lo = idx
    while lo > 0 and lines[lo - 1].strip() and not _is_boundary(lines[lo - 1]):
        lo -= 1
    hi = idx
    while hi + 1 < len(lines) and lines[hi + 1].strip() and not _is_boundary(lines[hi + 1]):
        hi += 1
    return lo, hi


def _fenced_lines(lines: list[str]) -> set[int]:
    """0-based indexes of the lines strictly INSIDE a fenced code block, over the whole file.

    A paragraph between blank lines inside a fence has no fence line of its own, so a check over
    the paragraph alone let it be reflowed. A backtick opener's info string may hold no backtick;
    a closer is the same character, at least as long, and bare. An unclosed fence runs to the end.
    """
    inside, run = set(), ""
    for i, line in enumerate(lines):
        s = line.strip()
        if run:
            if len(s) >= len(run) and set(s) == {run[0]}:
                run = ""
            else:
                inside.add(i)
            continue
        m = _FENCE_OPEN.match(s)
        if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
            run = m.group(1)
    return inside


def _starts_a_list(line: str) -> bool:
    s = line.lstrip()
    if s[:2] in _LIST_MARKERS:
        return True
    # an ordered marker: digits then '. ' or ') '
    head = s.split(" ", 1)[0]
    return head[:-1].isdigit() and head[-1:] in (".", ")") if head else False


def _starts_a_block(line: str) -> bool:
    """A wrapped line CommonMark would NOT read as a continuation of the paragraph above it.

    A list item, heading or blockquote opens a new block; a code fence or an HTML tag can open
    one too; and a line holding only '=' or '-' underlines the text above it as a setext heading,
    as a run of '***' or '___' turns into a thematic break. Any '<' counts, not just a block-level
    tag: pulling an inline tag or an autolink up a line costs nothing.
    """
    s = line.lstrip()
    return (_starts_a_list(line) or bool(_ATX.match(s) or _SETEXT.match(s) or _THEMATIC.match(s))
            or s.startswith((">", "<") + _FENCES))


def _pull_up(out: list[str], i: int, indent: str) -> None:
    """Move line `i`'s first token onto the end of line `i - 1`, dropping line `i` if emptied."""
    head, _, rest = out[i].lstrip().partition(" ")
    out[i - 1] = out[i - 1] + " " + head
    out[i] = indent + rest.lstrip() if rest.strip() else ""
    if not out[i].strip():
        del out[i]


def _first_line_is_a_break(out: list[str]) -> bool:
    # The paragraph's first line sits under a blank line or a boundary, so '===' there is plain
    # text - but a thematic-break run ('---', '***', '_ _ _') is a horizontal rule anywhere.
    return len(out) > 1 and bool(_THEMATIC.match(out[0].lstrip()))


def _breaks_before(out: list[str], i: int) -> bool:
    """True when line `i` would not continue line `i - 1` as plain paragraph text: it opens a new
    block, or line `i - 1` ends in a backslash, which Markdown reads as a hard line break."""
    return _starts_a_block(out[i]) or out[i - 1].endswith("\\")


def _marker_line(out: list[str]) -> int:
    """Index of the first line CommonMark would not read as this paragraph's text, else -1."""
    if _THEMATIC.match(out[0].lstrip()):
        return 0
    return next((i for i in range(1, len(out)) if _breaks_before(out, i)), -1)


def _interrupts_as_a_list(line: str) -> bool:
    """A list item CommonMark lets interrupt a paragraph: a '*' or '+' bullet, or an ordered
    marker numbered 1 ('1.', '1)'). '2024. Then' under prose is plain continuation text."""
    s = line.lstrip()
    if s[:2] in ("* ", "+ "):
        return True
    head = s.split(" ", 1)[0]
    return (len(s) > len(head) and head[-1:] in (".", ")") and head[:-1].isdigit()
            and int(head[:-1]) == 1)


def _list_refusal(block: list[str]) -> str:
    # The FIRST line decides whether this block is a list item. A SINGLE continuation line
    # starting with '- ' is damage left by a previous bad wrap (the wrap point fell before a
    # ' - ' clause; CommonMark renders it as a bullet and splits the paragraph), and it is exactly
    # what this tool exists to repair - refusing it made the repair impossible. Any other item a
    # paragraph can be interrupted by ('* ', '+ ', '1. ', '1) ') is not that damage shape, so it
    # is a real one-item list. Two or more marker lines, or one under a lead-in ending in ':', is
    # a real list too, and flattening it into prose destroys it.
    if _starts_a_list(block[0]):
        return "paragraph is a list item - refusing to reflow it"
    items = [i for i in range(1, len(block)) if _starts_a_list(block[i])]
    if (len(items) >= 2 or (items and block[items[0] - 1].rstrip().endswith(":"))
            or any(_interrupts_as_a_list(block[i]) for i in items)):
        return "paragraph holds a list under a lead-in line - refusing to reflow it"
    return ""


def _refusal(lines: list[str], lo: int, hi: int, fenced: set[int]) -> str:
    block = lines[lo : hi + 1]
    if any(_TABLE in l for l in block):
        return "paragraph contains a table row - refusing to reflow it"
    if any(l.lstrip().startswith(_FENCES) for l in block):
        return "paragraph contains a code fence - refusing to reflow it"
    if any(i in fenced for i in range(lo, hi + 1)):
        return "paragraph is inside a fenced code block - refusing to reflow it"
    if any(l.lstrip().startswith(">") for l in block):
        # Joining the lines keeps only the first '> ' and turns every later one into literal
        # text inside the quote. A '>' line under prose is a quote too (it interrupts the
        # paragraph), so there is no safe reading of it to repair.
        return "paragraph is or holds a blockquote - refusing to reflow it"
    if _is_heading(block[0]) or _THEMATIC.match(block[0].lstrip()):
        return "anchor is on a heading or thematic break - refusing to reflow it"
    if hi + 1 < len(lines) and _SETEXT.match(lines[hi + 1].lstrip()):
        return "paragraph is a setext heading - refusing to reflow it"
    if any(l.endswith(("  ", "\\")) for l in block[:-1]):
        # A hard break is meaningful only inside the paragraph; trailing spaces on its last line
        # are ignored by CommonMark, so they are no reason to refuse.
        return "paragraph contains a hard line break - refusing to reflow it"
    return _list_refusal(block)


def _protect_dash_clauses(wrapped: list[str], indent: str) -> list[str]:
    """Never leave a line CommonMark would read as something other than this paragraph's text.

    A wrap point falling before a ' - ', ' # ', ' > ', ' ``` ' or ' <tag>' clause makes the
    continuation a new block, and one falling after it can leave '---' or '===' alone on a line,
    which underlines everything above it as a heading; one falling after a token ending in a
    backslash ('C:\\') turns that backslash into a hard line break - all silently change the
    document. Pull
    such a line's first token up onto the previous line; the result is a few chars over the width
    at worst, which is strictly better than a paragraph that renders wrong. The repaired line is
    checked AGAIN, because its new first token can be a marker too ('- -'). A first line that is a
    bare thematic break ('--- rest' wrapped at 3) takes the next line's first token instead.
    """
    out = list(wrapped)
    while _first_line_is_a_break(out):
        _pull_up(out, 1, indent)
    i = 1
    while i < len(out):
        if _breaks_before(out, i) and out[i - 1].strip():
            _pull_up(out, i, indent)
            continue
        i += 1
    return out


def _paragraph_ending(endings: list[str], lo: int, hi: int) -> str:
    """The terminator for lines inside the rewrapped paragraph: its own, else the file's, else LF."""
    return (next((e for e in endings[lo:hi + 1] if e), "")
            or next((e for e in endings if e), "") or "\n")


def rewrap(text: str, anchor: str, width: int = 98) -> Result:
    """Rewrap only the paragraph containing `anchor`. Pure; does no I/O."""
    if not anchor.strip():
        return Result(False, reason="empty anchor")
    lines, endings = _split_lines(text)
    hits = [i for i, l in enumerate(lines) if anchor in l]
    if not hits:
        return Result(False, reason=f"anchor not found: {anchor!r}")

    bounds = {_paragraph_bounds(lines, i) for i in hits}
    if len(bounds) > 1:
        return Result(False, reason=f"anchor is ambiguous - matches {len(bounds)} paragraphs")
    lo, hi = bounds.pop()

    if reason := _refusal(lines, lo, hi, _fenced_lines(lines)):
        return Result(False, reason=reason, start_line=lo + 1, end_line=hi + 1)

    indent = lines[lo][: len(lines[lo]) - len(lines[lo].lstrip())]
    para = " ".join(l.strip() for l in lines[lo : hi + 1])
    wrapped = textwrap.wrap(
        para, width=width, initial_indent=indent, subsequent_indent=indent,
        break_long_words=False, break_on_hyphens=False,
    ) or [indent + para.strip()]
    wrapped = _protect_dash_clauses(wrapped, indent)
    if (bad := _marker_line(wrapped)) >= 0:
        # The repair ran out of tokens to pull up (a paragraph made only of marker runs, or a
        # pull-up that joined two short runs into a thematic break). Writing it would change what
        # the document renders, so it is never written.
        return Result(False, start_line=lo + 1, end_line=hi + 1,
                      reason=f"rewrapping would leave {wrapped[bad].strip()!r} alone on a line, "
                             "which Markdown reads as a new block - refusing to reflow it")

    eol = _paragraph_ending(endings, lo, hi)
    new_endings = [eol] * (len(wrapped) - 1) + [endings[hi]]
    notes = [f"line {i}: {len(l)} chars"
             for i, l in enumerate(wrapped, lo + 1) if len(l) > width]
    out = zip(lines[:lo] + wrapped + lines[hi + 1 :],
              endings[:lo] + new_endings + endings[hi + 1 :])
    changed = wrapped != lines[lo : hi + 1] or new_endings != endings[lo : hi + 1]
    return Result(
        ok=True, text="".join(b + e for b, e in out), start_line=lo + 1, end_line=hi + 1,
        line_delta=len(wrapped) - (hi - lo + 1), changed=changed, notes=notes,
    )


def _positive_width(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: {raw!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def _read(path: Path) -> tuple[str, bool]:
    """`(text, had_bom)`, line endings untouched (`newline=""`), the BOM split off."""
    with open(path, encoding="utf-8", newline="") as handle:
        text = handle.read()
    return (text[1:], True) if text.startswith(_BOM) else (text, False)


def _write_in_place(real: Path, data: bytes) -> None:
    """Overwrite `real`'s own bytes: same inode, so every hard link sees the new text."""
    with open(real, "r+b") as handle:
        handle.write(data)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())


def _write_file(path: Path, text: str, *, make_temp=tempfile.mkstemp) -> str:
    """Replace `path` with `text` exactly - no newline translation. Returns how it was written.

    "atomic": written to a temp file beside the target and renamed over it, so a failure midway
    cannot leave half a file. "in-place": the target's own bytes are overwritten, which is not
    atomic but is the only write that keeps the file what it was - used when the target has more
    than one hard link (a rename would detach this name from the others) and when the directory
    refuses the temp file or the rename although the file itself is writable. A read-only target
    is refused either way rather than silently replaced. `make_temp` is the temp-file seam.
    """
    real = Path(os.path.realpath(path))
    if not os.access(real, os.W_OK):
        raise PermissionError(errno.EACCES, "file is not writable", str(real))
    data = text.encode("utf-8")
    if real.stat().st_nlink > 1:
        _write_in_place(real, data)
        return "in-place"
    try:
        fd, tmp = make_temp(dir=str(real.parent), prefix="." + real.name + ".", suffix=".tmp")
    except PermissionError:
        _write_in_place(real, data)
        return "in-place"
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        shutil.copymode(real, tmp)
        os.replace(tmp, real)
    except PermissionError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        _write_in_place(real, data)
        return "in-place"
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    return "atomic"


def _parse(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--anchor", required=True, help="substring identifying the ONE paragraph")
    ap.add_argument("--width", type=_positive_width, default=98)
    ap.add_argument("--apply", action="store_true", help="write the file (default: dry run)")
    ap.add_argument("--json", action="store_true")
    return ap.parse_args(argv)


def _payload(args, r: Result, write: str, error: str = "") -> dict:
    reason = error or r.reason
    return {
        "ok": r.ok and not error, "command": "mdwrap",
        "data": {
            "file": str(args.file), "reason": reason,
            "start_line": r.start_line, "end_line": r.end_line,
            "line_delta": r.line_delta, "changed": r.changed,
            "applied": bool(write), "write": write, "notes": r.notes,
        },
        "skipped": [] if r.ok and not error else [reason],
    }


def _run(args) -> int:
    try:
        src, bom = _read(args.file)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    r = rewrap(src, args.anchor, args.width)
    write, error = "", ""
    if r.ok and r.changed and args.apply:
        try:
            write = _write_file(args.file, (_BOM if bom else "") + r.text)
        except OSError as exc:
            error = f"write failed: {exc}"

    if args.json:
        print(json.dumps(_payload(args, r, write, error), indent=2))
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        return 0 if r.ok else 1
    if not r.ok:
        print(f"refused: {r.reason}", file=sys.stderr)
        return 1
    verb = "rewrote" if write else ("would rewrite" if r.changed else "unchanged")
    span = f"lines {r.start_line}-{r.end_line}"
    print(f"{verb} {span} ({r.end_line - r.start_line + 1} -> "
          f"{r.end_line - r.start_line + 1 + r.line_delta} lines, delta {r.line_delta:+d})")
    for n in r.notes:
        print(f"  note: {n}", file=sys.stderr)
    if write == "in-place":
        print("  note: written in place, not atomically (a hard-linked file, or a directory that "
              "refused the temp file)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Rewrap one paragraph. An unexpected crash exits 2, never Python's default 1, which is this
    tool's "refused" answer."""
    args = _parse(argv)
    try:
        return _run(args)
    except Exception as exc:                             # noqa: BLE001 - a crash must not read as a refusal
        print(f"mdwrap: internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
