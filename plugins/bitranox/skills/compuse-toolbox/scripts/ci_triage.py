# /// script
# requires-python = ">=3.10"
# ///
"""Triage a build/CI log: strip ANSI, optionally isolate one step's block, and surface only the
error/warning lines with their line numbers.

Why: `gh run view --log` and `cargo build 2>&1` both dump huge noisy output, and every session
re-derives the same ANSI-strip -> step-isolate -> error-grep pipeline by hand. This does it once,
over any log (a file, stdin, a `gh` run, or a command's output).

Run:
  `uv run scripts/ci_triage.py --file build.log [--step "Run tests"] [--keywords error FAILED]`
  `uv run scripts/ci_triage.py --cmd "cargo build"`        (runs it, triages stderr+stdout)
  `uv run scripts/ci_triage.py --gh 12345 [--repo o/r]`    (fetches the run log via gh)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_HEADER = re.compile(r"^##\[group\]|^\s*Run ")
_DEFAULT_KW = ["error", "failed", "fail", "traceback", "panic", "warning", "fatal", "e[0-9]{3,}"]


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def error_lines(text: str, keywords=None) -> list[tuple[int, str]]:
    """[(1-based line, line)] for lines matching any keyword (default: error/warning/panic/...)."""
    kw = keywords if keywords is not None else _DEFAULT_KW
    rx = re.compile("|".join(kw), re.IGNORECASE)
    return [(i + 1, ln) for i, ln in enumerate(strip_ansi(text).splitlines()) if rx.search(ln)]


def isolate_step(text: str, step: str) -> str:
    """The block from the step/group header containing `step` up to the next header (or end)."""
    lines = strip_ansi(text).splitlines()
    start = next((i for i, ln in enumerate(lines) if _HEADER.search(ln) and step in ln), None)
    if start is None:
        return ""
    end = next((j for j in range(start + 1, len(lines)) if _HEADER.search(lines[j])), len(lines))
    return "\n".join(lines[start:end])


def _run(argv) -> str:
    out = subprocess.run(argv, capture_output=True, text=True)
    return (out.stdout or "") + (out.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Triage a build/CI log to its error/warning lines.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file")
    src.add_argument("--cmd", help="run this shell-free command (space-split) and triage its output")
    src.add_argument("--gh", metavar="RUN_ID", help="fetch a GitHub Actions run log via gh")
    ap.add_argument("--repo")
    ap.add_argument("--step", help="isolate only this step/group's block first")
    ap.add_argument("--keywords", nargs="+", help="override the error keyword set")
    args = ap.parse_args(argv)

    if args.file:
        text = open(args.file, encoding="utf-8", errors="replace").read()
    elif args.cmd:
        text = _run(args.cmd.split())
    elif args.gh:
        text = _run(["gh", "run", "view", args.gh, "--log"] + (["--repo", args.repo] if args.repo else []))
    else:
        text = sys.stdin.read()

    if args.step:
        text = isolate_step(text, args.step) or text
    hits = error_lines(text, keywords=args.keywords)
    for ln, line in hits:
        print(f"{ln}: {line}")
    print(f"{len(hits)} error/warning line(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
