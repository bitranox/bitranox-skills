# /// script
# requires-python = ">=3.10"
# ///
"""Edit a file at an EXACT anchor, or refuse - never a computed span between two markers.

The trap this ends: Python's no-match branches are SUCCESS-SHAPED. `str.replace` returns the
string unchanged and reports nothing, `str.partition` puts everything in the head, and
`str.find` returns -1, which then indexes from the END of the string. So a hand-rolled anchor
edit does not crash when it misses - it writes a file that looks edited and is not, or one
edited somewhere else entirely, and the write exits 0 either way.

Refusing on an absent anchor also catches a WRONG FILE as a side effect, because a file in the
wrong directory or the wrong repo rarely contains your exact expected text. That is a
deterministic check with no guard and no cwd bookkeeping.

Span replacement is supported but never blind: the end marker is searched FROM the start
offset (never from position 0), the removed region's line count must match what you state, and
anything you name with --must-keep is verified to have survived the write. A span meant for one
function once ate the two that sat between the markers; the file still parsed, and tests in two
unrelated modules were the only signal.

Run:
  `uv run scripts/anchor_edit.py replace F --anchor-file old.txt --new-file new.txt`
  `uv run scripts/anchor_edit.py insert F --anchor-file a.txt --new-file n.txt --after`
  `uv run scripts/anchor_edit.py replace-span F --start-file s.txt --end-file e.txt \\
       --new-text '' --expect-removed-lines 3 --must-keep 'def survivor('`
  add `--json` for an envelope, `--dry-run` to see the line delta without writing

The new text is spliced in VERBATIM - no newline, blank line or indentation is added for you,
so text meant to land as its own line must carry its own trailing newline. Stated because it
is the one thing a reader cannot infer from the flags, and getting it wrong silently glues the
insertion onto the anchor's line.

A file git could not restore is copied to `<name>.bak` first - untracked, gitignored, or tracked
but carrying uncommitted work. Tracked alone is not enough: `git checkout -- <file>` restores from
HEAD, so for a dirty file it discards precisely the content nobody else has. An existing `.bak` is
KEPT rather than overwritten, so a second run cannot replace the original with an already-edited
state; the run says when it kept one, because that copy may predate this session.

Exit codes: 0 = the edit was applied, 1 = refused (nothing written), 2 = usage or IO error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


class AnchorError(Exception):
    """A precondition or postcondition failed, so nothing was written.

    One exception type rather than several because every case has the same consequence for the
    caller - the file is untouched - and the message carries which case it was.
    """


def occurrences(text: str, anchor: str) -> int:
    """How many times the anchor appears. Zero and two are both refusals, for opposite reasons."""
    return text.count(anchor)


def require_unique(text: str, anchor: str, label: str = "anchor") -> int:
    """The offset of the ONLY occurrence, or raise naming the count.

    Zero means the file is not the one you think it is. Two or more means the edit would land on
    whichever came first, which is a coin toss decided by things like whether the construct is
    also quoted in a docstring above it.
    """
    found = occurrences(text, anchor)
    if found != 1:
        head = anchor.strip().splitlines()[0] if anchor.strip() else anchor
        raise AnchorError(f"{label} appears {found} times, needs exactly 1: {head!r}")
    return text.index(anchor)


def assert_no_removals(before: str, after: str) -> None:
    """Every CHARACTER of `before` must still appear in `after`, in order.

    An insertion removes nothing by definition, so this is the postcondition that catches a
    buggy edit rather than trusting one. Checked per character, not per line: inserting inside
    a line legitimately changes that line while removing nothing, and a line-level check calls
    that a removal, which would refuse correct edits and teach the caller to switch it off.

    The walk is a subsequence test, so a repeated fragment cannot mask a genuine loss by
    matching some other copy of itself further along.
    """
    i, j = 0, 0
    while i < len(before) and j < len(after):
        if before[i] == after[j]:
            i += 1
        j += 1
    if i < len(before):
        lost_line = before[:i + 1].splitlines()[-1] if before[:i + 1].splitlines() else before[i]
        raise AnchorError(f"the edit removed text it should have kept, at: {lost_line!r}")


def replace_exact(text: str, old: str, new: str) -> str:
    """Replace the one occurrence of `old` with `new`, or refuse."""
    require_unique(text, old, "old text")
    result = text.replace(old, new, 1)
    if result == text and old != new:
        raise AnchorError("the replacement produced no change, which cannot be right here")
    return result


def insert_at(text: str, anchor: str, new: str, *, where: str = "after") -> str:
    """Insert `new` before or after the one occurrence of `anchor`, removing nothing."""
    if where not in ("before", "after"):
        raise AnchorError(f"where must be 'before' or 'after', got {where!r}")
    start = require_unique(text, anchor)
    cut = start if where == "before" else start + len(anchor)
    result = text[:cut] + new + text[cut:]
    assert_no_removals(text, result)
    return result


def span_between(text: str, start: str, end: str) -> tuple[int, int]:
    """Offsets of the region from `start` up to (not including) `end`.

    `end` is searched FROM THE END OF `start`, never from position 0. Searching from 0 finds an
    earlier occurrence, the computed span runs backwards, and the slice yields nonsense instead
    of raising. The region must also be unambiguous: a second `end` after the first would make
    the boundary a guess.
    """
    begin = require_unique(text, start, "start marker")
    after = begin + len(start)
    stop = text.find(end, after)
    if stop == -1:
        raise AnchorError(f"end marker never occurs after the start marker: {end!r}")
    if text.find(end, stop + len(end)) != -1:
        raise AnchorError(f"end marker occurs more than once after the start marker: {end!r}")
    return begin, stop


def replace_span(text: str, start: str, end: str, new: str, *, expect_removed_lines: int,
                 must_keep=()) -> str:
    """Replace the region from `start` up to `end`, but only on the stated terms.

    `expect_removed_lines` is what turns a silent over-deletion into a refusal: the caller says
    how big the region should be, and a region that is bigger has swallowed something. Anything
    in `must_keep` is checked AFTER the edit, because naming what has to survive is the only
    check that speaks about the constructs rather than about the offsets.
    """
    begin, stop = span_between(text, start, end)
    removed = len(text[begin:stop].splitlines())
    if removed != expect_removed_lines:
        raise AnchorError(
            f"the span covers {removed} lines but expected {expect_removed_lines} - "
            "it is swallowing something between the markers")
    result = text[:begin] + new + text[stop:]
    for survivor in must_keep or ():
        if survivor not in result:
            raise AnchorError(f"the edit removed a construct named with --must-keep: {survivor!r}")
    return result


class EditResult:
    """What an edit did, named rather than returned as an anonymous tuple."""

    def __init__(self, path: Path, line_delta: int, backup: Path | None, written: bool,
                 backup_reused: bool = False):
        self.path = path
        self.line_delta = line_delta
        self.backup = backup
        self.written = written
        self.backup_reused = backup_reused

    def as_data(self) -> dict:
        return {"path": str(self.path), "line_delta": self.line_delta,
                "backup": str(self.backup) if self.backup else None,
                "backup_reused": self.backup_reused, "written": self.written}


def _git(path: Path, *args):
    """Run git in the file's directory, or None when git cannot be run at all.

    LC_ALL=C because a localized message is not a stable thing to branch on.
    """
    try:
        return subprocess.run(
            ["git", *args], cwd=str(path.parent), capture_output=True, text=True,
            encoding="utf-8", errors="replace", env={**os.environ, "LC_ALL": "C"})
    except (OSError, ValueError):
        return None


def is_recoverable_from_git(path: Path) -> bool:
    """Whether git could actually restore this file's CURRENT content. Unprovable answers False.

    Tracked is not enough. `git checkout -- <file>` restores from HEAD, so for a tracked file
    carrying uncommitted work it discards exactly the content nobody else has, and exits 0. A
    backup rule keyed on tracking alone therefore skips the backup in the one state it is for.

    Both questions are asked, because neither answers the other: `git status --porcelain` is
    EMPTY for a gitignored file exactly as for a clean one, so cleanliness alone reads an ignored
    file as safely stored in git.
    """
    tracked = _git(path, "ls-files", "--error-unmatch", "--", path.name)
    if tracked is None or tracked.returncode != 0:
        return False
    status = _git(path, "status", "--porcelain", "--", path.name)
    return status is not None and status.returncode == 0 and not status.stdout.strip()


def apply_to_file(path: Path, transform, *, dry_run: bool = False, backup: bool = True):
    """Read, transform, and write the file, backing it up first when git does not track it."""
    path = Path(path)
    try:
        before = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnchorError(f"cannot read {path}: {exc}")
    after = transform(before)
    delta = len(after.splitlines()) - len(before.splitlines())
    if dry_run:
        return EditResult(path, delta, None, written=False)
    saved, reused = None, False
    if backup and not is_recoverable_from_git(path):
        saved = path.with_name(path.name + ".bak")
        # FIRST WRITE WINS. This backup is written only for a file git cannot restore, so it is
        # the only copy that exists; overwriting it on a second run would replace the original
        # with an already-edited state and leave nothing holding the original. The earliest state
        # is also the one worth having when a chain of edits goes wrong.
        reused = saved.exists()
        if not reused:
            saved.write_text(before, encoding="utf-8")
    path.write_text(after, encoding="utf-8")
    return EditResult(path, delta, saved, written=True, backup_reused=reused)


def _text_from(inline, file_arg, label):
    """Exactly one of --X / --X-file, with `-` meaning stdin."""
    if inline is not None and file_arg is not None:
        raise AnchorError(f"give either --{label} or --{label}-file, not both")
    if inline is not None:
        return inline
    if file_arg is None:
        raise AnchorError(f"--{label} or --{label}-file is required")
    if file_arg == "-":
        return sys.stdin.read()
    try:
        return Path(file_arg).read_text(encoding="utf-8")
    except OSError as exc:
        raise AnchorError(f"cannot read --{label}-file: {exc}")


def _build_transform(args):
    new = _text_from(args.new_text, args.new_file, "new-text")
    if args.command == "replace":
        anchor = _text_from(args.anchor, args.anchor_file, "anchor")
        return lambda s: replace_exact(s, anchor, new)
    if args.command == "insert":
        anchor = _text_from(args.anchor, args.anchor_file, "anchor")
        where = "before" if args.before else "after"
        return lambda s: insert_at(s, anchor, new, where=where)
    start = _text_from(args.start, args.start_file, "start")
    end = _text_from(args.end, args.end_file, "end")
    return lambda s: replace_span(s, start, end, new,
                                  expect_removed_lines=args.expect_removed_lines,
                                  must_keep=args.must_keep or ())


def _add_common(sub):
    sub.add_argument("file")
    sub.add_argument("--new-text", help="spliced in VERBATIM; add your own trailing newline")
    sub.add_argument("--new-file", help="file holding the new text, or - for stdin")
    sub.add_argument("--json", action="store_true", help="machine-readable envelope")
    sub.add_argument("--dry-run", action="store_true", help="report the line delta, write nothing")
    sub.add_argument("--no-backup", action="store_true",
                     help="skip the .bak written when git could not restore the file")


def _parser():
    ap = argparse.ArgumentParser(description="Edit a file at an exact anchor, or refuse.")
    subs = ap.add_subparsers(dest="command", required=True)
    for name in ("replace", "insert"):
        sub = subs.add_parser(name)
        _add_common(sub)
        sub.add_argument("--anchor")
        sub.add_argument("--anchor-file", help="file holding the anchor, or - for stdin")
        if name == "insert":
            side = sub.add_mutually_exclusive_group()
            side.add_argument("--after", action="store_true", default=True,
                              help="insert after the anchor (the default)")
            side.add_argument("--before", action="store_true",
                              help="insert before the anchor")
    span = subs.add_parser("replace-span")
    _add_common(span)
    span.add_argument("--start")
    span.add_argument("--start-file")
    span.add_argument("--end")
    span.add_argument("--end-file")
    span.add_argument("--expect-removed-lines", type=int, required=True,
                      help="lines the region must cover; a bigger region is a refusal")
    span.add_argument("--must-keep", action="append",
                      help="text that must still be present after the write (repeatable)")
    return ap


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    target = Path(args.file)
    if not target.is_file():
        print(f"anchor_edit: no such file: {target}", file=sys.stderr)
        return 2
    try:
        result = apply_to_file(target, _build_transform(args), dry_run=args.dry_run,
                               backup=not args.no_backup)
    except AnchorError as exc:
        if args.json:
            print(json.dumps({"ok": False, "command": "anchor_edit", "skipped": [],
                              "data": {"reason": str(exc)}}, indent=2))
        print(f"anchor_edit: refused, nothing written - {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"ok": True, "command": "anchor_edit", "skipped": [],
                          "data": result.as_data()}, indent=2))
    else:
        verb = "would change" if args.dry_run else "changed"
        # Says KEPT rather than staying silent: a pre-existing .bak may predate this session, so
        # a reader must not assume it holds the state from just before this edit.
        kept = " (kept from an earlier run)" if result.backup_reused else ""
        note = f", backup {result.backup}{kept}" if result.backup else ""
        print(f"anchor_edit: {verb} {result.path} ({result.line_delta:+d} lines){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
