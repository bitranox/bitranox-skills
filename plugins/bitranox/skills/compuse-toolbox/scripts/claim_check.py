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

A partial read gets the same treatment. The control is counted across ALL files (a glob over
skills/*/SKILL.md gated on 'git' is normal use), so a control hit in the files that WERE read says
nothing about one that was not: a missing path, a typo, or a file no regex can match (binary, or
UTF-16 without a BOM, both of which read as NUL-interleaved text) blocks ABSENT and reports BROKEN.
A hit found in the readable files is still PRESENT. UTF-16 and UTF-8 with a BOM are decoded, and
lines are split on newlines only, as grep -n counts them. Files the control never matched are
listed, so a reader can see which ones the gate did not vouch for.

Verdicts and exit codes (format-independent):
  PRESENT  0   the pattern matched; matching path:line:text are reported
  ABSENT   1   the pattern did not match AND the control did, and every path was read
  BROKEN   2   the control missed, a path could not be read, the regex is invalid, or the tool
               itself failed - answer withheld

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
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


class _Unmatchable(Exception):
    """The file was read but no regex could match its decoded text."""


def _read_text(p: Path) -> str:
    """Decode a file the way a person means it: UTF-16 and UTF-8 BOMs honoured, else UTF-8.

    A NUL left in the decoded text means BOM-less UTF-16 or a binary. Scanning the replacement
    text would let the file count as read while no pattern could ever match it, which is how an
    unmatchable file used to fold silently into ABSENT.
    """
    raw = p.read_bytes()
    if raw.startswith(_UTF16_BOMS):
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    if "\x00" in text:
        raise _Unmatchable("NUL bytes: binary, or UTF-16 without a BOM")
    return text


def _lines(text: str):
    """Newline-split lines, numbered as grep -n numbers them (splitlines also breaks on \\f)."""
    parts = text.split("\n")
    if parts[-1] == "":
        parts.pop()  # the terminator of the last line is not a line of its own
    for n, line in enumerate(parts, 1):
        yield n, line[:-1] if line.endswith("\r") else line


def _result(verdict, reason, hits, control_hits, files_read, unreadable, no_control) -> dict:
    return {"verdict": verdict, "reason": reason, "hits": hits, "control_hits": control_hits,
            "files_read": files_read, "unreadable": unreadable, "no_control": no_control}


def _compile(pattern: str, control: str, flags: int):
    try:
        return re.compile(pattern, flags), re.compile(control, flags)
    except (re.error, OverflowError) as e:
        # OverflowError is what re raises for a repeat count past its limit ('a{4294967296}');
        # letting it escape would exit 1, which is ABSENT's code.
        raise ValueError("invalid regex: %s" % e) from e


def check(paths, pattern: str, control: str, *, ignore_case: bool = True) -> dict:
    """Return a verdict dict for `pattern` over `paths`, gated on `control` matching.

    PURE over the given paths (no globbing, no cwd) so it is unit-testable. `paths` may hold str
    or Path. A file that cannot be read is NOT silently skipped: it is listed in `unreadable`, and
    any unreadable file blocks ABSENT, because the control matching elsewhere proves nothing
    about a file that was never read.
    """
    try:
        pat, ctl = _compile(pattern, control, re.IGNORECASE if ignore_case else 0)
    except ValueError as e:
        return _result(BROKEN, str(e), [], 0, 0, [], [])

    hits, control_hits, files_read, unreadable, no_control = [], 0, 0, [], []
    for raw in paths:
        p = Path(raw)
        try:
            text = _read_text(p)
        except OSError as e:
            unreadable.append("%s (%s)" % (p, e.strerror or e))
            continue
        except _Unmatchable as e:
            unreadable.append("%s (%s)" % (p, e))
            continue
        files_read += 1
        file_control_hits = 0
        for n, line in _lines(text):
            if pat.search(line):
                hits.append({"path": str(p), "line": n, "text": line.strip()})
            if ctl.search(line):
                file_control_hits += 1
        control_hits += file_control_hits
        if not file_control_hits:
            no_control.append(str(p))

    if files_read == 0:
        reason = "no file could be read (%s)" % (", ".join(unreadable) or "empty path list")
        return _result(BROKEN, reason, hits, control_hits, 0, unreadable, no_control)
    if control_hits == 0:
        # The control is the whole point: it proves the pattern had a fair chance to match.
        reason = ("control %r never matched in %d file(s), so an ABSENT verdict would be "
                  "meaningless - fix the control or the paths" % (control, files_read))
        return _result(BROKEN, reason, hits, 0, files_read, unreadable, no_control)
    if unreadable and not hits:
        reason = ("%d path(s) could not be read (%s), so an ABSENT verdict would cover files "
                  "nobody looked at - fix the paths" % (len(unreadable), ", ".join(unreadable)))
        return _result(BROKEN, reason, hits, control_hits, files_read, unreadable, no_control)

    verdict = PRESENT if hits else ABSENT
    return _result(verdict, "", hits, control_hits, files_read, unreadable, no_control)


def _harden_stdout() -> None:
    """Escape what the console cannot encode rather than crash mid-listing.

    Under a cp1252 console or pipe (Windows, launched by plain `python` or `uv run`, which set no
    PYTHONIOENCODING) one hit holding U+2192 raised UnicodeEncodeError and exited 1 - ABSENT's
    code. Called only when run as a script, so an importer's stdout is never reconfigured.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):  # a stream that cannot be reconfigured keeps its setting
            pass


def main(argv=None) -> int:
    """Run the CLI. Any unexpected failure exits 2 (BROKEN), never 1, which means ABSENT."""
    try:
        return _main(argv)
    except Exception as exc:  # noqa: BLE001 - a crash must not read as a verdict
        print("claim_check: BROKEN: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return _EXIT[BROKEN]


def _main(argv) -> int:
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
    for path in r["no_control"]:
        print("no control match: %s" % path, file=sys.stderr)
    return _EXIT[v]


if __name__ == "__main__":
    _harden_stdout()
    raise SystemExit(main())
