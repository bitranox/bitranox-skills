# /// script
# requires-python = ">=3.10"
# ///
"""Is this claim about a guard REAL? Run the subject on a probe and a CONTROL, and score the pair.

The mistake this replaces: confirming a claim by running the ONE input that shows it. A guard that
fires on your probe has told you nothing until you know it does NOT fire on an input differing only
in the thing claimed. Without that second run "it fired" and "it fires on everything" are the same
observation, and the second one is a broken instrument reporting a finding.

So a claim is scored only when the probe and the control DISAGREE in the claimed direction, and the
outcome has THREE buckets rather than two:

    CONFIRMED   probe fired, control did not      - the claim holds and the control discriminates
    REFUTED     probe did not fire                - the claim is wrong, whatever the control did
    UNUSABLE    probe fired AND control fired     - the control did not discriminate, so this run
                                                    says nothing; fix the control and re-run

plus ERROR when the HARNESS could not run a side at all (it timed out, or the subject could not be
launched). That is not a firing: a hung probe scored as "fired" would read as CONFIRMED.

When EVERY claim comes back UNUSABLE the fault is usually the SUBJECT rather than the controls: it
fires on every input it is given, and under the default `--fired-when output` a banner it always
prints counts as firing. The report says which of the two it is, because the fix differs.

UNUSABLE is the bucket that keeps getting lost. Folding it into REFUTED reads as a clean sweep and
is how one pass reported 10 claims refuted where the truth was 7 refuted plus 3 never actually
tested. The exit code is built around that: any UNUSABLE claim makes the whole run exit 1, so a
report cannot be read as "all clear" when its controls were broken.

Re-run it after every fix. A fix that makes the suite green has not necessarily closed the finding -
that has happened twice - and this is the instrument that tells the difference.

Typical uses:
  * adjudicating review claims about a PreToolUse hook, one JSON payload per side
  * checking a guard you just fixed still fires on the case it was built for
  * proving a "false positive" report is real before changing anything

Run (plain python3, NOT uv run: the subject runs on THIS interpreter, and under uv run that is uv's
throwaway env, where a hook's optional imports such as PyYAML or lxml are missing, so it degrades in
a way it never does under hooks/run-python.sh in production):
  `python3 scripts/adjudicate.py --hook hooks/some-guard.py \\
      --name "fires on a mention" --probe '{"tool_input":{"command":"echo x"}}' \\
                                  --control '{"tool_input":{"command":"echo y"}}'`
  `python3 scripts/adjudicate.py --hook hooks/some-guard.py --claim-file claims.jsonl --json`

The subject gets the UTF-8 environment run-python.sh exports (PYTHONUTF8=1,
PYTHONIOENCODING=utf-8). `--timeout` is seconds per side and must be a positive finite number.

In a claim file, `probe`/`control` are a string or a JSON object (sent as its JSON text), and the
optional `probe_args`/`control_args` are lists of strings.

Exit codes: 0 = every claim adjudicated (confirmed or refuted), 1 = at least one UNUSABLE,
2 = usage or IO error, or at least one ERROR claim. `--json` emits the machine-readable envelope
on every path; a usage error gives `{"ok": false, "data": {"reason": ...}}`.
"""
from __future__ import annotations

# Run with plain python3, never `uv run`: the subject runs on sys.executable, which under uv run is
# uv's throwaway env without the optional deps a hook degrades without. toolbox-nudge reads this.
LAUNCH_WITH = "python3"

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

FIRED_MODES = ("output", "nonzero", "match")

# What hooks/run-python.sh exports before it execs a hook, so the subject decodes and encodes as it
# does in production rather than under whatever locale codec the caller happens to have.
_SHIM_ENV = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


@dataclass(frozen=True)
class Run:
    """What the subject actually did on one input."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    # Set only when the HARNESS failed (timeout, launch failure); the subject's own exit code is data.
    harness_error: str | None = None


@dataclass(frozen=True)
class Claim:
    """One claim: the subject is said to fire on `probe` and not on `control`.

    The control is REQUIRED, not optional. A claim with no control cannot be scored, and making it
    default to the empty string would silently turn every such claim into a one-sided probe - the
    exact failure this tool exists to prevent.
    """

    name: str
    probe: str
    control: str
    probe_args: list[str] = field(default_factory=list)
    control_args: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Adjudication:
    """One claim's verdict, with both runs kept so a reader can check the scoring."""

    name: str
    verdict: str
    probe_run: Run
    control_run: Run
    probe_fired: bool
    control_fired: bool


class UsageError(Exception):
    """A bad invocation or unreadable input; main reports it and exits 2."""


def verdict_for(probe_fired: bool, control_fired: bool) -> str:
    """The three-bucket score. This is the whole point of the tool.

    Note the asymmetry: a probe that did not fire is REFUTED whatever the control did, because the
    claim said the probe fires. Only when the probe DID fire does the control get a say, and then a
    control that also fired makes the run unusable rather than confirming anything.
    """
    if not probe_fired:
        return "REFUTED"
    if control_fired:
        return "UNUSABLE"
    return "CONFIRMED"


def fired(run: Run, mode: str, pattern: str | None) -> bool:
    """Did the subject FIRE on this input? What that means depends on the guard.

    A blocking guard fires by exiting non-zero; a nudge fires by writing additionalContext and
    exiting 0. `output` covers both and is the default. `match` is for a subject that always writes
    something, where only a particular line counts.
    """
    if mode == "nonzero":
        return run.returncode != 0
    if mode == "match":
        return bool(re.search(pattern or "", run.stdout + "\n" + run.stderr))
    return bool((run.stdout + run.stderr).strip())


def subject_for_hook(path) -> list[str]:
    """argv for running a hook script with the CURRENT interpreter.

    An argv LIST, never a command string: a string would have to be split, and the splitting rules
    differ between POSIX and Windows in ways that eat backslashes out of a path. There is nothing
    to split here, so that whole class of bug is unreachable.
    """
    return [sys.executable, str(path)]


def run_once(subject: list[str], stdin: str, args: list[str], timeout: float = 60.0) -> Run:
    """Run the subject once, feeding `stdin`, and capture everything it did."""
    try:
        completed = subprocess.run(
            [*subject, *args], input=stdin, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, env={**os.environ, **_SHIM_ENV})
    except subprocess.TimeoutExpired:
        # A hung subject is neither "fired" nor "did not fire": mark it so the claim scores ERROR.
        message = f"adjudicate: timed out after {timeout}s"
        return Run(returncode=124, stderr=message, harness_error=message)
    except OSError as exc:
        message = f"adjudicate: cannot run subject: {exc}"
        return Run(returncode=126, stderr=message, harness_error=message)
    return Run(completed.returncode, completed.stdout or "", completed.stderr or "")


def adjudicate(subject: list[str], claims: list[Claim], mode: str, pattern: str | None,
               timeout: float = 60.0) -> list[Adjudication]:
    """Score every claim by running BOTH sides. Never one side."""
    results = []
    for claim in claims:
        probe_run = run_once(subject, claim.probe, claim.probe_args, timeout)
        control_run = run_once(subject, claim.control, claim.control_args, timeout)
        if probe_run.harness_error or control_run.harness_error:
            results.append(Adjudication(claim.name, "ERROR", probe_run, control_run, False, False))
            continue
        p_fired = fired(probe_run, mode, pattern)
        c_fired = fired(control_run, mode, pattern)
        results.append(Adjudication(claim.name, verdict_for(p_fired, c_fired),
                                    probe_run, control_run, p_fired, c_fired))
    return results


def summarize(results: list[Adjudication]) -> dict:
    """Counts per bucket, plus `ok` - which is FALSE when any control failed to discriminate or
    any claim could not be run at all.

    `ok` deliberately does not mean "the claims were confirmed". A run where every claim is refuted
    worked perfectly; a run with one UNUSABLE or ERROR did not measure what it reports.
    """
    unusable = [r.name for r in results if r.verdict == "UNUSABLE"]
    errors = [r.name for r in results if r.verdict == "ERROR"]
    return {
        "total": len(results),
        "confirmed": sum(1 for r in results if r.verdict == "CONFIRMED"),
        "refuted": sum(1 for r in results if r.verdict == "REFUTED"),
        "unusable": len(unusable),
        "unusable_names": unusable,
        "confirmed_names": [r.name for r in results if r.verdict == "CONFIRMED"],
        "error": len(errors),
        "error_names": errors,
        "ok": not unusable and not errors,
    }


def _stdin_payload(value, where: str, key: str) -> str:
    """A side's stdin: a string as-is, a JSON object (a hook payload) as its JSON text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value)
    raise ValueError(f"{where}: '{key}' must be a string or a JSON object, not {type(value).__name__}")


def _argv_list(value, where: str, key: str) -> list[str]:
    """Extra argv for a side. A bare string is refused: list("--flag") is single characters."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{where}: '{key}' must be a list of strings")
    return list(value)


def _claim_from_line(line: str, where: str, number: int) -> Claim:
    obj = json.loads(line)
    if not isinstance(obj, dict) or "probe" not in obj or "control" not in obj:
        raise ValueError(f"{where}: a claim needs both 'probe' and 'control'")
    return Claim(name=str(obj.get("name") or f"line{number}"),
                 probe=_stdin_payload(obj["probe"], where, "probe"),
                 control=_stdin_payload(obj["control"], where, "control"),
                 probe_args=_argv_list(obj.get("probe_args", []), where, "probe_args"),
                 control_args=_argv_list(obj.get("control_args", []), where, "control_args"))


def load_claims(claim_file, name, probe, control) -> list[Claim]:
    """Build the claim list from a JSONL file and/or one inline claim.

    A line without both `probe` and `control` raises ValueError rather than defaulting the missing
    side: a claim with no control is not a weaker claim, it is an unscoreable one.
    """
    claims: list[Claim] = []
    if claim_file:
        # utf-8-sig: a claim file written by Windows PowerShell 5.1 starts with a BOM.
        with open(claim_file, encoding="utf-8-sig") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if line:
                    claims.append(_claim_from_line(line, f"{claim_file}:{number}", number))
    if probe is not None or control is not None:
        if probe is None or control is None:
            raise ValueError("--probe and --control must be given together")
        claims.append(Claim(name=name or "claim", probe=probe, control=control))
    return claims


def unusable_cause(summary: dict) -> str | None:
    """Which end is at fault when claims come back UNUSABLE - "control", "subject", or None.

    Both causes produce the identical verdict, and naming only the first sends a reader to fix a
    control that was never wrong. They are separable by COUNT rather than by inspection: one claim
    unusable among several is a control that does not differ in the claimed way, while EVERY claim
    unusable means the subject fired on every input it was given - which under the default
    `--fired-when output` is what a program that prints a banner unconditionally looks like.

    Two claims is the smallest sample that can show a pattern, so a lone unusable claim is still
    reported against the control: with one data point there is nothing to distinguish.
    """
    if not summary["unusable"]:
        return None
    if summary["unusable"] == summary["total"] and summary["total"] > 1:
        return "subject"
    return "control"


def _report(results: list[Adjudication], summary: dict) -> None:
    """The human view. Every UNUSABLE line says what to do, because the verdict is about the
    instrument rather than about the claim."""
    for result in results:
        print(f"  {result.verdict:9}  {result.name}")
        if result.verdict == "UNUSABLE":
            print("             control fired too - it does not differ from the probe in the "
                  "claimed way. Fix the control and re-run.")
        if result.verdict == "ERROR":
            cause = result.probe_run.harness_error or result.control_run.harness_error
            print(f"             {cause} - nothing was measured.")
    print(f"\n  {summary['confirmed']} confirmed, {summary['refuted']} refuted, "
          f"{summary['unusable']} unusable, {summary['error']} error, of {summary['total']}")


def _warn(summary: dict) -> None:
    """Always stderr, --json included, so stdout stays a clean parseable envelope."""
    if summary["error"]:
        print(f"adjudicate: {summary['error']} claim(s) ERROR - the harness could not run a side "
              f"(timed out, or the subject could not be launched), so nothing was measured: "
              f"{', '.join(summary['error_names'])}. Do NOT read them as confirmed or refuted.",
              file=sys.stderr)
    if not summary["unusable"]:
        return
    if unusable_cause(summary) == "subject":
        print(f"adjudicate: ALL {summary['total']} claim(s) UNUSABLE - the subject fired on "
              f"every input, including every control, so nothing was measured. That is usually "
              f"the subject rather than the controls: under --fired-when output any banner it "
              f"always prints counts as firing. Try --fired-when nonzero, or --fired-when "
              f"match with --fired-pattern. Do NOT read these as refuted.", file=sys.stderr)
    else:
        print(f"adjudicate: {summary['unusable']} claim(s) UNUSABLE - the control fired too, so "
              f"these were never actually tested: {', '.join(summary['unusable_names'])}. "
              f"Do NOT read them as refuted.", file=sys.stderr)


class _Parser(argparse.ArgumentParser):
    """An argparse error becomes a UsageError, so --json can still emit its envelope."""

    def error(self, message):
        raise UsageError(message)


def _positive_seconds(text: str) -> float:
    """--timeout as a positive finite float. nan and inf crashed inside subprocess with a traceback
    and exit 1 - the code this tool reserves for UNUSABLE - and 0 or a negative ran every side
    into an instant timeout that was then reported as ERROR claims rather than a bad argument."""
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive finite number of seconds: {text!r}")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(
        description="Score a claim about a guard by running it on a probe AND a control.")
    parser.add_argument("--hook", help="a hook/script path, run with the current interpreter")
    parser.add_argument("--name", help="name for the inline claim")
    parser.add_argument("--probe", help="stdin for the run that is claimed to FIRE")
    parser.add_argument("--control", help="stdin for the run that is claimed NOT to fire")
    parser.add_argument("--claim-file", help="JSONL: one {name, probe, control} per line")
    parser.add_argument("--fired-when", choices=FIRED_MODES, default="output",
                        help="what counts as firing (default: any output on stdout/stderr)")
    parser.add_argument("--fired-pattern", help="regex, required when --fired-when match")
    parser.add_argument("--timeout", type=_positive_seconds, default=60.0,
                        help="seconds per side, a positive finite number (default: 60)")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable envelope")
    return parser


def _validate(args) -> list[Claim]:
    """Everything checkable BEFORE a subject runs; raises UsageError."""
    if not args.hook:
        raise UsageError("no subject - pass --hook <path>")
    if not Path(args.hook).is_file():
        raise UsageError(f"--hook {args.hook!r} is not a file")
    if args.fired_when == "match" and not args.fired_pattern:
        raise UsageError("--fired-when match needs --fired-pattern")
    if args.fired_pattern is not None:
        try:
            re.compile(args.fired_pattern)
        except re.error as exc:
            raise UsageError(f"--fired-pattern is not a valid regex: {exc}") from exc
    try:
        claims = load_claims(args.claim_file, args.name, args.probe, args.control)
    except OSError as exc:
        raise UsageError(f"cannot read --claim-file {args.claim_file!r}: {exc}") from exc
    except ValueError as exc:  # json.JSONDecodeError is a ValueError
        raise UsageError(str(exc)) from exc
    if not claims:
        raise UsageError("no claims - pass --probe/--control or --claim-file")
    return claims


def _usage_failure(reason: str, as_json: bool) -> int:
    print(f"adjudicate: {reason}", file=sys.stderr)
    if as_json:
        print(json.dumps({"ok": False, "command": "adjudicate", "skipped": [],
                          "data": {"reason": reason}}, indent=2))
    return 2


def _reconfigure_streams() -> None:
    """A cp1252 console or pipe must print '?' for an unencodable claim name, not crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                pass


def main(argv=None) -> int:
    _reconfigure_streams()
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw)
    except UsageError as exc:
        # SystemExit(2) keeps argparse's contract for callers; the envelope is printed first.
        raise SystemExit(_usage_failure(str(exc), "--json" in raw)) from exc
    try:
        claims = _validate(args)
    except UsageError as exc:
        return _usage_failure(str(exc), args.json)

    results = adjudicate(subject_for_hook(args.hook), claims, args.fired_when,
                         args.fired_pattern, timeout=args.timeout)
    summary = summarize(results)
    _warn(summary)

    if args.json:
        print(json.dumps({"ok": summary["ok"], "command": "adjudicate", "skipped": [],
                          "data": {"summary": summary,
                                   "results": [asdict(r) for r in results]}}, indent=2))
    else:
        _report(results, summary)
    if summary["error"]:
        return 2
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
