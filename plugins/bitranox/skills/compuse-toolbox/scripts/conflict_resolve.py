# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Resolve the git merge-conflict hunks of ONE file, hunk by hunk, by rule - or refuse.

Why: the same throwaway resolver gets written again and again - a `re.sub` over
`<<<<<<< X\\n(.*?)=======\\n(.*?)>>>>>>> Y\\n`, keep one side or glue both (a CHANGELOG: both,
newer first), then a grep to see whether any marker is left. Its failures are silent: a DOTALL
regex that spans two hunks, a diff3 `|||||||` section kept as if it were ours, CRLF lines the
pattern never matches, a hunk count nobody checked. This parses the markers line-wise, applies an
explicit rule to every hunk, refuses anything it cannot place exactly, and re-scans the result.

Rules (`--hunk N=RULE`, 1-based; `--match REGEX=RULE`; `--all RULE` for every hunk without one):

    ours | theirs | base       keep that side (`base` only on a diff3 hunk, one with `|||||||`)
    both                       ours, then theirs
    both-theirs-first          theirs, then ours (the CHANGELOG case: the incoming entry on top)
    file:<path>                the hunk becomes that file's text, in the hunk's line ending

In a Markdown file (`.md`, `.markdown`, `.mdx`) the two joined sides of `both` /
`both-theirs-first` are separated by one blank line when the line where they meet is an ATX heading
on either side and neither side already leaves a blank line there: measured, a joined CHANGELOG hunk
left `...alike.` directly above `## [1.15.3]`, the re-scan found no marker and a formatter check
passed. Elsewhere a `#` line is not a heading (a Python comment), so the sides are joined as they are.

`ours` is the side after `<<<<<<<` and `theirs` the side before `>>>>>>>`, whatever git labels them: in a
rebase git swaps the roles, so `theirs` is the commit being replayed and `ours` the branch it lands on.

`--match` searches each hunk's ours and theirs text (re.MULTILINE, so ^ and $ are per line); it
must select exactly one hunk. In `REGEX=RULE` the split is at the LAST `=` whose remainder is a
valid rule, so a regex or a `file:` path may contain `=`. `--all` is a fallback: an explicit
`--hunk` or `--match` rule overrides it, but two explicit rules on one hunk are refused.

Refused, with nothing written: `--expect-hunks K` disagreeing with the parsed count, a rule naming
a hunk that does not exist, a hunk with two explicit rules or with none, a `--match` selecting no
hunk or several, `base` on a hunk with no base section, and malformed markers - unclosed, nested,
a separator or close with no open, a second separator, or a lone `=======` outside a hunk that
conflict_scan would count (one in the shape of a heading underline is text).

A marker line is exactly seven of `<`, `|`, `>` followed by end of line or whitespace (then the
label), or seven `=` with nothing but whitespace after. Lines keep their own endings, so a CRLF or
mixed file is rewritten byte for byte outside the hunks; a `file:` replacement is converted to the
ending of the hunk's `<<<<<<<` line and given a final one if it lacks it, except where the hunk
closed the file with no final newline, which is kept that way. A UTF-8 BOM is kept, and bytes that
are not UTF-8 pass through unchanged.

The write is atomic (a temp file in the same directory, then os.replace), keeps the file's mode,
and goes through a symlink to its target. The result is then re-scanned with conflict_scan's
rules, and any marker left (a replacement that carried one) is reported. A file with no hunks is
not written: exit 0 with a note.

`--list` writes nothing and shows each hunk's number, line range, labels and the first three
lines of each side.

Run:
  `uv run scripts/conflict_resolve.py FILE --list`
  `uv run scripts/conflict_resolve.py CHANGELOG.md --all both-theirs-first --expect-hunks 1`
  `uv run scripts/conflict_resolve.py F --hunk 1=ours --hunk 2=file:merged.txt --match 'import os=theirs'`

Exit codes: 0 = resolved and no marker remains (or the file had no hunks, or `--list` ran),
1 = written, but the re-scan found markers left, 2 = nothing written: a refusal (the reason on
stderr, `data.refused` under --json), an unreadable file, a usage error, a failed write, a crash.
A refusal is a refusal of the whole action, so it is 2, not 1. `--json` prints
`{ok, command, data, skipped}` on every exit; `data` is `{hunks: [{n, rule, lines}],
remaining_markers: [{line, text}], written, note?}`.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded
import conflict_scan

__all__ = [
    "Hunk",
    "Refusal",
    "Rule",
    "UsageError",
    "assign_rules",
    "main",
    "parse_hunks",
    "parse_rule",
    "resolve_text",
    "split_match_spec",
]

COMMAND = "conflict_resolve"
# Built with chr() so the source stays ASCII.
_BOM = chr(0xFEFF)
_SIDE_KINDS = ("ours", "theirs", "base", "both", "both-theirs-first")
# The same marker shapes conflict_scan reports, captured: the kind, then the label.
_MARKER = re.compile(r"(<{7}|\|{7}|>{7})(?:\s(.*))?$|(={7})\s*$")
_PREVIEW_LINES = 3


class Refusal(Exception):
    """The action as a whole was refused; nothing is written."""


class UsageError(Exception):
    """A bad invocation or an unreadable input, as opposed to a refusal."""


@dataclass
class Hunk:
    """One conflict hunk. `start`/`end` are the 1-based lines of its `<<<<<<<` and `>>>>>>>`.

    The side lists keep each line's own terminator, so joining them gives the exact bytes.
    `base` is None for a plain (non-diff3) hunk.
    """

    n: int
    start: int
    end: int
    ours_label: str
    theirs_label: str
    base_label: str | None
    ours: list[str]
    base: list[str] | None
    theirs: list[str]
    eol: str
    closes_file_unterminated: bool


@dataclass(frozen=True)
class Rule:
    """How to resolve a hunk: `kind` is a side kind or "file", `path` set only for "file"."""

    kind: str
    path: str | None = None

    def __str__(self) -> str:
        return "file:%s" % self.path if self.kind == "file" else self.kind


def _split_keepends(text: str) -> list[str]:
    """Split on '\\n' only, keeping it; str.splitlines also breaks on \\f, \\v and U+2028, which
    would move line numbers away from what git and conflict_scan count."""
    parts = text.split("\n")
    lines = [p + "\n" for p in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _body(line: str) -> str:
    """The line without its terminator."""
    if line.endswith("\r\n"):
        return line[:-2]
    return line[:-1] if line.endswith("\n") else line


def _eol(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    return "\n" if line.endswith("\n") else ""


def _marker(line: str) -> tuple[str, str] | None:
    """(kind char, label) for a marker line, else None."""
    m = _MARKER.match(_body(line))
    if m is None:
        return None
    if m.group(3):
        return "=", ""
    return m.group(1)[0], (m.group(2) or "").strip()


class _HunkBuilder:
    """Collects one hunk while the parser walks its lines."""

    def __init__(self, start: int, label: str, eol: str) -> None:
        self.start, self.ours_label, self.eol = start, label, eol
        self.section = "ours"
        self.base_label: str | None = None
        self.sides: dict[str, list[str]] = {"ours": [], "theirs": []}

    def feed(self, lineno: int, line: str, mark: tuple[str, str] | None) -> bool:
        """Take one line; True when it closed the hunk. Raises Refusal on a misplaced marker,
        a nested <<<<<<< included."""
        if mark is None:
            self.sides[self.section].append(line)
            return False
        kind, label = mark
        if kind == "|" and self.section == "ours":
            self.section, self.base_label, self.sides["base"] = "base", label, []
            return False
        if kind == "=" and self.section in ("ours", "base"):
            self.section = "theirs"
            return False
        if kind == ">" and self.section == "theirs":
            return True
        raise Refusal("line %d: %r inside the hunk opened at line %d (in its %s section) - "
                      "malformed or nested markers" % (lineno, _body(line), self.start, self.section))

    def build(self, n: int, end: int, close_label: str, close_eol: str) -> Hunk:
        return Hunk(n=n, start=self.start, end=end, ours_label=self.ours_label,
                    theirs_label=close_label, base_label=self.base_label, ours=self.sides["ours"],
                    base=self.sides.get("base"), theirs=self.sides["theirs"], eol=self.eol,
                    closes_file_unterminated=close_eol == "")


def _check_outside_markers(text: str, hunks: list[Hunk]) -> None:
    """Refuse a marker conflict_scan counts that sits outside every hunk (a half-resolved one)."""
    inside = set()
    for h in hunks:
        inside.update(range(h.start, h.end + 1))
    for lineno, line in conflict_scan.scan_text(text):
        if lineno not in inside:
            raise Refusal("line %d: %r is a conflict marker outside any hunk - a half-resolved "
                          "hunk; fix it by hand" % (lineno, line))


def parse_hunks(text: str) -> list[Hunk]:
    """Every conflict hunk in `text`, in order. Raises Refusal on malformed markers.

    Args:
        text: The file's text, line endings intact (a leading BOM is ignored).

    Returns:
        The hunks, numbered from 1.

    Examples:
        >>> [(h.n, h.start, h.end) for h in parse_hunks("<<<<<<< a\\nx\\n=======\\ny\\n>>>>>>> b\\n")]
        [(1, 1, 5)]
    """
    text = text[1:] if text.startswith(_BOM) else text
    hunks: list[Hunk] = []
    current: _HunkBuilder | None = None
    for i, line in enumerate(_split_keepends(text), start=1):
        mark = _marker(line)
        if current is None:
            # A stray |||||||, ======= or >>>>>>> out here is left to _check_outside_markers,
            # which decides it by conflict_scan's rules (a heading underline is text).
            if mark is not None and mark[0] == "<":
                current = _HunkBuilder(i, mark[1], _eol(line) or "\n")
            continue
        if current.feed(i, line, mark):
            assert mark is not None  # feed() closes only on a >>>>>>> marker
            hunks.append(current.build(len(hunks) + 1, i, mark[1], _eol(line)))
            current = None
    if current is not None:
        raise Refusal("the hunk opened at line %d is never closed by >>>>>>> - unclosed markers"
                      % current.start)
    _check_outside_markers(text, hunks)
    return hunks


def parse_rule(spec: str) -> Rule:
    """A Rule from its spelling. Raises UsageError on an unknown one.

    Examples:
        >>> parse_rule("both-theirs-first").kind
        'both-theirs-first'
        >>> str(parse_rule("file:a.txt"))
        'file:a.txt'
    """
    if spec in _SIDE_KINDS:
        return Rule(spec)
    if spec.startswith("file:") and len(spec) > len("file:"):
        return Rule("file", spec[len("file:"):])
    raise UsageError("unknown rule %r - use one of %s or file:<path>"
                     % (spec, ", ".join(_SIDE_KINDS)))


def split_match_spec(spec: str) -> tuple[str, Rule]:
    """(regex, rule) from `REGEX=RULE`, split at the last `=` whose remainder is a valid rule.

    Examples:
        >>> regex, rule = split_match_spec("a=b=ours")
        >>> regex, rule.kind
        ('a=b', 'ours')
    """
    positions = [i for i, ch in enumerate(spec) if ch == "="]
    for i in reversed(positions):
        try:
            rule = parse_rule(spec[i + 1:])
        except UsageError:
            continue
        if i == 0:
            break
        return spec[:i], rule
    raise UsageError("--match needs REGEX=RULE with a non-empty regex, got %r" % spec)


def _match_targets(by_match, hunks: list[Hunk]) -> list[tuple[int, Rule]]:
    """(hunk number, rule) for each --match; each regex must select exactly one hunk."""
    out = []
    for regex, rule in by_match:
        try:
            rx = re.compile(regex, re.MULTILINE)
        except re.error as exc:
            raise UsageError("--match regex %r does not compile: %s" % (regex, exc)) from exc
        hits = [h.n for h in hunks if rx.search("".join(h.ours)) or rx.search("".join(h.theirs))]
        if not hits:
            raise Refusal("--match %r matches no hunk" % regex)
        if len(hits) > 1:
            raise Refusal("--match %r matches %d hunks (%s) - make it select one"
                          % (regex, len(hits), ", ".join(map(str, hits))))
        out.append((hits[0], rule))
    return out


def assign_rules(hunks: list[Hunk], *, by_number: dict[int, Rule] | None = None,
                 by_match=(), default: Rule | None = None) -> list[Rule]:
    """The rule for each hunk, in order, or a Refusal naming what does not fit.

    Args:
        hunks: From parse_hunks.
        by_number: {1-based hunk number: rule}.
        by_match: [(regex, rule)]; each regex must select exactly one hunk.
        default: The --all rule, used for a hunk no explicit rule names.

    Returns:
        One Rule per hunk.
    """
    explicit: dict[int, list[Rule]] = {}
    for n, rule in (by_number or {}).items():
        if not 1 <= n <= len(hunks):
            raise Refusal("there is no hunk %d - the file has %d" % (n, len(hunks)))
        explicit.setdefault(n, []).append(rule)
    for n, rule in _match_targets(by_match, hunks):
        explicit.setdefault(n, []).append(rule)
    rules = []
    for h in hunks:
        given = explicit.get(h.n, [])
        if len(given) > 1:
            raise Refusal("hunk %d (lines %d-%d) is named by more than one rule: %s"
                          % (h.n, h.start, h.end, ", ".join(map(str, given))))
        rule = given[0] if given else default
        if rule is None:
            raise Refusal("hunk %d (lines %d-%d) has no rule - give --hunk %d=RULE or --all"
                          % (h.n, h.start, h.end, h.n))
        if rule.kind == "base" and h.base is None:
            raise Refusal("hunk %d (lines %d-%d) has no ||||||| base section, so `base` cannot "
                          "apply (only a diff3-style hunk has one)" % (h.n, h.start, h.end))
        rules.append(rule)
    return rules


def _read_replacement(path: str) -> str:
    try:
        return Path(path).read_bytes().decode("utf-8", errors="surrogateescape")
    except OSError as exc:
        raise UsageError("cannot read the replacement file %s: %s"
                         % (path, exc.strerror or exc)) from exc


def _file_lines(text: str, eol: str) -> list[str]:
    """`text` as whole lines in the hunk's ending; each line gets its own terminator."""
    if text.startswith(_BOM):
        text = text[1:]
    body = text.replace("\r\n", "\n")
    if not body:
        return []
    if body.endswith("\n"):
        body = body[:-1]
    return [line + eol for line in body.split("\n")]


_ATX_HEADING = re.compile(r"#{1,6}(?:[ \t]|$)")
MARKDOWN_SUFFIXES = frozenset({".md", ".markdown", ".mdx"})


def _join(first: list[str], second: list[str], eol: str, markdown: bool) -> list[str]:
    """`first` then `second`, with a blank line between when a Markdown heading meets text."""
    if not (markdown and first and second):
        return first + second
    last, nxt = _body(first[-1]).strip(), _body(second[0]).strip()
    if last and nxt and (_ATX_HEADING.match(last) or _ATX_HEADING.match(nxt)):
        return first + [eol] + second
    return first + second


def _replacement(hunk: Hunk, rule: Rule, read_file, markdown: bool = False) -> list[str]:
    if rule.kind == "file":
        return _file_lines(read_file(rule.path), hunk.eol)
    if rule.kind == "both":
        return _join(hunk.ours, hunk.theirs, hunk.eol, markdown)
    if rule.kind == "both-theirs-first":
        return _join(hunk.theirs, hunk.ours, hunk.eol, markdown)
    sides = {"ours": hunk.ours, "theirs": hunk.theirs, "base": hunk.base or []}
    return list(sides[rule.kind])


def resolve_text(text: str, rules: list[Rule], *, read_file=_read_replacement,
                 markdown: bool = False) -> str:
    """`text` with each hunk replaced by its rule's lines. PURE apart from `read_file`.

    Args:
        text: The conflicted text (a leading BOM is kept).
        rules: One per hunk, from assign_rules.
        read_file: Reads a `file:` rule's path; injectable for tests.
        markdown: The file is Markdown, so joined sides keep a heading's blank line.

    Returns:
        The resolved text.
    """
    bom = _BOM if text.startswith(_BOM) else ""
    body = text[len(bom):]
    hunks = parse_hunks(body)
    if len(rules) != len(hunks):
        raise Refusal("%d rules for %d hunks" % (len(rules), len(hunks)))
    lines = _split_keepends(body)
    out: list[str] = []
    cursor = 0
    for hunk, rule in zip(hunks, rules):
        out.extend(lines[cursor:hunk.start - 1])
        chosen = _replacement(hunk, rule, read_file, markdown)
        if hunk.closes_file_unterminated and chosen:
            # The hunk was the file's last line, which had no newline: keep the file that way.
            chosen[-1] = _body(chosen[-1])
        out.extend(chosen)
        cursor = hunk.end
    out.extend(lines[cursor:])
    return bom + "".join(out)


def _decode(raw: bytes) -> str:
    # surrogateescape: a non-UTF-8 byte survives the round trip unchanged instead of failing.
    return raw.decode("utf-8", errors="surrogateescape")


def _encode(text: str) -> bytes:
    return text.encode("utf-8", errors="surrogateescape")


def _atomic_write(path: Path, data: bytes) -> None:
    """Replace `path` with `data` atomically, keeping its mode. A crash leaves the old file."""
    mode = path.stat().st_mode
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".%s." % path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _remaining(text: str) -> list[dict]:
    body = text[1:] if text.startswith(_BOM) else text
    return [{"line": ln, "text": line} for ln, line in conflict_scan.scan_text(body)]


def _preview(side: list[str] | None) -> list[str] | None:
    return None if side is None else [_body(x) for x in side[:_PREVIEW_LINES]]


def _list_data(hunks: list[Hunk]) -> dict:
    return {"hunks": [{"n": h.n, "lines": [h.start, h.end],
                       "labels": {"ours": h.ours_label, "base": h.base_label,
                                  "theirs": h.theirs_label},
                       "ours": _preview(h.ours), "ours_lines": len(h.ours),
                       "base": _preview(h.base),
                       "base_lines": None if h.base is None else len(h.base),
                       "theirs": _preview(h.theirs), "theirs_lines": len(h.theirs)}
                      for h in hunks]}


def _print_list(path: Path, hunks: list[Hunk]) -> None:
    print("%s: %d hunk(s)" % (path, len(hunks)))
    for h in hunks:
        print("hunk %d  lines %d-%d" % (h.n, h.start, h.end))
        sides = [("ours", h.ours_label, h.ours), ("base", h.base_label, h.base),
                 ("theirs", h.theirs_label, h.theirs)]
        for name, label, side in sides:
            if side is None:
                continue
            more = " (+%d more)" % (len(side) - _PREVIEW_LINES) if len(side) > _PREVIEW_LINES else ""
            print("  %-6s [%s] %d line(s)%s" % (name, label, len(side), more))
            for line in side[:_PREVIEW_LINES]:
                print("    | %s" % _body(line))


def _build_parser() -> EnvelopeArgumentParser:
    ap = EnvelopeArgumentParser(
        prog="conflict_resolve", envelope_command=COMMAND,
        description="Resolve the merge-conflict hunks of one file by rule, or refuse.")
    ap.add_argument("file", help="the conflicted file")
    ap.add_argument("--hunk", action="append", default=[], metavar="N=RULE",
                    help="rule for hunk N (1-based): ours|theirs|base|both|both-theirs-first|"
                         "file:<path>")
    ap.add_argument("--match", action="append", default=[], metavar="REGEX=RULE",
                    help="rule for the one hunk whose ours or theirs text matches REGEX")
    ap.add_argument("--all", metavar="RULE", help="rule for every hunk no other rule names")
    ap.add_argument("--expect-hunks", type=int, metavar="K",
                    help="refuse unless the file has exactly K hunks")
    ap.add_argument("--list", action="store_true",
                    help="show the hunks and write nothing")
    ap.add_argument("--json", action="store_true", help="print the JSON envelope")
    return ap


def _parse_number_rules(specs: list[str]) -> dict[int, Rule]:
    out: dict[int, Rule] = {}
    for spec in specs:
        number, sep, rule = spec.partition("=")
        if not sep or not re.fullmatch(r"[0-9]{1,9}", number.strip()):
            raise UsageError("--hunk needs N=RULE with N a hunk number, got %r" % spec)
        n = int(number)
        if n in out:
            raise Refusal("hunk %d is named by more than one --hunk" % n)
        out[n] = parse_rule(rule)
    return out


class _Outcome:
    """What a run did, for the text report and the envelope alike."""

    def __init__(self) -> None:
        self.hunks: list[dict] = []
        self.remaining: list[dict] = []
        self.written = False
        self.note: str | None = None

    def data(self) -> dict:
        out = {"hunks": self.hunks, "remaining_markers": self.remaining, "written": self.written}
        if self.note:
            out["note"] = self.note
        return out


def _read_target(path: Path) -> str:
    try:
        return _decode(path.read_bytes())
    except OSError as exc:
        raise UsageError("cannot read %s: %s" % (path, exc.strerror or exc)) from exc


def _resolve(path: Path, args, outcome: _Outcome) -> int:
    by_number = _parse_number_rules(args.hunk)
    by_match = [split_match_spec(s) for s in args.match]
    default = parse_rule(args.all) if args.all else None
    # Write the link's target, never replace the link itself with a regular file.
    target = Path(os.path.realpath(path))
    text = _read_target(target)
    hunks = parse_hunks(text)
    if args.expect_hunks is not None and args.expect_hunks != len(hunks):
        raise Refusal("--expect-hunks %d, but the file has %d" % (args.expect_hunks, len(hunks)))
    rules = assign_rules(hunks, by_number=by_number, by_match=by_match, default=default)
    if not hunks:
        outcome.note = "no conflict hunks in %s - nothing to resolve, file not written" % path
        return EXIT_YES
    # Every replacement file is read here, before the write, so an unreadable one refuses.
    resolved = resolve_text(text, rules, markdown=path.suffix.lower() in MARKDOWN_SUFFIXES)
    outcome.hunks = [{"n": h.n, "rule": str(r), "lines": [h.start, h.end]}
                     for h, r in zip(hunks, rules)]
    _atomic_write(target, _encode(resolved))
    outcome.written = True
    outcome.remaining = _remaining(resolved)
    return EXIT_NO if outcome.remaining else EXIT_YES


def _report(path: Path, code: int, outcome: _Outcome) -> None:
    for h in outcome.hunks:
        print("hunk %d (lines %d-%d): %s" % (h["n"], h["lines"][0], h["lines"][1], h["rule"]))
    if outcome.note:
        print(outcome.note, file=sys.stderr)
        return
    if code == EXIT_YES:
        print("resolved %d hunk(s) in %s; no markers remain" % (len(outcome.hunks), path))
        return
    for m in outcome.remaining:
        print("%s:%d: %s" % (path, m["line"], m["text"]))
    print("MARKERS REMAIN in %s after resolving (a replacement carried them)" % path)


def _fail(args, code: int, message: str, *, refused: bool) -> int:
    print("conflict_resolve: %s" % message, file=sys.stderr)
    if args.json:
        data = {"reason": message, "written": False}
        if refused:
            data["refused"] = True
        emit(code, COMMAND, data, error=message)
    return code


def _list(path: Path, args) -> int:
    if args.hunk or args.match or args.all:
        return _fail(args, EXIT_ERROR, "--list writes nothing and takes no rules", refused=False)
    try:
        hunks = parse_hunks(_read_target(path))
    except Refusal as exc:
        return _fail(args, EXIT_ERROR, "refused - %s" % exc, refused=True)
    except UsageError as exc:
        return _fail(args, EXIT_ERROR, str(exc), refused=False)
    if args.json:
        return emit(EXIT_YES, COMMAND, _list_data(hunks))
    _print_list(path, hunks)
    return EXIT_YES


@guarded(COMMAND)
def main(argv=None) -> int:
    """Run the CLI; see the module docstring for rules and exit codes."""
    args = _build_parser().parse_args(argv)
    path = Path(args.file)
    if args.list:
        return _list(path, args)
    outcome = _Outcome()
    try:
        code = _resolve(path, args, outcome)
    except Refusal as exc:
        return _fail(args, EXIT_ERROR, "refused, nothing written - %s" % exc, refused=True)
    except UsageError as exc:
        return _fail(args, EXIT_ERROR, "%s - nothing written" % exc, refused=False)
    except OSError as exc:
        return _fail(args, EXIT_ERROR, "write failed, file unchanged - %s" % exc, refused=False)
    if args.json:
        return emit(code, COMMAND, outcome.data())
    _report(path, code, outcome)
    return code


if __name__ == "__main__":
    sys.exit(main())
