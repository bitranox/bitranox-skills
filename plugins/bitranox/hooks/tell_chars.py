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

GERMAN QUOTATION MARKS ARE NOT TELLS either (user decision 2026-09-18), so U+201E, U+201C,
U+201A, U+2018 and the guillemets U+00AB, U+00BB, U+2039, U+203A are all out of the set. German
prose quotes with U+201E ... U+201C or with U+00BB ... U+00AB; blocking those does not catch a
machine, it forces a German writer to spell correct typography wrongly, and there is no way to
tell the two apart from the codepoint alone because the rule fires on files and on commit
messages, which carry no language marker.

Two of the eight are shared with the English curly quotes and are the price of that: U+201C is
also the English OPENING double quote and U+2018 the English opening single, so an English curly
quote can now open unreported. The trade was weighed on what remains - U+2019, the curly
apostrophe, is the commonest English tell of all and is still in the set, as is U+201D, so a
curly PAIR still reports on its closing half. Only a curly opener closed with an ASCII quote gets
through, which is a shape neither a person nor a model tends to produce.
"""
import re

# Inclusive codepoint ranges to flag (the canonical tell set).
RANGES = [
    (0x0085, 0x0085), (0x00A0, 0x00A0), (0x00AD, 0x00AD),
    (0x061C, 0x061C), (0x180E, 0x180E), (0x2000, 0x200F),
    (0x2010, 0x2015), (0x2019, 0x2019), (0x201B, 0x201B), (0x201D, 0x201D),
    (0x201F, 0x201F), (0x2024, 0x2026), (0x2028, 0x202F),
    (0x205F, 0x205F), (0x2060, 0x2064),
    (0x2066, 0x2069), (0x2212, 0x2212), (0x26A0, 0x26A0), (0x2705, 0x2705),
    (0x2714, 0x2714), (0x2717, 0x2717), (0x274C, 0x274C), (0x2E3A, 0x2E3A),
    (0x2E3B, 0x2E3B), (0x3000, 0x3000), (0xFE0F, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFFC, 0xFFFC), (0xFFFD, 0xFFFD),
]


def _char_class():
    return "".join(chr(a) if a == b else "%c-%c" % (a, b) for a, b in RANGES)


_TELL = re.compile("[" + _char_class() + "]")

# An inline code span: a run of N backticks closed by a run of EXACTLY N, as CommonMark reads it.
# A single-backtick-only pattern scanned every ``double`` span as prose - the one form a writer
# uses precisely when the code itself contains a backtick.
_INLINE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")

# A fence line, after its indentation: a run of three or more backticks or tildes, then an info
# string. Indentation is not limited to three spaces here: a fence nested in a list item sits
# deeper, and reading it as prose would flag every deliberate example inside it.
_FENCE_RUN = re.compile(r"(`{3,}|~{3,})(.*)")

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


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def split_lines(text, keepends=False):
    """Split `text` on REAL line breaks only - never on U+2028, U+2029 or U+0085.

    `str.splitlines()` breaks on all three, and all three are themselves in `RANGES`. That single
    fact made the detector and the rewriter disagree about the same file: `find_tell_lines` split
    AT the separator, so the tell sat in no line and the file passed; `transform_outside_code`
    split with `keepends=True`, so it KEPT the separator, read the inline-code span as unterminated
    and rewrote through it. A file the sweep hook called clean could therefore still be rewritten,
    splitting a code span across two lines.

    Both halves share this one splitter so they can only ever answer the same question.
    It splits only on `\\r\\n`, `\\r` and `\\n` - the breaks an editor numbers lines by - so it keeps a
    form feed, a vertical tab and the U+001C..U+001E separators inside their line, where
    `str.splitlines()` would break. The empty-string and trailing-newline cases match
    `str.splitlines()`.
    """
    src = text or ""
    out, pos = [], 0
    for m in _LINE_BREAK.finditer(src):
        out.append(src[pos:m.end()] if keepends else src[pos:m.start()])
        pos = m.end()
    if pos < len(src):
        out.append(src[pos:])
    return out


def fence_opener(line):
    """(char, width) when `line` would OPEN a fenced block, else None.

    CommonMark's rule for an opener: a BACKTICK fence's info string may hold no backtick. Without
    that clause a prose line that merely begins with an inline span (```x```) reads as an opener,
    and the block it opens never closes, hiding every line after it."""
    m = _FENCE_RUN.fullmatch(line.lstrip().rstrip("\r\n"))
    if m is None or (m.group(1)[0] == "`" and "`" in m.group(2)):
        return None
    return m.group(1)[0], len(m.group(1))


def _closes(line, fence):
    """Whether `line` closes the block `fence` = (char, width) opened: the same character, a run
    at least as long, and nothing after it."""
    m = _FENCE_RUN.fullmatch(line.lstrip().rstrip("\r\n"))
    return (m is not None and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1]
            and not m.group(2).strip())


def lines_with_code_state(text, keepends=False):
    """Yield (line, is_code) for every line of `text`: is_code is True for a fence line and for
    every line inside a fenced block. An unclosed fence runs to the end.

    Closing follows CommonMark. A fence closes only on a bare run of its OWN character at least as
    long as its opener: toggling on any fence-looking line let a `~~~` inside a backtick block close
    it, and a four-backtick fence showing a three-backtick example close at the example - after
    which the example was treated as prose and the real prose after the block as code."""
    fence = None
    for line in split_lines(text, keepends=keepends):
        if fence is None:
            fence = fence_opener(line)
            yield line, fence is not None
            continue
        if _closes(line, fence):
            fence = None
        yield line, True


def transform_outside_code(text, fn, edges=False):
    """Rebuild `text` with `fn` applied to every stretch that is NOT code, leaving inline-code
    spans and fenced blocks byte-identical.

    With `edges=True`, `fn` is called as fn(stretch, starts_line, ends_line), so a rewriter can
    tell a LINE edge from the edge of an inline-code span: both reach it as a stretch with nothing
    beyond it, and only the first is the end of the text on that line.

    This is the write-side twin of `find_tell_lines`, and it exists so the detector and any
    rewriter agree about what counts as code. Without a shared primitive they drift: the sweep hook
    skipped code while a rewriter did not, so a file could pass the hook and still have the tell
    inside a deliberate example rewritten - which is how a curly-quote example in this repo was
    once flattened into two identical halves."""
    call = fn if edges else (lambda stretch, _starts, _ends: fn(stretch))
    out = []
    for line, is_code in lines_with_code_state(text, keepends=True):
        if is_code:
            out.append(line)
            continue
        parts = split_inline(line)
        last = len(parts) - 1
        for i in range(0, len(parts), 2):          # even indices are prose; spans stay verbatim
            parts[i] = call(parts[i], i == 0, i == last)
        out.append("".join(parts))
    return "".join(out)


def split_inline(line):
    """[prose, span, prose, span, ..., prose] for one line: the inline-code spans at the odd
    indices, verbatim, and the stretches around them (possibly empty) at the even ones."""
    pos, parts = 0, []
    for m in _INLINE.finditer(line):
        parts.append(line[pos:m.start()])
        parts.append(m.group(0))
        pos = m.end()
    parts.append(line[pos:])
    return parts


def decode_utf8(raw, truncated=False):
    """(text, bad_byte): `raw` decoded, and the offset of the first byte that is not valid UTF-8,
    or None when all of it decoded.

    Shared by both tell hooks so they read a file the same way. Never errors="replace": U+FFFD is
    in RANGES on purpose, because it is mojibake, so "replace" MINTS the exact character the
    detector hunts for once per undecodable byte, and every file that is not UTF-8 gets reported
    as carrying a tell it does not contain.

    Dropping those bytes silently is not the end state either: an em-dash saved by a Windows
    editor is byte 0x97, which is not valid UTF-8, so a silent drop reports such a file clean and
    misses exactly the character these hooks exist to catch. The offset comes back so the caller
    can report the ENCODING as its own finding.

    Pass truncated=True when `raw` came from a capped read. A cap can slice a multi-byte character
    in half, so a failure in the last three bytes of a truncated read is the READER's doing and is
    dropped rather than reported - reporting it would be the very fault this function avoids.
    """
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        if truncated and exc.start >= len(raw) - 3:
            return raw[:exc.start].decode("utf-8"), None
        return raw.decode("utf-8", errors="ignore"), exc.start


def _scannable(text):
    """Yield (lineno, line, scrubbed) for every line the tell scan is allowed to look at.

    `scrubbed` is the line with inline-code spans removed - the form to MATCH against; `line` is
    the original, for quoting back. Fenced blocks are skipped entirely. Both public scanners are
    built on this so they can never disagree about what counts as code."""
    for n, (line, is_code) in enumerate(lines_with_code_state(text), 1):
        if not is_code:
            yield n, line, _INLINE.sub("", line)


def find_tell_lines(text):
    """Return ['<lineno>: <line>', ...] for lines carrying a tell OUTSIDE inline-code spans and
    fenced blocks. Empty list means clean."""
    return ["%d: %s" % (n, line) for n, line, scrubbed in _scannable(text) if _TELL.search(scrubbed)]


def find_tell_codepoints(text):
    """Return ['<lineno>: U+XXXX U+YYYY', ...] - the same hits as `find_tell_lines`, naming the
    offending codepoints INSTEAD of quoting the line.

    For text a caller read out of a FILE rather than text it was handed. A guard that reports
    before its command has been approved must not quote file content back, because the path is
    still only a string somebody named; a line number and a codepoint locate the tell just as
    well and carry nothing the reader did not already have. Codepoints are deduplicated and
    sorted so the same line always reports the same way."""
    hits = []
    for n, _line, scrubbed in _scannable(text):
        found = _TELL.findall(scrubbed)
        if found:
            hits.append("%d: %s" % (n, " ".join("U+%04X" % cp for cp in sorted({ord(c) for c in found}))))
    return hits


def find_continuation_lines(text):
    """Return ['<lineno>: <line>', ...] for lines carrying an extraction line-continuation
    artifact, INCLUDING inside fenced code blocks. Empty list means clean.

    Deliberately not code-aware. `find_tell_lines` skips code so a file documenting the tells does
    not self-flag; that exemption is the blind spot this covers, because a wrapped token inside a
    fenced block is a command a reader copies and cannot run."""
    return ["%d: %s" % (n, line)
            for n, line in enumerate(split_lines(text), 1)
            if _CONTINUATION.search(line)]
