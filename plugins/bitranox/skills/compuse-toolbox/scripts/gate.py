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

A gate is given either as one shell-quoted string (`--gate '<cmd ...>'`, or a lone positional),
which is shlex-split, or after `--`, where the tokens are ALREADY real argv and are taken
verbatim - a `name=` prefix is only read on the shell-quoted form.

A gate is labeled by the `--name` written AFTER it (or a single-word `name=command` prefix);
written order is the pairing, so a name can never land on a gate the user did not name. A
lone positional gate (`-- <cmd ...>`) may be labeled by a single `--name` too, since there is
then only one gate to label. Any other placement, and an empty label, is a usage error (exit 2),
never a gate result. An unnamed gate is labeled by its whole command, never by argv[0].

Run:
  uv run scripts/gate.py --log /tmp/g.log -- pytest -q
  uv run scripts/gate.py --log /tmp/g.log --summary "passed" \\
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

# NOT "/tmp/gate.log": on Windows that string is DRIVE-RELATIVE, not absolute - Path turns it
# into `\tmp\gate.log`, so the log silently lands on whichever drive happens to be current
# and the "log: ..." line printed at the end names a path the user cannot open.
DEFAULT_LOG = str(Path(tempfile.gettempdir()) / "gate.log")


def split_command(spec: str) -> list[str]:
    r"""Split one shell-quoted command string into argv, without eating Windows paths.

    shlex's POSIX mode treats a backslash as an ESCAPE, so on Windows it silently destroyed
    every path in a gate: `C:\Program Files\Py\python.exe -c "print(1)"` split into
    ['C:Program', 'FilesPypython.exe', ...], the gate ran a binary that does not exist and
    reported rc=127 - a FALSE RED for a command that passes, which is precisely the
    misattribution this whole tool exists to prevent, produced by the tool itself.

    On Windows the fix is to stop processing escapes: quoting (both ' and ") keeps working,
    while a backslash stays the literal path separator it is there. A space still separates
    arguments on both platforms, so a path containing one must be quoted - exactly as the
    user's own shell already requires. POSIX keeps standard shlex behaviour, where a
    backslash genuinely IS an escape and callers rely on it.
    """
    if os.name != "nt":
        return shlex.split(spec)
    lexer = shlex.shlex(spec, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    try:
        return list(lexer)
    except ValueError:
        # The one shape escape-off cannot read: the C runtime's own `"a\"b"` convention for an
        # embedded quote, where dropping escapes leaves the quotes unbalanced. Fall back to the
        # lexer that tolerates it and strip one wrapping pair. Kept identical to diffbehave.py
        # and hooks/harness_checks.py, which hit the same quirk.
        out = []
        for token in shlex.split(spec, posix=False):
            if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
                token = token[1:-1]
            out.append(token)
        return out


def derived_name(argv: list[str]) -> str:
    """The label for a gate nobody named: the COMMAND ITSELF, truncated.

    Deliberately not argv[0] - see gate_spec for why that produced reports like "[PASS] env".
    Both routes into a gate (a single --gate/positional string and `-- <cmd ...>`) derive their
    name here, so the same command cannot be labeled two different ways depending on how it was
    written. The two routes differ only in SPLITTING: a quoted string is shlex-split, while
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


@dataclass
class GateReport:
    results: list[GateResult]

    @property
    def ok(self) -> bool:
        """True only when EVERY gate exited 0. A missing binary counts as failed."""
        return all(r.returncode == 0 for r in self.results)


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
            results.append(GateResult(name=name, argv=list(argv), returncode=rc, summary_lines=lines))

    return GateReport(results=results)


def format_report(report: GateReport, log_path) -> str:
    out = []
    for r in report.results:
        mark = "PASS" if r.returncode == 0 else "FAIL"
        out.append(f"  [{mark}] {r.name} (rc={r.returncode})")
        out.extend(f"         {ln.strip()}" for ln in r.summary_lines[:3])
    out.append("")
    out.append("ALL GATES PASSED" if report.ok else "GATE RED - follow-up NOT run")
    out.append(f"log: {log_path}")
    return "\n".join(out)


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="run gates, keep their real exit status")
    p.add_argument("--gate", action=_WrittenOrder, default=None,
                   help="a gate as one shell-quoted string (repeatable); split with shlex, run "
                        "without a shell. Optionally prefix it 'name=command' to label it, but "
                        "only when name is a SINGLE WORD (no space, no leading '-', no '/') - "
                        "anything else is left as part of the command untouched. For a label "
                        "with spaces, use --name instead")
    p.add_argument("--name", action=_WrittenOrder, default=None,
                   help="an explicit label for the --gate WRITTEN BEFORE IT (repeatable; "
                        "overrides any 'name=' prefix on that gate and is the only way to give "
                        "a label with spaces). A lone positional gate may be labeled too. An "
                        "empty or blank label is a usage error, not a silently ignored one")
    p.add_argument("--log", default=DEFAULT_LOG,
                   help=f"append all gate output here [{DEFAULT_LOG}]")
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
            # A lone positional written WITHOUT `--` is the whole gate as one shell-quoted
            # string, so it gets shlex-split and can carry a name= prefix, exactly like --gate.
            positional = gate_spec(args.rest[0])

    written = getattr(args, "written", None) or []
    if not any(option == "gate" for option, _ in written) and positional is None:
        p.error("no gate given: use --gate '<cmd>' or -- <cmd ...>")
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

    report = run_gates(gates, args.log, args.summary)
    print(format_report(report, args.log))
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
