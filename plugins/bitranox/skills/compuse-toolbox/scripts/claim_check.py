#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Check whether a claim is already true of some files - and refuse to answer "no" blindly.

Why: the dangerous result from a content check is a NEGATIVE, because "not found" and "I never
really looked" are the same output. Measured failures that motivated this tool: a `grep -ric`
whose `file:count` output was never parsed (every row read as absent), a similarity threshold set
above the entire distribution (no pair could ever match), and a marker-count proxy standing in for
reading the file.

So every query carries a CONTROL: a pattern that MUST match. If the control misses, the verdict is
BROKEN, not ABSENT - the check itself is wrong and the answer is withheld. That turns a silent
false all-clear into a loud failure.

Verdicts and exit codes (format-independent):
  PRESENT  0   the pattern matched; matching path:line:text are reported
  ABSENT   1   the pattern did not match AND the control did, so the files were genuinely read
  BROKEN   2   the control missed, no file was read, or the regex is invalid - answer withheld

Run: uv run scripts/claim_check.py FILE... --pattern REGEX --control REGEX [--json] [--case-sensitive]
     uv run scripts/claim_check.py skills/*/SKILL.md --pattern 'LC_ALL=C' --control 'git'
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PRESENT, ABSENT, BROKEN = "PRESENT", "ABSENT", "BROKEN"
_EXIT = {PRESENT: 0, ABSENT: 1, BROKEN: 2}


def check(paths, pattern: str, control: str, *, ignore_case: bool = True) -> dict:
    """Return a verdict dict for `pattern` over `paths`, gated on `control` matching.

    PURE over the given paths (no globbing, no cwd) so it is unit-testable. `paths` may hold str
    or Path. A file that cannot be read is NOT silently skipped: it lowers files_read, which is
    what makes an all-zero result report BROKEN instead of ABSENT.
    """
    flags = re.IGNORECASE if ignore_case else 0
    try:
        pat = re.compile(pattern, flags)
        ctl = re.compile(control, flags)
    except re.error as e:
        return {"verdict": BROKEN, "reason": "invalid regex: %s" % e, "hits": [],
                "control_hits": 0, "files_read": 0, "unreadable": []}

    hits, control_hits, files_read, unreadable = [], 0, 0, []
    for raw in paths:
        p = Path(raw)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            unreadable.append("%s (%s)" % (p, e.strerror or e))
            continue
        files_read += 1
        for n, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                hits.append({"path": str(p), "line": n, "text": line.strip()})
            if ctl.search(line):
                control_hits += 1

    if files_read == 0:
        reason = "no file could be read (%s)" % (", ".join(unreadable) or "empty path list")
        return {"verdict": BROKEN, "reason": reason, "hits": hits,
                "control_hits": control_hits, "files_read": 0, "unreadable": unreadable}
    if control_hits == 0:
        # The control is the whole point: it proves the pattern had a fair chance to match.
        return {"verdict": BROKEN,
                "reason": "control %r never matched in %d file(s), so an ABSENT verdict would be "
                          "meaningless - fix the control or the paths" % (control, files_read),
                "hits": hits, "control_hits": 0, "files_read": files_read, "unreadable": unreadable}

    verdict = PRESENT if hits else ABSENT
    return {"verdict": verdict, "reason": "", "hits": hits, "control_hits": control_hits,
            "files_read": files_read, "unreadable": unreadable}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Check whether a pattern is already present in files, gated on a control match.")
    ap.add_argument("paths", nargs="*", help="files to scan (shell-expanded globs are fine)")
    ap.add_argument("--pattern", required=True, help="the claim to test, as a regex")
    ap.add_argument("--control", required=True,
                    help="a regex that MUST match; if it does not, the verdict is BROKEN not ABSENT")
    ap.add_argument("--case-sensitive", action="store_true", help="default is case-insensitive")
    ap.add_argument("--json", action="store_true", help="emit a JSON envelope on stdout")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    r = check(args.paths, args.pattern, args.control, ignore_case=not args.case_sensitive)
    v = r["verdict"]

    if args.json:
        # Diagnostics go to stderr so stdout stays parseable even on a BROKEN/ABSENT result.
        if r["reason"]:
            print("claim_check: %s" % r["reason"], file=sys.stderr)
        json.dump({"ok": v == PRESENT, "command": "claim_check", "data": r,
                   "skipped": r["unreadable"]}, sys.stdout, indent=1)
        print()
        return _EXIT[v]

    for h in r["hits"]:
        print("%s:%d: %s" % (h["path"], h["line"], h["text"]))
    if v == BROKEN:
        print("BROKEN: %s" % r["reason"], file=sys.stderr)
    elif v == ABSENT:
        print("ABSENT (control matched %d time(s) across %d file(s), so the files were read)"
              % (r["control_hits"], r["files_read"]), file=sys.stderr)
    else:
        print("PRESENT: %d hit(s) across %d file(s)" % (len(r["hits"]), r["files_read"]),
              file=sys.stderr)
    for u in r["unreadable"]:
        print("skipped: %s" % u, file=sys.stderr)
    return _EXIT[v]


if __name__ == "__main__":
    raise SystemExit(main())
