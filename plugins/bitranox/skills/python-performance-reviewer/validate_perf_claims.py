#!/usr/bin/env python3
"""Extract performance claims from a diff so they can be checked against real profiling.

A "claim" is any phrase asserting a speed/size change: "40% faster", "3x speedup",
"reduced latency by 30%", "improves throughput", "better cache hit rate", etc.
find_performance_claims returns the matched claim phrases (de-duplicated, in order).

Usage:
  python validate_perf_claims.py [diff_file]
  (defaults to LLM-CONTEXT/review-anal/scope/changes.diff when no path is given)
"""
import os
import re
import sys

DEFAULT_DIFF = "LLM-CONTEXT/review-anal/scope/changes.diff"

# Each pattern matches a whole claim phrase; group(0) is the human-readable claim.
_CLAIM_PATTERNS = [
    # number-first: "40% faster", "30 % lower latency", "2x speedup"
    r"\d+(?:\.\d+)?\s*%\s*(?:faster|slower|lower|higher|less|more|improvement|improv\w*|speed\w*|reduc\w*|gain\w*|throughput|latency|memory)",
    r"\d+(?:\.\d+)?\s*x\s*(?:faster|slower|speed\w*|improv\w*|reduc\w*)?",
    # keyword-first: "faster by 40%", "reduced latency by 30%", "improved by 2x"
    r"(?:faster|slower|improv\w*|reduc\w*|optimiz\w*|speed\w*|gain\w*|cut|lower\w*|boost\w*)[^.\n]*?\b\d+(?:\.\d+)?\s*[%x]",
    # qualitative cache / perf claims with no number
    r"cache\s+hit\s+rate",
    r"(?:significantly|much|far)\s+(?:faster|slower|quicker)",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _CLAIM_PATTERNS]


def find_performance_claims(diff_file):
    """Return a de-duplicated list of performance-claim phrases found in *diff_file*."""
    with open(diff_file, encoding="utf-8", errors="replace") as f:
        content = f.read()

    seen, claims = set(), []
    for rx in _COMPILED:
        for m in rx.finditer(content):
            phrase = " ".join(m.group(0).split())  # normalise whitespace
            key = phrase.lower()
            if key not in seen:
                seen.add(key)
                claims.append(phrase)
    return claims


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else DEFAULT_DIFF
    if not os.path.exists(path):
        print(f"No diff file found at: {path}")
        return 1
    claims = find_performance_claims(path)
    print(f"Found {len(claims)} performance claim(s) in {path}")
    for c in claims:
        print(f"  - {c}")
    print("\nValidate each against a REAL profiled run (find_hotspots / compare_performance);"
          " never accept a claim on synthetic benchmarks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
