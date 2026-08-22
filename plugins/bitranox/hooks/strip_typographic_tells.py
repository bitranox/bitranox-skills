#!/usr/bin/env python3
"""Normalize typographic AI-writing tells to ASCII.

Deterministic first pass for the humanize skills: replace em/en dashes, curly
quotes, ellipsis, non-breaking and zero-width spaces, BOM, bidi controls, heavy
verdict emoji (check/cross/warning -> OK/NO/WARN), and related non-ASCII
punctuation with plain ASCII, so public-facing text carries no
typographic "AI tell". The judgment rewrites (promotional language, rule of
three, and the rest) are described in SKILL.md and stay with the model.

An em dash becomes a spaced hyphen carrying one space per side, reusing the space
already beside it, so a spaced em dash needs no hand tidy afterwards. Wider
spacing beside the dash is column padding and stays as it is, as does whitespace
at either end of the line. The other dashes become a bare hyphen and keep the
text's spacing.

This is the exact inverse of the tell-sweep detector: running it makes a file
pass that check. Symbols that are intentionally allowed (arrow, multiply sign,
>=, <=, !=, check mark, bullet) are left untouched.

Usage:
  strip_typographic_tells.py FILE [FILE ...]   rewrite each file in place
  strip_typographic_tells.py --check FILE ...  exit 1 if any tell remains (no write)
  strip_typographic_tells.py -                 read stdin, write normalized stdout

The replacement table is built from code points with chr()/ranges so this script
is itself pure ASCII and passes the same check.
"""

import re
import sys
from pathlib import Path

# The sweep hook and this script MUST agree about what counts as code, or a file that passes the
# sweep still gets its deliberate examples rewritten. One implementation, in the shared module -
# which is a sibling here, so this works whether the file is imported or run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tell_chars  # noqa: E402


def _build_table():
    table = {}
    # Spaces of various widths -> one ASCII space.
    for cp in [0x00A0, 0x202F, 0x205F, 0x3000] + list(range(0x2000, 0x200B)):
        table[cp] = " "
    # Zero-width, bidi, and other invisibles -> removed.
    removable = (
        [0x00AD, 0x061C, 0x180E, 0xFEFF, 0xFFFC, 0xFFFD]
        + list(range(0x200B, 0x2010))   # ZWSP, ZWNJ, ZWJ, LRM, RLM
        + list(range(0x202A, 0x202F))   # bidi embeddings/overrides
        + list(range(0x2060, 0x2065))   # word joiner, invisible operators
        + list(range(0x2066, 0x206A))   # bidi isolates
    )
    for cp in removable:
        table[cp] = ""
    # Line/paragraph separators -> newline.
    for cp in [0x0085, 0x2028, 0x2029]:
        table[cp] = "\n"
    # Dashes -> a plain hyphen, keeping whatever spacing the text already had. The em-dash family
    # (U+2014, U+2E3A, U+2E3B) is deliberately absent: it reads as a spaced hyphen, which a fixed
    # table entry cannot produce without doubling existing spaces, so `_EM_DASH_RUN` owns it.
    for cp in [0x2010, 0x2011, 0x2012, 0x2013, 0x2015, 0x2212]:
        table[cp] = "-"
    # Quotation marks and guillemets.
    for cp in [0x2018, 0x2019, 0x201A, 0x201B, 0x2039, 0x203A]:
        table[cp] = "'"
    for cp in [0x00AB, 0x00BB, 0x201C, 0x201D, 0x201E, 0x201F]:
        table[cp] = '"'
    # Dot leaders / ellipsis.
    table[0x2024] = "."
    table[0x2025] = ".."
    table[0x2026] = "..."
    # Heavy verdict emoji -> ASCII markers (house style); drop the variation selector.
    table[0x2705] = "OK"
    table[0x2714] = "OK"
    table[0x2717] = "NO"
    table[0x274C] = "NO"
    table[0x26A0] = "WARN"
    table[0xFE0F] = ""
    return table


TABLE = _build_table()

# An em dash becomes a SPACED hyphen, so the replacement has to know what is already next to it.
# A translate entry cannot: mapping U+2014 to " - " kept the original spaces and turned
# "a <em dash> b" into "a  -  b", which every caller then tidied by hand. This pattern reuses the
# space already beside the dash instead, so a spaced em dash comes out as " - ", and it is why the
# em-dash family is not in TABLE.
#
# Exactly ONE space per side is taken ([ \t]? , not [ \t]*): a wider run is column padding, and
# collapsing it corrupts what it aligned. Measured over the repo's own markdown - injecting a
# spaced em dash at every spaced hyphen outside code, then running this script - the one-space
# form round-trips byte-identical, while consuming the whole run rewrote a padded table cell and
# an aligned trailing comment.
#
# The whitespace class is [ \t] and NEVER \s: \s matches a newline, and consuming one joins two
# lines and silently destroys the structure of the file. Whitespace at a line edge is left alone
# in both directions - a run reached from the line start is indentation (eating it re-nests a list
# item) and a trailing run can be a markdown hard line break (two spaces), so a run against a
# newline is neither consumed nor created.
_EM_DASHES = "".join(chr(cp) for cp in (0x2014, 0x2E3A, 0x2E3B))
_ON_THE_LINE = "[^ \t\n]"          # neither horizontal whitespace nor a line break
_EM_DASH_RUN = re.compile(
    "(?:(?<=%s)[ \t]?)?[%s](?:[ \t]?(?=%s))?" % (_ON_THE_LINE, _EM_DASHES, _ON_THE_LINE)
)
_SPACE_OR_BREAK = (" ", "\t", "\n")


def _spaced_hyphen(match):
    """Return the hyphen with a space only on the sides that face text on the same line.

    A side with NO character at all is a segment edge, which is not necessarily a line edge: the
    caller splits each line at its inline-code spans, so "`x`<em dash>y" arrives here as
    "<em dash>y". A space is the safe answer there (dropping it would weld the hyphen onto the
    code span) and it is also what the old table entry produced."""
    text = match.string
    before = text[match.start() - 1] if match.start() else ""
    after = text[match.end()] if match.end() < len(text) else ""
    left = "" if before in _SPACE_OR_BREAK else " "
    right = "" if after in _SPACE_OR_BREAK else " "
    return left + "-" + right


def _normalize_prose(text):
    """Translate the tells in one non-code stretch, then fix the em-dash spacing.

    The order matters: the table turns non-breaking spaces into plain ones and drops the
    zero-width characters, so an em dash padded with either reaches the dash pass surrounded by
    ordinary spaces and collapses like any other."""
    return _EM_DASH_RUN.sub(_spaced_hyphen, text.translate(TABLE))


def normalize(text):
    """Return text with every typographic tell OUTSIDE code replaced by its ASCII form.

    Inline-code spans and fenced blocks are left byte-identical: a tell inside them is usually a
    deliberate example of the very character being documented, and rewriting it destroys the
    example. This is the same code definition the tell-sweep hook uses."""
    return tell_chars.transform_outside_code(text, _normalize_prose)


def _main(argv):
    args = argv[1:]
    check = False
    if args and args[0] == "--check":
        check, args = True, args[1:]

    if not args or args == ["-"]:
        data = sys.stdin.read()
        out = normalize(data)
        if check:
            return 1 if out != data else 0
        sys.stdout.write(out)
        return 0

    rc = 0
    for path in args:
        # newline="" on BOTH sides so line endings round-trip untouched. The defaults translate
        # on read and rewrite as os.linesep, so this tool silently converted every file it
        # rewrote to the platform ending - CRLF on Windows, in a repo whose gate requires LF.
        with open(path, encoding="utf-8", newline="") as fh:
            data = fh.read()
        out = normalize(data)
        if out == data:
            continue
        if check:
            sys.stderr.write("typographic tells found: %s\n" % path)
            rc = 1
        else:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
    return rc


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
