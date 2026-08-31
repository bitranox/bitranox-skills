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

The tell codepoints and the ignore-code-span scanner live in the shared `tell_chars` module
(so the `commit-tell-sweep` PreToolUse hook uses the exact same set). This source stays pure ASCII.

Pure standard library. Reads the PostToolUse event JSON on stdin. Exit 2 surfaces
the hit list to the model (the tool already ran); every other path (including any
error) exits 0, so a broken guard never wedges a turn.
"""
import json
import sys

import tell_chars


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
        with open(fp, "rb") as fh:
            raw = fh.read()
    except Exception:
        return 0
    # Read through the shared decoder, never errors="replace": that MINTS a U+FFFD per undecodable
    # byte and U+FFFD is itself a tell, so this hook reported a tell it had created - and because
    # it blocks the whole FILE until clean, a character the reader invents cannot be edited out and
    # the file could never become clean. The rewriter beside it (strip_typographic_tells) opens
    # strict and skips such a file, so this keeps the detector and the rewriter answering the same
    # question.
    text, bad_byte = tell_chars.decode_utf8(raw)

    hits = tell_chars.find_tell_lines(text)
    joins = tell_chars.find_continuation_lines(text)
    if not hits and not joins and bad_byte is None:
        return 0

    if bad_byte is not None:
        sys.stderr.write(
            "%s is not valid UTF-8 (first bad byte at byte %d). A tell saved in another encoding "
            "is invisible to this check - an em-dash from a Windows editor is byte 0x97. Read the "
            "file, replace the mis-encoded characters with ASCII, and rewrite the whole file as "
            "UTF-8 with the Write tool.\n" % (fp, bad_byte)
        )
    if hits:
        sys.stderr.write(
            "AI-writing tell(s) found in %s outside code spans "
            "(em/en-dash, curly quote, ellipsis, NBSP, ZWSP, BOM, etc.).\n"
            "Replace with ASCII (use - , . : () ...).\n" % fp
        )
        sys.stderr.write("\n".join(hits[:20]) + "\n")
    if joins:
        sys.stderr.write(
            "Extraction line-continuation artifact(s) in %s (U+2190 at a wrapped join).\n"
            "A token was split in two, so any command or path on these lines is broken: rejoin the\n"
            "halves and delete the marker. An arrow FOLLOWED by a space is prose and is not this.\n"
            % fp
        )
        sys.stderr.write("\n".join(joins[:20]) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
