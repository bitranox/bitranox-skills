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
  `uv run scripts/anchor_edit.py batch --spec edits.json` - many exact replacements, across
       files, every one checked before ANY file is written
  add `--json` for an envelope, `--dry-run` to see the line delta without writing
  `uv run scripts/anchor_edit.py reap F` lists F's backups; `--apply` deletes them

`batch` reads a JSON spec (a file, or - for stdin): a list of edits, or an object
`{"edits": [...], "expect_line_delta": {"<abs path>": N}}`. Each edit is
`{"file": "<abs path>", "old": "...", "new": "...", "count": 1}`; `count` (default 1) is how many
times `old` must occur, and every occurrence is replaced. Edits to one file apply in order, each
seeing the previous result. Nothing is written unless every edit matches its count and every
`expect_line_delta` holds - so a one-line record edit that must not change the line count states
`0` there. Two spellings of one path are one file.

The new text is spliced in VERBATIM - no newline, blank line or indentation is added for you,
so text meant to land as its own line must carry its own trailing newline. Stated because it
is the one thing a reader cannot infer from the flags, and getting it wrong silently glues the
insertion onto the anchor's line.

A file git could not restore is copied to `<name>.bak` first - untracked, gitignored, or tracked
but carrying uncommitted work. Tracked alone is not enough: `git checkout -- <file>` restores from
HEAD, so for a dirty file it discards precisely the content nobody else has. Every run gets its
OWN copy - `.bak`, then `.bak.001`, `.bak.002` upward, higher number newer and zero-padded so a
name sort is age order - so no run can destroy the state another one recorded, and the run prints
the exact path it wrote. The copy is byte-exact.

`reap` deletes those backups once git CAN restore the file (tracked, committed, nothing local),
and refuses otherwise. It previews unless given `--apply`, because it cannot tell a `.bak` this
tool wrote from one another tool left, and because the backups hold states from BEFORE each edit
that git may never have seen: committing keeps the result, not the steps.

Line endings are kept: a file whose every newline is CRLF is matched and edited as LF (so an LF
anchor still matches) and written back as CRLF, new text with CRLF of its own included; any other
file is edited byte for byte. The file must be UTF-8; a BOM is kept.

Exit codes: 0 = the edit was applied (or, with --dry-run, would be), 2 = it was not: refused with
nothing written (the anchor is absent or ambiguous, a postcondition failed, reap of a file git
cannot restore), or a usage or IO error (unreadable or non-UTF-8 file, missing anchor argument,
a write that failed), or a crash. A refusal is a refusal of the whole action, so it is 2, not 1;
the message (and `data.refused` under --json) says which it was. `--json` prints the envelope
`{ok, command, data, skipped}` on every exit; `ok` is false exactly on exit 2.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from _cli_envelope import EnvelopeArgumentParser, emit, run_guarded


class AnchorError(Exception):
    """A precondition or postcondition failed, so nothing was written.

    One exception type rather than several because every case has the same consequence for the
    caller - the file is untouched - and the message carries which case it was.
    """


class UsageError(Exception):
    """A bad invocation or an IO failure, as opposed to a refusal. Both exit 2; the envelope's
    `data.refused` tells them apart."""


def line_count(text: str) -> int:
    """Lines as a line-oriented file has them: split on newline only.

    `str.splitlines` also breaks on form feed, U+2028 and friends, so a Python file holding a
    form feed would count one line more than it has.
    """
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def occurrences(text: str, anchor: str) -> int:
    """How many times the anchor appears, OVERLAPPING ones included. Zero and two are both
    refusals, for opposite reasons.

    `str.count` skips an occurrence that overlaps the previous one, so "}\\n}" in "}\\n}\\n}\\n"
    counts once although it starts at offsets 0 and 2 - an ambiguous anchor passed as unique.
    """
    if not anchor:
        return len(text) + 1
    found, at = 0, text.find(anchor)
    while at != -1:
        found += 1
        at = text.find(anchor, at + 1)
    return found


def require_unique(text: str, anchor: str, label: str = "anchor") -> int:
    """The offset of the ONLY occurrence, or raise naming the count.

    Zero means the file is not the one you think it is. Two or more means the edit would land on
    whichever came first, which is a coin toss decided by things like whether the construct is
    also quoted in a docstring above it.
    """
    found = occurrences(text, anchor)
    if found != 1:
        head = anchor.strip().split("\n")[0] if anchor.strip() else anchor
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
        lost_line = before[:i + 1].rstrip("\n").split("\n")[-1] or before[i]
        raise AnchorError(f"the edit removed text it should have kept, at: {lost_line!r}")


def replace_exact(text: str, old: str, new: str) -> str:
    """Replace the one occurrence of `old` with `new`, or refuse."""
    require_unique(text, old, "old text")
    result = text.replace(old, new, 1)
    if result == text and old != new:
        raise AnchorError("the replacement produced no change, which cannot be right here")
    return result


def replace_counted(text: str, old: str, new: str, count: int = 1) -> str:
    """Replace every occurrence of `old`, which must occur exactly `count` times, or refuse.

    Overlapping occurrences are refused when `count` is above 1: `str.replace` rewrites only the
    non-overlapping ones, so "aa" in "aaa" counts twice and is replaced once.
    """
    if count == 1:
        return replace_exact(text, old, new)
    found = occurrences(text, old)
    if found != count:
        head = old.strip().split("\n")[0] if old.strip() else old
        raise AnchorError(f"old text appears {found} times, expected {count}: {head!r}")
    if text.count(old) != count:
        raise AnchorError(f"old text overlaps itself, so replacing all {count} is ambiguous: "
                          f"{old!r}")
    return text.replace(old, new)


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
    # From stop + 1, not stop + len(end): a second copy OVERLAPPING the first is still a second.
    if text.find(end, stop + 1) != -1:
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
    removed = line_count(text[begin:stop])
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

    def __init__(self, path: Path, line_delta: int, backup: Path | None, written: bool):
        self.path = path
        self.line_delta = line_delta
        self.backup = backup
        self.written = written

    def as_data(self) -> dict:
        return {"path": str(self.path), "line_delta": self.line_delta,
                "backup": str(self.backup) if self.backup else None, "written": self.written}


def _git(path: Path, *args):
    """Run git in the file's directory, or None when git cannot be run at all.

    LC_ALL=C because a localized message is not a stable thing to branch on.
    GIT_LITERAL_PATHSPECS=1 because the file name is passed as a pathspec, and as a glob
    `f[1].md` matches a tracked `f1.md`, answering for a different file.
    """
    try:
        return subprocess.run(
            ["git", *args], cwd=str(path.parent), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, "LC_ALL": "C", "GIT_LITERAL_PATHSPECS": "1"})
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

    `ls-files -v` must also tag it `H`: a skip-worktree (`S`) or assume-unchanged (lower-case)
    file reports clean in `git status` whatever local work it holds.
    """
    tracked = _git(path, "ls-files", "-v", "--error-unmatch", "--", path.name)
    if tracked is None or tracked.returncode != 0 or not tracked.stdout.startswith("H "):
        return False
    status = _git(path, "status", "--porcelain", "--", path.name)
    return status is not None and status.returncode == 0 and not status.stdout.strip()


def _numbered_backups(path: Path):
    """`(number, path)` for every `<name>.bak.<digits>`, padded (`.001`) or not (`.1`) alike.

    Unpadded names are what earlier versions wrote, and they still hold their place in the
    sequence. A suffix that is not all ASCII digits (`.bak.orig`) is somebody else's file.
    """
    prefix = path.name + ".bak."
    for sibling in path.parent.glob(_glob_escape(prefix) + "*"):
        suffix = sibling.name[len(prefix):]
        if suffix.isascii() and suffix.isdigit():
            yield int(suffix), sibling


def _backup_indexes(path: Path):
    """The numbers already taken, whatever sits at each name: a taken name is never reused."""
    return (index for index, _ in _numbered_backups(path))


def existing_backups(path: Path) -> list[Path]:
    """This file's backups on disk, oldest first: `.bak`, then the numbered ones by number.

    Regular files only (a symlink to one counts): a directory that happens to carry a
    backup-shaped name was not written by this tool and is not a copy of anything.
    """
    first = path.with_name(path.name + ".bak")
    found = [first] if first.is_file() else []
    numbered = sorted((index, sibling) for index, sibling in _numbered_backups(path)
                      if sibling.is_file())
    return found + [sibling for _, sibling in numbered]


def reap_backups(path: Path, *, apply: bool) -> list[Path]:
    """The backups of a file git can restore, deleted when `apply` is set; refused otherwise.

    Raises:
        AnchorError: git cannot restore the file, so its backups may be the only copies left.
        UsageError: a delete failed; the backups listed before it are already gone.
    """
    if not is_recoverable_from_git(path):
        raise AnchorError(f"git cannot restore {path} (untracked, ignored, or carrying "
                          "uncommitted work), so its backups may be the only copies")
    backups = existing_backups(path)
    for backup in backups if apply else ():
        try:
            backup.unlink()
        except OSError as exc:
            raise UsageError(f"cannot delete {backup}: {exc}; any listed before it are deleted"
                             ) from exc
    return backups


def _glob_escape(text: str) -> str:
    """Escape glob metacharacters, so a file named `a[1].md` finds its own backups."""
    return "".join(f"[{c}]" if c in "*?[" else c for c in text)


def next_backup_path(path: Path) -> Path:
    """The next backup name: `<name>.bak`, then `<name>.bak.001`, `.bak.002`, and upward.

    Nothing is ever overwritten. Each copy is the only record of the state before its own edit,
    and the file is being backed up at all precisely because git cannot restore it, so reusing a
    name would destroy a state no other copy holds. `.bak` is the original and a higher number is
    newer.

    The number is zero-padded to three digits so a plain name sort is age order, and it is one
    past the HIGHEST number present rather than the first gap: refilling a deleted `.001` would
    file the newest state under the oldest number.

    A `.bak` some other tool left behind is skipped for the same reason - it is somebody's only
    copy of something, and this tool did not put it there.

    The count is unbounded on purpose: a safety copy that deletes itself after N runs is not one.
    Past 999 the number simply widens (`.bak.1000`), so name order breaks there; a refused edit
    would be the worse failure.
    """
    first = path.with_name(path.name + ".bak")
    if not first.exists():
        return first
    index = max(_backup_indexes(path), default=0) + 1
    candidate = path.with_name(f"{path.name}.bak.{index:03d}")
    while candidate.exists():  # a name only a racing run could have taken since the scan
        index += 1
        candidate = path.with_name(f"{path.name}.bak.{index:03d}")
    return candidate


def _is_all_crlf(text: str) -> bool:
    """Every newline is part of a CRLF, and there is at least one."""
    return "\n" in text and text.count("\r\n") == text.count("\n")


def _read_file(path: Path) -> tuple[bytes, str]:
    """(raw bytes, decoded text). UsageError when unreadable or not UTF-8."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise UsageError(f"cannot read {path}: {exc}") from exc
    try:
        return raw, raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UsageError(f"{path} is not UTF-8 ({exc}); nothing written") from exc


def _write_bytes(target: Path, data: bytes, what: str) -> None:
    try:
        target.write_bytes(data)
    except OSError as exc:
        raise UsageError(f"{what}: {exc}") from exc


def _back_to_crlf(before: str, after: str) -> str:
    """The CRLF file's text again, from the LF form it was edited in.

    A CR LF in `after` came from the NEW text, not from the file, whenever `before` holds none -
    the file's own CRLFs were all turned into LF - so it is made LF first; otherwise converting
    every LF wrote it back as CR CR LF. When `before` does hold one (the file had a CR before a
    CRLF, a CR that is content), it is left alone, since the two can no longer be told apart.
    """
    lf = after if "\r\n" in before else after.replace("\r\n", "\n")
    return lf.replace("\n", "\r\n")


class _Plan:
    """A transformed file held in memory, not yet written: what `commit_plan` needs."""

    def __init__(self, path: Path, raw: bytes, before: str, after: str, crlf: bool):
        self.path = path
        self.raw = raw
        self.before = before
        self.after = after
        self.crlf = crlf

    @property
    def line_delta(self) -> int:
        return line_count(self.after) - line_count(self.before)


def plan_file(path: Path, transform) -> _Plan:
    """Read and transform the file in memory. Raises AnchorError / UsageError; writes nothing."""
    path = Path(path)
    raw, text = _read_file(path)
    crlf = _is_all_crlf(text)
    before = text.replace("\r\n", "\n") if crlf else text
    return _Plan(path, raw, before, transform(before), crlf)


def commit_plan(plan: _Plan, *, backup: bool = True) -> EditResult:
    """Write a planned edit, backing the file up first when git could not restore it."""
    saved = None
    if backup and not is_recoverable_from_git(plan.path):
        saved = next_backup_path(plan.path)
        _write_bytes(saved, plan.raw, f"cannot write the backup {saved}, nothing written")
    out = _back_to_crlf(plan.before, plan.after) if plan.crlf else plan.after
    where = f"the pre-edit content is in {saved}" if saved else "restore it from git"
    _write_bytes(plan.path, out.encode("utf-8"),
                 f"writing {plan.path} failed, it may be unchanged or partly written - {where}")
    return EditResult(plan.path, plan.line_delta, saved, written=True)


def apply_to_file(path: Path, transform, *, dry_run: bool = False, backup: bool = True):
    """Read, transform, and write the file, backing it up first when git does not track it.

    Read and written as BYTES, so line endings survive: an all-CRLF file is transformed as LF
    (an LF anchor still matches) and written back as CRLF, any other file byte for byte. The
    backup is the original bytes.
    """
    plan = plan_file(path, transform)
    if dry_run:
        return EditResult(plan.path, plan.line_delta, None, written=False)
    return commit_plan(plan, backup=backup)


class BatchRefusal(AnchorError):
    """A batch refused before any write, naming the edit (1-based) when one edit caused it."""

    def __init__(self, index: int | None, message: str):
        super().__init__(message)
        self.index = index


class BatchEdit:
    """One exact replacement of a batch, numbered from 1 in the order the spec gave it."""

    def __init__(self, index: int, file: Path, old: str, new: str, count: int):
        self.index = index
        self.file = file
        self.old = old
        self.new = new
        self.count = count


_EDIT_KEYS = {"file", "old", "new", "count"}
_SPEC_KEYS = {"edits", "expect_line_delta"}


def _spec_path(value, where: str) -> Path:
    if not isinstance(value, str) or not value:
        raise UsageError(f"{where}: 'file' must be a non-empty string")
    path = Path(value)
    if not path.is_absolute():
        raise UsageError(f"{where}: refusing a relative path, pass an absolute one: {value}")
    if not path.is_file():
        raise UsageError(f"{where}: no such file: {value}")
    return path


def _spec_edit(index: int, row) -> BatchEdit:
    where = f"edit {index}"
    if not isinstance(row, dict):
        raise UsageError(f"{where}: must be an object, not {type(row).__name__}")
    unknown = set(row) - _EDIT_KEYS
    if unknown:
        raise UsageError(f"{where}: unknown key(s) {sorted(unknown)}")
    for key in ("old", "new"):
        if not isinstance(row.get(key), str):
            raise UsageError(f"{where}: '{key}' is required and must be a string")
    if not row["old"]:
        raise UsageError(f"{where}: 'old' is empty, which matches everywhere")
    count = row.get("count", 1)
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise UsageError(f"{where}: 'count' must be a positive integer")
    return BatchEdit(index, _spec_path(row.get("file"), where), row["old"], row["new"], count)


def parse_batch_spec(text: str) -> tuple[list[BatchEdit], dict[Path, int]]:
    """The spec's edits and its expected line delta per RESOLVED path. Raises UsageError."""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise UsageError(f"the spec is not JSON: {exc}") from exc
    if isinstance(doc, list):
        doc = {"edits": doc}
    if not isinstance(doc, dict):
        raise UsageError("the spec must be a list of edits or an object with 'edits'")
    unknown = set(doc) - _SPEC_KEYS
    if unknown:
        raise UsageError(f"unknown spec key(s) {sorted(unknown)}")
    rows = doc.get("edits")
    if not isinstance(rows, list) or not rows:
        raise UsageError("no edits in the spec")
    edits = [_spec_edit(i, row) for i, row in enumerate(rows, start=1)]
    expect_raw = doc.get("expect_line_delta", {})
    if not isinstance(expect_raw, dict):
        raise UsageError("'expect_line_delta' must map an absolute path to an integer")
    expect: dict[Path, int] = {}
    for name, delta in expect_raw.items():
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise UsageError(f"expect_line_delta[{name!r}] must be an integer")
        expect[_spec_path(name, f"expect_line_delta[{name!r}]").resolve()] = delta
    return edits, expect


def plan_batch(edits: list[BatchEdit], expect: dict[Path, int]) -> list[_Plan]:
    """Every file's edits applied in memory, in spec order, or the first refusal.

    Grouped by RESOLVED path: two spellings of one file planned apart would each start from the
    disk copy, and the second write would silently drop the first one's edits.
    """
    order: list[Path] = []
    groups: dict[Path, list[BatchEdit]] = {}
    for edit in edits:
        key = edit.file.resolve()
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(edit)
    unplanned = set(expect) - set(groups)
    if unplanned:
        names = sorted(map(str, unplanned))
        raise UsageError(f"expect_line_delta names a file no edit touches: {names}")
    plans = []
    for key in order:
        plan = plan_file(key, lambda text, todo=groups[key]: _apply_in_order(text, todo))
        want = expect.get(key)
        if want is not None and plan.line_delta != want:
            raise BatchRefusal(None, f"{key} would change by {plan.line_delta:+d} lines, "
                                     f"expected {want:+d}")
        plans.append(plan)
    return plans


def _apply_in_order(text: str, edits: list[BatchEdit]) -> str:
    for edit in edits:
        try:
            text = replace_counted(text, edit.old, edit.new, edit.count)
        except AnchorError as exc:
            raise BatchRefusal(edit.index, f"edit {edit.index} ({edit.file}): {exc}") from exc
    return text


def commit_batch(plans: list[_Plan], *, backup: bool = True) -> list[EditResult]:
    """Write every plan. A failed write names the files already written, which stay written."""
    done: list[EditResult] = []
    for plan in plans:
        try:
            done.append(commit_plan(plan, backup=backup))
        except UsageError as exc:
            written = ", ".join(str(r.path) for r in done) or "none"
            raise UsageError(f"{exc}; files already written: {written}") from exc
    return done


def _read_stdin() -> str:
    """stdin as UTF-8 whatever the locale, with the universal newlines read_text would apply."""
    data = sys.stdin.buffer.read().decode("utf-8-sig")
    return data.replace("\r\n", "\n").replace("\r", "\n")


def _text_from(inline, file_arg, label):
    """Exactly one of --X / --X-file, with `-` meaning stdin. utf-8-sig: a file written by
    Windows PowerShell 5.1 starts with a BOM, which would otherwise become part of the anchor."""
    if inline is not None and file_arg is not None:
        raise UsageError(f"give either --{label} or --{label}-file, not both")
    if inline is not None:
        return inline
    if file_arg is None:
        raise UsageError(f"--{label} or --{label}-file is required")
    try:
        if file_arg == "-":
            return _read_stdin()
        return Path(file_arg).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"cannot read --{label}-file: {exc}") from exc


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
    ap = EnvelopeArgumentParser(description="Edit a file at an exact anchor, or refuse.",
                                envelope_command="anchor_edit")
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
    batch = subs.add_parser("batch", help="many exact replacements, all checked before any write")
    batch.add_argument("--spec", required=True, help="JSON spec file, or - for stdin")
    batch.add_argument("--json", action="store_true", help="machine-readable envelope")
    batch.add_argument("--dry-run", action="store_true",
                       help="report each file's line delta, write nothing")
    batch.add_argument("--no-backup", action="store_true",
                       help="skip the .bak written when git could not restore a file")
    reap = subs.add_parser("reap", help="delete a file's backups once git can restore the file")
    reap.add_argument("file")
    reap.add_argument("--apply", action="store_true",
                      help="delete them; without it the backups are only listed")
    reap.add_argument("--json", action="store_true", help="machine-readable envelope")
    return ap


def _reconfigure_streams() -> None:
    """A cp1252 console or pipe must print '?' for an unencodable path, not crash after the
    write has already happened."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (OSError, ValueError):
                pass


def main(argv=None) -> int:
    """The CLI. An uncaught exception exits 2 with the envelope under --json, never a traceback."""
    return run_guarded(_main, argv, command="anchor_edit")


def _main(argv=None) -> int:
    _reconfigure_streams()
    args = _parser().parse_args(argv)
    if args.command == "batch":
        return _run_batch(args)
    target = Path(args.file)
    if not target.is_absolute():
        # Which file a relative path names depends on the cwd, and a cwd persists across calls.
        # The absent-anchor check does NOT cover this: a sibling repo is exactly where the anchor
        # is most likely to be PRESENT in the wrong file - template-copied docs, a section
        # duplicated across repos - so the edit lands elsewhere and exits 0.
        return _usage(args, f"refusing a relative path, pass an absolute one: {target}")
    if not target.is_file():
        return _usage(args, f"no such file: {target}")
    if args.command == "reap":
        return _run_reap(target, args)
    try:
        result = apply_to_file(target, _build_transform(args), dry_run=args.dry_run,
                               backup=not args.no_backup)
    except AnchorError as exc:
        return _fail(args, f"refused, nothing written - {exc}", exc, refused=True)
    except UsageError as exc:
        # The message itself says whether anything was written: a failed target write may
        # already have left a backup behind.
        return _fail(args, f"error - {exc}", exc)
    if args.json:
        emit(0, "anchor_edit", result.as_data())
    else:
        verb = "would change" if args.dry_run else "changed"
        # The exact path, because a later run writes .bak.001, .bak.002 and so on - printing a bare
        # "backup written" would leave the reader to guess which of them this run produced. The
        # reap hint sits here because this line is where the reader learns a backup exists.
        note = (f", backup {result.backup} (once committed, clear with: "
                f"anchor_edit.py reap {result.path} --apply)" if result.backup else "")
        print(f"anchor_edit: {verb} {result.path} ({result.line_delta:+d} lines){note}")
    return 0


def _fail(args, message: str, exc: Exception, *, refused: bool = False, **data) -> int:
    """Exit 2. `refused` marks a refusal (nothing written) apart from a usage or IO error."""
    if args.json:
        emit(2, "anchor_edit", {"reason": str(exc), **({"refused": True} if refused else {}),
                                **data}, error=str(exc))
    print(f"anchor_edit: {message}", file=sys.stderr)
    return 2


def _usage(args, message: str) -> int:
    if getattr(args, "json", False):
        emit(2, "anchor_edit", {"reason": message}, error=message)
    print(f"anchor_edit: {message}", file=sys.stderr)
    return 2


def _read_spec(spec: str) -> str:
    try:
        if spec == "-":
            return sys.stdin.buffer.read().decode("utf-8-sig")
        return Path(spec).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError(f"cannot read --spec: {exc}") from exc


def _run_batch(args) -> int:
    try:
        edits, expect = parse_batch_spec(_read_spec(args.spec))
        plans = plan_batch(edits, expect)
        results = ([EditResult(p.path, p.line_delta, None, written=False) for p in plans]
                   if args.dry_run else commit_batch(plans, backup=not args.no_backup))
    except BatchRefusal as exc:
        return _fail(args, f"refused, nothing written - {exc}", exc, refused=True,
                     edit=exc.index)
    except AnchorError as exc:
        return _fail(args, f"refused, nothing written - {exc}", exc, refused=True)
    except UsageError as exc:
        return _fail(args, f"error - {exc}", exc)
    if args.json:
        emit(0, "anchor_edit", {"dry_run": args.dry_run,
                                "files": [{**r.as_data(), "edits": sum(
                                    1 for e in edits if e.file.resolve() == r.path)}
                                          for r in results]})
        return 0
    verb = "would change" if args.dry_run else "changed"
    for r in results:
        note = f", backup {r.backup}" if r.backup else ""
        print(f"anchor_edit: {verb} {r.path} ({r.line_delta:+d} lines){note}")
    return 0


def _run_reap(target: Path, args) -> int:
    try:
        backups = reap_backups(target, apply=args.apply)
    except AnchorError as exc:
        return _fail(args, f"refused, nothing deleted - {exc}", exc, refused=True)
    except UsageError as exc:
        return _fail(args, f"error - {exc}", exc)
    if args.json:
        emit(0, "anchor_edit", {"path": str(target), "backups": [str(b) for b in backups],
                                "deleted": args.apply})
        return 0
    if not backups:
        print(f"anchor_edit: no backups of {target}")
        return 0
    head = "deleted" if args.apply else "would delete (pass --apply)"
    print(f"anchor_edit: {head} {len(backups)} backup(s) of {target}:")
    for backup in backups:
        print(f"  {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
