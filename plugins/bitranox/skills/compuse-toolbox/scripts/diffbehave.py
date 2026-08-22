# /// script
# requires-python = ">=3.10"
# ///
"""Do two implementations BEHAVE the same on the same inputs? Run both, diff what they actually did.

The mistake this replaces: judging "does this behave differently" by LOOKING at the two versions -
an `ast.dump` comparison (identifier-sensitive, so a rename alone reads as a behaviour change), a
line count, a `grep -c`. None of those execute anything, so none of them can answer the question.
The only way to answer it is differential EXECUTION: run both sides on the same input and compare
what actually happened.

The second half of the tool is `--expect-differ`: a detector you hand-roll to verify your own work
must be run against a KNOWN NEGATIVE and required to say DIFFER. A comparison that reports AGREE for
every input it is ever given has proved nothing, and it looks exactly like a pass. So the tool can be
told how many cases MUST differ, and it fails when they do not.

Typical uses:
  * a retired implementation vs its replacement: feed both the same synthetic inputs and compare
    verdicts, across the real cases AND the ones that must NOT fire
  * before/after a refactor: same inputs, same outputs?
  * two CLIs that are supposed to be equivalent

Run:
  `uv run scripts/diffbehave.py --a "python3 old.py" --b "python3 new.py" --case-file cases.jsonl`
  `uv run scripts/diffbehave.py --a "python3 hook_old.py" --b "python3 hook_new.py" \\
      --case '{"x":1}' --expect-differ 1`

Exit codes: 0 = expectation met, 1 = expectation not met (or nothing differed when it had to),
2 = usage/IO error. `--json` emits the machine-readable envelope.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Run:
    """What one side actually did."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class Case:
    """One input fed identically to both sides."""

    name: str
    stdin: str = ""
    args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CaseResult:
    name: str
    verdict: str
    a: Run
    b: Run


def _norm(text: str) -> str:
    """Trailing whitespace is formatting, not behaviour - comparing it makes every run differ."""
    return "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()


def verdict(a: Run, b: Run) -> str:
    """AGREE when exit code, stdout and stderr all match; DIFFER otherwise.

    stderr is compared on purpose: a guard's whole output is its refusal message, so two guards
    that both exit 2 with different reasons are NOT equivalent.
    """
    same = (a.returncode == b.returncode
            and _norm(a.stdout) == _norm(b.stdout)
            and _norm(a.stderr) == _norm(b.stderr))
    return "AGREE" if same else "DIFFER"


def _split_command(command: str, windows: bool | None = None) -> list[str]:
    """Split a command string into argv, honouring the platform's quoting rules.

    shlex.split defaults to POSIX mode, where a backslash ESCAPES the next character. On Windows
    that silently eats the separators in a program path: "C:\\tools\\py.exe" becomes
    "C:toolspy.exe", the command cannot start, and BOTH sides of a comparison then fail the same
    way - so diffbehave reported AGREE for a command that never ran.

    Turning escape processing off keeps quoting working while a backslash stays a separator.
    Non-POSIX mode was the earlier fix; it leaves quotes attached to the token, so `--opt="a b"`
    came apart into '--opt="a' + 'b"'. It survives only as the fallback for the C runtime's
    `"a\\"b"` convention, which escape-off reads as an unbalanced quote. gate.py and
    hooks/harness_checks.py carry the same pair for the same reason.
    """
    on_windows = (os.name == "nt") if windows is None else windows
    if not on_windows:
        return shlex.split(command)
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    try:
        return list(lexer)
    except ValueError:
        out = []
        for token in shlex.split(command, posix=False):
            if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
                token = token[1:-1]
            out.append(token)
        return out


def _run_one(command: str, case: Case, timeout: float) -> Run:
    """Execute one side. A command that cannot start is a RESULT, never an exception.

    `encoding="utf-8", errors="replace"` is explicit: with no encoding, capture decodes with the
    machine's locale codec, which fails differently per platform - stdout can come back None on
    Windows, and POSIX raises past a handler that only catches OSError.
    """
    argv = _split_command(command) + list(case.args)
    try:
        proc = subprocess.run(argv, input=case.stdin, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, check=False)
    except FileNotFoundError as exc:
        return Run(returncode=127, stderr=str(exc))
    except subprocess.TimeoutExpired:
        return Run(returncode=124, stderr=f"timeout after {timeout}s")
    except OSError as exc:
        return Run(returncode=126, stderr=str(exc))
    return Run(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def compare(command_a: str, command_b: str, cases: list[Case], timeout: float = 60.0) -> list[CaseResult]:
    """Run every case through both sides and judge each."""
    results = []
    for case in cases:
        a = _run_one(command_a, case, timeout)
        b = _run_one(command_b, case, timeout)
        results.append(CaseResult(name=case.name, verdict=verdict(a, b), a=a, b=b))
    return results


def summarize(results: list[CaseResult]) -> dict:
    """Counts plus the names that differed - the part a reader acts on."""
    differing = [r.name for r in results if r.verdict == "DIFFER"]
    return {
        "total": len(results),
        "agree": sum(1 for r in results if r.verdict == "AGREE"),
        "differ": len(differing),
        "any_differ": bool(differing),
        "differing": differing,
    }


def meets_expectation(summary: dict, expect_differ: int) -> bool:
    """False when fewer cases differed than required - the known-negative check."""
    return summary["differ"] >= expect_differ


def _load_cases(args) -> list[Case]:
    """Build the case list. A missing/unreadable --case-file raises OSError - the caller turns
    that into a typed exit-2 error rather than a traceback."""
    cases: list[Case] = []
    for i, payload in enumerate(args.case or []):
        cases.append(Case(name=f"case{i + 1}", stdin=payload))
    if args.case_file:
        with open(args.case_file, encoding="utf-8") as fh:
            raw_lines = fh.readlines()
        for i, line in enumerate(raw_lines):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                cases.append(Case(name=f"line{i + 1}", stdin=line))
                continue
            if isinstance(obj, dict) and ("stdin" in obj or "args" in obj):
                cases.append(Case(name=obj.get("name") or f"line{i + 1}",
                                  stdin=obj.get("stdin", ""), args=list(obj.get("args", []))))
            else:
                cases.append(Case(name=f"line{i + 1}", stdin=line))
    return cases


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run two commands on the same inputs and diff what they did.")
    ap.add_argument("--a", required=True, help="the first command (shell-quoted, no shell used)")
    ap.add_argument("--b", required=True, help="the second command")
    ap.add_argument("--case", action="append", help="an input fed to stdin (repeatable)")
    ap.add_argument("--case-file", help="JSONL: one {name, stdin, args} per line, or raw lines")
    ap.add_argument("--expect-differ", type=int, default=0,
                    help="require at least N cases to DIFFER (the known-negative check)")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--json", action="store_true", help="emit the machine-readable envelope")
    args = ap.parse_args(argv)

    try:
        cases = _load_cases(args)
    except OSError as exc:
        print(f"diffbehave: cannot read --case-file {args.case_file!r}: {exc}", file=sys.stderr)
        return 2
    if not cases:
        print("diffbehave: no cases - pass --case or --case-file", file=sys.stderr)
        return 2

    results = compare(args.a, args.b, cases, timeout=args.timeout)
    summary = summarize(results)
    ok = meets_expectation(summary, args.expect_differ)

    if args.expect_differ and not ok:
        # Always to stderr, --json included, so stdout stays a clean parseable envelope.
        print(f"diffbehave: FAILED - required at least {args.expect_differ} case(s) to DIFFER, got "
              f"{summary['differ']}. A comparison that never says DIFFER has proved nothing.",
              file=sys.stderr)

    if args.json:
        print(json.dumps({"ok": ok, "command": "diffbehave", "skipped": [],
                          "data": {"summary": summary,
                                   "results": [asdict(r) for r in results]}}, indent=2))
    else:
        for r in results:
            print(f"  {r.verdict:6}  {r.name}")
            if r.verdict == "DIFFER":
                print(f"           a: rc={r.a.returncode} out={_norm(r.a.stdout)[:70]!r} "
                      f"err={_norm(r.a.stderr)[:70]!r}")
                print(f"           b: rc={r.b.returncode} out={_norm(r.b.stdout)[:70]!r} "
                      f"err={_norm(r.b.stderr)[:70]!r}")
        print(f"\n  {summary['agree']}/{summary['total']} agree, {summary['differ']} differ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
