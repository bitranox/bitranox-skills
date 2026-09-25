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

Exit codes: 0 = clean; 1 = error/warning lines found, or the `--cmd` command exited non-zero;
2 = the tool could not do its job (bad argument, unreadable file, command not found, `gh` failed,
`--step` names no step in the log). Line numbers always count from the top of the whole log, so
they match `grep -n`, including under `--step`.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# `gh run view --log` prefixes each line with "job<TAB>step<TAB>timestamp "; a downloaded job log
# prefixes it with the timestamp alone. Both hide a header from a ^-anchored match.
_GH_PREFIX = re.compile(r"^(?:[^\t\n]*\t[^\t\n]*\t)?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?")
_HEADER = re.compile(r"^##\[group\]|^\s*Run ")
# Word-bound so a hex sha, a crate named "failure" or "stderr" is not a hit; the scoped
# case-sensitive arms keep CamelCase exception names (TypeError, DeprecationWarning) and rustc codes.
_DEFAULT_KW = [
    r"\berror(?:s|ed)?\b", r"(?-i:[a-z]Error\b)", r"\bfail(?:ed|s)?\b", r"\btraceback\b",
    r"\bpanic(?:ked)?\b", r"\bwarnings?\b", r"(?-i:[a-z]Warning\b)", r"\bfatal\b",
    r"(?-i:\bE\d{3,}\b)",
]
# "0 failed", "0 errors", "0 warnings" are a green summary, not a failure.
_ZERO_COUNT = re.compile(r"\b0 (?:failed|failures?|errors?|warnings?)\b", re.IGNORECASE)
_BOMS = [(b"\xef\xbb\xbf", "utf-8"), (b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")]

Runner = Callable[[Sequence[str]], "tuple[str, int]"]


class TriageError(Exception):
    """The tool cannot do its job; main reports it and exits 2."""


def strip_ansi(text: str) -> str:
    return _ANSI.sub("", text)


def log_lines(text: str) -> list[str]:
    """Lines split on newline only, so a form feed or U+2028 cannot shift the numbering."""
    lines = strip_ansi(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def content(line: str) -> str:
    """The line with any gh/timestamp prefix removed."""
    return _GH_PREFIX.sub("", line, count=1)


def error_lines(text: str, keywords=None) -> list[tuple[int, str]]:
    """[(1-based line, line)] for lines matching any keyword (default: error/warning/panic/...)."""
    return _hits(log_lines(text), keywords, 0, None)


def _hits(lines: list[str], keywords, start: int, end: int | None) -> list[tuple[int, str]]:
    kw = keywords if keywords is not None else _DEFAULT_KW
    rx = re.compile("|".join(kw), re.IGNORECASE)
    scrub = keywords is None
    out = []
    for i in range(start, len(lines) if end is None else end):
        # Match the content only: a job or step NAMED "Check for errors" must not flag every line.
        body = content(lines[i])
        if rx.search(_ZERO_COUNT.sub("", body) if scrub else body):
            out.append((i + 1, lines[i]))
    return out


def locate_step(lines: list[str], step: str) -> tuple[int, int] | None:
    """(start, end) line indices of the block from the header naming `step` to the next header."""
    bodies = [content(ln) for ln in lines]
    start = next((i for i, b in enumerate(bodies) if _HEADER.search(b) and step in b), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, len(bodies)) if _HEADER.search(bodies[j])), len(bodies))
    return start, end


def isolate_step(text: str, step: str) -> str:
    """The block from the step/group header containing `step` up to the next header (or end)."""
    lines = log_lines(text)
    span = locate_step(lines, step)
    return "" if span is None else "\n".join(lines[span[0]:span[1]])


def decode(data: bytes) -> str:
    """Decode log bytes: honour a UTF-8/UTF-16 BOM (PowerShell 5.1 `>` writes UTF-16LE), else UTF-8."""
    for bom, enc in _BOMS:
        if data.startswith(bom):
            return data[len(bom):].decode(enc, errors="replace")
    return data.decode("utf-8", errors="replace")


def _run(argv: Sequence[str]) -> tuple[str, int]:
    exe = shutil.which(argv[0])
    if exe is None:
        raise TriageError(f"command not found: {argv[0]}")
    out = subprocess.run([exe, *argv[1:]], capture_output=True)
    return decode(out.stdout or b"") + decode(out.stderr or b""), out.returncode


def _tail(text: str, n: int = 20) -> str:
    return "\n".join(log_lines(text)[-n:])


def _read_source(args, run: Runner) -> tuple[str, int]:
    """(log text, exit code of the command that produced it; 0 for a file or stdin)."""
    if args.file is not None:
        try:
            with open(args.file, "rb") as fh:
                return decode(fh.read()), 0
        except OSError as exc:
            raise TriageError(f"cannot read {args.file}: {exc}") from exc
    if args.cmd is not None:
        argv = args.cmd.split()
        if not argv:
            raise TriageError("--cmd is empty")
        try:
            return run(argv)
        except OSError as exc:
            raise TriageError(f"cannot run {argv[0]}: {exc}") from exc
    if args.gh is not None:
        return _read_gh(args, run)
    return decode(sys.stdin.buffer.read()), 0


def _read_gh(args, run: Runner) -> tuple[str, int]:
    argv = ["gh", "run", "view", args.gh, "--log"] + (["--repo", args.repo] if args.repo else [])
    try:
        text, rc = run(argv)
    except OSError as exc:
        raise TriageError(f"cannot run gh: {exc}") from exc
    if rc != 0:
        raise TriageError(f"gh exited {rc}; no log to triage:\n{_tail(text)}")
    return text, 0


def _validate(args) -> None:
    for flag in ("file", "cmd", "gh"):
        value = getattr(args, flag)
        if value is not None and not value.strip():
            raise TriageError(f"--{flag} is empty")
    try:
        re.compile("|".join(args.keywords or _DEFAULT_KW))
    except re.error as exc:
        raise TriageError(f"--keywords is not a valid regex: {exc}") from exc


def _reconfigure_streams() -> None:
    """A cp1252 console or pipe must print '?' for an unencodable char, not crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                pass


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Triage a build/CI log to its error/warning lines. "
                                 "Exit 0 clean, 1 errors found or command failed, 2 tool error.")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--file")
    src.add_argument("--cmd", help="run this shell-free command (space-split) and triage its output")
    src.add_argument("--gh", metavar="RUN_ID", help="fetch a GitHub Actions run log via gh")
    ap.add_argument("--repo")
    ap.add_argument("--step", help="isolate only this step/group's block first (exit 2 if absent)")
    ap.add_argument("--keywords", nargs="+", help="override the error keyword set (each is a regex)")
    return ap


def triage(args, run: Runner) -> int:
    _validate(args)
    text, cmd_rc = _read_source(args, run)
    lines = log_lines(text)
    start, end = 0, None
    if args.step:
        span = locate_step(lines, args.step)
        if span is None:
            raise TriageError(f"step not found in the log: {args.step!r}")
        start, end = span
    hits = _hits(lines, args.keywords, start, end)
    for ln, line in hits:
        print(f"{ln}: {line}")
    print(f"{len(hits)} error/warning line(s)")
    if cmd_rc != 0:
        print(f"command exited {cmd_rc}; last lines of its output:\n{_tail(text)}")
        return 1
    return 1 if hits else 0


def main(argv=None, *, run: Runner = _run) -> int:
    _reconfigure_streams()
    args = _parser().parse_args(argv)
    try:
        return triage(args, run)
    except TriageError as exc:
        print(f"ci_triage: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
