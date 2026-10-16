# /// script
# requires-python = ">=3.14"
# ///
"""Is a test suite already running in this checkout or any of its git worktrees?

Two suites in one checkout corrupt each other's verdict: they share fixed ports, a test database,
a coverage file and the project venv, and the failures read like a defect in whatever was just
changed. So before starting a gate the question is "is one already running HERE?" - and the
hand-rolled answers get it wrong in three ways:

- `pgrep -f pytest` matches the shell running the check, because that shell's own command line
  holds the word, so it reports a suite that does not exist; and `pkill -f` kills that shell.
- A substring of the whole command line also matches `mypytestish`, an editor on `pytest.ini`,
  and every `bash -c '... pytest ...'` that merely mentions the word.
- "Here" is not one directory. Each git worktree is its own checkout, with a suite of its own,
  and a process sitting in a worktree nested under the main checkout is in both paths.

This jig resolves the repository's main checkout and every worktree from `git worktree list
--porcelain`, reads each process's cwd from `/proc/<pid>/cwd`, and attributes a process to the
DEEPEST checkout containing that cwd. It matches by ARGV TOKENS read from `/proc/<pid>/cmdline`,
never by a substring of the joined line:

  pytest   argv[0] is `pytest`/`py.test`; or a python interpreter whose script is one; or the
           tokens `-m pytest` (also `python -m pytest`, `coverage run -m pytest`)
  bmk      the program (argv[0], or the script a python runs, or `-m bmk`) is `bmk`, with a
           gate verb after it: test, test-all, testintegration, push, release, ship
  make     argv[0] is `make`/`gmake` with one of those verbs as a target
  --match  your own: one or more whitespace-separated tokens that must appear CONSECUTIVELY in
           the argv, each equal to an argv token or to its basename (`--match "cargo test"`)

The jig's own process and every ancestor are excluded, so the command running it - whatever its
argv says - can never be reported. A shell handed a command string (`bash -c '... pytest ...'`)
never matches either, since that string is one token; the suite it starts is its own process
and is found as one.

It reports each busy process (pid, rule, cwd, checkout, argv truncated), how many processes and
checkouts it examined, and how many of its own chain it set aside (`processes_excluded`).
Examining zero checkouts is a refusal, and so is a process table in which not one cwd could be
read (examined plus excluded is zero), never a clean answer. Zero EXAMINED alone is not: on a
hosted CI runner every process the user can read is the jig's own chain, and "nothing else is
running" is then the true answer. A process whose cwd cannot be read (another user's) is counted
in `skipped` and `processes_unreadable`, since it might be a suite this jig cannot see.

`--wait-s N` polls (every `--interval` seconds) until the checkouts are free or N seconds pass,
and says which happened.

Linux only: it needs `/proc`. On macOS, Windows or anywhere without it, it says so and exits 2
rather than guess.

Exit codes: 0 = nothing is running, 1 = a suite is running (or still running when `--wait-s`
ran out), 2 = could not answer (no /proc, not a git repository, zero checkouts examined, no
readable process at all, bad arguments, an internal error).

Run:
  `uv run scripts/suite_busy.py`                       (the cwd's repository)
  `uv run scripts/suite_busy.py --repo ~/src/app --json`
  `uv run scripts/suite_busy.py --wait-s 600 --match "cargo test"`
"""

import argparse
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded

__all__ = ["Busy", "Checkout", "Matcher", "Scan", "ancestors", "attribute", "builtin_matchers",
           "execute", "parse_worktrees", "scan", "token_matcher"]

COMMAND = "suite_busy"
PROC = Path("/proc")
_JSON_FLAGS = ("--json", "--json-bare")
_ARGV_SHOWN = 160
_MIN_INTERVAL = 0.2
_DELETED = " (deleted)"

_PYTEST_NAMES = frozenset({"pytest", "py.test"})
_GATE_VERBS = frozenset({"test", "test-all", "testintegration", "push", "release", "ship"})
_MAKE_NAMES = frozenset({"make", "gmake"})
# make options whose value is the NEXT token, so `make -C test all` names a directory, not a target.
_MAKE_VALUE_OPTIONS = frozenset({"-C", "-f", "-I", "-o", "-W", "--directory", "--file",
                                 "--makefile", "--include-dir", "--old-file", "--assume-old",
                                 "--new-file", "--assume-new", "--what-if"})
_PYTHON_RX = re.compile(r"^python[0-9.]*[wt]?$")
# Interpreter options that take the NEXT token as their value, so that token is not the script.
_PYTHON_VALUE_OPTIONS = frozenset({"-W", "-X", "--check-hash-based-pycs"})

#: (name, predicate over an argv) - a rule says whether one process is a suite.
Matcher = tuple[str, Callable[[Sequence[str]], bool]]


class SuiteBusyError(Exception):
    """Reported as one line and exit 2, never as a traceback."""


@dataclass(frozen=True)
class Checkout:
    """One checkout of the repository: the main one or a linked worktree."""
    path: str
    branch: str


@dataclass(frozen=True)
class Busy:
    """A process matching a rule, inside a checkout."""
    pid: int
    rule: str
    cwd: str
    checkout: str
    argv: str


@dataclass(frozen=True)
class Scan:
    """What one pass over /proc found, and how much of the table it could actually read.

    `processes_examined` counts the processes judged against the rules; `excluded` counts the
    jig's own process and ancestors whose cwd was read and then set aside. Their sum is what the
    zero-is-a-refusal rule tests: on a hosted CI runner every readable process can be the jig's
    own chain, which leaves zero examined although /proc was read fine.
    """
    busy: tuple[Busy, ...]
    processes_examined: int
    unreadable_cwd: int
    excluded: int = 0

    @property
    def processes_read(self) -> int:
        """Processes whose cwd could be read at all, examined or excluded."""
        return self.processes_examined + self.excluded


# ---- argv rules ----------------------------------------------------------------------------------

def _base(token: str) -> str:
    return os.path.basename(token)


def _python_script(argv: Sequence[str]) -> str | None:
    """The script a python interpreter runs, or None (a `-c`/`-m` run, or no script at all)."""
    i = 1
    while i < len(argv):
        tok = argv[i]
        if tok in ("-c", "-m") or tok.startswith(("-c", "-m")) and len(tok) > 2:
            return None
        if tok == "--":
            return argv[i + 1] if i + 1 < len(argv) else None
        if tok in _PYTHON_VALUE_OPTIONS:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        return tok
    return None


def _program(argv: Sequence[str]) -> str:
    """The basename of what this process RUNS: argv[0], or the script a python interpreter runs."""
    if not argv:
        return ""
    name = _base(argv[0])
    if _PYTHON_RX.match(name):
        script = _python_script(argv)
        if script is not None:
            return _base(script)
    return name


def _runs_module(argv: Sequence[str], modules: frozenset[str]) -> bool:
    """`-m <module>` (or `-m<module>`) anywhere in argv, for one of `modules`."""
    for i, tok in enumerate(argv):
        if tok == "-m" and i + 1 < len(argv) and argv[i + 1] in modules:
            return True
        if tok.startswith("-m") and tok[2:] in modules:
            return True
    return False


def _is_pytest(argv: Sequence[str]) -> bool:
    return _program(argv) in _PYTEST_NAMES or _runs_module(argv, _PYTEST_NAMES)


def _is_bmk_gate(argv: Sequence[str]) -> bool:
    if _program(argv) != "bmk" and not _runs_module(argv, frozenset({"bmk"})):
        return False
    return any(tok in _GATE_VERBS for tok in argv[1:])


def _make_targets(argv: Sequence[str]) -> list[str]:
    """The operands of a make argv: options, their separate values and VAR=value dropped."""
    targets: list[str] = []
    i = 1
    while i < len(argv):
        tok = argv[i]
        if tok in _MAKE_VALUE_OPTIONS:
            i += 2
            continue
        if not tok.startswith("-") and "=" not in tok:
            targets.append(tok)
        i += 1
    return targets


def _is_make_gate(argv: Sequence[str]) -> bool:
    if not argv or _base(argv[0]) not in _MAKE_NAMES:
        return False
    return any(tok in _GATE_VERBS for tok in _make_targets(argv))


def builtin_matchers() -> list[Matcher]:
    """The three rules a gate run is recognised by: pytest, a bmk gate verb, a make gate target."""
    return [("pytest", _is_pytest), ("bmk", _is_bmk_gate), ("make", _is_make_gate)]


def token_matcher(spec: str) -> Matcher:
    """A user rule: the whitespace-separated tokens of `spec`, consecutive in argv.

    Each token compares equal to an argv token or to its basename, never as a substring, so
    `--match pytest` does not match `mypytestish` and `--match "cargo test"` needs both words.
    """
    want = spec.split()
    if not want:
        raise SuiteBusyError("--match needs at least one token")

    def predicate(argv: Sequence[str]) -> bool:
        for start in range(len(argv) - len(want) + 1):
            window = argv[start:start + len(want)]
            if all(tok == w or _base(tok) == w for tok, w in zip(window, want, strict=True)):
                return True
        return False

    return (f"match:{spec}", predicate)


# ---- checkouts ----------------------------------------------------------------------------------

def parse_worktrees(porcelain: str) -> list[Checkout]:
    """The checkouts in `git worktree list --porcelain` output, main first. PURE.

    Examples:
        >>> parse_worktrees("worktree /r\\nHEAD abc\\nbranch refs/heads/main\\n\\n"
        ...                 "worktree /r/wt\\nHEAD def\\ndetached\\n\\n")
        [Checkout(path='/r', branch='main'), Checkout(path='/r/wt', branch='(detached)')]
    """
    out: list[Checkout] = []
    path = branch = None
    for line in porcelain.splitlines() + [""]:
        if line.startswith("worktree "):
            path, branch = line[len("worktree "):], ""
        elif line.startswith("branch ") and path is not None:
            branch = line[len("branch "):].removeprefix("refs/heads/")
        elif line == "detached" and path is not None:
            branch = "(detached)"
        elif line == "bare" and path is not None:
            branch = "(bare)"
        elif not line and path is not None:
            out.append(Checkout(path, branch or "?"))
            path = branch = None
    return out


def attribute(cwd: str, checkouts: Sequence[Checkout]) -> Checkout | None:
    """The DEEPEST checkout containing `cwd`, or None. PURE.

    A worktree nested under the main checkout is inside both paths; the process belongs to the
    worktree, which is the checkout whose suite it is.
    """
    best: Checkout | None = None
    for co in checkouts:
        root = co.path.rstrip("/") or "/"
        inside = cwd == root or cwd.startswith(root + "/") or root == "/"
        if inside and (best is None or len(root) > len(best.path.rstrip("/"))):
            best = co
    return best


# ---- /proc --------------------------------------------------------------------------------------

def _read_argv(pdir: Path) -> list[str]:
    try:
        raw = (pdir / "cmdline").read_bytes()
    except OSError:
        return []
    parts = raw.decode("utf-8", errors="replace").split("\0")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _read_cwd(pdir: Path) -> str | None:
    try:
        target = os.readlink(pdir / "cwd")
    except OSError:
        return None
    return target[: -len(_DELETED)] if target.endswith(_DELETED) else target


def _ppid(pdir: Path) -> int | None:
    try:
        stat = (pdir / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rest = stat[stat.rfind(")") + 1:].split()
    return int(rest[1]) if len(rest) >= 2 and rest[1].lstrip("-").isdigit() else None


def ancestors(pid: int, proc_root: Path) -> set[int]:
    """`pid` plus every ancestor, walking ppid. Cycle- and gap-safe. PURE over proc_root."""
    seen: set[int] = set()
    cur: int | None = pid
    while cur is not None and cur > 0 and cur not in seen:
        seen.add(cur)
        cur = _ppid(proc_root / str(cur))
    return seen


def _first_rule(argv: Sequence[str], matchers: Sequence[Matcher]) -> str | None:
    for name, predicate in matchers:
        if predicate(argv):
            return name
    return None


def scan(proc_root: Path, checkouts: Sequence[Checkout], matchers: Sequence[Matcher],
         exclude: set[int]) -> Scan:
    """Busy processes under `proc_root` inside one of `checkouts`. PURE over proc_root."""
    busy: list[Busy] = []
    examined = unreadable = excluded = 0
    for pdir in sorted(proc_root.glob("[0-9]*"), key=lambda p: int(p.name)):
        pid = int(pdir.name)
        cwd = _read_cwd(pdir)
        if pid in exclude:
            # Counted only when its cwd was READ, so a table in which nothing at all is readable
            # still sums to zero; an unreadable ancestor (init, as root) is in neither count,
            # since being excluded it could never be the suite this jig failed to see.
            if cwd is not None:
                excluded += 1
            continue
        if cwd is None:
            if pdir.exists():
                unreadable += 1
            continue
        examined += 1
        checkout = attribute(cwd, checkouts)
        if checkout is None:
            continue
        argv = _read_argv(pdir)
        rule = _first_rule(argv, matchers)
        if rule is not None:
            busy.append(Busy(pid, rule, cwd, checkout.path, " ".join(argv)[:_ARGV_SHOWN]))
    return Scan(tuple(busy), examined, unreadable, excluded)


# ---- adapters ----------------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SuiteBusyError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise SuiteBusyError(f"git {args[0]} failed in {repo}: "
                             f"{(proc.stderr or '').strip()[:200]}")
    return proc.stdout


def checkouts_of(repo: Path) -> list[Checkout]:
    """The main checkout and every worktree of the repository holding `repo`, paths resolved."""
    if not repo.is_dir():
        raise SuiteBusyError(f"not a directory: {repo}")
    listed = parse_worktrees(_git(repo, "worktree", "list", "--porcelain"))
    return [Checkout(os.path.realpath(co.path), co.branch) for co in listed]




def build_parser() -> argparse.ArgumentParser:
    p = EnvelopeArgumentParser(description=(__doc__ or COMMAND).splitlines()[0],
                               envelope_command=COMMAND, json_flags=_JSON_FLAGS)
    p.add_argument("--repo", default=".",
                   help="any path inside the repository (default: cwd); its main checkout and "
                        "every worktree are examined")
    p.add_argument("--match", action="append", default=[], metavar="TOKENS",
                   help="an extra rule: tokens that must appear consecutively in a process's "
                        "argv (each equal to a token or its basename); repeatable")
    p.add_argument("--no-builtin", action="store_true",
                   help="use only the --match rules, not the pytest/bmk/make ones")
    p.add_argument("--wait-s", type=float, default=0.0, metavar="N",
                   help="poll until free or N seconds have passed (default: answer once)")
    p.add_argument("--interval", type=float, default=2.0, metavar="S",
                   help=f"seconds between polls under --wait-s (minimum {_MIN_INTERVAL})")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true", help="print an indented JSON envelope")
    out.add_argument("--json-bare", action="store_true", help="print a one-line JSON envelope")
    return p


def _indent(args: argparse.Namespace) -> int | None:
    return None if args.json_bare else 2


def _refuse(args: argparse.Namespace, message: str, data: dict[str, Any] | None = None) -> int:
    if args.json or args.json_bare:
        emit(EXIT_ERROR, COMMAND, data, error=message, indent=_indent(args))
    print(f"{COMMAND}: {message}", file=sys.stderr)
    return EXIT_ERROR


def _validate(args: argparse.Namespace) -> list[Matcher]:
    if args.wait_s < 0 or args.wait_s != args.wait_s:
        raise SuiteBusyError("--wait-s must be a number of seconds, 0 or more")
    if not args.interval >= _MIN_INTERVAL:
        raise SuiteBusyError(f"--interval must be at least {_MIN_INTERVAL} seconds")
    matchers = [] if args.no_builtin else builtin_matchers()
    matchers += [token_matcher(spec) for spec in args.match]
    if not matchers:
        raise SuiteBusyError("--no-builtin with no --match leaves nothing to look for")
    return matchers


def _poll(proc_root: Path, checkouts: list[Checkout], matchers: list[Matcher], *,
          wait_s: float, interval: float,
          clock: Callable[[], float], sleep: Callable[[float], None]) -> tuple[Scan, float, int]:
    """Scan, and under a wait keep scanning until free or the deadline. (scan, waited, polls)."""
    start = clock()
    polls = 0
    while True:
        # Re-read every poll: the exclusion is this process's chain, which is fixed, but a
        # reparented ancestor (its parent exited) would otherwise stop being excluded.
        result = scan(proc_root, checkouts, matchers, ancestors(os.getpid(), proc_root))
        polls += 1
        waited = clock() - start
        if not result.busy or waited >= wait_s:
            return result, waited, polls
        sleep(min(interval, max(wait_s - waited, 0.0)))


def _render(result: Scan, checkouts: list[Checkout], waited: float, wait_s: float) -> str:
    head = (f"BUSY: {len(result.busy)} suite process(es)" if result.busy else "FREE")
    if wait_s:
        head += f" after waiting {waited:.1f}s" + (" (deadline reached)" if result.busy else "")
    lines = [f"{head}; examined {result.processes_examined} process(es) across "
             f"{len(checkouts)} checkout(s), set aside {result.excluded} of its own chain"]
    if result.unreadable_cwd:
        lines.append(f"  not examined: {result.unreadable_cwd} process(es) whose cwd could not "
                     "be read (another user's?)")
    lines += [f"  {b.pid:>8}  {b.rule:<10} {b.checkout}  cwd={b.cwd}\n            {b.argv}"
              for b in result.busy]
    return "\n".join(lines)


@guarded(COMMAND, json_flags=_JSON_FLAGS)
def main(argv: list[str] | None = None) -> int:
    """Answer once or wait; an uncaught exception exits 2, never Python's 1, which means busy."""
    return execute(argv)


def execute(argv: list[str] | None = None, *, proc_root: Path = PROC,
            clock: Callable[[], float] = time.monotonic,
            sleep: Callable[[float], None] = time.sleep) -> int:
    """The whole run. The /proc root, clock and sleep are seams: a platform without /proc, and a
    wait, are testable without either."""
    args = build_parser().parse_args(argv)
    if not proc_root.is_dir():
        return _refuse(args, f"no {proc_root} on this platform ({sys.platform}), so which "
                             "processes run where cannot be read - this jig answers on Linux "
                             "only")
    try:
        matchers = _validate(args)
        checkouts = checkouts_of(Path(args.repo).expanduser())
    except SuiteBusyError as exc:
        return _refuse(args, str(exc))
    if not checkouts:
        return _refuse(args, "git listed zero checkouts, so nothing was examined")
    result, waited, polls = _poll(proc_root, checkouts, matchers, wait_s=args.wait_s,
                                  interval=args.interval, clock=clock, sleep=sleep)
    data = {"busy": [b.__dict__ for b in result.busy],
            "checkouts": [co.__dict__ for co in checkouts],
            "checkouts_examined": len(checkouts),
            "processes_examined": result.processes_examined,
            "processes_excluded": result.excluded,
            "processes_unreadable": result.unreadable_cwd,
            "rules": [name for name, _ in matchers],
            "waited_s": round(waited, 3), "polls": polls,
            "timed_out": bool(args.wait_s) and bool(result.busy)}
    skipped = ([f"{result.unreadable_cwd} process(es) whose cwd could not be read"]
               if result.unreadable_cwd else [])
    if result.processes_read == 0:
        # Not "nothing left once the jig's own chain is set aside" (a hosted runner, where every
        # readable process IS that chain): only a table in which no cwd could be read at all.
        return _refuse(args, "zero processes could be examined (no cwd in the process table "
                             "could be read), so no answer is possible", data)
    code = EXIT_NO if result.busy else EXIT_YES
    if args.json or args.json_bare:
        return emit(code, COMMAND, data, skipped=skipped, indent=_indent(args))
    print(_render(result, checkouts, waited, args.wait_s))
    return code


if __name__ == "__main__":
    sys.exit(main())
