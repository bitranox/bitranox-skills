#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# dependencies = ["tomlkit"]
# ///
"""Bump the marketplace version: plugin.json, pyproject.toml and a new CHANGELOG.md section at once.

A maintainer tool for this repo, not something the plugin runs. The version lives in two files
(plugin.json is the source of truth, pyproject.toml the copy the build backend reads) and every
release needs a CHANGELOG heading for it; repo-gate refuses a commit where they disagree. This
jig moves all three together from the version ORIGIN holds:

    bump_version.py --part patch --changelog notes.md        # 10.4.3 -> 10.4.4
    bump_version.py --to 10.5.0 --changelog notes.md [--json]

`notes.md` holds the section BODY (`### Fixed` and its bullets); the jig writes the
`## [<version>]` heading above the newest release heading.

It fetches the remote first and reads origin's plugin.json with `git show`, because the shared
checkout moves under a session: it refuses when the working copy's plugin.json or pyproject.toml
does not name origin's version (a peer pushed a bump, or this checkout was bumped already), when
the target is not above origin's, and when CHANGELOG.md already documents the target. Every new
text is built and checked in memory before the first file is written, then all three are read
back and must agree.

pyproject.toml is edited with tomlkit when it is importable (`uv run` provides it from the
header above); under a bare interpreter the one `version` line of `[project]` is replaced and the
whole document re-parsed with tomllib, which must equal the original apart from that key.

Exit codes: 0 bumped, 1 refused (nothing written), 2 could not run (no git, the fetch or the ref
failed, a file is missing or unreadable).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    import tomlkit
except ImportError:  # the hooks suite runs under a bare interpreter; see the module docstring
    tomlkit = None

__all__ = [
    "HAVE_TOMLKIT",
    "BumpRefused",
    "CouldNotRun",
    "main",
    "next_version",
    "set_pyproject_version",
]

HAVE_TOMLKIT = tomlkit is not None
PLUGIN_JSON = Path("plugins") / "bitranox" / ".claude-plugin" / "plugin.json"
PYPROJECT = Path("pyproject.toml")
CHANGELOG = Path("CHANGELOG.md")
_SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
_RELEASE_HEADING = re.compile(r"^## \[", re.M)
_ANY_H2 = re.compile(r"^## ", re.M)


class BumpRefused(Exception):
    """The bump would be wrong; nothing was written. Exit 1."""


class CouldNotRun(Exception):
    """An input could not be read or git could not answer. Exit 2."""


@dataclass(frozen=True)
class Plan:
    origin: str
    new: str
    texts: dict[Path, str]


# ---- versions -------------------------------------------------------------------------------


def _parse(version: str) -> tuple[int, int, int]:
    match = _SEMVER.fullmatch(version)
    if match is None:
        raise BumpRefused("%r is not a MAJOR.MINOR.PATCH version" % version)
    return int(match[1]), int(match[2]), int(match[3])


def next_version(current: str, part: str) -> str:
    """`current` raised by one `part` (patch, minor or major), lower parts reset to 0."""
    major, minor, patch = _parse(current)
    if part == "major":
        return "%d.0.0" % (major + 1)
    if part == "minor":
        return "%d.%d.0" % (major, minor + 1)
    return "%d.%d.%d" % (major, minor, patch + 1)


# ---- git ------------------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    # An inherited GIT_DIR (a hook, a linked worktree's push) would aim git at another repo.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=env,
                              encoding="utf-8", errors="replace", timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CouldNotRun("git %s failed to run: %s" % (args[0], exc)) from exc
    if proc.returncode != 0:
        raise CouldNotRun("git %s exited %d: %s" % (" ".join(args), proc.returncode, proc.stderr.strip()))
    return proc.stdout


def origin_version(root: Path, ref: str, *, fetch: bool) -> str:
    """The version plugin.json names on `ref`, after fetching that ref's branch when asked."""
    if fetch:
        remote, _, branch = ref.partition("/")
        _git(root, "fetch", "--quiet", remote, branch)
    blob = _git(root, "show", "%s:%s" % (ref, PLUGIN_JSON.as_posix()))
    try:
        return str(json.loads(blob)["version"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CouldNotRun("%s on %s names no version: %s" % (PLUGIN_JSON.as_posix(), ref, exc)) from exc


# ---- the three edits ------------------------------------------------------------------------


def _read(root: Path, rel: Path) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except OSError as exc:
        raise CouldNotRun("%s could not be read: %s" % (rel.as_posix(), exc)) from exc


def _pyproject_version(text: str) -> str:
    try:
        return str(tomllib.loads(text)["project"]["version"])
    except (tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
        raise CouldNotRun("pyproject.toml declares no readable [project] version: %s" % exc) from exc


def set_plugin_version(text: str, version: str) -> str:
    """plugin.json with `version` replaced, key order and two-space layout kept."""
    data = json.loads(text)
    data["version"] = version
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def set_pyproject_version(text: str, version: str, *, editor: str | None = None) -> str:
    """pyproject.toml with `[project].version` replaced and every other byte kept.

    `editor` is "tomlkit" or "stdlib"; None takes tomlkit when it is importable.
    """
    chosen = editor or ("tomlkit" if HAVE_TOMLKIT else "stdlib")
    if chosen == "tomlkit":
        if tomlkit is None:
            raise CouldNotRun("tomlkit is not installed")
        doc = tomlkit.parse(text)
        doc["project"]["version"] = version  # type: ignore[index]
        new = tomlkit.dumps(doc)
    else:
        new = _stdlib_set_version(text, version)
    _assert_only_version_moved(text, new, version)
    return new


def _stdlib_set_version(text: str, version: str) -> str:
    """Replace the one `version = "..."` line inside `[project]`; refuse anything less clear-cut."""
    lines = text.splitlines(keepends=True)
    section, hits = None, []
    for index, line in enumerate(lines):
        header = re.match(r"\s*\[([^\[\]]+)\]\s*(?:#.*)?$", line)
        if header:
            section = header[1].strip()
            continue
        if section == "project" and re.match(r'\s*version\s*=\s*"[^"]*"', line):
            hits.append(index)
    if len(hits) != 1:
        raise BumpRefused("found %d `version = \"...\"` lines in [project]; edit pyproject.toml with tomlkit "
                          "(uv run bump_version.py) instead" % len(hits))
    lines[hits[0]] = re.sub(r'"[^"]*"', '"%s"' % version, lines[hits[0]], count=1)
    return "".join(lines)


def _assert_only_version_moved(old: str, new: str, version: str) -> None:
    # The proof the edit was safe, whichever editor made it: the parsed documents differ in that
    # one key and nowhere else.
    before, after = tomllib.loads(old), tomllib.loads(new)
    if after.get("project", {}).get("version") != version:
        raise BumpRefused("the pyproject.toml edit did not land on [project].version")
    after["project"]["version"] = before.get("project", {}).get("version")
    if before != after:
        raise BumpRefused("the pyproject.toml edit changed more than [project].version")


def add_changelog_section(text: str, version: str, body: str) -> str:
    """CHANGELOG.md with `## [version]` and `body` above the newest release heading."""
    body = body.strip("\n")
    if not body.strip():
        raise BumpRefused("the changelog section is empty")
    if _ANY_H2.search(body):
        raise BumpRefused("the changelog section carries its own `## ` heading; give only its body")
    if re.search(r"^## \[" + re.escape(version) + r"\]", text, re.M):
        raise BumpRefused("CHANGELOG.md already has a ## [%s] section" % version)
    match = _RELEASE_HEADING.search(text)
    if match is None:
        raise CouldNotRun("CHANGELOG.md has no `## [` release heading to insert above")
    section = "## [%s]\n\n%s\n\n" % (version, body)
    return text[: match.start()] + section + text[match.start():]


# ---- the run --------------------------------------------------------------------------------


def plan_bump(root: Path, args: argparse.Namespace) -> Plan:
    """Every new text, built and checked in memory. Raises BumpRefused or CouldNotRun."""
    origin = origin_version(root, args.ref, fetch=args.fetch)
    pj_text, pp_text, cl_text = _read(root, PLUGIN_JSON), _read(root, PYPROJECT), _read(root, CHANGELOG)
    try:
        working = str(json.loads(pj_text)["version"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CouldNotRun("%s names no readable version: %s" % (PLUGIN_JSON.as_posix(), exc)) from exc
    declared = _pyproject_version(pp_text)
    if working != origin or declared != origin:
        raise BumpRefused("the working copy is not at origin's version: %s says %s, plugin.json says %s, "
                          "pyproject.toml says %s. Another session bumped, or this checkout already was; "
                          "sync with %s first." % (args.ref, origin, working, declared, args.ref))
    new = args.to or next_version(origin, args.part)
    if _parse(new) <= _parse(origin):
        raise BumpRefused("%s is not above %s's version %s" % (new, args.ref, origin))
    try:
        body = Path(args.changelog).read_text(encoding="utf-8")
    except OSError as exc:
        raise CouldNotRun("the changelog section file could not be read: %s" % exc) from exc
    texts = {
        PLUGIN_JSON: set_plugin_version(pj_text, new),
        PYPROJECT: set_pyproject_version(pp_text, new),
        CHANGELOG: add_changelog_section(cl_text, new, body),
    }
    return Plan(origin, new, texts)


def apply_plan(root: Path, plan: Plan) -> None:
    for rel, text in plan.texts.items():
        (root / rel).write_text(text, encoding="utf-8", newline="\n")
    _assert_agree(root, plan.new)


def _assert_agree(root: Path, version: str) -> None:
    pj = str(json.loads(_read(root, PLUGIN_JSON))["version"])
    pp = _pyproject_version(_read(root, PYPROJECT))
    documented = re.search(r"^## \[" + re.escape(version) + r"\]", _read(root, CHANGELOG), re.M) is not None
    if not (pj == pp == version and documented):
        raise CouldNotRun("read back plugin.json=%s pyproject.toml=%s changelog documents %s: %s"
                          % (pj, pp, version, documented))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--part", choices=("patch", "minor", "major"), help="raise this part of origin's version")
    target.add_argument("--to", help="the exact new version (must be above origin's)")
    parser.add_argument("--changelog", required=True, help="file holding the new section's body")
    parser.add_argument("--root", default=".", help="repo root (default: the cwd)")
    parser.add_argument("--ref", default="origin/master", help="remote-tracking ref holding the released version")
    parser.add_argument("--no-fetch", dest="fetch", action="store_false", help="trust the ref as last fetched")
    parser.add_argument("--json", action="store_true", help="print a JSON envelope")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        plan = plan_bump(root, args)
        apply_plan(root, plan)
    except BumpRefused as exc:
        return _emit(args.json, 1, "refused: %s" % exc, None)
    except CouldNotRun as exc:
        return _emit(args.json, 2, "could not run: %s" % exc, None)
    data = {"origin": plan.origin, "new": plan.new, "ref": args.ref}
    return _emit(args.json, 0, "bumped %s -> %s (plugin.json, pyproject.toml, CHANGELOG.md)" % (plan.origin, plan.new), data)


def _emit(as_json: bool, code: int, message: str, data: dict[str, str] | None) -> int:
    if as_json:
        print(json.dumps({"ok": code == 0, "command": "bump", "message": message, "data": data}))
    else:
        print(message, file=sys.stdout if code == 0 else sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
