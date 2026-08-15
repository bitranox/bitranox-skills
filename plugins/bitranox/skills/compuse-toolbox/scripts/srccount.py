# /// script
# requires-python = ">=3.10"
# ///
"""Count first-party source files per tree, and show how much of the raw count was excluded.

Why: sizing a decision on "how much code lives here" is normally done with a one-off
`find <dir> -name '*.py' -not -path '*/.venv/*' | wc -l`, and that filter is the instrument.
It returned 271423 .py for one subtree against a true 4859, because it covered `.venv` and
missed `venv-*/`, `venv_*/` and `site-packages/`. Nothing failed - the command exited 0 and
printed a confident number that was then quoted as evidence. Vendored trees outnumber
first-party source by one to two orders of magnitude, so whatever the exclusion misses
DOMINATES the result instead of nudging it.

So this tool always reports BOTH numbers plus the excluded share, names which pattern excluded
what, and prints the extensions it searched - a bare 0 is unreadable without them, and reads as
"no code here" when it means "wrong extension".

The share is INFORMATIONAL, never a verdict. A healthy tree here reads 79-99% excluded, so a
high share means the tool worked; there is deliberately no exit code gated on it.

LIMITATION, and it is the same class of error from a new direction: the exclusion list matches
DIRECTORY NAMES, so it cannot see a third-party project CHECKED OUT as ordinary source. A tree
holding an upstream codebase reports those files as first-party, and with the broad default
extension set the headline is dominated by them (measured: one root reads 87696 source, of which
36689 .c sit in one upstream kernel checkout). Detecting that is not possible by name - a nested
`.git` marks every first-party repo here too, so treating one as foreign would zero out the tree.

Two things narrow that. CONTENT markers (see CONTENT_MARKERS) exclude a dependency or cache tree
whatever its name, which a name list structurally cannot do. And the tool refuses to show a total
alone: `source by extension` AND `source by directory` print with EVERY count, so a dominant
subtree is as visible as a dominant extension and the reader excludes it with `--exclude <name>`.
Read those two lines before quoting the total; a headline read on its own is the failure this
tool exists to prevent.

Run: `uv run scripts/srccount.py --root .`                        # default source extensions
     `uv run scripts/srccount.py --root src --root vendor --ext .py`
     `uv run scripts/srccount.py --root . --ext .py --ext .sh --json`
     `uv run scripts/srccount.py --audit --root .`   # check the list against the tree

Exit, counting: 0 = source found, 1 = nothing matched in ANY root (usually a wrong --ext or
                path), 2 = could not count (missing root, unreadable tree).
Exit, --audit:  answers "is the NAME list complete for this tree". 0 = yes, 1 = it has a blind
                spot that the content markers are covering (the COUNT is right either way),
                2 = could not read the tree. Unused members are reported but never set the
                code: on a partial tree nearly every member is unused, and a gate that always
                fires is one nobody reads.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# The exclusion list IS the instrument. Every shape, not the one you type first: the filter
# that produced 271423 had exactly `.venv` and nothing else. Matched against whole path
# COMPONENTS (see excluded_reason), so these are directory names, not substrings.
#
# It is a MAP, not a set, and the set is derived from it, so a name cannot be added without
# saying what creates it. THREE admission rules, all required:
#
#   1. A fixed name that a NAMED TOOL writes. If you cannot say which tool, it does not belong.
#   2. Not a plausible first-party package name. `coverage` fails this - it is a real PyPI
#      package - as do `build`, `dist`, `target` and `out`. A test pins those as never-excluded.
#   3. MEASURED PRESENT in this tree. This is a personal, machine-local jig; its exclusion list
#      is evidence about one machine, not a taxonomy of every build tool that exists.
#
# Rule 3 exists because rules 1 and 2 gate EFFORT, not CORRECTNESS - a plausible reason can be
# written for almost any name, and the list had reached 23 of which 11 occurred nowhere here.
# Measured 2026-08-15 over 455074 directories, one `find -type d -printf '%f'` pass: dropped
# .eggs, .gradle, .mypy_cache, .next, .nox, .nuxt, .parcel-cache, .terraform, .tox,
# dist-packages, htmlcov and the glob `.venv_*`, all at zero occurrences. Re-measure before
# adding: a name that does not occur cannot be excluding anything.
#
# Dropping a name is SAFE because it is not the only defence. An unexcluded generated dir is
# COUNTED, and therefore appears in `source by directory`, one `--exclude <name>` from being
# removed - the decomposition does the work the classifier used to guess at.
#
# Named EXCLUDED rather than VENDORED because it is not all vendored code: dependency trees
# dominate it, but `.git` and `__pycache__` are simply not first-party source either, and
# reporting them under a "vendored" heading would be a small lie in the tool's own output.
EXCLUDED_REASONS: dict[str, str] = {
    ".venv": "virtualenv created by python -m venv / uv, holds installed dependencies",
    "venv": "virtualenv created by python -m venv / uv, holds installed dependencies",
    "site-packages": "install root written by pip / uv inside an environment",
    "node_modules": "dependency root written by npm / yarn / pnpm",
    "vendor": "conventional vendored-dependency dir for go mod vendor and composer",
    "third_party": "conventional vendored-dependency dir in Google-style layouts",
    "thirdparty": "conventional vendored-dependency dir, unspaced spelling",
    ".git": "repository metadata written by git",
    "__pycache__": "bytecode cache written by CPython",
    ".pytest_cache": "run cache written by pytest",
    ".ruff_cache": "lint cache written by ruff",
    ".docusaurus": "site build state written by docusaurus",
}
EXCLUDED_EXACT: frozenset[str] = frozenset(EXCLUDED_REASONS)

# A venv is routinely named for its python or its project, so the shapes are open-ended.
EXCLUDED_GLOB_REASONS: dict[str, str] = {
    "venv-*": "virtualenv named for its python or project, e.g. venv-vk-<user>",
    "venv_*": "virtualenv named for its python or project, e.g. venv_navision-gateway",
    ".venv-*": "hidden virtualenv named for its target, e.g. .venv-3.13 and .venv-win",
    "*.egg-info": "package metadata written by setuptools",
}
EXCLUDED_GLOBS: tuple[str, ...] = tuple(EXCLUDED_GLOB_REASONS)

# CONTENT beats names. A name list structurally cannot catch a dependency tree someone named
# unusually, so these files are checked during COUNTING, not only in --audit, and the exclusion
# propagates to the whole subtree.
#
# A marker must PROVE it, not merely be named that: each carries a VALIDATOR, because checking
# the filename alone would let any directory holding an unrelated file called CACHEDIR.TAG
# silently drop real source from the count. Validation FAILS OPEN - an unreadable or
# unrecognised marker leaves the directory counted, because a counted file is visible in the
# breakdown while a wrongly excluded one is simply gone.
#
# Rule 3 (MEASURED PRESENT) applies here exactly as it does to the name list; the `measured`
# field records what each one actually caught, A/B over five roots on 2026-08-15.
_CACHEDIR_SIGNATURE = b"Signature: 8a477f597d28d172789f06886806bc55"


def _is_cachedir_tag(path: Path) -> bool:
    """The bford.info/cachedir spec: the file BEGINS with the signature line. PURE-ish (reads)."""
    try:
        return path.read_bytes()[: len(_CACHEDIR_SIGNATURE)] == _CACHEDIR_SIGNATURE
    except OSError:
        return False


def _is_pyvenv_cfg(path: Path) -> bool:
    """PEP 405 defines the file by its `home` key, so a stray file of that name is not a venv."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(line.split("=", 1)[0].strip() == "home" for line in text.splitlines() if "=" in line)


@dataclass(frozen=True)
class ContentMarker:
    """What writes this file, how to prove it is really that, and what it measurably catches."""

    reason: str
    validate: Callable[[Path], bool]
    measured: str


CONTENT_MARKERS: dict[str, ContentMarker] = {
    "CACHEDIR.TAG": ContentMarker(
        reason="cache directory - the bford.info convention cargo and tool caches write",
        validate=_is_cachedir_tag,
        measured="6768 files across five roots, almost all a cargo target/; 264 tags in the "
                 "tree and every one carries the signature. Also catches .import_linter_cache, "
                 "which is in no name list here.",
    ),
    "pyvenv.cfg": ContentMarker(
        reason="virtualenv - the file python -m venv writes to mark one",
        validate=_is_pyvenv_cfg,
        measured="1 file across five roots (a venv's bin/Activate.ps1). Small because venv "
                 "CONTENTS live under site-packages, which the name list already covers - this "
                 "reaches only the venv files outside it, and nothing else can.",
    ),
}

# Defaulting to ONE language makes a tool for COMPARING subtrees report 0 for a tree written
# in another, and 0 reads as "no code here" rather than "wrong flag". Prose and data formats
# stay out: this counts source, so .md/.txt/.json/.yaml are not members.
DEFAULT_EXTENSIONS: tuple[str, ...] = (
    ".py", ".sh", ".bash", ".ps1", ".psm1", ".rs", ".go", ".js", ".ts", ".tsx", ".jsx",
    ".rb", ".pl", ".pm", ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".sql", ".lua", ".php",
    ".bas", ".cls", ".vba",
)


@dataclass
class TreeCount:
    """What one tree's count actually consists of."""

    root: Path
    source: int = 0
    excluded: int = 0
    by_pattern: dict[str, int] = field(default_factory=dict)
    by_ext: dict[str, int] = field(default_factory=dict)
    by_top_dir: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.source + self.excluded

    @property
    def excluded_share(self) -> float:
        return 0.0 if self.total == 0 else 100.0 * self.excluded / self.total


def normalise_extensions(extensions: list[str] | None) -> list[str]:
    """`py` and `.py` mean the same; None means the default source set. PURE."""
    if extensions is None:
        return list(DEFAULT_EXTENSIONS)
    return [e if e.startswith(".") else f".{e}" for e in extensions]


def excluded_reason(parts: tuple[str, ...], extra: tuple[str, ...]) -> str | None:
    """The pattern that makes this path excluded, or None. PURE.

    Matching is on whole path COMPONENTS, never on a substring of the path, so a directory
    merely starting with the letters `vendor` (`vendored_by_us_on_purpose/`) is first-party.
    Over-excluding is the mirror of the bug this tool exists to stop.
    """
    for part in parts:
        if part in EXCLUDED_EXACT or part in extra:
            return part
        for glob in EXCLUDED_GLOBS:
            if fnmatch.fnmatch(part, glob):
                return glob
    return None


def _proven_marker(dirpath: Path, filenames: list[str]) -> str | None:
    """The marker this directory PROVES, or None. Name present AND validator satisfied."""
    for name, marker in CONTENT_MARKERS.items():
        if name in filenames and marker.validate(dirpath / name):
            return name
    return None


def count_tree(
    root: Path | str,
    extensions: list[str] | None = None,
    extra_excludes: list[str] | None = None,
) -> TreeCount:
    """Walk root once, splitting matching files into first-party source and excluded.

    Raises FileNotFoundError when root does not exist: a count of 0 for a path that is not
    there is the silent-wrong-answer shape this tool exists to prevent.
    """
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"not a directory: {root}")
    extra = tuple(extra_excludes or ())
    suffixes = set(normalise_extensions(extensions))
    result = TreeCount(root=root)
    root_str = str(root)
    # os.walk, not rglob("*") + is_file(): rglob stats EVERY entry, and these trees hold
    # hundreds of thousands of them inside the very venv dirs being excluded, so the stat
    # storm dominated the runtime on a network/ZFS mount. os.walk hands back filenames
    # already classified by scandir, so the per-file stat disappears. The excluded subtree
    # is still walked - not pruned - because its COUNT is the whole point of the tool.
    content_excluded: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(root_str):
        rel = os.path.relpath(dirpath, root_str)
        parts = () if rel == os.curdir else tuple(rel.split(os.sep))
        reason = excluded_reason(parts, extra)
        if reason is None:
            # os.walk is top-down, so a parent is always seen first: one dict lookup carries
            # a content exclusion down the whole subtree without re-testing ancestors.
            reason = content_excluded.get(os.path.dirname(dirpath))
        if reason is None:
            marker = _proven_marker(Path(dirpath), filenames)
            if marker is not None:
                reason = f"content:{marker}"
        if reason is not None and reason.startswith("content:"):
            content_excluded[dirpath] = reason
        for name in filenames:
            suffix = os.path.splitext(name)[1]
            if suffix not in suffixes:
                continue
            if reason is None:
                result.source += 1
                result.by_ext[suffix] = result.by_ext.get(suffix, 0) + 1
                top = parts[0] if parts else os.curdir
                result.by_top_dir[top] = result.by_top_dir.get(top, 0) + 1
            else:
                result.excluded += 1
                result.by_pattern[reason] = result.by_pattern.get(reason, 0) + 1
    return result


# --- self-audit ---------------------------------------------------------------------------
# Rule 3 (a member must be MEASURED PRESENT here) was a comment, and nothing re-measured as
# the tree changed. This makes it something the tool checks about itself.

@dataclass
class AuditReport:
    """What the exclusion list looks like against the tree as it stands now."""

    roots: list[Path]
    unused_members: list[str] = field(default_factory=list)
    content_only: list[Path] = field(default_factory=list)
    top_counted_dirs: list[tuple[str, int]] = field(default_factory=list)
    ranked_total: int = 0


def audit(
    roots: list[Path | str],
    extensions: list[str] | None = None,
    extra_excludes: list[str] | None = None,
    top: int = 15,
) -> AuditReport:
    """Three checks, in descending order of how much judgement they need.

    1. Members matching no directory - rule 3 drop candidates. INFORMATION, not a failure:
       run against a partial tree almost every member is unused, and a gate that always
       fires is one nobody reads.
    2. Directories the CONTENT markers caught that the NAME list did not - the name list's
       blind spots. Since content exclusion now runs during counting, these are covered, not
       uncaught: the COUNT is right either way. What the exit code answers is the narrower
       question "is the name list complete for this tree", so 1 means it has a gap that
       something else is carrying, not that a number is wrong.
    3. Directory names ranked by how much counted source sits directly in them. No
       classification whatever, just where the number comes from, so a generated or vendored
       tree the list cannot name still surfaces for a human to judge.
    """
    extra = tuple(extra_excludes or ())
    suffixes = set(normalise_extensions(extensions))
    report = AuditReport(roots=[Path(r) for r in roots])
    seen_dirnames: set[str] = set()
    counted: dict[str, int] = {}
    content_excluded: dict[str, str] = {}

    for root in report.roots:
        if not root.is_dir():
            raise FileNotFoundError(f"not a directory: {root}")
        root_str = str(root)
        for dirpath, dirnames, filenames in os.walk(root_str):
            seen_dirnames.update(dirnames)
            rel = os.path.relpath(dirpath, root_str)
            parts = () if rel == os.curdir else tuple(rel.split(os.sep))
            name_reason = excluded_reason(parts, extra)
            reason = name_reason
            if reason is None:
                reason = content_excluded.get(os.path.dirname(dirpath))
            if reason is None:
                marker = _proven_marker(Path(dirpath), filenames)
                if marker is not None and parts:
                    reason = f"content:{marker}"
                    report.content_only.append(Path(dirpath))
            if reason is not None and reason.startswith("content:"):
                content_excluded[dirpath] = reason
            if reason is not None:
                continue
            here = parts[-1] if parts else os.curdir
            for name in filenames:
                if os.path.splitext(name)[1] in suffixes:
                    counted[here] = counted.get(here, 0) + 1

    for name in sorted(EXCLUDED_EXACT):
        if name not in seen_dirnames:
            report.unused_members.append(name)
    for glob in EXCLUDED_GLOBS:
        if not any(fnmatch.fnmatch(d, glob) for d in seen_dirnames):
            report.unused_members.append(glob)

    ranked = sorted(counted.items(), key=lambda kv: (-kv[1], kv[0]))
    report.top_counted_dirs = ranked[:top]
    report.ranked_total = len(ranked)
    return report


def render_audit(report: AuditReport) -> str:
    lines = [f"audit of {len(report.roots)} root(s): " + ", ".join(str(r) for r in report.roots), ""]
    if report.content_only:
        lines.append("NAME-LIST BLIND SPOTS - excluded by CONTENT, no name in the list matched:")
        lines += [f"  {p}" for p in report.content_only]
        lines.append("  the count is already right; add the name only if you want it named")
    else:
        lines.append("name-list blind spots: none (every content marker sat under a known name)")
    lines.append("")
    if report.unused_members:
        lines.append("members matching no directory here (drop candidates IF this is the full corpus):")
        lines.append("  " + ", ".join(report.unused_members))
    else:
        lines.append("every member matched at least one directory")
    lines.append("")
    lines.append("counted source by directory name - judge whether any is generated or vendored:")
    lines += [f"  {n}={c}" for n, c in report.top_counted_dirs]
    hidden = report.ranked_total - len(report.top_counted_dirs)
    if hidden > 0:
        lines.append(f"  ... (+{hidden} more directory names, rerun with --top {report.ranked_total})")
    return "\n".join(lines)


def _top(counts: dict[str, int], limit: int = 12) -> str:
    """Largest first, so a dominant contributor is the first thing read. PURE."""
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    shown = ", ".join(f"{k}={v}" for k, v in ranked[:limit])
    return shown + (f", ... (+{len(ranked) - limit} more)" if len(ranked) > limit else "")


def render_table(counts: list[TreeCount], extensions: list[str]) -> str:
    """Human view: source is what you asked for, the rest is context for reading it.

    The extension list is printed even when nothing matched - a bare 0 cannot be told apart
    from "searched for the wrong thing" without it.
    """
    shown = " ".join(extensions[:8]) + (" ..." if len(extensions) > 8 else "")
    width = max((len(str(c.root)) for c in counts), default=4)
    lines = [f"extensions: {shown}", ""]
    lines.append(f"{'tree'.ljust(width)}  {'source':>8}  {'excluded':>8}  {'share':>7}")
    for c in counts:
        lines.append(
            f"{str(c.root).ljust(width)}  {c.source:>8}  {c.excluded:>8}  {c.excluded_share:>6.1f}%"
        )
    for c in counts:
        # A total is only safe to read beside where it came from. An upstream project CHECKED
        # OUT as ordinary source is invisible to a name-based exclusion list, so the headline
        # is printed with its decomposition ALWAYS, never on a threshold.
        if c.source:
            per_ext = _top(c.by_ext)
            per_dir = _top(c.by_top_dir)
            lines.append(f"  {c.root}: source by extension {per_ext}")
            lines.append(f"  {c.root}: source by directory {per_dir}")
        if c.by_pattern:
            lines.append(f"  {c.root}: excluded by {_top(c.by_pattern)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--root", action="append", default=None, help="tree to count, repeatable [.]")
    p.add_argument("--ext", action="append", default=None,
                   help="file extension, repeatable [a broad source set; see DEFAULT_EXTENSIONS]")
    p.add_argument("--exclude", action="append", default=None,
                   help="extra directory NAME to treat as excluded, repeatable")
    p.add_argument("--json", action="store_true", help="emit a machine-readable envelope")
    p.add_argument("--audit", action="store_true",
                   help="check the exclusion list against the tree instead of counting")
    p.add_argument("--top", type=int, default=15,
                   help="how many directory names --audit ranks [15]; it says when it truncates")
    args = p.parse_args(argv)

    roots = args.root or ["."]
    exts = normalise_extensions(args.ext)

    if args.audit:
        try:
            report = audit(list(roots), extensions=args.ext,
                           extra_excludes=args.exclude, top=args.top)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            print(f"srccount: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps({
                "ok": True,
                "command": "srccount --audit",
                "data": {
                    "roots": [str(r) for r in report.roots],
                    "unused_members": report.unused_members,
                    "content_only": [str(p) for p in report.content_only],
                    "ranked_total": report.ranked_total,
                    "top_counted_dirs": [{"name": n, "source": c} for n, c in report.top_counted_dirs],
                },
                "skipped": [],
            }, indent=1))
        else:
            print(render_audit(report))
        return 1 if report.content_only else 0

    counts: list[TreeCount] = []
    for r in roots:
        try:
            counts.append(count_tree(r, extensions=args.ext, extra_excludes=args.exclude))
        except (FileNotFoundError, PermissionError, OSError) as exc:
            print(f"srccount: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps({
            "ok": True,
            "command": "srccount",
            "data": {
                "extensions": exts,
                "roots": [
                    {
                        "root": str(c.root),
                        "source": c.source,
                        "excluded": c.excluded,
                        "total": c.total,
                        "excluded_share": round(c.excluded_share, 2),
                        "by_pattern": c.by_pattern,
                        "by_ext": c.by_ext,
                        "by_top_dir": c.by_top_dir,
                    }
                    for c in counts
                ],
            },
            "skipped": [],
        }, indent=1))
    else:
        print(render_table(counts, exts))

    # 0 yes / 1 no: nothing matched in ANY root almost always means a wrong --ext or path.
    # Gated on ALL roots, not any: a genuinely empty tree among several is a real answer.
    if not any(c.source for c in counts):
        print(
            f"srccount: no source files matched {' '.join(exts[:8])} in any root - "
            "check --ext and the paths before reading this as 'no code here'",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
