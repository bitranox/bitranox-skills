# /// script
# requires-python = ">=3.14"
# ///
"""Do the lines this change ADDS contain a name from a private redaction list?

A project that publishes a redacted copy of itself keeps the names it must never publish in a
private list - one rule per line, often `literal==>replacement` so the same file drives the
redaction. Checking a change against that list by hand goes wrong in two silent ways:

- `grep -Ff <list>` treats EVERY line as a pattern. A bare `#` comment line then matches every
  `#` in the diff, so the real hits drown in noise and get skimmed; and a `name==>Room1` rule is
  searched as the literal text `name==>Room1`, which appears nowhere, so the name it exists to
  catch is never found.
- Grepping the whole diff counts removed and context lines too. A commit that REMOVES a leak then
  reads as one that adds it, and the hit that matters is buried among those that do not.

This jig parses the list properly (blank lines and `#` lines are comments; the pattern is the
text before `==>`, stripped - the parser is pushcheck's `parse_rules`, which its --denylist-file
reads through too), matches each pattern as a case-insensitive literal substring (never
a regex; `str.casefold`, so an upper-case `STRASSE` also matches a pattern spelled with the
German sharp s), and scans ONLY the added lines of the change:

  --range A..B   every commit in the range, read commit by commit (a name added in one commit
                 and removed in the next is still published, in that first commit), plus every
                 commit MESSAGE in the range, which a push publishes too
  --staged       what the next `git commit` would record (`git diff --cached`)
  --worktree     everything not yet committed: tracked changes against HEAD, plus every
                 untracked file that is not ignored, all of whose lines are added

Before scanning it runs a LIVENESS CONTROL: for every parsed pattern, a synthetic added line
holding it goes through the same diff parser and matcher, and must come back as exactly that
rule. If it does not,
the instrument is broken and the run refuses (exit 2) rather than report a clean result it could
not have produced otherwise. A list that parses to zero patterns is refused the same way, and so
is a change that adds no line at all (nothing staged, a clean tree, an empty range): the report
always states how many patterns were parsed, how many comment lines were skipped and how many
added lines were scanned, because "no hits" after reading nothing looks exactly like a clean
change.

A pattern may itself be private, and so may the line it was found in. `--redact-hits` prints
neither: each hit names the rule by its index and list line, plus a short hash of the pattern.
The JSON always carries the index and list line; the pattern text and the hit's excerpt appear
only without `--redact-hits`.

Binary files are never scanned; each one is named in `skipped`. Diff hunk lines are read with
pushcheck's parser (a `+++ ` line is a header only before a file's first hunk; lines split on
newline only), so the two jigs cannot disagree about what a diff adds.

Exit codes: 0 = no added line holds a listed name, 1 = at least one does, 2 = could not run (an
unreadable or empty list, a bad range, git failing, the liveness control failing, an internal
error).

Run:
  `uv run scripts/redaction_scan.py --list tools/names-private.txt --range origin/main..HEAD`
  `uv run scripts/redaction_scan.py --list names.txt --staged --redact-hits --json`
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded
from pushcheck import (
    PushCheckError,
    Rule,
    RuleList,
    added_lines,
    binary_files,
    fold_case,
    parse_rules,
    range_diff,
    range_messages,
    repo_root,
    split_lines,
)

__all__ = ["Hit", "Matcher", "Rule", "RuleList", "control_failures", "execute", "match_rules",
           "parse_rules", "scan_added", "scan_diff", "scan_messages", "scan_untracked_text"]

COMMAND = "redaction_scan"
_SHORT_PATTERN = 3                  # a pattern this short matches nearly every line; warn about it
_EXCERPT = 120
_DIFF_FLAGS = ["--unified=0", "--no-color", "--no-ext-diff"]


class ScanError(Exception):
    """Reported as one line and exit 2, never as a traceback."""


@dataclass(frozen=True)
class Hit:
    """A listed pattern found in one added line."""
    location: str                   # a file path, or `commit <sha12> message`
    line: int
    rule: Rule
    excerpt: str

    def as_dict(self, redact: bool) -> dict[str, Any]:
        out: dict[str, Any] = {"file": self.location, "line": self.line, "pattern_index": self.rule.index,
                     "list_line": self.rule.list_line, "pattern_hash": self.rule.digest}
        if not redact:
            out["pattern"] = self.rule.pattern
            out["excerpt"] = self.excerpt
        return out


#: Which rules a line holds. Injectable so the liveness control can be shown to refuse a broken one.
Matcher = Callable[[str, tuple[Rule, ...]], list[Rule]]


def match_rules(text: str, rules: tuple[Rule, ...]) -> list[Rule]:
    """The rules whose pattern is a case-insensitive literal substring of `text`. PURE."""
    folded = fold_case(text)
    return [r for r in rules if fold_case(r.pattern) in folded]


def scan_added(lines: Iterable[tuple[str, int, str]], rules: tuple[Rule, ...],
               matcher: Matcher = match_rules) -> tuple[list[Hit], int]:
    """Hits in `(location, line, text)` triples, and how many triples were read. PURE."""
    hits: list[Hit] = []
    count = 0
    for location, lineno, text in lines:
        count += 1
        hits.extend(Hit(location, lineno, rule, text.strip()[:_EXCERPT])
                    for rule in matcher(text, rules))
    return hits, count


def scan_diff(diff: str, rules: tuple[Rule, ...],
              matcher: Matcher = match_rules) -> tuple[list[Hit], int]:
    """Hits in the ADDED lines of a unified diff only; removed and context lines never count."""
    return scan_added(added_lines(diff), rules, matcher)


def scan_messages(messages: list[tuple[str, str]], rules: tuple[Rule, ...],
                  matcher: Matcher = match_rules) -> tuple[list[Hit], int]:
    """Hits in commit messages, each located as `commit <sha12> message` and its line."""
    triples = ((f"commit {sha[:12]} message", n, line)
               for sha, message in messages
               for n, line in enumerate(split_lines(message), start=1))
    return scan_added(triples, rules, matcher)


def scan_untracked_text(path: str, text: str, rules: tuple[Rule, ...],
                        matcher: Matcher = match_rules) -> tuple[list[Hit], int]:
    """Hits in a new, untracked file: every one of its lines is an added line."""
    return scan_added(((path, n, line) for n, line in enumerate(split_lines(text), start=1)),
                      rules, matcher)


def control_failures(rules: tuple[Rule, ...], matcher: Matcher = match_rules) -> list[Rule]:
    """The liveness control: the rules a planted added line holding them does NOT come back as.

    One synthetic diff carries one added line per rule, the pattern set inside other text, and
    goes through the same diff parser and matcher as the real change. Each line must hit its own
    rule; a rule that does not come back means the instrument cannot see what it is looking for,
    and an empty result is the only pass. No rules at all is a failure too (reported by the
    caller as zero patterns).
    """
    planted = "".join(f"+control >{rule.pattern}< control\n" for rule in rules)
    diff = (f"diff --git a/.control b/.control\n+++ b/.control\n@@ -0,0 +1,{len(rules)} @@\n"
            + planted)
    hits, _ = scan_diff(diff, rules, matcher)
    found = {(h.line, h.rule.index) for h in hits}
    return [rule for n, rule in enumerate(rules, start=1) if (n, rule.index) not in found]


# ---- adapters ----------------------------------------------------------------------------------

def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=str(repo),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              check=False)
    except OSError as exc:
        raise ScanError(f"cannot run git: {exc}") from exc
    if proc.returncode != 0:
        raise ScanError(f"git {args[0]} failed: {(proc.stderr or '').strip()[:200]}")
    return proc.stdout


def read_list(path: str) -> str:
    """The list's text. utf-8-sig, because an editor's BOM would glue onto the first pattern."""
    try:
        return Path(path).expanduser().read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ScanError(f"cannot read --list: {exc.strerror or exc}") from exc
    except UnicodeDecodeError as exc:
        # The exception text is not echoed: the offending bytes belong to a private name.
        raise ScanError(f"--list is not UTF-8 text (undecodable byte at offset {exc.start}); "
                        "re-save it as UTF-8") from None


def _untracked(repo: Path) -> list[str]:
    out = _git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    return [p for p in out.split("\0") if p]


@dataclass
class Scan:
    hits: list[Hit]
    added: int
    message_lines: int
    skipped: list[str]


def _scan_untracked(repo: Path, rules: tuple[Rule, ...], scan: Scan, matcher: Matcher) -> None:
    for rel in _untracked(repo):
        try:
            data = (repo / rel).read_bytes()
        except OSError as exc:
            raise ScanError(f"cannot read untracked file {rel}: {exc.strerror or exc}") from exc
        if b"\0" in data:
            scan.skipped.append(f"{rel}: binary content is not scanned")
            continue
        hits, read = scan_untracked_text(rel, data.decode("utf-8", errors="replace"), rules,
                                         matcher)
        scan.hits.extend(hits)
        scan.added += read


def run_scan(repo: Path, mode: str, rev_range: str | None, rules: tuple[Rule, ...],
             matcher: Matcher = match_rules) -> Scan:
    """Read the change named by `mode` and scan its added lines (and, for a range, messages)."""
    try:
        if mode == "range":
            diff = range_diff(repo, rev_range or "")
            messages = range_messages(repo, rev_range or "")
        else:
            diff = _git(repo, "diff", *(["--cached"] if mode == "staged" else ["HEAD"]),
                        *_DIFF_FLAGS, "--")
            messages = []
    except PushCheckError as exc:
        raise ScanError(str(exc)) from exc
    hits, added = scan_diff(diff, rules, matcher)
    msg_hits, message_lines = scan_messages(messages, rules, matcher)
    scan = Scan(hits + msg_hits, added, message_lines,
                [f"{name}: binary content is not scanned" for name in binary_files(diff)])
    if mode == "worktree":
        _scan_untracked(repo, rules, scan, matcher)
    scan.hits = list(dict.fromkeys(scan.hits))
    return scan


def _render_hit(hit: Hit, redact: bool) -> str:
    rule = hit.rule
    name = f"rule #{rule.index} (list line {rule.list_line}, sha256:{rule.digest})"
    if redact:
        return f"  {hit.location}:{hit.line}  {name}"
    return f"  {hit.location}:{hit.line}  {name} {rule.pattern!r}  {hit.excerpt}"


def build_parser() -> argparse.ArgumentParser:
    p = EnvelopeArgumentParser(description=(__doc__ or COMMAND).splitlines()[0],
                               envelope_command=COMMAND, json_flags=("--json", "--json-bare"))
    p.add_argument("--list", required=True, metavar="PATH",
                   help="the redaction list: one rule per line, `literal` or "
                        "`literal==>replacement`; blank and `#` lines are comments")
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument("--range", dest="rev_range", metavar="A..B",
                       help="every commit in the range, and their messages")
    which.add_argument("--staged", action="store_true", help="the index (git diff --cached)")
    which.add_argument("--worktree", action="store_true",
                       help="everything uncommitted: tracked changes vs HEAD plus untracked, "
                            "non-ignored files")
    p.add_argument("--repo", default=".", help="the repository (default: cwd)")
    p.add_argument("--redact-hits", action="store_true",
                   help="never print a pattern or the line it was found in; name the rule by "
                        "index, list line and a short hash instead")
    out = p.add_mutually_exclusive_group()
    out.add_argument("--json", action="store_true", help="print an indented JSON envelope")
    out.add_argument("--json-bare", action="store_true", help="print a one-line JSON envelope")
    return p


def _mode(args: argparse.Namespace) -> str:
    return "range" if args.rev_range is not None else "staged" if args.staged else "worktree"


def _refuse(args: argparse.Namespace, message: str, data: dict[str, Any] | None = None) -> int:
    if args.json or args.json_bare:
        emit(EXIT_ERROR, COMMAND, data, error=message, indent=None if args.json_bare else 2)
    print(f"{COMMAND}: {message}", file=sys.stderr)
    return EXIT_ERROR


def _tolerate_unencodable_output() -> None:
    """A cp1252 console must not turn a report into a traceback whose exit reads as a verdict."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            continue


@guarded(COMMAND, json_flags=("--json", "--json-bare"))
def main(argv: list[str] | None = None) -> int:
    """Scan the change; an uncaught exception exits 2, never Python's 1, which means 'a hit'."""
    return execute(argv)


def execute(argv: list[str] | None = None, *, matcher: Matcher = match_rules) -> int:
    """The whole run, with the matcher as a seam so a broken one can be shown to be refused."""
    _tolerate_unencodable_output()
    args = build_parser().parse_args(argv)
    mode = _mode(args)
    try:
        parsed = parse_rules(read_list(args.list))
    except ScanError as exc:
        return _refuse(args, str(exc))
    counts = {"patterns": len(parsed.rules), "comment_lines": parsed.comment_lines,
              "blank_lines": parsed.blank_lines, "empty_rules": parsed.empty_rules}
    if not parsed.rules:
        return _refuse(args, "the list parsed to zero patterns, so nothing could be found - "
                             "check the path and that rules are not all commented out", counts)
    missed = control_failures(parsed.rules, matcher)
    if missed:
        return _refuse(args, "liveness control failed: a planted added line holding rule "
                             + ", ".join(f"#{r.index}" for r in missed)
                             + " was not found, so a clean result would mean nothing", counts)
    for rule in parsed.rules:
        if len(rule.pattern) < _SHORT_PATTERN:
            print(f"{COMMAND}: warning: rule #{rule.index} (list line {rule.list_line}) is "
                  f"{len(rule.pattern)} character(s) long and will match almost any line",
                  file=sys.stderr)
    try:
        repo = repo_root(Path(args.repo).expanduser())
        scan = run_scan(repo, mode, args.rev_range, parsed.rules, matcher)
    except (ScanError, PushCheckError) as exc:
        return _refuse(args, str(exc), counts)
    if scan.added + scan.message_lines == 0:
        return _refuse(args, f"the {mode} change adds no lines, so there was nothing to scan",
                       {**counts, "added_lines_scanned": 0})
    code = EXIT_NO if scan.hits else EXIT_YES
    data: dict[str, Any] = {"mode": mode, "range": args.rev_range, **counts, "control": "fired",
            "added_lines_scanned": scan.added, "message_lines_scanned": scan.message_lines,
            "hits": [h.as_dict(args.redact_hits) for h in scan.hits]}
    if args.json or args.json_bare:
        return emit(code, COMMAND, data, skipped=scan.skipped,
                    indent=None if args.json_bare else 2)
    verdict = f"{len(scan.hits)} HIT(S)" if scan.hits else "CLEAN"
    print(f"{verdict}: {len(parsed.rules)} pattern(s) parsed ({parsed.comment_lines} comment "
          f"line(s) skipped), control fired, {scan.added} added line(s)"
          + (f" and {scan.message_lines} commit-message line(s)" if mode == "range" else "")
          + f" scanned ({mode})")
    for line in scan.skipped:
        print(f"  not scanned: {line}")
    for hit in scan.hits:
        print(_render_hit(hit, args.redact_hits))
    return code


if __name__ == "__main__":
    sys.exit(main())
