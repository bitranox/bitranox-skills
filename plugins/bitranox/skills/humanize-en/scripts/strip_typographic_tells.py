#!/usr/bin/env python3
"""Normalize typographic AI-writing tells to ASCII.

Deterministic first pass for the humanize skills: replace em/en dashes, curly
quotes, ellipsis, non-breaking and zero-width spaces, BOM, bidi controls, and
related non-ASCII punctuation with plain ASCII, so public-facing text carries no
typographic "AI tell". The judgment rewrites (promotional language, rule of
three, and the rest) are described in SKILL.md and stay with the model.

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

import sys


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
    # Dashes. Em dash becomes spaced hyphen; the rest become a plain hyphen.
    for cp in [0x2010, 0x2011, 0x2012, 0x2013, 0x2015, 0x2212]:
        table[cp] = "-"
    for cp in [0x2014, 0x2E3A, 0x2E3B]:
        table[cp] = " - "
    # Quotation marks and guillemets.
    for cp in [0x2018, 0x2019, 0x201A, 0x201B, 0x2039, 0x203A]:
        table[cp] = "'"
    for cp in [0x00AB, 0x00BB, 0x201C, 0x201D, 0x201E, 0x201F]:
        table[cp] = '"'
    # Dot leaders / ellipsis.
    table[0x2024] = "."
    table[0x2025] = ".."
    table[0x2026] = "..."
    return table


TABLE = _build_table()


def normalize(text):
    """Return text with every typographic tell replaced by its ASCII form."""
    return text.translate(TABLE)


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
        with open(path, encoding="utf-8") as fh:
            data = fh.read()
        out = normalize(data)
        if out == data:
            continue
        if check:
            sys.stderr.write("typographic tells found: %s\n" % path)
            rc = 1
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(out)
    return rc


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
