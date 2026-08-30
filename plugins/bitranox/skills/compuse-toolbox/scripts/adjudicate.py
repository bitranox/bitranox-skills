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

Run:
  `uv run scripts/adjudicate.py --hook hooks/some-guard.py \\
      --name "fires on a mention" --probe '{"tool_input":{"command":"echo x"}}' \\
                                  --control '{"tool_input":{"command":"echo y"}}'`
  `uv run scripts/adjudicate.py --hook hooks/some-guard.py --claim-file claims.jsonl --json`

Exit codes: 0 = every claim adjudicated (confirmed or refuted), 1 = at least one UNUSABLE,
2 = usage or IO error. `--json` emits the machine-readable envelope on every path.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field

FIRED_MODES = ("output", "nonzero", "match")


@dataclass(frozen=True)
class Run:
    """What the subject actually did on one input."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


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
            encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        # A hung subject is not a silent zero: name it so it cannot read as "did not fire".
        return Run(returncode=124, stderr=f"adjudicate: timed out after {timeout}s")
    except OSError as exc:
        return Run(returncode=126, stderr=f"adjudicate: cannot run subject: {exc}")
    return Run(completed.returncode, completed.stdout or "", completed.stderr or "")


def adjudicate(subject: list[str], claims: list[Claim], mode: str, pattern: str | None,
               timeout: float = 60.0) -> list[Adjudication]:
    """Score every claim by running BOTH sides. Never one side."""
    results = []
    for claim in claims:
        probe_run = run_once(subject, claim.probe, claim.probe_args, timeout)
        control_run = run_once(subject, claim.control, claim.control_args, timeout)
        p_fired = fired(probe_run, mode, pattern)
        c_fired = fired(control_run, mode, pattern)
        results.append(Adjudication(claim.name, verdict_for(p_fired, c_fired),
                                    probe_run, control_run, p_fired, c_fired))
    return results


def summarize(results: list[Adjudication]) -> dict:
    """Counts per bucket, plus `ok` - which is FALSE when any control failed to discriminate.

    `ok` deliberately does not mean "the claims were confirmed". A run where every claim is refuted
    worked perfectly; a run with one UNUSABLE did not measure what it reports.
    """
    unusable = [r.name for r in results if r.verdict == "UNUSABLE"]
    return {
        "total": len(results),
        "confirmed": sum(1 for r in results if r.verdict == "CONFIRMED"),
        "refuted": sum(1 for r in results if r.verdict == "REFUTED"),
        "unusable": len(unusable),
        "unusable_names": unusable,
        "confirmed_names": [r.name for r in results if r.verdict == "CONFIRMED"],
        "ok": not unusable,
    }


def load_claims(claim_file, name, probe, control) -> list[Claim]:
    """Build the claim list from a JSONL file and/or one inline claim.

    A line without both `probe` and `control` raises ValueError rather than defaulting the missing
    side: a claim with no control is not a weaker claim, it is an unscoreable one.
    """
    claims: list[Claim] = []
    if claim_file:
        with open(claim_file, encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict) or "probe" not in obj or "control" not in obj:
                    raise ValueError(
                        f"{claim_file}:{number}: a claim needs both 'probe' and 'control'")
                claims.append(Claim(name=obj.get("name") or f"line{number}",
                                    probe=obj["probe"], control=obj["control"],
                                    probe_args=list(obj.get("probe_args", [])),
                                    control_args=list(obj.get("control_args", []))))
    if probe is not None or control is not None:
        if probe is None or control is None:
            raise ValueError("--probe and --control must be given together")
        claims.append(Claim(name=name or "claim", probe=probe, control=control))
    return claims


def _report(results: list[Adjudication], summary: dict) -> None:
    """The human view. Every UNUSABLE line says what to do, because the verdict is about the
    instrument rather than about the claim."""
    for result in results:
        print(f"  {result.verdict:9}  {result.name}")
        if result.verdict == "UNUSABLE":
            print("             control fired too - it does not differ from the probe in the "
                  "claimed way. Fix the control and re-run.")
    print(f"\n  {summary['confirmed']} confirmed, {summary['refuted']} refuted, "
          f"{summary['unusable']} unusable, of {summary['total']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Score a claim about a guard by running it on a probe AND a control.")
    parser.add_argument("--hook", help="a hook/script path, run with the current interpreter")
    parser.add_argument("--name", help="name for the inline claim")
    parser.add_argument("--probe", help="stdin for the run that is claimed to FIRE")
    parser.add_argument("--control", help="stdin for the run that is claimed NOT to fire")
    parser.add_argument("--claim-file", help="JSONL: one {name, probe, control} per line")
    parser.add_argument("--fired-when", choices=FIRED_MODES, default="output",
                        help="what counts as firing (default: any output on stdout/stderr)")
    parser.add_argument("--fired-pattern", help="regex, required when --fired-when match")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--json", action="store_true", help="emit the machine-readable envelope")
    args = parser.parse_args(argv)

    if not args.hook:
        print("adjudicate: no subject - pass --hook <path>", file=sys.stderr)
        return 2
    if args.fired_when == "match" and not args.fired_pattern:
        print("adjudicate: --fired-when match needs --fired-pattern", file=sys.stderr)
        return 2

    try:
        claims = load_claims(args.claim_file, args.name, args.probe, args.control)
    except OSError as exc:
        print(f"adjudicate: cannot read --claim-file {args.claim_file!r}: {exc}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"adjudicate: {exc}", file=sys.stderr)
        return 2
    if not claims:
        print("adjudicate: no claims - pass --probe/--control or --claim-file", file=sys.stderr)
        return 2

    results = adjudicate(subject_for_hook(args.hook), claims, args.fired_when,
                         args.fired_pattern, timeout=args.timeout)
    summary = summarize(results)

    if not summary["ok"]:
        # Always stderr, --json included, so stdout stays a clean parseable envelope.
        print(f"adjudicate: {summary['unusable']} claim(s) UNUSABLE - the control fired too, so "
              f"these were never actually tested: {', '.join(summary['unusable_names'])}. "
              f"Do NOT read them as refuted.", file=sys.stderr)

    if args.json:
        print(json.dumps({"ok": summary["ok"], "command": "adjudicate", "skipped": [],
                          "data": {"summary": summary,
                                   "results": [asdict(r) for r in results]}}, indent=2))
    else:
        _report(results, summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
