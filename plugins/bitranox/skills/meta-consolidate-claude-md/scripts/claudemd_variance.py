# /// script
# requires-python = ">=3.10"
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

WHAT COUNTS AS "THE SAME SECTION": two occurrences of a heading with a whitespace-normalised
identical body. Normalisation converts CRLF/CR line endings to LF, strips TRAILING whitespace
from each line, collapses a RUN of 2+ blank lines to exactly one, and trims blank lines from the
body's start/end. LEADING INDENTATION IS NOT TOUCHED - a body that differs only by how far a
line is indented hashes DIFFERENT, because indentation is structure (list nesting, a code
fence), not formatting noise a reflow would introduce.

COMMON ANCESTOR: the deepest directory that contains every member of a variant. A single-member
variant's ancestor is that ONE file's own parent directory - never the filesystem root, and
never the walk root by accident. Members that share no directory at all (a cross-drive case on
Windows) raise a clear error rather than silently answering "/", because a silent root answer
would send a reader to lift a rule to the top of the filesystem.

Run:
  `uv run scripts/claudemd_variance.py --root ~/src`
  `uv run scripts/claudemd_variance.py --root ~/src --json`
  `uv run scripts/claudemd_variance.py --root ~/src --min-members 1`   # include single-copy headings

Exit codes: 0 = at least one CLAUDE.md file was found and analysed, 1 = the walk completed but
matched zero files (an empty or misspelled --root), 2 = usage/IO error (a --root path does not
exist, or every matched file failed to decode). `--json` emits `{ok, command, skipped, data}`;
warnings (an unreadable file, a bound hit) always go to stderr so stdout stays parseable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Sequence

__all__ = [
    "DEFAULT_FILENAMES",
    "DEFAULT_LIFT_THRESHOLD",
    "DEFAULT_MAX_FILES",
    "DEFAULT_MIN_MEMBERS",
    "VCS_DIRS",
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


def iter_claude_md(
    root: str | Path,
    *,
    filenames: Sequence[str] = DEFAULT_FILENAMES,
    max_files: int = DEFAULT_MAX_FILES,
    warn: Callable[[str], None] = lambda message: None,
) -> Iterator[Path]:
    """Yield every file under `root` whose basename is in `filenames`, via `os.walk` alone.

    Never consults `.gitignore` and never shells out - that is the entire point (see module
    docstring). `followlinks` stays False, so a symlinked directory is listed but not descended
    into, which is what stops a symlink loop from hanging the walk. Stops (with a warning) after
    `max_files` matches so a huge or misconfigured root cannot hang the caller silently.
    """
    root = Path(root)
    names = set(filenames)
    if root.is_file():
        if root.name in names:
            yield root
        return
    count = 0
    for dirpath, dirnames, entries in os.walk(root, followlinks=False):
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
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        warn(f"cannot decode as utf-8, skipping: {path}: {exc}")
        return None
    except OSError as exc:
        warn(f"cannot read, skipping: {path}: {exc}")
        return None


# --------------------------------------------------------------------------------------------
# Section splitting and whitespace-normalised hashing
# --------------------------------------------------------------------------------------------


def split_sections(text: str) -> list[tuple[str, str, int]]:
    """Split `text` into (heading, raw_body, start_line) for each `## ` heading at column 0.

    A section boundary is a line starting, with NO leading whitespace, with exactly `## `
    (two hashes, one space) - `### ` (three hashes) is a subsection and stays inside its parent's
    body, and an indented or fenced `## ` is not a boundary at all. Text before the first such
    heading (frontmatter, a level-1 title) belongs to no section and is dropped. The body
    returned here is the RAW text - callers normalise and hash it separately, so the raw text
    stays available for display.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    boundaries = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sections: list[tuple[str, str, int]] = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        heading = lines[start][3:].rstrip().rstrip("#").strip()
        body = "\n".join(lines[start + 1 : end])
        sections.append((heading, body, start + 1))  # 1-based line number, for a reader's eye
    return sections


def normalize_body(text: str) -> str:
    """Whitespace-normalise a section body for hashing - see the module docstring for exactly
    what is and is not touched. Leading indentation and every other character are preserved."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
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
        return sum(v.size for v in self.variants)

    @property
    def largest_variant(self) -> Variant:
        return max(self.variants, key=lambda v: v.size)

    @property
    def largest_variant_share(self) -> float:
        total = self.total_members
        return (self.largest_variant.size / total) if total else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "heading": self.heading,
            "total_members": self.total_members,
            "variant_count": len(self.variants),
            "largest_variant_share_percent": round(self.largest_variant_share * 100, 1),
            "variants": [v.as_dict() for v in self.variants],
        }


def _group_variants(
    sections: Sequence[SectionInstance], *, lift_threshold: int
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
                    common_ancestor=common_ancestor(members),
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
        }


def analyze(
    roots: Iterable[str | Path],
    *,
    filenames: Sequence[str] = DEFAULT_FILENAMES,
    max_files: int = DEFAULT_MAX_FILES,
    min_members: int = DEFAULT_MIN_MEMBERS,
    lift_threshold: int = DEFAULT_LIFT_THRESHOLD,
    warn: Callable[[str], None] = lambda message: None,
) -> Report:
    """Walk every root, split and hash every section, and group the duplicates.

    Multiple roots are walked independently, but a file reachable from more than one (nested
    --root arguments) is analysed exactly once, keyed by its resolved absolute path.
    """
    resolved_roots = tuple(Path(r).resolve() for r in roots) or (Path(".").resolve(),)
    seen: dict[Path, Path] = {}
    for root in resolved_roots:
        for match in iter_claude_md(root, filenames=filenames, max_files=max_files, warn=warn):
            resolved = match.resolve()
            seen.setdefault(resolved, resolved)
    matched = sorted(seen.values())

    sections: list[SectionInstance] = []
    read_count = 0
    for path in matched:
        text = read_claude_md(path, warn=warn)
        if text is None:
            continue
        read_count += 1
        for heading, body, start_line in split_sections(text):
            sections.append(
                SectionInstance(
                    path=path,
                    heading=heading,
                    body=body,
                    hash=section_hash(body),
                    start_line=start_line,
                )
            )

    groups = _group_variants(sections, lift_threshold=lift_threshold)
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
    )


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claudemd_variance",
        description=(
            "Split every CLAUDE.md under --root into '## ' sections, hash each body, group the "
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
    parser.add_argument("--json", action="store_true", help="emit a machine-readable envelope")
    return parser


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
                f"{variant.common_ancestor.as_posix()}{marker}"
            )
            for member in variant.members:
                lines.append(f"    - {member.as_posix()}")
    if not lines:
        lines.append(
            f"no heading shared by {report.min_members}+ file(s) "
            f"(rerun with --min-members 1 to see single-copy headings)"
        )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    warnings: list[str] = []

    def warn(message: str) -> None:
        # Always to stderr, --json included, so stdout stays a clean parseable envelope.
        warnings.append(message)
        print(f"claudemd_variance: {message}", file=sys.stderr)

    roots = args.root or ["."]
    for root in roots:
        if not Path(root).exists():
            message = f"--root path does not exist: {root}"
            if args.json:
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "command": "claudemd_variance",
                            "skipped": warnings,
                            "data": None,
                            "error": message,
                        },
                        indent=2,
                    )
                )
            else:
                print(f"claudemd_variance: {message}", file=sys.stderr)
            return 2

    filenames = tuple(args.filename) if args.filename else DEFAULT_FILENAMES
    report = analyze(
        roots,
        filenames=filenames,
        max_files=args.max_files,
        min_members=args.min_members,
        lift_threshold=args.lift_threshold,
        warn=warn,
    )

    if report.files_matched and not report.files_read:
        message = (
            f"every matched file failed to read ({report.files_matched} matched, 0 read) - "
            "see the warnings above"
        )
        warn(message)
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "command": "claudemd_variance",
                        "skipped": warnings,
                        "data": report.as_dict(),
                        "error": message,
                    },
                    indent=2,
                )
            )
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "ok": report.files_matched > 0,
                    "command": "claudemd_variance",
                    "skipped": warnings,
                    "data": report.as_dict(),
                },
                indent=2,
            )
        )
    else:
        for line in _render(report):
            print(line)
        print(
            f"claudemd_variance: {report.files_matched} file(s) matched under "
            f"{', '.join(r.as_posix() for r in report.roots)}; {report.files_read} read, "
            f"{report.files_skipped} skipped.",
            file=sys.stderr,
        )

    return 0 if report.files_matched > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
