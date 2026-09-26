# /// script
# requires-python = ">=3.10"
# ///
"""Triage a build/CI log: strip ANSI, optionally isolate one step's block, and surface only the
error/warning lines with their line numbers.

Why: `gh run view --log` and `cargo build 2>&1` both dump huge noisy output, and every session
re-derives the same ANSI-strip -> step-isolate -> error-grep pipeline by hand. This does it once,
over any log (a file, stdin, a `gh` run, or a command's output).

Run (plain python3, NOT uv run: `--cmd` inherits the launcher's environment, and under uv run a
`python3 -m pytest` there fails with No module named pytest):
  `python3 scripts/ci_triage.py --file build.log [--step "Run tests"] [--keywords error FAILED]`
  `python3 scripts/ci_triage.py --cmd "cargo build"`        (runs it, triages stderr+stdout)
  `python3 scripts/ci_triage.py --gh 12345 [--repo o/r]`    (fetches the run log via gh)

Exit codes: 0 = clean; 1 = error/warning lines found, or the `--cmd` command exited non-zero;
2 = the tool could not do its job (bad argument, unreadable file, command not found, `gh` failed,
`--step` names no step in the log). Line numbers always count from the top of the whole log, so
they match `grep -n`, including under `--step`.

`--step NAME` selects, in every job, every step whose `gh run view --log` step column (the step name
as GitHub lists it) OR whose own `##[group]`/`Run ` header contains NAME. A line with no step column
- a downloaded job log, or one gh wrote as UNKNOWN STEP - belongs to the block it continues: from a
header containing NAME, or from a selected step, up to the next header, mapped line or job.

`--cmd` is split into argv the way a shell would split it (shlex on POSIX, CommandLineToArgvW on
Windows) and run without a shell; quote with DOUBLE quotes, which both honour.

The default keywords ignore a keyword that is only a path component (`src/errors/mod.rs`) or part
of a command-line flag (`-Wno-error=foo`, `--fail-under=80`); `--keywords` matches raw text.
"""
from __future__ import annotations

# Run with plain python3, never `uv run`: the command this jig runs inherits the launcher's
# environment, and under uv run a child `python3` resolves to uv's throwaway build env, where
# pytest and the project's packages are missing - a false RED. toolbox-nudge reads this.
LAUNCH_WITH = "python3"

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence

# gate's splitter, not a copy: shlex on POSIX, CommandLineToArgvW on Windows. A bare str.split()
# ignored quoting, so `--cmd "python3 -c 'import x'"` ran with its argument torn in two.
from gate import split_command

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# `gh run view --log` prefixes each line with "job<TAB>step<TAB>timestamp "; a downloaded job log
# prefixes it with the timestamp alone. Both hide a header from a ^-anchored match.
_GH_PREFIX = re.compile(r"^(?:[^\t\n]*\t[^\t\n]*\t)?\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?")
# The same gh prefix with its job and step columns captured; a downloaded job log has neither.
_GH_COLUMNS = re.compile(r"^([^\t\n]*)\t([^\t\n]*)\t\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")
# What gh writes in the step column for a line it could not map to a step.
_GH_UNMAPPED = "UNKNOWN STEP"
_HEADER = re.compile(r"^##\[group\]|^\s*Run ")
# Word-bound so a hex sha or "stderr" is not a hit; the scoped case-sensitive arms keep exception
# class names, whose "Error"/"Warning" follows any letter or digit (TypeError, OSError, HTTPError),
# and rustc codes. "failure(s)" and "failing" are maven's BUILD FAILURE and mocha's "1 failing".
_DEFAULT_KW = [
    r"\berror(?:s|ed)?\b", r"(?-i:[A-Za-z0-9]Error\b)", r"\bfail(?:ed|s|ures?|ing)?\b",
    r"\btraceback\b", r"\bpanic(?:s|ked|king)?\b", r"\bwarnings?\b", r"(?-i:[A-Za-z0-9]Warning\b)",
    r"\bfatal\b", r"(?-i:\bE\d{3,}\b)",
]
# A zero count in either order ("0 failed", "Errors: 0", "Failures: 0") is a green summary.
_COUNTED = r"(?:failed|failures?|failing|errors?|errored|warnings?)"
_ZERO_COUNT = re.compile(rf"\b0 {_COUNTED}\b|\b{_COUNTED}\s*[:=]\s*0(?![\d.])", re.IGNORECASE)
# A cargo progress line names a crate, and a crate may be called failure, error-chain or warnings.
_CARGO_CRATE = re.compile(
    r"(?-i:\b(?:Compiling|Checking|Downloaded|Downloading|Documenting|Fresh|Installing|Installed|"
    r"Locking|Adding|Updating|Removing|Unpacking))\s+[A-Za-z0-9_-]+(?=\s+v\d)")
# A keyword that is a PATH COMPONENT (src/errors/mod.rs) or part of a command-line FLAG
# (-Wno-error=foo, --fail-under=80, --no-fail-fast) names a place or an option, not an outcome.
# A flag starts a token and has a letter right after its dashes, so go test's `--- FAIL:` and a
# diff's `- error` line are left alone; a path component touches a separator, so a gcc/MSVC
# `file.c:3: error:` keeps its keyword, which is separated from the path by `: `.
_PATH_OR_FLAG = re.compile(r"(?<!\S)--?[A-Za-z][\w-]*(?:=\S*)?|(?<=[/\\])[\w.-]+|[\w.-]+(?=[/\\])")
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
    lines = log_lines(text)
    return _hits(lines, keywords, range(len(lines)))


def _scrub(body: str) -> str:
    """The default keywords' view of a line: zero counts, cargo crate names, path components and
    command-line flags removed."""
    return _PATH_OR_FLAG.sub("", _CARGO_CRATE.sub("", _ZERO_COUNT.sub("", body)))


def _hits(lines: list[str], keywords, indices: Iterable[int]) -> list[tuple[int, str]]:
    kw = keywords if keywords is not None else _DEFAULT_KW
    rx = re.compile("|".join(kw), re.IGNORECASE)
    scrub = keywords is None
    out = []
    for i in indices:
        # Match the content only: a job or step NAMED "Check for errors" must not flag every line.
        body = content(lines[i])
        if rx.search(_scrub(body) if scrub else body):
            out.append((i + 1, lines[i]))
    return out


def _gh_columns(line: str) -> tuple[str | None, str | None]:
    """(job, step) of a `gh run view --log` line; step is None when the line has no step column
    or gh wrote UNKNOWN STEP for it, and job is None only for a line with no gh columns at all."""
    m = _GH_COLUMNS.match(line)
    if m is None:
        return None, None
    job, step = m.group(1), m.group(2)
    return job, (None if step == _GH_UNMAPPED else step)


def _chosen_steps(columns, lines: list[str], step: str) -> set[tuple[str | None, str]]:
    """The (job, step name) pairs of every mapped step whose name, or one of whose own headers,
    contains `step`."""
    chosen: set[tuple[str | None, str]] = set()
    for (job, name), ln in zip(columns, lines):
        if name is None:
            continue
        body = content(ln)
        if step in name or (_HEADER.search(body) and step in body):
            chosen.add((job, name))
    return chosen


def locate_step(lines: list[str], step: str) -> list[int]:
    """Indices of the lines belonging to `step`, in every job; empty when no step matches.

    A gh log names each line's step in its 2nd column. A MAPPED step is selected whole when its
    name contains `step` or when any of its own `##[group]`/`Run ` headers does - both, never one
    route shadowing the other, so a name matching "Install pytest" cannot hide the step whose
    header is "Run pytest -q". A line with no step column (a downloaded job log, or gh's UNKNOWN
    STEP) belongs to the block it continues: the mapped step above it, or the header block it is
    in, up to the next header, the next mapped line or the next job. Every match counts, because a
    matrix run repeats the step once per job and the failing job need not be the first.
    """
    columns = [_gh_columns(ln) for ln in lines]
    chosen = _chosen_steps(columns, lines, step)
    picked: list[int] = []
    inside = False
    previous_job: str | None = None
    for i, ((job, name), ln) in enumerate(zip(columns, lines)):
        if job != previous_job:
            inside = False
            previous_job = job
        if name is not None:
            inside = (job, name) in chosen
        elif _HEADER.search(content(ln)):
            inside = step in content(ln)
        if inside:
            picked.append(i)
    return picked


def isolate_step(text: str, step: str) -> str:
    """The lines of every block belonging to `step` (see locate_step), joined; "" when absent."""
    lines = log_lines(text)
    return "\n".join(lines[i] for i in locate_step(lines, step))


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
        try:
            argv = split_command(args.cmd)
        except (ValueError, OSError) as exc:
            raise TriageError(f"--cmd cannot be split into arguments: {exc}: {args.cmd!r}") from exc
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
    src.add_argument("--cmd", help="run this command WITHOUT a shell and triage its output; it is "
                     "split into argv like a shell would (shlex on POSIX, CommandLineToArgvW on "
                     "Windows, which has no single-quoting, so quote with DOUBLE quotes)")
    src.add_argument("--gh", metavar="RUN_ID", help="fetch a GitHub Actions run log via gh")
    ap.add_argument("--repo")
    ap.add_argument("--step", help="triage only this step: the gh step name, else the ##[group]/Run "
                    "header text; every job's copy counts (exit 2 if absent)")
    ap.add_argument("--keywords", nargs="+", help="override the error keyword set (each is a regex)")
    return ap


def triage(args, run: Runner) -> int:
    _validate(args)
    text, cmd_rc = _read_source(args, run)
    lines = log_lines(text)
    indices: Iterable[int] = range(len(lines))
    if args.step:
        indices = locate_step(lines, args.step)
        if not indices:
            raise TriageError(f"step not found in the log: {args.step!r}")
    hits = _hits(lines, args.keywords, indices)
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
