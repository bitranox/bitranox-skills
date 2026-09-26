#!/usr/bin/env python3
"""Extract performance claims from a diff so they can be checked against real profiling.

A "claim" is any phrase asserting a speed/size change: "40% faster", "3x speedup",
"reduced latency by 30%", "improves throughput", "twice as fast", "better cache hit rate",
etc. Only ADDED lines are scanned (a removed or context line is not a claim the change
makes). find_performance_claims returns each claim phrase once, in diff order, with where
it was first seen: ``path:line`` in the new file when the diff has hunk headers, else
``diff line N``.

Usage:
  python validate_perf_claims.py [diff_file]
  (defaults to LLM-CONTEXT/review-anal/scope/changes.diff when no path is given)

Exit codes: 0 the diff was scanned (whether or not claims were found), 2 the diff could
not be read or the arguments were invalid.
"""
import argparse
import re
import sys

DEFAULT_DIFF = "LLM-CONTEXT/review-anal/scope/changes.diff"

_NUM = r"(?<![\w.])\d+(?:\.\d+)?"
# A multiplier "x": never one followed by another number, which makes it a dimension
# ("10 x 20", "1920 x 1080"; "1920x1080" already fails the word boundary).
_TIMES = r"x\b(?!\s*\d)"
# Each pattern matches a whole claim phrase; group(0) is the human-readable claim.
_CLAIM_PATTERNS = [
    # number-first: "40% faster", "30 % lower latency"
    _NUM + r"\s*%\s*(?:faster|slower|lower|higher|less|more|improvement|improv\w*|speed\w*|reduc\w*|gain\w*|throughput|latency|memory)",
    # "2x speedup", "3x" - but never a hex literal (0xFF) or a dimension (1920x1080, 10 x 20)
    r"(?<![\w.])(?!0x)\d+(?:\.\d+)?\s*" + _TIMES
    + r"(?:\s*(?:faster|slower|speed\w*|improv\w*|reduc\w*))?",
    # keyword-first: "faster by 40%", "reduced latency by 30%", "improved by 2x"; the word
    # boundaries keep "execute" and "cut_width" from reading as "cut"
    r"\b(?:faster|slower|improv\w*|reduc\w*|optimiz\w*|speed\w*|gain\w*|cut|lower\w*|boost\w*)\b"
    r"[^.\n]*?" + _NUM + r"\s*(?:%|" + _TIMES + ")",
    # numberless claims
    r"\bimprov\w*\s+(?:the\s+)?(?:throughput|latency|performance|speed)\b",
    r"\b(?:twice|thrice|\d+(?:\.\d+)?\s+times)\s+(?:as\s+)?(?:fast|faster|quicker|slower)\b",
    r"cache\s+hit\s+rate",
    r"\b(?:significantly|much|far)\s+(?:faster|slower|quicker)\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _CLAIM_PATTERNS]
_HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _new_file_path(header):
    path = header[4:].split("\t")[0].strip()
    if path == "/dev/null":
        return None
    return path.removeprefix("b/")


def _added_lines(content):
    """Yield (location, text) for every added line of a unified diff.

    Splits on "\\n" only: splitlines() would also break at U+2028, form feed and friends,
    and the tail after such a break no longer starts with "+" so it would be skipped.
    """
    path, new_line, old_left, new_left = None, 0, 0, 0
    for number, raw in enumerate(content.split("\n"), start=1):
        line = raw.removesuffix("\r")
        if old_left > 0 or new_left > 0:
            tag = line[:1]
            if tag == "+":
                yield f"{path}:{new_line}", line[1:]
                new_line, new_left = new_line + 1, new_left - 1
            elif tag == "-":
                old_left -= 1
            elif tag != "\\":  # context line (a "\ No newline" marker counts for neither side)
                new_line, old_left, new_left = new_line + 1, old_left - 1, new_left - 1
            continue
        hunk = _HUNK.match(line)
        if hunk and path:
            old_left = int(hunk.group(1) or 1)
            new_line, new_left = int(hunk.group(2)), int(hunk.group(3) or 1)
        elif line.startswith("+++ "):
            path = _new_file_path(line)
        elif line.startswith("+"):
            yield f"diff line {number}", line[1:]


def find_performance_claims(diff_file):
    """Return [{"claim": phrase, "where": location}] for the claims added in *diff_file*."""
    with open(diff_file, encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    seen, claims = set(), []
    for where, text in _added_lines(content):
        for rx in _COMPILED:
            for m in rx.finditer(text):
                phrase = " ".join(m.group(0).split())  # normalise whitespace
                key = phrase.lower()
                if key not in seen:
                    seen.add(key)
                    claims.append({"claim": phrase, "where": where})
    return claims


def _utf8_output():
    # A cp1252 console cannot encode most non-ASCII paths or claim text.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Extract performance claims from a diff.")
    parser.add_argument("diff_file", nargs="?", default=DEFAULT_DIFF,
                        help=f"unified diff to scan (default: {DEFAULT_DIFF})")
    args = parser.parse_args(argv)
    path = args.diff_file
    try:
        claims = find_performance_claims(path)
    except FileNotFoundError:
        print(f"No diff file found at: {path}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"ERROR reading {path}: {e}", file=sys.stderr)
        return 2
    print(f"Found {len(claims)} performance claim(s) in {path}")
    for c in claims:
        print(f"  - {c['claim']}  ({c['where']})")
    print("\nValidate each against a REAL profiled run (find_hotspots / compare_performance);"
          " never accept a claim on synthetic benchmarks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
