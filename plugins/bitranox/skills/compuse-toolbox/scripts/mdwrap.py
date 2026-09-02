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
2. **The stray list marker.** `textwrap` knows nothing about markdown, so a wrap point falling just
   before a " - " clause puts a dash at the start of a line, which CommonMark then renders as a
   bullet - silently splitting the paragraph in two when the file is viewed. Hit in the same
   session.

So this takes an ANCHOR (a substring that identifies the paragraph) rather than a rule, refuses
when the anchor is missing or matches more than one paragraph, and reports the changed line range
and the line delta so the caller can check the radius against the change they meant to make.

Paragraph = the maximal run of non-blank lines around the anchor. A paragraph containing a table
row, a fence, or a list marker is REFUSED rather than reflowed, because rewrapping those corrupts
them. The paragraph's own leading indent is taken from its first line and preserved.

`--width` is the TOTAL line length including the paragraph's leading indent, matching how the
file is read and how a linter counts it - not the prose width alone.

It is a target, not a hard cap, in exactly one case: repairing a stray bullet pulls the ` - `
token up onto the previous line, which can leave that line a few characters over (measured 99
against a requested 98). A paragraph that renders wrong is the worse failure and it is silent,
so the overflow wins - and every over-width line is listed in `notes` so it is never hidden.
If you need the width as an absolute guarantee, check `notes` and fix those lines by hand.

Dry-run by DEFAULT: it prints what would change and writes nothing until `--apply`. That is the
point of the tool, so the safe direction is the default one.

Run: `uv run tools/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --width 98`
     `uv run tools/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --width 98 --apply`
     `uv run tools/mdwrap.py --file TODO.md --anchor "NEXT STEP:" --json`

Exit codes: 0 = rewrapped (or would be), 1 = refused (anchor not found, ambiguous, or a paragraph
that must not be reflowed), 2 = error (unreadable file, bad arguments).
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Result", "rewrap", "main"]

# A paragraph holding any of these is structure, not prose: reflowing it corrupts it.
_TABLE = "|"
_FENCES = ("```", "~~~")
_LIST_MARKERS = ("- ", "* ", "+ ")


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


def _paragraph_bounds(lines: list[str], idx: int) -> tuple[int, int]:
    """Maximal run of non-blank lines containing `idx`, as 0-based [lo, hi] inclusive."""
    lo = idx
    while lo > 0 and lines[lo - 1].strip():
        lo -= 1
    hi = idx
    while hi + 1 < len(lines) and lines[hi + 1].strip():
        hi += 1
    return lo, hi


def _starts_a_list(line: str) -> bool:
    s = line.lstrip()
    if s[:2] in _LIST_MARKERS:
        return True
    # an ordered marker: digits then '. ' or ') '
    head = s.split(" ", 1)[0]
    return head[:-1].isdigit() and head[-1:] in (".", ")") if head else False


def _refusal(lines: list[str], lo: int, hi: int) -> str:
    block = lines[lo : hi + 1]
    if any(_TABLE in l for l in block):
        return "paragraph contains a table row - refusing to reflow it"
    if any(l.lstrip().startswith(_FENCES) for l in block):
        return "paragraph contains a code fence - refusing to reflow it"
    # Only the FIRST line decides whether this block is a list. A CONTINUATION line starting
    # with '- ' is damage left by a previous bad wrap (CommonMark renders it as a bullet and
    # splits the paragraph), and it is exactly what this tool exists to repair - refusing it
    # here made the repair impossible and made a 'no stray bullet remains' check pass on the
    # empty output of the refusal.
    if _starts_a_list(block[0]):
        return "paragraph is a list item - refusing to reflow it"
    return ""


def _protect_dash_clauses(wrapped: list[str], indent: str) -> list[str]:
    """Never leave a line starting with a list marker.

    A wrap point falling before a ' - ' clause makes CommonMark render the continuation as a
    bullet, silently splitting the paragraph. Pull such a line's first token up onto the previous
    line; the result is one char over the width at worst, which is strictly better than a
    paragraph that renders wrong.
    """
    out = list(wrapped)
    i = 1
    while i < len(out):
        if _starts_a_list(out[i]) and out[i - 1].strip():
            head, _, rest = out[i].lstrip().partition(" ")
            out[i - 1] = out[i - 1] + " " + head
            out[i] = indent + rest if rest else ""
            if not out[i].strip():
                del out[i]
                continue
        i += 1
    return out


def rewrap(text: str, anchor: str, width: int = 98) -> Result:
    """Rewrap only the paragraph containing `anchor`. Pure; does no I/O."""
    if not anchor.strip():
        return Result(False, reason="empty anchor")
    lines = text.split("\n")
    hits = [i for i, l in enumerate(lines) if anchor in l]
    if not hits:
        return Result(False, reason=f"anchor not found: {anchor!r}")

    bounds = {_paragraph_bounds(lines, i) for i in hits}
    if len(bounds) > 1:
        return Result(False, reason=f"anchor is ambiguous - matches {len(bounds)} paragraphs")
    lo, hi = bounds.pop()

    if reason := _refusal(lines, lo, hi):
        return Result(False, reason=reason, start_line=lo + 1, end_line=hi + 1)

    indent = lines[lo][: len(lines[lo]) - len(lines[lo].lstrip())]
    para = " ".join(l.strip() for l in lines[lo : hi + 1])
    wrapped = textwrap.wrap(
        para, width=width, initial_indent=indent, subsequent_indent=indent,
        break_long_words=False, break_on_hyphens=False,
    ) or [indent + para.strip()]
    wrapped = _protect_dash_clauses(wrapped, indent)

    old = lines[lo : hi + 1]
    notes = [f"line {i}: {len(l)} chars"
             for i, l in enumerate(wrapped, lo + 1) if len(l) > width]
    out = lines[:lo] + wrapped + lines[hi + 1 :]
    return Result(
        ok=True, text="\n".join(out), start_line=lo + 1, end_line=hi + 1,
        line_delta=len(wrapped) - len(old), changed=wrapped != old, notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, type=Path)
    ap.add_argument("--anchor", required=True, help="substring identifying the ONE paragraph")
    ap.add_argument("--width", type=int, default=98)
    ap.add_argument("--apply", action="store_true", help="write the file (default: dry run)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    try:
        src = args.file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    r = rewrap(src, args.anchor, args.width)
    payload = {
        "ok": r.ok, "command": "mdwrap",
        "data": {
            "file": str(args.file), "reason": r.reason,
            "start_line": r.start_line, "end_line": r.end_line,
            "line_delta": r.line_delta, "changed": r.changed,
            "applied": bool(r.ok and r.changed and args.apply), "notes": r.notes,
        },
        "skipped": [] if r.ok else [r.reason],
    }
    if r.ok and r.changed and args.apply:
        args.file.write_text(r.text, encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2))
    elif not r.ok:
        print(f"refused: {r.reason}", file=sys.stderr)
    else:
        verb = "rewrote" if payload["data"]["applied"] else ("would rewrite" if r.changed else "unchanged")
        span = f"lines {r.start_line}-{r.end_line}"
        print(f"{verb} {span} ({r.end_line - r.start_line + 1} -> "
              f"{r.end_line - r.start_line + 1 + r.line_delta} lines, delta {r.line_delta:+d})")
        for n in r.notes:
            print(f"  note: {n}", file=sys.stderr)
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
