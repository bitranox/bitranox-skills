#!/usr/bin/env python3
"""Canonical typographic / invisible AI-writing tell codepoints, plus a line scanner.

Shared by the `tell-sweep` PostToolUse hook (prose FILES) and the `commit-tell-sweep`
PreToolUse hook (git `-m`/`-F` messages), so the tell set lives in exactly ONE place.
`RANGES` is the canonical set the memory rule points at. Pure ASCII source (codepoints as
hex ranges). Tells inside inline-code spans (`...`) and fenced blocks (``` / ~~~) are IGNORED,
so text that DOCUMENTS the tells does not self-flag.

Allowed-on-purpose symbols are NOT in the set: arrow U+2192, multiplication U+00D7,
>= U+2265, <= U+2264, != U+2260, check U+2713, bullet U+2022. The heavy verdict emoji
(U+2705/U+274C/U+2714/U+2717/U+26A0 + the U+FE0F selector) ARE tells - house style is
ASCII OK/NO/WARN markers (user decision 2026-07-05).
"""
import re

# Inclusive codepoint ranges to flag (the canonical tell set).
RANGES = [
    (0x0085, 0x0085), (0x00A0, 0x00A0), (0x00AB, 0x00AB), (0x00AD, 0x00AD),
    (0x00BB, 0x00BB), (0x061C, 0x061C), (0x180E, 0x180E), (0x2000, 0x200F),
    (0x2010, 0x2015), (0x2018, 0x201F), (0x2024, 0x2026), (0x2028, 0x202F),
    (0x2039, 0x2039), (0x203A, 0x203A), (0x205F, 0x205F), (0x2060, 0x2064),
    (0x2066, 0x2069), (0x2212, 0x2212), (0x26A0, 0x26A0), (0x2705, 0x2705),
    (0x2714, 0x2714), (0x2717, 0x2717), (0x274C, 0x274C), (0x2E3A, 0x2E3A),
    (0x2E3B, 0x2E3B), (0x3000, 0x3000), (0xFE0F, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFFC, 0xFFFC), (0xFFFD, 0xFFFD),
]


def _char_class():
    return "".join(chr(a) if a == b else "%c-%c" % (a, b) for a, b in RANGES)


_TELL = re.compile("[" + _char_class() + "]")
_INLINE = re.compile(r"`[^`]*`")


def find_tell_lines(text):
    """Return ['<lineno>: <line>', ...] for lines carrying a tell OUTSIDE inline-code spans and
    fenced blocks. Empty list means clean."""
    hits = []
    in_fence = False
    for n, line in enumerate((text or "").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _TELL.search(_INLINE.sub("", line)):
            hits.append("%d: %s" % (n, line))
    return hits
