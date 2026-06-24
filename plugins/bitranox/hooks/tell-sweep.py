#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) guard against AI-writing typographic / invisible
tells in prose files.

Flags em/en-dashes, curly quotes, ellipsis, guillemets, and invisible blanks
(NBSP, ZWSP, BOM, bidi controls, ...) that were just written to a prose file
(*.md, *.markdown, *.txt, or a CLAUDE.md). These are the strongest signs of
machine-generated text; the rule is to use plain ASCII instead.

Tells inside inline-code spans (`...`) and fenced code blocks (``` / ~~~) are
IGNORED, so a file that DOCUMENTS the tells (a CLAUDE.md "no LLM tells" section, a
humanizer skill, a note about the characters) does not false-positive on its own
examples. A genuine reference to the character itself belongs in backticks anyway.

Code files are skipped (legit unicode in test data / identifiers); commit messages
and code comments rely on the manual sweep plus the humanizer skill.

The tell codepoints are listed as hex ranges so this source stays pure ASCII.
Allowed-on-purpose symbols are NOT in the set: arrow U+2192, multiplication U+00D7,
>= U+2265, <= U+2264, != U+2260, check U+2713, bullet U+2022.

Pure standard library. Reads the PostToolUse event JSON on stdin. Exit 2 surfaces
the hit list to the model (the tool already ran); every other path (including any
error) exits 0, so a broken guard never wedges a turn.
"""
import json
import re
import sys

# Inclusive codepoint ranges to flag (matches the umbrella CLAUDE.md sweep).
RANGES = [
    (0x0085, 0x0085), (0x00A0, 0x00A0), (0x00AB, 0x00AB), (0x00AD, 0x00AD),
    (0x00BB, 0x00BB), (0x061C, 0x061C), (0x180E, 0x180E), (0x2000, 0x200F),
    (0x2010, 0x2015), (0x2018, 0x201F), (0x2024, 0x2026), (0x2028, 0x202F),
    (0x2039, 0x2039), (0x203A, 0x203A), (0x205F, 0x205F), (0x2060, 0x2064),
    (0x2066, 0x2069), (0x2212, 0x2212), (0x2E3A, 0x2E3A), (0x2E3B, 0x2E3B),
    (0x3000, 0x3000), (0xFEFF, 0xFEFF), (0xFFFC, 0xFFFC), (0xFFFD, 0xFFFD),
]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    fp = (event.get("tool_input") or {}).get("file_path") or ""
    low = fp.lower()
    if not (low.endswith((".md", ".markdown", ".txt")) or low.endswith("claude.md")):
        return 0
    try:
        with open(fp, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except Exception:
        return 0

    cls = "".join(chr(a) if a == b else "%c-%c" % (a, b) for a, b in RANGES)
    tell = re.compile("[" + cls + "]")
    inline = re.compile(r"`[^`]*`")

    hits = []
    in_fence = False
    for n, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if tell.search(inline.sub("", line)):
            hits.append("%d: %s" % (n, line))
    if not hits:
        return 0

    sys.stderr.write(
        "AI-writing tell(s) found in %s outside code spans "
        "(em/en-dash, curly quote, ellipsis, NBSP, ZWSP, BOM, etc.).\n"
        "Replace with ASCII (use - , . : () ...).\n" % fp
    )
    sys.stderr.write("\n".join(hits[:20]) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
