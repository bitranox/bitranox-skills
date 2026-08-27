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

# A PDF or HTML extraction marks a WRAPPED line with U+2190 at the join. Two shapes are artifacts,
# one is prose:
#   " <-token"   the wrapped remainder of a token - the shape that splits a command or a path in
#                two, so a reader who copies it gets something that fails
#   "<-" alone   a lone marker line; it carries nothing and renders as literal garbage
#   "x <- y"     an arrow FOLLOWED by whitespace is ordinary prose and is never flagged
# U+2192 (->) is an allowed-on-purpose symbol per this module's header and is not matched here.
#
# This deliberately scans INSIDE fenced blocks, which is the opposite of the tell scan above. That
# difference is the whole point: the tell scan skips code so a file documenting the tells does not
# self-flag, and a split command lives in exactly that blind spot. 104 broken commands and paths
# shipped through it.
_CONTINUATION = re.compile("[ \t]\u2190(?=\\S)|^[ \t]*\u2190-?[ \t]*$")


def transform_outside_code(text, fn):
    """Rebuild `text` with `fn` applied to every stretch that is NOT code, leaving inline-code
    spans and fenced blocks byte-identical.

    This is the write-side twin of `find_tell_lines`, and it exists so the detector and any
    rewriter agree about what counts as code. Without a shared primitive they drift: the sweep hook
    skipped code while a rewriter did not, so a file could pass the hook and still have the tell
    inside a deliberate example rewritten - which is how a curly-quote example in this repo was
    once flattened into two identical halves."""
    out = []
    in_fence = False
    for line in (text or "").splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        pos, parts = 0, []
        for m in _INLINE.finditer(line):
            parts.append(fn(line[pos:m.start()]))
            parts.append(m.group(0))            # the span, verbatim
            pos = m.end()
        parts.append(fn(line[pos:]))
        out.append("".join(parts))
    return "".join(out)


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


def find_continuation_lines(text):
    """Return ['<lineno>: <line>', ...] for lines carrying an extraction line-continuation
    artifact, INCLUDING inside fenced code blocks. Empty list means clean.

    Deliberately not code-aware. `find_tell_lines` skips code so a file documenting the tells does
    not self-flag; that exemption is the blind spot this covers, because a wrapped token inside a
    fenced block is a command a reader copies and cannot run."""
    return ["%d: %s" % (n, line)
            for n, line in enumerate((text or "").splitlines(), 1)
            if _CONTINUATION.search(line)]
