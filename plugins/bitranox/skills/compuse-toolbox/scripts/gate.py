# /// script
# requires-python = ">=3.10"
# ///
"""Run quality gates, keep their REAL exit status, and only then run a follow-up action.

Why: the recurring footgun is `<gate> 2>&1 | grep summary && git push`. A pipeline exits with
its LAST element's status, so grep/head/tail succeed even when the gate failed - the `&&`
fires and a red state gets pushed. Writing `echo "RC=$?"` after a pipe records the same wrong
status. Hit three times in one session (twice unnoticed, once caught by the PreToolUse guard),
which is why this exists: the guard blocks the wrong form but does not supply the right one.

Each gate runs via subprocess with NO shell and NO pipe, so `returncode` is the gate's own.
Output goes to a log; summary lines are grepped from that log AFTERWARDS, never from a pipe
that could mask the status.

A gate is given either as one quoted string (`--gate "<cmd ...>"`, or a lone positional), which
is split into argv by the platform's own rules, or after `--`, where the tokens are ALREADY real
argv and are taken verbatim - a `name=` prefix is only read on the quoted form.

Quote that string with DOUBLE quotes, on every platform. Splitting is shlex on POSIX and
CommandLineToArgvW on Windows, and a Windows command line has no single-quoting at all: a single
quote arrives as an ordinary character glued to the argument, which then splits at its spaces
anyway. So `--gate 'pytest -q'` is ONE gate on POSIX and two broken arguments on Windows.

A gate is labeled by the `--name` written AFTER it (or a single-word `name=command` prefix);
written order is the pairing, so a name can never land on a gate the user did not name. A
lone positional gate (`-- <cmd ...>`) may be labeled by a single `--name` too, since there is
then only one gate to label. Any other placement, and an empty label, is a usage error (exit 2),
never a gate result. An unnamed gate is labeled by its whole command, never by argv[0].

Two ways a correct exit status still proves nothing, both closed here:

  * A SHARED log. The default used to be one fixed `<tempdir>/gate.log`. Gates APPEND, so two
    runs at once (parallel agents, two worktrees, a CI matrix cell) wrote into one file and each
    read the other's lines back - measured 2026-07-29, a PASS was read beside a different
    worktree's log. The default is now a fresh per-invocation file; `--log` still pins an
    explicit path, which is what a caller who wants to read the log afterwards should use.
  * A filter that matched NOTHING. `pytest -k <typo>` and `cargo test <prefix no test starts
    with>` run zero tests and exit 0, so the status says green about work that never happened.
    Each gate's output is now read for the count the runner itself reports, that count is
    printed, and a recognised count of ZERO fails the gate whatever it exited. A gate that is
    not a test runner reports no count and is judged on its status alone.

Run (plain python3, NOT uv run: this jig declares no dependencies, and uv run puts its own
ephemeral interpreter on the environment the CHILD gates inherit - measured, a gate shelling
out to `python3 -m pytest` then died with `No module named pytest` and reported a false RED):
  python3 scripts/gate.py --log /tmp/g.log -- pytest -q
  python3 scripts/gate.py --log /tmp/g.log --summary "passed" \\
      --gate "pytest -q" --name "unit tests" \\
      --gate "ruff check src" \\
      --then "git push origin HEAD"
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


_NAME_WIDTH = 56                                                # keeps one report line readable

# NOT "/tmp": on Windows that string is DRIVE-RELATIVE, not absolute - Path turns it into
# `\tmp`, so the log silently lands on whichever drive happens to be current and the
# "log: ..." line printed at the end names a path the user cannot open.
def default_log_path() -> str:
    """A FRESH log file for THIS invocation - deliberately never a shared, fixed name.

    The old default was the one constant path `<tempdir>/gate.log`. Gates append to it, so two
    runs at the same time interleave into a single file and each one greps the other's output
    back out: measured 2026-07-29, a PASS was read beside another worktree's log. Nothing in the
    report shows it, because the `log:` line names the same path either way - the wrong answer
    is indistinguishable from the right one, which is the exact failure this tool exists to
    prevent, arriving through the log instead of through a pipe.

    mkstemp rather than an f-string on the pid: it creates the file ATOMICALLY under a name
    nothing else holds, so two runs cannot be handed the same path even when they share a pid
    namespace (containers) or a pid has been recycled. The pid stays in the PREFIX because it is
    what a human greps for when several of these are lying around in the temp dir.

    No `dir=`, so mkstemp resolves the temp dir through tempfile.gettempdir() at CALL time and
    TMPDIR set by the caller is honoured. A module constant computed at import would freeze
    whatever was set when the module was first loaded, which is the same "decided once, shared
    by everyone after" shape as the fixed log name being removed here.
    """
    fd, path = tempfile.mkstemp(prefix=f"gate-{os.getpid()}-", suffix=".log")
    os.close(fd)                                    # only the NAME is wanted; run_gates reopens it
    return path


# What a test runner says it RAN. Kept as module constants so the shapes are readable together
# and a new runner is one line rather than a rewrite of the matcher.
_CARGO_RUNNING = re.compile(r"^\s*running (\d+) tests?\b", re.MULTILINE)
_PYTEST_SELECTED = re.compile(r"^.*?\b(\d+) selected\b", re.MULTILINE)
_PYTEST_COLLECTED = re.compile(r"^.*?\bcollected (\d+) items?\b", re.MULTILINE)
_PYTEST_NO_TESTS = re.compile(r"^.*\bno tests ran\b", re.MULTILINE)


def observed_test_count(text: str) -> int | None:
    r"""How many tests the gate's OWN output says it ran, or None if it is not a test run.

    None and 0 are DIFFERENT answers and must stay so. None means "this gate is not a test
    runner" - `ruff check`, `git status`, a build - and it goes on being judged by its exit
    status alone. 0 means "a test runner ran and nothing was there to run", which is the state
    this function exists to catch. Defaulting an unrecognised gate to 0 would fail every lint
    gate in every caller's pipeline, so the recogniser has to be able to say "not applicable".

    That is also why the shapes below are narrow rather than a generic "(\d+) (passed|errors)"
    sweep: a linter printing `Found 0 errors.` is a GREEN run, and a matcher loose enough to
    read a count out of it turns the tool's own success line into a red gate.

    cargo/libtest prints one `running N tests` line per test BINARY, so those SUM - a workspace
    whose lib tests ran and whose integration binary matched nothing has still run tests.

    pytest is read in the order that survives DESELECTION, because deselection is precisely the
    zero-match case: `collected 300 items / 300 deselected / 0 selected` is a filter that hit
    nothing, and its `collected` number is 300, so reading `collected` alone reports the empty
    run as a 300-test pass. The SELECTED count wins wherever pytest prints one. `no tests ran`
    is pytest's own wording for the same state under `-q`, where it prints no counts at all.

    Known limit, deliberately left: a `-q` run that DID run tests prints only `5 passed`, which
    is not matched here, so it reports None and is judged on its status. That is the safe
    direction - the dangerous state (zero) is still caught by `no tests ran`, and widening the
    match to the summary line is what would produce the false red described above.
    """
    cargo = [int(n) for n in _CARGO_RUNNING.findall(text)]
    if cargo:
        return sum(cargo)
    selected = _PYTEST_SELECTED.findall(text)
    if selected:
        return int(selected[-1])
    collected = _PYTEST_COLLECTED.findall(text)
    if collected:
        return sum(int(n) for n in collected)
    if _PYTEST_NO_TESTS.search(text):
        return 0
    return None


def _windows_argv(command):
    r"""Windows argv via CommandLineToArgvW - the C runtime's OWN command-line parser.

    This is the function every Windows program uses to read its own command line, so a command
    string is split here exactly as the program it names would split it. ctypes is stdlib, which
    matters: a hook runs on a bare interpreter with no venv and no third-party import available.

    `ctypes.wintypes` does not import on POSIX at all, so the import has to be function-local.
    """
    if not command.strip():
        # CommandLineToArgvW("") does NOT return an empty list - it returns the path of the
        # CURRENT executable, so an empty spec would silently become a gate on python itself.
        return []
    import ctypes                       # noqa: PLC0415 - Windows-only; wintypes cannot import on POSIX
    from ctypes import wintypes         # noqa: PLC0415 - same

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL

    count = ctypes.c_int(0)
    argv = shell32.CommandLineToArgvW(command, ctypes.byref(count))
    if not argv:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        kernel32.LocalFree(argv)


def split_command(spec: str) -> list[str]:
    r"""Split one quoted command string into argv, by the platform's own rules.

    POSIX: shlex. Windows: CommandLineToArgvW, so the string is split exactly as the program it
    names would split it.

    shlex's POSIX mode was the bug. It treats a backslash as an ESCAPE, so on Windows it
    destroyed every path in a command: `C:\Program Files\Py\python.exe` became `C:Program` +
    `FilesPypython.exe`, and the caller then ran a binary that does not exist. Approximating the
    rules with shlex-minus-escape-processing fixed the common shapes but still mis-read the C
    runtime's own `"a\"b"` quoting, so the real parser is called instead: it removes the class of
    problem rather than the instances of it.

    Kept identical in gate.py, diffbehave.py and hooks/harness_checks.py.
    """
    if os.name != "nt":
        return shlex.split(spec)
    return _windows_argv(spec)


def derived_name(argv: list[str]) -> str:
    """The label for a gate nobody named: the COMMAND ITSELF, truncated.

    Deliberately not argv[0] - see gate_spec for why that produced reports like "[PASS] env".
    Both routes into a gate (a single --gate/positional string and `-- <cmd ...>`) derive their
    name here, so the same command cannot be labeled two different ways depending on how it was
    written. The two routes differ only in SPLITTING: a quoted string goes through
    split_command (shlex on POSIX, CommandLineToArgvW on Windows), while
    tokens after `--` are taken verbatim (the shell already split them, and re-splitting a lone
    one tore a path with a space in half - see main).
    """
    return " ".join(argv)[:_NAME_WIDTH]


def gate_spec(spec: str):
    """Turn one --gate string into (display name, argv).

    `name=command` sets the name explicitly, but only when the head reads like an actual
    label: a single word, no leading '-', no '/'. A real invocation was `env -u VIRTUAL_ENV
    BMK_PYTHON_CMD=/path/.venv/bin/python make test` - that command carries a genuine
    assignment (`BMK_PYTHON_CMD=...`) of its own, and partitioning on that first '=' gives a
    head of "env -u VIRTUAL_ENV BMK_PYTHON_CMD": non-empty, no leading '-', no '/', so an
    earlier version of this guard accepted it as the label and ran "/path/.venv/bin/python
    make test" as the gate - the interpreter tried to open a file literally named "make" and
    died, reported as a genuine-looking FAIL for what was really a parsing mistake (exactly
    the misattribution this tool exists to prevent). A real label is one word ("unit",
    "lint"); a multi-word head is the START of a command, never a name, so any whitespace in
    the head disqualifies it and the whole spec is kept as the command.

    Otherwise the name is the COMMAND ITSELF, truncated - deliberately not argv[0], which is a
    wrapper (env/uv/timeout/sudo) far more often than it is the thing under test and produced
    reports like "[PASS] env". Skipping wrappers cleverly was tried and misfired (`env -u X uv
    run pytest` came out as "run --extra dev"), so this shows the command verbatim: longer,
    but it never lies.
    """
    name = ""
    if "=" in spec:
        head, _, tail = spec.partition("=")
        head = head.strip()
        # a label is a single word - never split `--flag=value`, a path, or a multi-word
        # command prefix that merely happens to contain its own '=' assignment further along
        if head and not head.startswith("-") and "/" not in head and not any(c.isspace() for c in head):
            name, spec = head, tail
    argv = split_command(spec)
    if not argv:
        raise ValueError(f"empty gate: {spec!r}")
    return (name[:_NAME_WIDTH] if name else derived_name(argv)), argv


class _WrittenOrder(argparse.Action):
    """Append (option, value) to ONE list shared by --gate and --name, in written order.

    argparse's own `action="append"` fills a separate list per option, which discards the order
    the two were interleaved in. Pairing those lists by index made `--gate A --gate B --name x`
    label gate A - a label on a gate the user never named, and the exact mislabeling this tool
    exists to prevent. The written order IS the pairing, so it has to survive parsing.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        written = getattr(namespace, "written", None)
        if written is None:
            written = []
            setattr(namespace, "written", written)              # per-parse list; the default stays None
        written.append((self.dest, values))


def pair_names_with_gates(written, has_positional_gate: bool):
    """Turn the written (option, value) sequence into [(explicit name or None, gate spec)].

    A --name labels the ONE --gate written before it. Consequences, all deliberate:
      * fewer names than gates is normal - an unnamed gate keeps the name derived from its
        command, and nothing shifts;
      * a second --name for the same gate is 'more names than gates' - the only way to write
        it is to intend a pairing that does not exist;
      * a --name before any --gate has nothing to label. It is accepted in exactly one
        unambiguous case, returned as `leading`: a lone positional gate (`--name x -- true`),
        which cannot be preceded by anything because it is always written last;
      * an EMPTY (or blank) --name is refused outright. It cannot label anything, yet it still
        consumed its gate's one pairing slot, so `--gate g --name "" --name real` failed with
        "more --name than --gate" although one usable name was given - a message describing a
        mistake the user did not make.

    Returns (pairs, leading_names). Raises ValueError with a message describing THIS mistake -
    never a name/gate count, which would misdescribe a misplaced --name.
    """
    pairs: list[tuple[str | None, str]] = []
    leading: list[str] = []
    for option, value in written:
        if option == "gate":
            pairs.append((None, value))
            continue
        if not value.strip():
            raise ValueError("--name must not be empty: an empty label cannot name a gate, and "
                             "silently dropping it would consume that gate's pairing slot")
        if not pairs:
            leading.append(value)
        elif pairs[-1][0] is not None:
            raise ValueError(
                f"more --name than --gate: each --name labels the one --gate written before it, "
                f"and that gate already has the name {pairs[-1][0]!r}"
            )
        else:
            pairs[-1] = (value, pairs[-1][1])
    if leading and (pairs or not has_positional_gate):
        raise ValueError("--name must be written AFTER the --gate it labels")
    if len(leading) > 1:
        raise ValueError(f"more --name than --gate: {len(leading)} names for the one gate given")
    return pairs, leading


@dataclass
class GateResult:
    name: str
    argv: list[str]
    returncode: int
    summary_lines: list[str] = field(default_factory=list)
    test_count: int | None = None

    @property
    def ok(self) -> bool:
        """Green only if it exited 0 AND, where it is a test run, actually ran a test.

        `test_count != 0` is True for None too, and that is the point: a gate that is not a test
        runner has no count to refuse and keeps being judged on its status alone.
        """
        return self.returncode == 0 and self.test_count != 0


@dataclass
class GateReport:
    results: list[GateResult]

    @property
    def ok(self) -> bool:
        """True only when EVERY gate passed. A missing binary counts as failed, and so does a
        test gate that ran zero tests however it exited - see GateResult.ok."""
        return all(r.ok for r in self.results)


def run_gates(gates, log_path, summary: str = "") -> GateReport:
    """Run `gates` in order, appending all output to `log_path`; return the real statuses.

    `gates` is [(name, argv_list)]. argv is a LIST, never a shell string, so no quoting or
    globbing surprises and no shell to swallow the status. `summary` is an optional regex;
    matching lines from that gate's own output are kept for a compact report.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(summary) if summary else None
    results: list[GateResult] = []

    with log_path.open("a", encoding="utf-8") as log:
        for name, argv in gates:
            log.write(f"\n=== gate: {name} :: {' '.join(argv)} ===\n")
            log.flush()
            try:
                proc = subprocess.run(
                    argv, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", check=False,
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                rc = proc.returncode
            except OSError as e:
                # A missing/unrunnable binary is a FAILED gate, not a crash of the runner:
                # the caller's follow-up must still be blocked.
                out, rc = f"could not run {argv!r}: {e}\n", 127
            log.write(out)
            log.flush()
            lines = [ln for ln in out.splitlines() if pattern.search(ln)] if pattern else []
            # Counted from the gate's OWN combined output, not from the log file: the log is
            # opened in append mode and may already hold earlier gates, so reading it back
            # would attribute a previous gate's tests to this one.
            results.append(GateResult(name=name, argv=list(argv), returncode=rc,
                                      summary_lines=lines, test_count=observed_test_count(out)))

    return GateReport(results=results)


def format_report(report: GateReport, log_path) -> str:
    out = []
    for r in report.results:
        mark = "PASS" if r.ok else "FAIL"
        # The count is printed for EVERY recognised test run, not only the zero one: a reader
        # who never sees the number cannot notice it halving between two runs either.
        counted = "" if r.test_count is None else f" [{r.test_count} tests]"
        out.append(f"  [{mark}] {r.name} (rc={r.returncode}){counted}")
        if r.test_count == 0:
            out.append("         REFUSED: ran 0 tests. A filter matching nothing exits 0, so "
                       "this gate's status is not evidence that anything was checked.")
        out.extend(f"         {ln.strip()}" for ln in r.summary_lines[:3])
    out.append("")
    out.append("ALL GATES PASSED" if report.ok else "GATE RED - follow-up NOT run")
    out.append(f"log: {log_path}")
    return "\n".join(out)


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="run gates, keep their real exit status")
    p.add_argument("--gate", action=_WrittenOrder, default=None,
                   help="a gate as one DOUBLE-quoted string (repeatable), split into argv by "
                        "the platform's rules (shlex on POSIX, CommandLineToArgvW on Windows, "
                        "which has no single-quoting at all) and run "
                        "without a shell. Optionally prefix it 'name=command' to label it, but "
                        "only when name is a SINGLE WORD (no space, no leading '-', no '/') - "
                        "anything else is left as part of the command untouched. For a label "
                        "with spaces, use --name instead")
    p.add_argument("--name", action=_WrittenOrder, default=None,
                   help="an explicit label for the --gate WRITTEN BEFORE IT (repeatable; "
                        "overrides any 'name=' prefix on that gate and is the only way to give "
                        "a label with spaces). A lone positional gate may be labeled too. An "
                        "empty or blank label is a usage error, not a silently ignored one")
    p.add_argument("--log", default=None,
                   help="append all gate output here [default: a FRESH per-invocation file "
                        f"under {tempfile.gettempdir()}; the old fixed default was one shared "
                        "path, so two concurrent runs appended into a single file and a reader "
                        "could not tell whose output was whose]")
    p.add_argument("--summary", default="", help="regex; matching output lines are shown per gate")
    p.add_argument("--then", default="", help="run ONLY if every gate passed")
    # NOT argparse.REMAINDER: it swallows every option that follows the first positional, so
    # `gate.py "pytest -q" --then "git push"` collapsed into ONE nonsense gate and failed
    # rc=127 naming the whole command line - a usage error wearing a broken-gate costume.
    # With nargs="*" argparse parses the options normally and strips the first `--`.
    p.add_argument("rest", nargs="*", help='<cmd> as one quoted string, or -- <cmd ...>')
    args = p.parse_args(raw)

    # `--` means the calling shell has ALREADY split the command, so what follows are real argv
    # tokens; argparse strips that first `--`, so the raw arguments are the only place it is
    # still visible. Deciding by COUNT instead re-split a lone token through shlex, and a path
    # with a space in it (`-- '/path/my gate.sh'`) came apart into '/path/my' + 'gate.sh', ran
    # '/path' and reported "[FAIL] /path (rc=127)" - a false red for a script that exits 0,
    # which flipped to PASS as soon as any second token followed. A verdict must never turn on
    # an argument the gate ignores.
    positional = None
    if args.rest:
        if "--" in raw or len(args.rest) > 1:
            # Real argv already. The NAME still comes from the whole command, never argv[0]:
            # `-- env -u VIRTUAL_ENV make --version` reported "[FAIL] env (rc=2)", naming the
            # wrapper instead of the thing under test, while the single-string gate named it
            # correctly - both routes derive the name through derived_name for that reason.
            positional = (derived_name(args.rest), list(args.rest))
        else:
            # A lone positional written WITHOUT `--` is the whole gate as one quoted
            # string, so it goes through split_command and can carry a name= prefix, exactly
            # like --gate.
            positional = gate_spec(args.rest[0])

    written = getattr(args, "written", None) or []
    if not any(option == "gate" for option, _ in written) and positional is None:
        p.error('no gate given: use --gate "<cmd>" or -- <cmd ...>')
    try:
        pairs, leading = pair_names_with_gates(written, positional is not None)
    except ValueError as exc:
        # A mispaired name is a USAGE error (exit 2), never a gate result: reporting it as a
        # red gate would be the misattribution this tool exists to prevent.
        p.error(str(exc))
        raise                                                   # unreachable: p.error exits

    gates = []
    for explicit, spec in pairs:
        derived, gate_argv = gate_spec(spec)
        gates.append((explicit or derived, gate_argv))
    if positional is not None:
        name, gate_argv = positional
        gates.append((leading[0] if leading else name, gate_argv))

    # Resolved HERE, not as an argparse default: an argparse default is evaluated once at
    # parser-construction time, which would hand every gate run in one process the same file
    # and reintroduce the sharing this fixes one scope further in.
    log_path = args.log or default_log_path()
    report = run_gates(gates, log_path, args.summary)
    print(format_report(report, log_path))
    if not report.ok:
        return 1
    if args.then:
        # The follow-up runs through a SHELL, unlike the gates. That is deliberate: a
        # follow-up is routinely compound ("git add X && git commit"), and shlex-splitting
        # it handed git a literal "&&" as a pathspec so the commit silently never ran. The
        # tool's guarantee is that a GATE's status is never masked by a pipe - it was never
        # that the follow-up avoids a shell. By here every gate has already passed.
        print(f"\ngates green -> running: {args.then}")
        return subprocess.run(args.then, shell=True, check=False).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
