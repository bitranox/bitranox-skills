# /// script
# requires-python = ">=3.10"
# ///
"""Would this push publish something private? Answer BEFORE pushing, not after.

Publishing is the irreversible direction. A local path, an internal hostname or an operator's
username that reaches a public repo stays in its public history even after the file is fixed,
because scrubbing it needs a force-push - which breaks every clone that already fetched.

Two things make this a tool rather than a habit:

1. **Visibility comes from the REMOTE, never from the directory name.** A tree that sorts repos
   into `public/` and `private/` folders is a filing convention, not a fact about GitHub, and it
   drifts: measured, a folder named `public/...` held a PRIVATE repo. A name-based guess is
   wrong in both directions - it also calls a public repo private and waves the scan through,
   which is the direction that publishes.
2. **Every non-answer fails CLOSED.** Unknown visibility, an unreadable range and an EMPTY range
   are refusals. A gate that reports "no findings" after examining nothing is indistinguishable
   from one that works, so this one always states how many lines it read and treats zero as a
   refusal.

Only ADDED lines are scanned. A `-` line is content leaving the repo, and flagging it would make
a cleanup commit unpushable, which is backwards.

Documentation-safe values are deliberately NOT findings: the RFC5737 ranges (192.0.2.0/24,
198.51.100.0/24, 203.0.113.0/24), `example.com`/`.test`/`.invalid`, loopback, and placeholder
home paths like `/home/user/`. Flagging those trains a reader to skim the report, which is how a
real finding gets waved through.

The pattern list is a FLOOR, never a proof. It cannot know your infrastructure's names, so pass
them with --denylist-file (one term per line); the file is yours and is never shipped, which is
what lets this tool be public while the terms stay private.

Run:
  `uv run scripts/pushcheck.py --repo . --json`
  `uv run scripts/pushcheck.py --range origin/main..HEAD --denylist-file ~/.config/infra.txt`
  `uv run scripts/pushcheck.py --visibility public --range HEAD~3..HEAD`   (skip the gh lookup)

Exit codes: 0 = safe to push, 1 = a PUBLIC repo's range carries private-looking content,
2 = refused to answer (unknown visibility, empty range, bad arguments, git or gh failure).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

__all__ = ["Finding", "Verdict", "parse_remote", "scan_text", "scan_diff", "decide"]

# A remote URL in any of the shapes git accepts. Owner and repo are what the visibility lookup
# needs; the host decides whether we can ask at all.
_SCP_RX = re.compile(r"^(?:(?P<user>[^@/]+)@)?(?P<host>[^:/@]+):(?P<path>[^:].*)$")
_URL_RX = re.compile(r"^[a-z][a-z0-9+.-]*://(?:[^@/]+@)?(?P<host>[^:/]+)(?::\d+)?/(?P<path>.+)$")

# Absolute paths that carry local layout. Deliberately not "every absolute path": /usr/bin/python3
# belongs in documentation, and flagging it would bury the findings that matter.
_ABS_RX = re.compile(
    r"(?P<hit>(?:/home/|/Users/|/root/|/media/|/mnt/|/srv/)[A-Za-z0-9._-]+"
    r"|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+)")
# Home directories written as documentation. `alice` is NOT here on purpose: a real-looking name
# is a candidate for a human to clear, and the cost of clearing one is a sentence.
_PLACEHOLDER_USERS = {"user", "username", "youruser", "you", "me", "example", "USER", "$USER"}

# A host is a finding when its TLD says "not on the public internet".
_INTERNAL_TLDS = {"internal", "local", "lan", "home", "corp", "intranet", "private", "localdomain"}
_HOST_RX = re.compile(r"\b(?P<host>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
                      r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+)\b")
_DOC_DOMAINS = ("example.com", "example.net", "example.org", "example.test", "example.invalid")
_DOC_TLDS = {"test", "invalid", "example"}

_IPV4_RX = re.compile(r"\b(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\b")
# RFC5737 exists so an address can be written down. Treating one as a leak is a false positive
# with a real cost: it is the kind that makes people pass --no-verify.
_DOC_NETS = ("192.0.2.", "198.51.100.", "203.0.113.")


@dataclass(frozen=True)
class Finding:
    """One private-looking value, located well enough to open the file and look."""

    kind: str
    file: str
    line: int
    text_excerpt: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "file": self.file, "line": self.line,
                "excerpt": self.text_excerpt}


@dataclass(frozen=True)
class Verdict:
    """The answer, plus how much was read to reach it - the second half is not optional."""

    ok: bool
    exit_code: int
    reason: str
    examined_lines: int
    visibility: str | None = None
    findings: list[Finding] = field(default_factory=list)
    unused_exclusions: list[str] = field(default_factory=list)


def parse_remote(url: str) -> tuple[str, str, str] | None:
    """(host, owner, repo) for a remote URL, or None when it names no owner/repo pair.

    None is a real answer and not a parse failure to paper over: a filesystem remote genuinely
    has no visibility to look up, and inventing an owner would produce a confident wrong one.
    """
    raw = (url or "").strip()
    if not raw:
        return None
    m = _URL_RX.match(raw) or _SCP_RX.match(raw)
    if not m:
        return None
    path = m.group("path").strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    return (m.group("host"), parts[-2], parts[-1])


def _abs_path_hits(line: str) -> list[str]:
    out = []
    for m in _ABS_RX.finditer(line):
        hit = m.group("hit")
        tail = re.split(r"[/\\]", hit)[-1]
        if tail not in _PLACEHOLDER_USERS:
            out.append(hit)
    return out


def _looks_like_a_host(labels: list[str]) -> bool:
    """Whether a dotted name is host-shaped rather than attribute access.

    `Path.home()`, `self.local` and `settings.home` are shaped exactly like domains, and an
    internal TLD set that does not exclude them reports them - measured on this repo's own
    history. That false positive is not cosmetic: a report the reader learns to skim is how the
    one real finding gets waved through. So a host must LOOK like one, either by carrying a digit
    or hyphen in its first label or by having three or more labels. The cost is a plain
    two-label name like `db.internal`, which the --denylist-file covers and which is why this
    pattern set is documented as a floor rather than a proof.
    """
    if len(labels) >= 3:
        return True
    first = labels[0]
    return any(c.isdigit() or c == "-" for c in first)


def _hostname_hits(line: str) -> list[str]:
    out = []
    for m in _HOST_RX.finditer(line):
        host = m.group("host")
        low = host.lower()
        if low.endswith(_DOC_DOMAINS) or low.split(".")[-1] in _DOC_TLDS:
            continue
        if line[m.end():m.end() + 1] == "(":          # a method call, not a host
            continue
        labels = low.split(".")
        if labels[-1] in _INTERNAL_TLDS and _looks_like_a_host(labels):
            out.append(host)
    return out


def _private_ip_hits(line: str) -> list[str]:
    out = []
    for m in _IPV4_RX.finditer(line):
        ip = m.group("ip")
        try:
            a, b = (int(x) for x in ip.split(".")[:2])
        except ValueError:                                   # not four real octets
            continue
        if any(ip.startswith(net) for net in _DOC_NETS):
            continue
        if a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168):
            out.append(ip)
        elif a == 100 and 64 <= b <= 127 or (a == 169 and b == 254):
            out.append(ip)
    return out


def scan_text(text: str, path: str, denylist: tuple[str, ...] | list[str] = ()) -> list[Finding]:
    """Every private-looking value in `text`, with 1-based line numbers. PURE."""
    terms = [t.strip().lower() for t in denylist if t.strip()]
    found: list[Finding] = []
    for n, line in enumerate((text or "").splitlines(), start=1):
        for hit in _abs_path_hits(line):
            found.append(Finding("abs_path", path, n, hit))
        for hit in _hostname_hits(line):
            found.append(Finding("hostname", path, n, hit))
        for hit in _private_ip_hits(line):
            found.append(Finding("private_ip", path, n, hit))
        low = line.lower()
        for term in terms:
            if term in low:
                found.append(Finding("denylist", path, n, line.strip()[:120]))
    return found


_HUNK_RX = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,\d+)? @@")


def scan_diff(diff: str, denylist: tuple[str, ...] | list[str] = ()) -> list[Finding]:
    """Findings in the ADDED lines of a unified diff, attributed to file and new-file line.

    Removed lines are skipped deliberately: they are content LEAVING the repo, so flagging them
    would refuse exactly the commit that cleans a leak up.
    """
    found: list[Finding] = []
    path = "?"
    lineno = 0
    for raw in (diff or "").splitlines():
        if raw.startswith("+++ "):
            target = raw[4:].strip()
            path = target[2:] if target.startswith(("a/", "b/")) else target
            continue
        if raw.startswith("--- ") or raw.startswith("diff --git"):
            continue
        hunk = _HUNK_RX.match(raw)
        if hunk:
            lineno = int(hunk.group("start"))
            continue
        if raw.startswith("+"):
            found.extend(Finding(f.kind, path, lineno, f.text_excerpt)
                         for f in scan_text(raw[1:], path, denylist))
            lineno += 1
        elif not raw.startswith("-"):
            lineno += 1
    return found


def added_line_count(diff: str) -> int:
    """How many added lines the scan actually read - the denominator the verdict must report."""
    return sum(1 for line in (diff or "").splitlines()
               if line.startswith("+") and not line.startswith("+++"))


def exclude_findings(findings: list[Finding], patterns: list[str]) -> tuple[list[Finding],
                                                                          list[str]]:
    """Drop findings whose file matches an exclusion, and name the exclusions that matched none.

    Security fixtures are the case this exists for: a project that TESTS for private-looking
    values necessarily contains them, and this tool refused its own repository's every push on
    exactly that. A gate routinely bypassed is the failure it exists to prevent, arriving by a
    different route.

    An exclusion matching nothing is REPORTED rather than ignored, because the quiet direction is
    a caller believing a path is covered by a pattern that never applied.
    """
    kept = [f for f in findings
            if not any(fnmatch(f.file, pat) or f.file == pat for pat in patterns)]
    used = {pat for f in findings for pat in patterns
            if fnmatch(f.file, pat) or f.file == pat}
    return kept, [pat for pat in patterns if pat not in used]


def decide(*, visibility: str | None, findings: list[Finding], examined_lines: int,
           unused_exclusions: list[str] | None = None) -> Verdict:
    """The verdict. PURE, and every non-answer fails closed."""
    unused = list(unused_exclusions or [])
    if visibility is None:
        return Verdict(False, 2, "could not resolve the repository's visibility from its remote; "
                                 "refusing rather than guessing from the directory name",
                       examined_lines, None, findings, unused)
    if examined_lines <= 0:
        return Verdict(False, 2, "the range is empty, so nothing was examined - that is a broken "
                                 "check, not a clean one", examined_lines, visibility, findings, unused)
    if visibility == "public" and findings:
        return Verdict(False, 1, f"{len(findings)} private-looking value(s) in {examined_lines} "
                                 f"added line(s) bound for a PUBLIC repo", examined_lines,
                       visibility, findings, unused)
    if findings:
        return Verdict(True, 0, f"{len(findings)} finding(s) in {examined_lines} added line(s), "
                                f"but the repo is {visibility} - reported, not refused",
                       examined_lines, visibility, findings, unused)
    return Verdict(True, 0, f"clean across {examined_lines} added line(s)", examined_lines,
                   visibility, findings, unused)


# ---- adapters ----------------------------------------------------------------------------------

class PushCheckError(Exception):
    """Reported as a typed message and exit 2, never as a traceback."""


def _run(args: list[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise PushCheckError(f"cannot run {args[0]}: {exc}") from exc
    if proc.returncode != 0:
        raise PushCheckError(f"{' '.join(args[:2])} failed: {(proc.stderr or '').strip()[:200]}")
    return proc.stdout


def remote_url(repo: Path, remote: str) -> str:
    return _run(["git", "remote", "get-url", remote], repo).strip()


def default_range(repo: Path) -> str:
    """`@{u}..HEAD`, but only once an upstream exists - otherwise say so instead of scanning all."""
    try:
        _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo)
    except PushCheckError as exc:
        raise PushCheckError("no upstream is configured, so the pending range is undefined - "
                             "pass --range explicitly") from exc
    return "@{u}..HEAD"


def range_diff(repo: Path, rev_range: str) -> str:
    return _run(["git", "diff", "--unified=0", rev_range], repo)


def gh_visibility(host: str, owner: str, repo: str, gh: str = "gh") -> str | None:
    """The repo's visibility per the forge API, or None when it cannot be established."""
    if host.lower() != "github.com":
        return None
    try:
        out = _run([gh, "repo", "view", f"{owner}/{repo}", "--json", "visibility"], Path.cwd())
    except PushCheckError:
        return None
    try:
        value = json.loads(out).get("visibility")
    except (ValueError, AttributeError):
        return None
    return str(value).lower() if value else None


def _render(verdict: Verdict) -> str:
    head = ("SAFE TO PUSH" if verdict.ok else "REFUSED") + f": {verdict.reason}"
    lines = [head, f"visibility  {verdict.visibility or '(unresolved)'}",
             f"examined    {verdict.examined_lines} added line(s)"]
    if verdict.unused_exclusions:
        lines.append("! these --exclude patterns matched nothing: "
                     + ", ".join(verdict.unused_exclusions))
    lines += [f"  {f.kind:<11} {f.file}:{f.line}  {f.text_excerpt}" for f in verdict.findings]
    return "\n".join(lines)


def _emit(as_json: bool, verdict: Verdict) -> None:
    if as_json:
        print(json.dumps({"ok": verdict.ok, "command": "pushcheck",
                          "data": {"visibility": verdict.visibility,
                                   "examined_lines": verdict.examined_lines,
                                   "reason": verdict.reason,
                                   "unused_exclusions": verdict.unused_exclusions,
                                   "findings": [f.as_dict() for f in verdict.findings]},
                          "skipped": []}, indent=2))
    else:
        print(_render(verdict))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--repo", default=".", help="the repository to check (default: cwd)")
    p.add_argument("--remote", default="origin", help="remote whose URL names the repo")
    p.add_argument("--range", dest="rev_range", default=None,
                   help="commit range to scan (default: @{u}..HEAD)")
    p.add_argument("--visibility", default=None, choices=["public", "private", "internal"],
                   help="skip the forge lookup and state the visibility")
    p.add_argument("--denylist-file", default=None,
                   help="your own hostnames/usernames, one per line; never shipped")
    p.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                   help="skip findings in these paths (security fixtures); repeatable. An "
                        "exclusion matching nothing is reported, not ignored")
    p.add_argument("--gh", default="gh", help="path to the gh CLI")
    p.add_argument("--json", action="store_true", dest="as_json", help="emit a JSON envelope")
    return p


def _denylist(path: str | None) -> list[str]:
    if not path:
        return []
    try:
        return Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PushCheckError(f"cannot read --denylist-file: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = Path(args.repo).expanduser()
        if not (repo / ".git").exists():
            raise PushCheckError(f"not a git repository: {repo}")
        visibility = args.visibility
        if visibility is None:
            parsed = parse_remote(remote_url(repo, args.remote))
            visibility = gh_visibility(*parsed, gh=args.gh) if parsed else None
        rev_range = args.rev_range or default_range(repo)
        diff = range_diff(repo, rev_range)
        findings = scan_diff(diff, _denylist(args.denylist_file))
        findings, unused = exclude_findings(findings, list(args.exclude))
        verdict = decide(visibility=visibility, findings=findings,
                         examined_lines=added_line_count(diff), unused_exclusions=unused)
    except PushCheckError as exc:
        verdict = Verdict(False, 2, str(exc), 0, None, [])
        _emit(args.as_json, verdict)
        if not args.as_json:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(args.as_json, verdict)
    return verdict.exit_code


if __name__ == "__main__":
    sys.exit(main())
