# /// script
# requires-python = ">=3.14"
# ///
"""Measure duplicated `## ` sections across a tree of CLAUDE.md files.

Step 1 of this skill's own procedure ("measure, verify, converge, lift") is: split every
CLAUDE.md into `## ` sections, hash each section body, group the identical ones, and compute
the common ancestor of each group. Two sessions hand-rolled that script from scratch before
this one shipped it - the same chore, twice, is what a jig is for.

ENUMERATION IS A PLAIN FILESYSTEM WALK - never `grep`, and never gitignore-aware. A hand-rolled
enumeration built on the session's own `grep` silently drops gitignored files: measured on a
real tree, `grep -rn` found 0 of 30 files a filesystem walk found, because the project CLAUDE.md
files were gitignored. This tool never shells out at all (no `grep`, no `git`), so it cannot
inherit that blind spot. It does not follow symlinked directories (a symlink loop would hang an
unbounded walk) and does not descend into `.git`/`.hg`/`.svn`/`.bzr`.

COPIES ARE PRUNED: a CLAUDE.md under a virtualenv (`.venv`, `.venv-3.12`, ...), `node_modules`,
`site-packages` or `__pycache__`, under `.claude/worktrees/`, or inside a linked git worktree (a
directory whose `.git` FILE points into another repository's `worktrees/`) is a copy nobody edits,
and counting it inflates every duplicate count. A submodule (its `.git` file points into
`modules/`) is a repository of its own and is walked; so is a --root that is itself a linked
worktree. `--no-prune` walks everything; the summary and `data.dirs_pruned` say how many
directories were left out.

SECTION LEVELS: `--levels 2` (the default) splits at `## ` headings only; `--levels 1-3` splits at
every `#`, `##` and `###` heading, each section running to the next heading of a selected level.
A file with no heading at the chosen levels contributes nothing, so the summary and
`data.files_without_sections` count and name those files rather than letting them read as
analysed.

WHAT COUNTS AS "THE SAME SECTION": two occurrences of a heading with a whitespace-normalised
identical body. Normalisation converts CRLF/CR line endings to LF, strips TRAILING whitespace
from each line, collapses a RUN of 2+ blank lines to exactly one, trims blank lines from the
body's start/end, and re-pads every table row (a line starting with `|`): each cell's
surrounding spaces are dropped and a separator cell's dash run becomes `---`, keeping its
alignment colons, so a table a formatter re-padded hashes the same. LEADING INDENTATION IS NOT
TOUCHED - a body that differs only by how far a line is indented hashes DIFFERENT, because
indentation is structure (list nesting, a code fence), not formatting noise a reflow would
introduce.

COMMON ANCESTOR: the deepest directory that contains every member of a variant. A single-member
variant's ancestor is that ONE file's own parent directory - never the filesystem root, and
never the walk root by accident. Members that share no directory at all (a cross-drive case on
Windows) raise a clear error rather than silently answering "/", because a silent root answer
would send a reader to lift a rule to the top of the filesystem.

Run:
  `uv run scripts/claudemd_variance.py --root ~/src`
  `uv run scripts/claudemd_variance.py --root ~/src --json`
  `uv run scripts/claudemd_variance.py --root ~/src --min-members 1`   # include single-copy headings
  `uv run scripts/claudemd_variance.py --root ~/src --levels 1-3`      # split at #, ## and ###

Exit codes: 0 = at least one CLAUDE.md file was found and analysed, 1 = the walk completed but
matched zero files (an empty or misspelled --root), 2 = error (a --root path does not exist,
every matched file failed to decode, a variant's members share no directory, or any other
failure). `--json` emits `{ok, command, skipped, data}` on every exit; ok means the run finished without
error, so it is true on exit 0 and exit 1 and false on exit 2, and only an exit-2 envelope adds
`error` (a zero-match run failed at nothing, so it carries none);
warnings (an unreadable file, a directory the walk cannot list, a bound hit) always go to stderr
so stdout stays parseable. Every JSON string is valid UTF-8: a name that is not shows its
undecodable bytes as \\xNN, and `data.undecodable_paths` lists each such path as
`{shown, bytes_hex}` with its exact bytes.

A `## ` line inside a fenced code block (CommonMark: 3+ backticks or tildes) is not a heading, and
a heading's closing sequence is a run of `#` preceded by whitespace, so `## Using C#` keeps its `#`.
A heading's file count is its number of DISTINCT files: one file repeating a heading is one file.
The largest variant's share is over COPIES, one per distinct (file, body) pair: a file carrying
the heading with two different bodies is a copy of each variant, so more than one variant always
means a share below 100%.

Decisions:
- Copies are pruned by DEFAULT, with --no-prune to opt out: on a real tree of 121 CLAUDE.md files
  21 sat under a virtualenv or a linked worktree, and every one of them inflated a duplicate
  count. Pinned by TestVendoredAndWorktreeCopiesArePruned.
- The default level stays `## ` so an existing report keeps its meaning; --levels widens it, and
  files with no section at the chosen levels are counted instead of silently contributing
  nothing. Pinned by TestHeadingLevels.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Iterable, Iterator, Sequence

__all__ = [
    "DEFAULT_FILENAMES",
    "DEFAULT_LIFT_THRESHOLD",
    "DEFAULT_MAX_FILES",
    "DEFAULT_MIN_MEMBERS",
    "VCS_DIRS",
    "VENDORED_DIRS",
    "DEFAULT_LEVELS",
    "parse_levels",
    "Report",
    "SectionInstance",
    "HeadingGroup",
    "Variant",
    "analyze",
    "common_ancestor",
    "iter_claude_md",
    "normalize_body",
    "read_claude_md",
    "section_hash",
    "split_sections",
]

DEFAULT_FILENAMES = ("CLAUDE.md",)
VCS_DIRS = frozenset({".git", ".hg", ".svn", ".bzr"})
#: Directories holding installed or generated copies, never a CLAUDE.md anyone edits.
VENDORED_DIRS = frozenset({"node_modules", "site-packages", "__pycache__"})
DEFAULT_LEVELS = (2,)

# A walk that never stops is the whole failure mode this bound exists to prevent - a huge or
# misconfigured --root must be reported, not hung on silently.
DEFAULT_MAX_FILES = 20_000

# Headings occurring in exactly one file have nothing to consolidate; hidden by default so the
# report leads with what is actually duplicated. --min-members 1 (or 0) shows everything,
# including the single-member case this tool still defines a real common ancestor for.
DEFAULT_MIN_MEMBERS = 2

# The skill's own heuristic ("a group of 3+") is an ANNOTATION here, not a filter: every variant
# is always reported, this only marks which ones clear the skill's own lift-worthiness bar.
DEFAULT_LIFT_THRESHOLD = 3


# --------------------------------------------------------------------------------------------
# Enumeration - filesystem walk only, no grep, no gitignore awareness
# --------------------------------------------------------------------------------------------


def _is_linked_worktree(directory: Path) -> bool:
    """True when `directory` holds a `.git` FILE pointing into another repository's worktrees/."""
    marker = directory / ".git"
    if not marker.is_file():
        return False
    try:
        text = marker.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "/worktrees/" in text.replace("\\", "/")


def _pruned(dirpath: str, name: str) -> bool:
    """A child directory whose CLAUDE.md files are copies (see the module docstring)."""
    if name in VCS_DIRS or name in VENDORED_DIRS or name.startswith(".venv"):
        return True
    if name == "worktrees" and Path(dirpath).name == ".claude":
        return True
    return _is_linked_worktree(Path(dirpath) / name)


def iter_claude_md(
    root: str | Path,
    *,
    filenames: Sequence[str] = DEFAULT_FILENAMES,
    max_files: int = DEFAULT_MAX_FILES,
    warn: Callable[[str], None] = lambda message: None,
    prune: bool = True,
    pruned: list[Path] | None = None,
) -> Iterator[Path]:
    """Yield every file under `root` whose basename is in `filenames`, via `os.walk` alone.

    Never consults `.gitignore` and never shells out - that is the entire point (see module
    docstring). `followlinks` stays False, so a symlinked directory is listed but not descended
    into, which is what stops a symlink loop from hanging the walk. Stops (with a warning) after
    `max_files` matches so a huge or misconfigured root cannot hang the caller silently. With
    `prune`, copies (virtualenvs, node_modules, linked worktrees) are not descended into, and
    each left-out directory is appended to `pruned` when one is given.
    """
    root = Path(root)
    names = set(filenames)
    if root.is_file():
        if root.name in names:
            yield root
        return
    count = 0

    def unlistable(err: OSError) -> None:
        # Without this, os.walk drops a directory it cannot list and the run reports ok.
        warn(f"cannot list, skipping: {err.filename}: {err}")

    for dirpath, dirnames, entries in os.walk(root, onerror=unlistable, followlinks=False):
        if prune:
            kept = []
            for d in dirnames:
                if not _pruned(dirpath, d):
                    kept.append(d)
                elif pruned is not None and d not in VCS_DIRS:
                    pruned.append(Path(dirpath) / d)
            dirnames[:] = kept
        else:
            dirnames[:] = [d for d in dirnames if d not in VCS_DIRS]
        for entry in sorted(entries):
            if entry not in names:
                continue
            if count >= max_files:
                warn(
                    f"stopped walk after {max_files} matched file(s) under {root} - "
                    "raise --max-files to widen the bound"
                )
                return
            count += 1
            yield Path(dirpath) / entry


def read_claude_md(path: Path, *, warn: Callable[[str], None]) -> str | None:
    """The file's text, or None (with a warning) when it cannot be decoded or read at all.

    Strict utf-8: a stray latin-1 byte must not silently become a replacement character that
    then hashes as something the file never actually contained, and it must not crash the run
    either - it is reported as skipped instead, matching every sibling tool's convention.
    """
    try:
        # utf-8-sig: a byte-order mark is not text, and left in place it hides a first-line heading.
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        warn(f"cannot decode as utf-8, skipping: {path}: {exc}")
        return None
    except OSError as exc:
        warn(f"cannot read, skipping: {path}: {exc}")
        return None


# --------------------------------------------------------------------------------------------
# Section splitting and whitespace-normalised hashing
# --------------------------------------------------------------------------------------------


# CommonMark fences: up to three spaces of indent, then 3+ backticks or tildes. A backtick
# opener's info string may not hold a backtick; a closer is the same character, at least as
# long, followed by nothing but whitespace.
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
# A closing sequence is a run of # preceded by whitespace (or standing alone): "## Using C#"
# keeps its #, "## Closed ##" loses the trailing run.
_CLOSING_RE = re.compile(r"(?:^|(?<![ \t])[ \t]+)#+[ \t]*$")


def _fence_opener(line: str) -> str | None:
    """The fence run that opens a code block on this line, or None."""
    match = _FENCE_RE.match(line)
    if not match:
        return None
    run, info = match.group(1), match.group(2)
    if run[0] == "`" and "`" in info:
        return None
    return run


def _closes(line: str, opener: str) -> bool:
    match = _FENCE_RE.match(line)
    if not match:
        return False
    run, rest = match.group(1), match.group(2)
    return run[0] == opener[0] and len(run) >= len(opener) and not rest.strip()


_HEADING_RE = re.compile(r"(#{1,6}) ")


def _heading_level(line: str) -> int | None:
    match = _HEADING_RE.match(line)
    return len(match.group(1)) if match else None


def _heading_lines(lines: Sequence[str], levels: Sequence[int] = DEFAULT_LEVELS) -> list[int]:
    """Indices of the boundary lines (a heading at one of `levels`, at column 0), skipping every
    line inside a fenced code block."""
    boundaries: list[int] = []
    opener: str | None = None
    for i, line in enumerate(lines):
        if opener is not None:
            if _closes(line, opener):
                opener = None
            continue
        opener = _fence_opener(line)
        if opener is None and _heading_level(line) in levels:
            boundaries.append(i)
    return boundaries


def split_sections(
    text: str, levels: Sequence[int] = DEFAULT_LEVELS
) -> list[tuple[str, str, int]]:
    """Split `text` into (heading, raw_body, start_line) for each heading at column 0 whose level
    is in `levels` (default: `## ` only). With several levels every selected heading starts a
    section of its own; the description below is the default's.

    A section boundary is a line starting, with NO leading whitespace, with exactly `## `
    (two hashes, one space) - `### ` (three hashes) is a subsection and stays inside its parent's
    body, and an indented or fenced `## ` is not a boundary at all. Text before the first such
    heading (frontmatter, a level-1 title) belongs to no section and is dropped. The body
    returned here is the RAW text - callers normalise and hash it separately, so the raw text
    stays available for display.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    boundaries = _heading_lines(lines, levels)
    sections: list[tuple[str, str, int]] = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        heading = _CLOSING_RE.sub("", lines[start].lstrip("#")[1:]).strip()
        body = "\n".join(lines[start + 1 : end])
        sections.append((heading, body, start + 1))  # 1-based line number, for a reader's eye
    return sections


def normalize_body(text: str) -> str:
    """Whitespace-normalise a section body for hashing - see the module docstring for exactly
    what is and is not touched. Leading indentation and every other character are preserved."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [_table_row(line.rstrip()) for line in text.split("\n")]
    collapsed: list[str] = []
    blank_run = False
    for line in lines:
        if line == "":
            if blank_run:
                continue
            blank_run = True
        else:
            blank_run = False
        collapsed.append(line)
    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()
    return "\n".join(collapsed)


_SEPARATOR_CELL = re.compile(r"(:?)-+(:?)")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _table_row(line: str) -> str:
    """A table row with each cell's padding dropped and a separator cell's dashes as `---`.

    Only the space AROUND a cell goes: its own text, an escaped pipe and the row's indentation
    stay. Any other line is returned unchanged.
    """
    stripped = line.lstrip()
    if not stripped.startswith("|"):
        return line
    indent = line[: len(line) - len(stripped)]
    closed = stripped.endswith("|") and len(stripped) > 1
    cells = _CELL_SPLIT.split(stripped)[1:]
    if closed:
        cells = cells[:-1]
    out = []
    for cell in cells:
        cell = cell.strip()
        sep = _SEPARATOR_CELL.fullmatch(cell)
        out.append(f"{sep.group(1)}---{sep.group(2)}" if sep else cell)
    return indent + "|" + "|".join(out) + ("|" if closed else "")


def section_hash(body: str) -> str:
    """sha256 of the whitespace-normalised body, hex-encoded."""
    return hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------
# Common ancestor
# --------------------------------------------------------------------------------------------


def common_ancestor(
    paths: Sequence[str | Path],
    *,
    _commonpath: Callable[[list[str]], str] = os.path.commonpath,
) -> Path:
    """The deepest directory that contains every one of `paths` (files, not directories).

    A single path's ancestor is that file's own PARENT directory - the file itself is not a lift
    target, and the answer is never the filesystem root by construction. Several paths get the
    true shared directory of their parents via `os.path.commonpath`; when no such directory
    exists at all (paths resolve onto different Windows drives) this raises ValueError instead
    of silently returning "/" - a wrong-but-plausible root answer is exactly what would send a
    reader to lift a rule to the top of the filesystem.

    `_commonpath` is an injection seam so the cross-drive/no-common-root branch can be exercised
    deterministically in a test without needing a second real drive.
    """
    if not paths:
        raise ValueError("common_ancestor() needs at least one path")
    parents = [Path(p).resolve().parent for p in paths]
    if len(parents) == 1:
        return parents[0]
    try:
        return Path(_commonpath([str(p) for p in parents]))
    except ValueError as exc:
        raise ValueError(
            f"no common ancestor directory across {[str(p) for p in parents]}: {exc}"
        ) from exc


# --------------------------------------------------------------------------------------------
# Grouping
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SectionInstance:
    """One `## ` occurrence found in one file."""

    path: Path
    heading: str
    body: str
    hash: str
    start_line: int


@dataclass(frozen=True)
class Variant:
    """One whitespace-normalised body shared by however many files carry this heading."""

    heading: str
    hash: str
    members: tuple[Path, ...]
    common_ancestor: Path
    lift_candidate: bool

    @property
    def size(self) -> int:
        return len(self.members)

    def as_dict(self) -> dict[str, object]:
        return {
            "hash": self.hash,
            "hash_short": self.hash[:12],
            "member_count": self.size,
            "members": [p.as_posix() for p in self.members],
            "common_ancestor": self.common_ancestor.as_posix(),
            "lift_candidate": self.lift_candidate,
        }


@dataclass(frozen=True)
class HeadingGroup:
    """Every variant found for one heading text, across the whole walk."""

    heading: str
    variants: tuple[Variant, ...]

    @property
    def total_members(self) -> int:
        """Distinct FILES carrying this heading. A file holding the heading twice is one file,
        not two, so it can never pass --min-members 2 on its own."""
        return len({member for v in self.variants for member in v.members})

    @property
    def largest_variant(self) -> Variant:
        return max(self.variants, key=lambda v: v.size)

    @property
    def copy_count(self) -> int:
        """Distinct (file, body) copies of this heading. Equals total_members unless one file
        carries the heading with two different bodies; that file is one copy of EACH variant."""
        return sum(v.size for v in self.variants)

    @property
    def largest_variant_share(self) -> float:
        """The largest variant's share of the COPIES, not of the files: over files, one file
        holding two bodies made "2 variants, largest covers 100%", which reads as converged."""
        total = self.copy_count
        return (self.largest_variant.size / total) if total else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "heading": self.heading,
            "total_members": self.total_members,
            "copy_count": self.copy_count,
            "variant_count": len(self.variants),
            "largest_variant_share_percent": round(self.largest_variant_share * 100, 1),
            "variants": [v.as_dict() for v in self.variants],
        }


def _group_variants(
    sections: Sequence[SectionInstance],
    *,
    lift_threshold: int,
    _commonpath: Callable[[list[str]], str] = os.path.commonpath,
) -> list[HeadingGroup]:
    by_heading: dict[str, dict[str, list[SectionInstance]]] = {}
    for section in sections:
        by_heading.setdefault(section.heading, {}).setdefault(section.hash, []).append(section)

    groups: list[HeadingGroup] = []
    for heading, by_hash in by_heading.items():
        variants: list[Variant] = []
        for digest, instances in by_hash.items():
            members = tuple(sorted({inst.path for inst in instances}))
            variants.append(
                Variant(
                    heading=heading,
                    hash=digest,
                    members=members,
                    common_ancestor=common_ancestor(members, _commonpath=_commonpath),
                    lift_candidate=len(members) >= lift_threshold,
                )
            )
        variants.sort(key=lambda v: (-v.size, v.hash))
        groups.append(HeadingGroup(heading=heading, variants=tuple(variants)))
    groups.sort(key=lambda g: (-g.total_members, g.heading))
    return groups


# --------------------------------------------------------------------------------------------
# Top-level analysis
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Report:
    roots: tuple[Path, ...]
    filenames: tuple[str, ...]
    files_matched: int
    files_read: int
    files_skipped: int
    section_count: int
    min_members: int
    lift_threshold: int
    heading_groups: tuple[HeadingGroup, ...]
    levels: tuple[int, ...] = DEFAULT_LEVELS
    files_without_sections: tuple[Path, ...] = ()
    dirs_pruned: int = 0

    def all_paths(self) -> set[Path]:
        """Every path the report names: roots, members and common ancestors."""
        paths = set(self.roots) | set(self.files_without_sections)
        for group in self.heading_groups:
            for variant in group.variants:
                paths.update(variant.members)
                paths.add(variant.common_ancestor)
        return paths

    def as_dict(self) -> dict[str, object]:
        return {
            "roots": [p.as_posix() for p in self.roots],
            "filenames": list(self.filenames),
            "files_matched": self.files_matched,
            "files_read": self.files_read,
            "files_skipped": self.files_skipped,
            "section_count": self.section_count,
            "min_members": self.min_members,
            "lift_threshold": self.lift_threshold,
            "heading_groups": [g.as_dict() for g in self.heading_groups],
            "levels": list(self.levels),
            "files_without_sections": [p.as_posix() for p in self.files_without_sections],
            "dirs_pruned": self.dirs_pruned,
            "undecodable_paths": undecodable_paths(self.all_paths()),
        }


def analyze(
    roots: Iterable[str | Path],
    *,
    filenames: Sequence[str] = DEFAULT_FILENAMES,
    max_files: int = DEFAULT_MAX_FILES,
    min_members: int = DEFAULT_MIN_MEMBERS,
    lift_threshold: int = DEFAULT_LIFT_THRESHOLD,
    warn: Callable[[str], None] = lambda message: None,
    levels: Sequence[int] = DEFAULT_LEVELS,
    prune: bool = True,
    _commonpath: Callable[[list[str]], str] = os.path.commonpath,
) -> Report:
    """Walk every root, split and hash every section, and group the duplicates.

    Multiple roots are walked independently, but a file reachable from more than one (nested
    --root arguments) is analysed exactly once, keyed by its resolved absolute path.
    `_commonpath` is passed through to `common_ancestor` (see there). Raises ValueError when a
    variant's members share no directory at all.
    """
    resolved_roots = tuple(Path(r).resolve() for r in roots) or (Path(".").resolve(),)
    seen: dict[Path, Path] = {}
    pruned: list[Path] = []
    for root in resolved_roots:
        for match in iter_claude_md(root, filenames=filenames, max_files=max_files, warn=warn,
                                    prune=prune, pruned=pruned):
            resolved = match.resolve()
            seen.setdefault(resolved, resolved)
    matched = sorted(seen.values())

    sections: list[SectionInstance] = []
    read_count = 0
    without: list[Path] = []
    for path in matched:
        text = read_claude_md(path, warn=warn)
        if text is None:
            continue
        read_count += 1
        found = split_sections(text, levels)
        if not found:
            without.append(path)
        for heading, body, start_line in found:
            sections.append(
                SectionInstance(
                    path=path,
                    heading=heading,
                    body=body,
                    hash=section_hash(body),
                    start_line=start_line,
                )
            )

    groups = _group_variants(sections, lift_threshold=lift_threshold, _commonpath=_commonpath)
    groups = [g for g in groups if g.total_members >= min_members]

    return Report(
        roots=resolved_roots,
        filenames=tuple(filenames),
        files_matched=len(matched),
        files_read=read_count,
        files_skipped=len(matched) - read_count,
        section_count=len(sections),
        min_members=min_members,
        lift_threshold=lift_threshold,
        heading_groups=tuple(groups),
        levels=tuple(levels),
        files_without_sections=tuple(without),
        dirs_pruned=len(set(pruned)),
    )


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claudemd_variance",
        description=(
            "Split every CLAUDE.md under --root into sections ('## ' by default, see --levels), "
            "hash each body, group the "
            "identical ones, and report each variant's common ancestor and the largest variant's "
            "share of the group."
        ),
        epilog=(
            "WHITESPACE NORMALISATION (what makes two bodies 'the same'): CRLF/CR line endings "
            "become LF, trailing whitespace is stripped from each line, a run of 2+ blank lines "
            "collapses to one, and blank lines at the body's start/end are trimmed. LEADING "
            "INDENTATION IS NOT NORMALISED - a body differing only by how far a line is indented "
            "hashes DIFFERENT.\n\n"
            "COMMON ANCESTOR: the deepest directory containing every member of a variant. A "
            "single-member variant's ancestor is that file's own parent directory, never the "
            "filesystem root. Members sharing no directory at all raise a clear error instead of "
            "silently answering '/'.\n\n"
            "Enumeration is a plain filesystem walk - never grep, never gitignore-aware - so a "
            "gitignored CLAUDE.md is found exactly like a tracked one."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="DIR",
        help="directory to walk, repeatable (default: the current directory)",
    )
    parser.add_argument(
        "--filename",
        action="append",
        default=[],
        metavar="NAME",
        help="exact filename to match, repeatable (default: CLAUDE.md)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help=f"stop (with a warning) after this many matches per root (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--min-members",
        type=int,
        default=DEFAULT_MIN_MEMBERS,
        help=f"hide a heading whose total occurrences are below this (default: {DEFAULT_MIN_MEMBERS}; "
        "use 1 to see single-copy headings too, each with its own defined common ancestor)",
    )
    parser.add_argument(
        "--lift-threshold",
        type=int,
        default=DEFAULT_LIFT_THRESHOLD,
        help=f"mark a variant as a lift candidate at this member count or above "
        f"(default: {DEFAULT_LIFT_THRESHOLD}, matching this skill's own '3+' heuristic)",
    )
    parser.add_argument(
        "--levels",
        type=parse_levels,
        default=DEFAULT_LEVELS,
        metavar="N|N-M",
        help="heading levels that start a section, one level or a range (default: 2; "
        "1-3 splits at #, ## and ###)",
    )
    parser.add_argument(
        "--no-prune",
        dest="prune",
        action="store_false",
        help="also walk virtualenvs, node_modules, site-packages and linked worktrees",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable envelope")
    return parser


def parse_levels(text: str) -> tuple[int, ...]:
    """`"2"` -> (2,), `"1-3"` -> (1, 2, 3); levels 1 to 6, ascending. Raises ArgumentTypeError."""
    match = re.fullmatch(r"([1-6])(?:-([1-6]))?", text.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"want a level 1-6 or a range like 1-3, got {text!r}")
    low = int(match.group(1))
    high = int(match.group(2) or low)
    if high < low:
        raise argparse.ArgumentTypeError(f"the range runs backwards: {text!r}")
    return tuple(range(low, high + 1))


def _raw_bytes(text: str) -> bytes:
    """The bytes a str decoded from the filesystem stands for, by os.fsencode's own rule
    (surrogateescape on POSIX); an unpaired surrogate it cannot map is kept by surrogatepass."""
    try:
        return os.fsencode(text)
    except UnicodeError:
        return text.encode("utf-8", "surrogatepass")


def utf8_safe(text: str) -> str:
    """`text` when it is valid UTF-8, else its raw bytes with each undecodable one as \\xNN.

    A POSIX name that is not UTF-8 arrives as lone surrogates: no encoding can print one, and
    json.dumps writes it as a \\udcXX escape that a strict JSON reader rejects or mangles."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return _raw_bytes(text).decode("utf-8", "backslashreplace")
    return text


def undecodable_paths(paths: Iterable[Path]) -> list[dict[str, str]]:
    """{shown, bytes_hex} for every path that is not valid UTF-8, sorted by the shown form.

    `shown` is the string the report prints in the path's place; `bytes_hex` is the exact bytes
    (os.fsencode of the forward-slash form), so a consumer can get the real name back."""
    out: dict[str, dict[str, str]] = {}
    for path in paths:
        text = path.as_posix()
        shown = utf8_safe(text)
        if shown != text:
            out[shown] = {"shown": shown, "bytes_hex": _raw_bytes(text).hex()}
    return [out[key] for key in sorted(out)]


def _json_safe(value: object) -> object:
    """`value` with every string made valid UTF-8 (see utf8_safe), for the one JSON emitter."""
    if isinstance(value, str):
        return utf8_safe(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {utf8_safe(str(key)): _json_safe(item) for key, item in value.items()}
    return value


def _dump_envelope(envelope: dict[str, object]) -> None:
    """Print the --json envelope. The only place JSON is written, so every field - paths,
    warnings, the error text - passes through _json_safe and a new field cannot forget to."""
    print(json.dumps(_json_safe(envelope), indent=2))


def _shown(path: Path) -> str:
    """A path for a human reader (see utf8_safe)."""
    return utf8_safe(path.as_posix())


def _render(report: Report) -> list[str]:
    lines: list[str] = []
    for group in report.heading_groups:
        lines.append(
            f"## {group.heading}  ({group.total_members} file(s), {len(group.variants)} "
            f"variant(s), largest covers {group.largest_variant_share * 100:.1f}%)"
        )
        for variant in group.variants:
            marker = "  LIFT CANDIDATE" if variant.lift_candidate else ""
            lines.append(
                f"  [{variant.hash[:12]}] {variant.size} file(s) -> common ancestor: "
                f"{_shown(variant.common_ancestor)}{marker}"
            )
            for member in variant.members:
                lines.append(f"    - {_shown(member)}")
    if not lines:
        lines.append(
            f"no heading shared by {report.min_members}+ file(s) "
            f"(rerun with --min-members 1 to see single-copy headings)"
        )
    return lines


def _tolerant_stdio() -> None:
    """Escape what the console encoding cannot carry instead of crashing on it: a Windows pipe is
    cp1252 (a CJK heading), and a POSIX path that is not UTF-8 decodes to lone surrogates that no
    encoding accepts. backslashreplace keeps the report readable and loses no information."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)   # absent on a replaced stream
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            pass


def _fail(message: str, *, as_json: bool, warnings: list[str], data: object = None) -> int:
    """Report an error the way the caller asked for output, and return exit code 2."""
    if as_json:
        _dump_envelope({"ok": False, "command": "claudemd_variance", "skipped": warnings,
                        "data": data, "error": message})
    else:
        print(f"claudemd_variance: {message}", file=sys.stderr)
    return 2


def _emit(report: Report, *, as_json: bool, warnings: list[str]) -> None:
    if as_json:
        # ok = ran without error (exit 0 or 1); the zero-match 'no' is the exit code's to carry.
        _dump_envelope({"ok": True, "command": "claudemd_variance",
                        "skipped": warnings, "data": report.as_dict()})
        return
    for line in _render(report):
        print(line)
    print(
        f"claudemd_variance: {report.files_matched} file(s) matched under "
        f"{', '.join(r.as_posix() for r in report.roots)}; {report.files_read} read, "
        f"{report.files_skipped} skipped; {len(report.files_without_sections)} had no section "
        f"at the chosen levels {list(report.levels)}; {report.dirs_pruned} copy dir(s) pruned.",
        file=sys.stderr,
    )
    for path in report.files_without_sections:
        print(f"  no section: {_shown(path)}", file=sys.stderr)


def main(
    argv: Sequence[str] | None = None,
    *,
    _commonpath: Callable[[list[str]], str] = os.path.commonpath,
) -> int:
    """CLI entry point. `_commonpath` reaches `common_ancestor`, so the cross-drive error
    path is testable without a second drive."""
    args = _build_parser().parse_args(argv)
    _tolerant_stdio()

    warnings: list[str] = []

    def warn(message: str) -> None:
        # Always to stderr, --json included, so stdout stays a clean parseable envelope.
        warnings.append(message)
        print(f"claudemd_variance: {message}", file=sys.stderr)

    roots = args.root or ["."]
    for root in roots:
        if not Path(root).exists():
            return _fail(f"--root path does not exist: {root}", as_json=args.json,
                         warnings=warnings)

    filenames = tuple(args.filename) if args.filename else DEFAULT_FILENAMES
    try:
        report = analyze(
            roots,
            filenames=filenames,
            max_files=args.max_files,
            min_members=args.min_members,
            lift_threshold=args.lift_threshold,
            warn=warn,
            levels=args.levels,
            prune=args.prune,
            _commonpath=_commonpath,
        )
    except Exception as exc:  # noqa: BLE001 - exit 1 means "zero files"; a crash must not say that
        return _fail(str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}",
                     as_json=args.json, warnings=warnings)

    if report.files_matched and not report.files_read:
        message = (
            f"every matched file failed to read ({report.files_matched} matched, 0 read) - "
            "see the warnings above"
        )
        warn(message)
        if args.json:
            return _fail(message, as_json=True, warnings=warnings, data=report.as_dict())
        return 2

    _emit(report, as_json=args.json, warnings=warnings)
    return 0 if report.files_matched > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
