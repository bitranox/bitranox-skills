# /// script
# requires-python = ">=3.10"
# ///
"""After a per-target fan-out, find text that landed in the WRONG target.

When N agents each work their own target (a repo, a package, a memory level), an agent can write
into a sibling's target and still report success naming its own: a sibling's package name in a
docstring, one level's descriptor written over another's. Every recorded incident was found only
from ground truth, never from the agents' reports. This is that ground-truth check.

For every target it reads only the lines that target GAINED - `git diff -U0` against `--since`
(default: the work tree plus the index against HEAD) plus every untracked, non-ignored file, since
`git diff` never shows a file created in the wrong place - and looks for the OTHER targets'
identifiers in them. Whole-file scanning is noise: old changelog entries legitimately name
dependencies. A target that is a plain file (a memory level's CLAUDE.local.md, which git ignores)
has every line treated as added.

Identifiers default to each target NAME in its snake_case, kebab-case and space-separated spellings,
case-insensitive, matched as a whole word (`alpha_library` is not `alpha_lib`), plus any
`--ident NAME=TOKEN`. A name the scanned target declares as a dependency in its pyproject.toml
(Python 3.11+, which reads TOML) is not a finding, nor is a `--allow NAME=TOKEN` for that target.

  `python3 scripts/fanout_crosscheck.py --target alpha_lib=../alpha_lib --target beta-tool=../beta-tool`
  `... --since beta-tool=<sha>`  per target, or `--since <rev>` for every target; repeatable
  add `--json` for the `{ok, command, data, skipped}` envelope (`ok` false exactly on exit 2)

It always reports how much it examined. Zero added lines across all targets is exit 2, never a
clean pass: a wrong `--since`, or a fan-out that changed nothing, would otherwise print a green
that means nothing.

Exit codes: 0 = nothing foreign found, 1 = findings (one line each: target, file:line, the foreign
target and the token, the line), 2 = a usage error (fewer than two targets, a name given twice, a
target that is neither a file nor a git work tree, a `--since` that does not resolve), a target
that could not be read, zero added lines, or an internal error.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _cli_envelope import (
    EXIT_ERROR,
    EXIT_NO,
    EXIT_YES,
    EnvelopeArgumentParser,
    emit,
    guarded,
)

try:
    import tomllib
except ImportError:  # Python 3.10: dependencies cannot be read, --allow still works
    tomllib = None  # type: ignore[assignment]

COMMAND = "fanout_crosscheck"
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_DEP_NAME = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


class CrosscheckError(ValueError):
    """Bad input or an unreadable target; exits 2 with nothing claimed."""


@dataclass
class Target:
    name: str
    path: Path
    since: str | None = None
    tokens: list[str] = field(default_factory=list)
    allowed: set[str] = field(default_factory=set)
    files: int = 0
    added: int = 0


def normalise(token: str) -> str:
    """The comparison form of a name: lower case, every run of - _ . or space one hyphen (PEP 503)."""
    return re.sub(r"[-_.\s]+", "-", token.strip().lower())


def spellings(name: str) -> list[str]:
    """NAME as snake_case, kebab-case and space-separated, one entry when it has a single part."""
    parts = [p for p in re.split(r"[-_\s]+", name.strip()) if p]
    return sorted({"_".join(parts), "-".join(parts), " ".join(parts)})


def _token_pattern(token: str) -> re.Pattern[str]:
    # A word character or hyphen on either side means a LONGER name: alpha_library, gamma-ray.
    return re.compile(r"(?<![\w-])" + re.escape(token) + r"(?![\w-])", re.IGNORECASE)


def added_lines_from_diff(diff: str):
    """Yield (file, line number, text) for every added line of a `git diff -U0` patch."""
    current, number = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = None if target == "/dev/null" else re.sub(r"^b/", "", target)
            continue
        hunk = _HUNK.match(line)
        if hunk:
            number = int(hunk.group(1))
            continue
        if current is not None and line.startswith("+"):
            yield current, number, line[1:]
            number += 1


def _git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=str(cwd),
                          capture_output=True, check=False)


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def _file_lines(path: Path, rel: str):
    raw = path.read_bytes()
    if b"\0" in raw:  # binary: no text to hold a name
        return
    for number, text in enumerate(_decode(raw).splitlines(), start=1):
        yield rel, number, text


def target_lines(target: Target):
    """Every (file, line, text) the target gained. Raises CrosscheckError when it cannot tell."""
    if target.path.is_file():
        yield from _file_lines(target.path, target.path.name)
        return
    if not target.path.is_dir():
        raise CrosscheckError(f"target {target.name}: {target.path} does not exist")
    if _git(["rev-parse", "--is-inside-work-tree"], target.path).returncode != 0:
        raise CrosscheckError(f"target {target.name}: {target.path} is not a git work tree "
                              "(pass a plain file to scan it whole)")
    base = target.since or "HEAD"
    if _git(["rev-parse", "--verify", "-q", f"{base}^{{commit}}"], target.path).returncode != 0:
        raise CrosscheckError(f"target {target.name}: {base!r} does not resolve to a commit there")
    diff = _git(["diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames", "--relative", base,
                 "--", "."], target.path)
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z"], target.path)
    if diff.returncode != 0 or untracked.returncode != 0:
        raise CrosscheckError(f"target {target.name}: git could not list its changes: "
                              f"{_decode(diff.stderr or untracked.stderr).strip()}")
    yield from added_lines_from_diff(_decode(diff.stdout))
    for rel in filter(None, _decode(untracked.stdout).split("\0")):
        yield from _file_lines(target.path / rel, rel)


def declared_dependencies(path: Path) -> tuple[set[str], str | None]:
    """Normalised dependency names from PATH/pyproject.toml, and a note when they were not read."""
    pyproject = path / "pyproject.toml" if path.is_dir() else None
    if pyproject is None or not pyproject.is_file():
        return set(), None
    if tomllib is None:
        return set(), f"{pyproject}: dependencies not read (Python 3.10 has no tomllib); use --allow"
    try:
        doc = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return set(), f"{pyproject}: dependencies not read ({exc})"
    project = doc.get("project", {})
    specs = list(project.get("dependencies", []))
    for group in list(project.get("optional-dependencies", {}).values()) + list(
            doc.get("dependency-groups", {}).values()):
        specs += [s for s in group if isinstance(s, str)]
    names = {_DEP_NAME.match(s).group(1) for s in specs if _DEP_NAME.match(s)}
    return {normalise(n) for n in names}, None


def _pairs(values, flag, form):
    for value in values or []:
        name, sep, rest = value.partition("=")
        if not sep or not name or not rest:
            raise CrosscheckError(f"{flag} takes {form}, got {value!r}")
        yield name, rest


def build_targets(args) -> tuple[list[Target], list[str]]:
    targets: dict[str, Target] = {}
    for name, path in _pairs(args.target, "--target", "NAME=PATH"):
        if name in targets:
            raise CrosscheckError(f"target {name} is given twice")
        targets[name] = Target(name, Path(path), tokens=spellings(name))
    if len(targets) < 2:
        raise CrosscheckError("give at least two --target NAME=PATH: one target has no siblings")
    for name, token in _pairs(args.ident, "--ident", "NAME=TOKEN"):
        _known(targets, name, "--ident").tokens.append(token)
    for name, token in _pairs(args.allow, "--allow", "NAME=TOKEN"):
        _known(targets, name, "--allow").allowed.add(normalise(token))
    for value in args.since or []:
        name, sep, rev = value.partition("=")
        if sep and name in targets:
            targets[name].since = rev
        else:
            for target in targets.values():
                target.since = target.since or value
    skipped = []
    for target in targets.values():
        deps, note = declared_dependencies(target.path)
        target.allowed |= deps
        if note:
            skipped.append(note)
    return list(targets.values()), skipped


def _known(targets, name, flag) -> Target:
    if name not in targets:
        raise CrosscheckError(f"{flag} names {name}, which is not a --target")
    return targets[name]


def crosscheck(targets: list[Target]) -> list[dict]:
    """Every added line in one target that holds another target's identifier."""
    patterns = {t.name: [(tok, _token_pattern(tok)) for tok in t.tokens] for t in targets}
    findings = []
    for scanned in targets:
        files = set()
        for rel, number, text in target_lines(scanned):
            files.add(rel)
            scanned.added += 1
            for other in targets:
                if other is scanned or normalise(other.name) in scanned.allowed:
                    continue
                hit = next((tok for tok, pat in patterns[other.name]
                            if pat.search(text) and normalise(tok) not in scanned.allowed), None)
                if hit:
                    findings.append({"target": scanned.name, "file": rel, "line": number,
                                     "foreign": other.name, "token": hit, "text": text})
        scanned.files = len(files)
    return findings


def _parse(argv):
    ap = EnvelopeArgumentParser(envelope_command=COMMAND, description=(
        "Find text that landed in the wrong target after a per-target fan-out."))
    ap.add_argument("--target", action="append", metavar="NAME=PATH", required=True,
                    help="repeatable, at least two; a git work tree (its added lines) or a plain "
                         "file (every line)")
    ap.add_argument("--since", action="append", metavar="[NAME=]REV",
                    help="compare against REV instead of HEAD; NAME=REV for one target")
    ap.add_argument("--ident", action="append", metavar="NAME=TOKEN",
                    help="another identifier of target NAME to look for")
    ap.add_argument("--allow", action="append", metavar="NAME=TOKEN",
                    help="TOKEN is not a finding inside target NAME")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    return ap.parse_args(argv)


def _harden_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass


@guarded(COMMAND)
def main(argv=None) -> int:
    """Run the check. An uncaught exception exits 2, never 1 (findings) or 0 (clean)."""
    args = _parse(argv)
    try:
        targets, skipped = build_targets(args)
        findings = crosscheck(targets)
    except (CrosscheckError, OSError) as exc:
        print(f"{COMMAND}: {exc}", file=sys.stderr)
        return emit(EXIT_ERROR, COMMAND, error=str(exc)) if args.json else EXIT_ERROR
    examined = {"targets": len(targets), "files": sum(t.files for t in targets),
                "added_lines": sum(t.added for t in targets)}
    data = {"examined": examined, "findings": findings,
            "targets": [{"name": t.name, "path": str(t.path), "since": t.since or "HEAD",
                         "files": t.files, "added_lines": t.added} for t in targets]}
    for note in skipped:
        print(f"{COMMAND}: {note}", file=sys.stderr)
    if examined["added_lines"] == 0:
        message = (f"0 added lines across {len(targets)} targets - a wrong --since, or nothing "
                   "changed, so there was nothing to check")
        print(f"{COMMAND}: {message}", file=sys.stderr)
        return emit(EXIT_ERROR, COMMAND, data, skipped=skipped, error=message) if args.json \
            else EXIT_ERROR
    code = EXIT_NO if findings else EXIT_YES
    if args.json:
        return emit(code, COMMAND, data, skipped=skipped)
    for f in findings:
        print(f"{f['target']}: {f['file']}:{f['line']}: {f['foreign']} ({f['token']}) | "
              f"{f['text'].strip()[:200]}")
    print(f"examined {examined['targets']} targets, {examined['files']} files, "
          f"{examined['added_lines']} added lines: {len(findings)} finding(s)")
    return code


if __name__ == "__main__":
    _harden_stdout()
    sys.exit(main())
