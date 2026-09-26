#!/usr/bin/env python3
"""Mechanical helper for the adopting-external-skills skill.

Fetch a third-party Claude Code skill, run a blocking license gate, normalize it to bitranox
conventions, scaffold a tests/ stub, and record attribution - then print a follow-up checklist.
A human reviews and integrates. This script deliberately does the mechanical parts ONLY.

It NEVER commits, pushes, opens a PR, removes or disables any installed plugin, edits the
user's Claude settings, or reaches the network beyond the single named upstream fetch.

Usage:
    python adopt_skill.py <source> [--name <bitranox-name>] [--dest <skills-dir>]
                          [--subdir <path-within-source>]

<source> is a git URL (file:// included), a local path to a skill directory, or a path to a
SKILL.md.

Exit codes: 0 adopted, 1 the license gate stopped the adoption (nothing was written),
2 error (bad source, clone failure, no marketplace checkout, an existing destination, ...).

Pure standard library. Cross-platform: paths via pathlib, git via argv lists (never shell=True).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Permissive licenses we may redistribute inside this MIT collection.
ACCEPTED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Apache-2.0"}
# Copyleft / strong-share-alike: cannot ship inside an MIT collection.
REJECTED = {"GPL", "LGPL", "AGPL", "MPL"}

# Foreign marketplace namespaces an adopted skill may reference; rewritten to bitranox.
FOREIGN_NAMESPACES = ("superpowers", "obra", "vercel")

_COPYRIGHT_RX = re.compile(r"(?im)^\s*(copyright\s+(?:\(c\)|\xa9|©)?.*?\b\d{4}.*)$")
# The whole expression, not its first id: "MIT OR GPL-3.0-only" read as "MIT" accepted a GPL
# file, and "(MIT OR GPL-2.0-only)" matched nothing at all. A comment closer (`*/`, `-->`) ends it.
_SPDX_RX = re.compile(r"SPDX-License-Identifier:[ \t]*([A-Za-z0-9.\-+() \t]+)")
_NAME_RX = re.compile(r"^[a-z][a-z0-9-]+$")
_BOM = "\ufeff"


# ---------------------------------------------------------------------------
# License gate
# ---------------------------------------------------------------------------

def classify_license_text(text):
    """Map raw license text to a canonical id. Returns an id, the string 'REJECT', or None."""
    if not text:
        return None
    low = text.lower()
    # Reject copyleft first so a dual mention cannot slip through as permissive.
    if "gnu affero general public license" in low or "\nagpl" in low:
        return "REJECT"
    if "gnu lesser general public license" in low:
        return "REJECT"
    if "gnu general public license" in low:
        return "REJECT"
    if "mozilla public license" in low:
        return "REJECT"
    if "apache license" in low and "version 2.0" in low:
        return "Apache-2.0"
    if "permission to use, copy, modify, and/or distribute this software" in low:
        return "ISC"
    if "all advertising materials" in low:
        # BSD-4-Clause: the advertising clause is not in the accepted family, so a human decides.
        return None
    if "redistribution and use in source and binary forms" in low:
        return "BSD-3-Clause" if "neither the name of" in low else "BSD-2-Clause"
    if "permission is hereby granted, free of charge" in low:
        return "MIT"
    return None


def _classify_single_id(sid):
    norm = sid.upper().replace("_", "-")
    for acc in ACCEPTED:
        if norm == acc.upper():
            return acc
    if norm in {"BSD", "BSD-LICENSE"}:
        return "BSD-3-Clause"
    if norm.startswith(("GPL", "LGPL", "AGPL", "MPL")):
        return "REJECT"
    return None


_EXPR_SPLIT_RX = re.compile(r"\s+(?:AND|OR|WITH)\s+|[()]", re.IGNORECASE)


def classify_license_id(spdx):
    """Map an SPDX id or license EXPRESSION (a manifest field, a PEP 639 `license` string, an
    SPDX header) to an accepted id, 'REJECT', or None.

    Every id in an expression counts: one copyleft id rejects it (an `OR` choice included - which
    alternative applies is a human's call, never the gate's), any id or exception it does not know
    leaves it None, and only an expression of accepted ids is accepted, as written.
    """
    if not spdx:
        return None
    s = " ".join(spdx.strip().strip('"').strip("'").split())
    leaves = [leaf.strip() for leaf in _EXPR_SPLIT_RX.split(s) if leaf.strip()]
    if not leaves:
        return None
    mapped = [_classify_single_id(leaf) for leaf in leaves]
    if "REJECT" in mapped:
        return "REJECT"
    if None in mapped:
        return None
    return mapped[0] if len(leaves) == 1 else s


def _accepted(mapped):
    return mapped not in (None, "REJECT")


def _spdx_ids(text):
    """Every SPDX-License-Identifier expression in `text`, with a trailing `-->` remnant cut."""
    out = []
    for raw in _SPDX_RX.findall(text):
        expr = raw.strip().rstrip("-").strip()
        if expr:
            out.append(expr)
    return out


_MANIFEST_NAMES = {"plugin.json", "package.json", "marketplace.json", "pyproject.toml"}
_SPDX_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sh", ".ps1", ".md",
                  ".c", ".h", ".cpp", ".go", ".rs", ".rb", ".java", ".yml", ".yaml", ".toml"}
_VCS_DIRS = {".git", ".hg", ".svn"}
# A license file by NAME: LICENSE / LICENCE / UNLICENSE / COPYING, bare or with a variant tag
# (LICENSE-MIT, COPYING.LESSER, LICENSE.md), plus any file in a REUSE-style LICENSES/ dir. A code
# file that happens to be called license.py is a program, not a license.
_LICENSE_NAME_RX = re.compile(r"^(?:(?:UN)?LICEN[CS]ES?|COPYING)(?:[-.][A-Za-z0-9.-]*)?$",
                              re.IGNORECASE)
_LICENSE_DIRS = {"licenses", "licences"}
_CODE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".ps1", ".json", ".toml", ".yml",
                  ".yaml", ".html", ".css", ".go", ".rs", ".rb", ".java", ".c", ".h"}

try:
    import tomllib
    _TOML_LOADS = tomllib.loads
except ImportError:  # Python 3.10 has no stdlib TOML parser; see _pyproject_license_lines
    _TOML_LOADS = None


_NOTICE_NAMES = {"NOTICE", "NOTICE.TXT", "NOTICE.MD"}


def _root_first(files, tree):
    return sorted(set(files), key=lambda p: (len(p.relative_to(tree).parts), p.as_posix()))


def _subtree_files(tree, base):
    """(every file under `base` outside VCS dirs; one problem per thing the gate cannot vouch for).

    The skill's subtree is what copytree ships, and copytree(symlinks=False) ships a link's
    TARGET: a symlinked dir, or a symlinked file pointing out of `base`, would ship content this
    walk never read, so each is a problem, like a directory that could not be listed."""
    files, problems = [], []

    def onerror(err):
        problems.append(f"{getattr(err, 'filename', None) or '?'}: cannot list "
                        f"({err.strerror or err})")

    for dirpath, dirnames, filenames in os.walk(base, onerror=onerror):
        here = Path(dirpath)
        keep = []
        for d in sorted(dirnames):
            if d in _VCS_DIRS:
                continue
            if (here / d).is_symlink():
                problems.append(f"{(here / d).relative_to(tree).as_posix()}: a symlinked dir "
                                "(copying the skill would ship its target, which the gate "
                                "did not read)")
            else:
                keep.append(d)
        dirnames[:] = keep
        for name in filenames:
            path = here / name
            if path.is_symlink() and not _inside(path, base):
                problems.append(f"{path.relative_to(tree).as_posix()}: a symlink to a file "
                                "outside the skill (copying would ship that file)")
            else:
                files.append(path)
    return files, problems


def _governing_file(entry, tree):
    """True for an ancestor-dir entry that governs what sits below it: a license file, a
    manifest, or a NOTICE. Prose and code in an ancestor dir are not shipped and declare nothing."""
    return (_is_license_file(entry.relative_to(tree)) or entry.name in _MANIFEST_NAMES
            or entry.name.upper() in _NOTICE_NAMES)


def _ancestor_files(tree, skill_dir):
    """(the governing files of each dir from the skill dir's parent up to the source root, plus
    the files of a REUSE LICENSES/ dir beside them; problems). Never their other subtrees: a
    sibling plugin's LICENSE governs the sibling, not the skill."""
    files, problems = [], []
    for d in [p for p in skill_dir.parents if p == tree or tree in p.parents]:
        try:
            entries = sorted(d.iterdir())
        except OSError as exc:
            problems.append(f"{d}: cannot list ({exc.strerror or exc})")
            continue
        for entry in entries:
            if entry.is_dir() and entry.name.lower() in _LICENSE_DIRS:
                sub, sub_problems = _subtree_files(tree, entry)
                files += sub
                problems += sub_problems
            elif entry.is_file() and _governing_file(entry, tree):
                files.append(entry)
    return files, problems


def _scoped_files(tree, skill_dir):
    """(files, problems) of the license scope: the skill's whole subtree (what ships) plus the
    governing files of every ancestor dir up to the source root (what licenses it)."""
    files, problems = _subtree_files(tree, skill_dir)
    anc_files, anc_problems = _ancestor_files(tree, skill_dir)
    return _root_first(files + anc_files, tree), anc_problems + problems


def _read_text(path):
    """(text, None), or ("", reason) when the file cannot be read."""
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace"), None
    except OSError as exc:
        return "", f"unreadable ({exc.strerror or exc})"


def _is_license_file(rel):
    parts = rel.parts
    if len(parts) > 1 and parts[-2].lower() in _LICENSE_DIRS:
        return True
    return bool(_LICENSE_NAME_RX.match(parts[-1])) and rel.suffix.lower() not in _CODE_SUFFIXES


def _walk_keys(node):
    """(key, value) for every mapping key at any depth of a parsed JSON/TOML document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key, value
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def _license_value(value):
    """[(kind, value)] for one `license` value: a string is an id or expression; a table names
    `text`, `file` (pyproject) or `type` (npm); a list holds several. Anything else cannot be read,
    and says so - a shape the gate does not know must stop it, not be skipped."""
    if isinstance(value, str):
        return [("id", value)]
    if isinstance(value, list):
        return [decl for item in value for decl in _license_value(item)] or [
            ("unreadable", "an empty license list")]
    if isinstance(value, dict):
        out = [(kind, value[key]) for key, kind in (("type", "id"), ("text", "text"),
                                                    ("file", "file"))
               if isinstance(value.get(key), str)]
        return out or [("unreadable", f"a license table with keys {sorted(value)}")]
    return [("unreadable", f"a license value of type {type(value).__name__}")]


def _license_files_value(value):
    """[(kind, value)] for a PEP 639 `license-files` value: glob patterns of license files."""
    if isinstance(value, str):
        return [("files", value)]
    if isinstance(value, dict):   # the older setuptools table form
        value = [p for key in ("paths", "globs") for p in (value.get(key) or [])]
    if isinstance(value, list) and value and all(isinstance(p, str) for p in value):
        return [("files", p) for p in value]
    return [("unreadable", "a license-files value it cannot read")]


def _json_license_decls(text):
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return [("unreadable", f"does not parse as JSON ({exc})")]
    return [decl for key, value in _walk_keys(doc) if key in ("license", "licenses")
            for decl in _license_value(value)]


_TOML_LICENSE_LINE = re.compile(r"(?m)^[ \t]*(license(?:-files)?)\b[^=\n]*=[ \t]*(.*)$")
_TOML_LICENSE_TABLE = re.compile(r"(?m)^[ \t]*\[[^\]\n]*\blicense\b[^\]\n]*\]")
_TOML_PLAIN_STRING = re.compile(r"""(?:"([^"\\]*)"|'([^']*)')[ \t]*(?:#.*)?""")


def _pyproject_license_lines(text):
    """The no-tomllib reading: only `license = "<id>"` on one line is understood. Every other
    license key, dotted key or [..license..] table is reported unreadable, so the gate stops."""
    out = []
    for m in _TOML_LICENSE_LINE.finditer(text):
        plain = _TOML_PLAIN_STRING.fullmatch(m.group(2).strip())
        if m.group(1) == "license" and plain and re.match(r"^[ \t]*license[ \t]*=", m.group(0)):
            out.append(("id", plain.group(1) if plain.group(1) is not None else plain.group(2)))
        else:
            out.append(("unreadable", f"`{m.group(0).strip()[:60]}` needs tomllib (Python 3.11+)"))
    out += [("unreadable", f"`{m.group(0).strip()}` needs tomllib (Python 3.11+)")
            for m in _TOML_LICENSE_TABLE.finditer(text)]
    return out


def _pyproject_license_decls(text, loads=_TOML_LOADS):
    """[(kind, value)] for every `license` and `license-files` key in a pyproject.toml, in any
    table ([project], [tool.poetry], ...). `loads` is the TOML parser; None reads lines instead."""
    if loads is None:
        return _pyproject_license_lines(text)
    try:
        doc = loads(text)
    except ValueError as exc:  # tomllib.TOMLDecodeError is a ValueError
        return [("unreadable", f"does not parse as TOML ({exc})")]
    out = []
    for key, value in _walk_keys(doc):
        if key == "license":
            out += _license_value(value)
        elif key == "license-files":
            out += _license_files_value(value)
    return out


def _text_id(text):
    """The id a license text field holds: a bare id or expression, else recognised wording."""
    one_line = " ".join(text.split())
    mapped = classify_license_id(one_line) if "\n" not in text.strip() and len(one_line) < 200 else None
    return mapped if mapped is not None else _license_file_id(text)


def _inside(path, tree):
    try:
        path.resolve().relative_to(tree.resolve())
        return True
    except (OSError, ValueError):
        return False


def _named_file_decl(tree, path, label, where):
    """(mapped, label, where) for a license file a manifest names by path."""
    if not _inside(path, tree):
        return (None, f"{label} lies outside the source", where)
    if not path.is_file():
        return (None, f"{label} not found", where)
    text, problem = _read_text(path)
    if problem:
        return (None, f"{label} {problem}", where)
    return (_license_file_id(text), f"{label} text not recognised", where)


def _manifest_decl(tree, base, kind, value, where):
    """(mapped, label, where) entries for one (kind, value) a manifest declared."""
    if kind == "id":
        return [(classify_license_id(value), f"unrecognised license id {value!r}", where)]
    if kind == "text":
        return [(_text_id(value), "license text not recognised", where)]
    if kind == "file":
        return [_named_file_decl(tree, base / value, f"license file {value!r}", where)]
    if kind == "files":
        try:
            matches = sorted(base.glob(value)) if not Path(value).is_absolute() else []
        except (ValueError, NotImplementedError, OSError):
            matches = []
        return [_named_file_decl(tree, m, f"license file {m.name!r}", where) for m in matches] or [
            (None, f"license-files pattern {value!r} matched no file", where)]
    return [(None, value, where)]


def _manifest_decls(tree, files):
    """Every license declaration in every manifest anywhere in the tree - a vendored package's
    package.json ships with it, so it declares a license of what is adopted too."""
    decls = []
    for f in files:
        if f.name not in _MANIFEST_NAMES:
            continue
        where = f.relative_to(tree).as_posix()
        text, problem = _read_text(f)
        if problem:
            decls.append((None, problem, where))
            continue
        raw = (_pyproject_license_decls(text) if f.name == "pyproject.toml"
               else _json_license_decls(text))
        for kind, value in raw:
            decls += _manifest_decl(tree, f.parent, kind, value, where)
    return decls


def _spdx_decls(tree, files):
    """Every SPDX-License-Identifier expression in the head of every source file, in a stable
    order: the walk order must never decide a legal verdict."""
    decls = []
    for f in files:
        if f.suffix.lower() not in _SPDX_SUFFIXES:
            continue
        where = f"SPDX header in {f.relative_to(tree).as_posix()}"
        text, problem = _read_text(f)
        if problem:
            decls.append((None, problem, where))
            continue
        decls += [(classify_license_id(e), f"unrecognised license id {e!r}", where)
                  for e in _spdx_ids(text[:2000])]
    return decls


def _license_file_decls(tree, files):
    """([(mapped, label, where)], [(where, text)]) for EVERY license file in the tree: an MIT
    LICENSE beside a GPL COPYING is a GPL tree, whichever file a reader opens first."""
    decls, texts = [], []
    for f in files:
        rel = f.relative_to(tree)
        if not _is_license_file(rel):
            continue
        where = rel.as_posix()
        text, problem = _read_text(f)
        if problem:
            decls.append((None, problem, where))
            continue
        decls.append((_license_file_id(text), "license text not recognised", where))
        texts.append((where, text))
    return decls, texts


def _license_file_id(text):
    """The id a license file's text states: its recognised wording, else the SPDX expressions it
    holds (REJECT if any rejects, all combined when all are accepted), else None."""
    lic_id = classify_license_text(text)
    if lic_id or not text:
        return lic_id
    mapped = [classify_license_id(e) for e in _spdx_ids(text)]
    if "REJECT" in mapped:
        return "REJECT"
    if mapped and all(_accepted(m) for m in mapped):
        return _combine(mapped)
    return None


def _combine(ids):
    """One id for several accepted ones: the id itself when they agree, else all of them."""
    unique = sorted(set(ids))
    if len(unique) == 1:
        return unique[0]
    return " AND ".join(f"({i})" if " " in i else i for i in unique)


def _verdict(status, lic_id, where, parts):
    return {"id": lic_id, "status": status, "where": where, **parts}


def _joined(labelled):
    """One text from [(where, text)]: the text itself when there is one, else each labelled."""
    if len(labelled) == 1:
        return labelled[0][1]
    return "\n\n".join(f"{where}:\n\n{text.strip()}" for where, text in labelled)


def _notice_parts(tree, files, texts):
    """{copyright, text, notice} for the attribution: every license file's text, labelled when
    there are several, the first copyright line among them, and every NOTICE in the scope."""
    notices = []
    for f in files:
        if f.name.upper() in _NOTICE_NAMES:
            text, problem = _read_text(f)
            if not problem:
                notices.append((f.relative_to(tree).as_posix(), text))
    match = next((m for m in (_COPYRIGHT_RX.search(t) for _w, t in texts) if m), None)
    return {"copyright": match.group(1).strip() if match else "",
            "text": _joined(texts) if texts else "", "notice": _joined(notices) if notices else ""}


def find_license(tree, skill_dir=None):
    """Search a fetched tree for the license of the skill at `skill_dir` (default: the tree root).

    The scope is what ships plus what governs it: EVERY file of the skill's subtree (what
    copytree copies), and the license files, manifests and NOTICE of each ANCESTOR dir up to the
    tree root (not those dirs' other subtrees - a sibling plugin's LICENSE governs the sibling).
    Within it every declared license counts: every license file (LICENSE, COPYING, LICENSE-*,
    LICENSES/*), every SPDX header, and every `license` / `license-files` value of every
    plugin.json, package.json, marketplace.json and pyproject.toml, in whatever form it takes (an
    SPDX expression, a table with `text` or `file`, an npm `type` object or list). ANY copyleft id
    rejects. Anything the gate cannot read, classify or vouch for - an unlistable dir, a symlink
    whose target would ship unread, an unreadable or unparseable file, a license text it does not
    recognise, an id it can neither accept nor reject, a named license file that is missing -
    stops it for a human ('absent') rather than letting a permissive declaration decide. Returns
    a dict: {id, status, copyright, text, notice, where}; status is 'accept', 'reject' or 'absent'.
    """
    # abspath collapses a "plugins/b/../a" spelling, so the ancestor walk climbs the real chain.
    tree = Path(os.path.abspath(tree))
    skill_dir = tree if skill_dir is None else Path(os.path.abspath(skill_dir))
    if skill_dir != tree and tree not in skill_dir.parents:
        return _verdict("absent", None, f"{skill_dir}: the skill lies outside the source",
                        _notice_parts(tree, [], []))
    files, walk_errors = _scoped_files(tree, skill_dir)
    file_decls, texts = _license_file_decls(tree, files)
    declared = file_decls + _manifest_decls(tree, files) + _spdx_decls(tree, files)
    parts = _notice_parts(tree, files, texts)

    for mapped, _label, where in declared:
        if mapped == "REJECT":
            return _verdict("reject", None, where, parts)
    if walk_errors:
        return _verdict("absent", None, walk_errors[0], parts)
    for mapped, label, where in declared:
        if mapped is None:
            return _verdict("absent", None, f"{where}: {label}", parts)
    if not declared:
        return _verdict("absent", None, "", parts)
    # The id credited: the license files' when there are any (they carry the text the notice
    # reproduces), else every other declaration's.
    source = file_decls or declared
    return _verdict("accept", _combine([m for m, _l, _w in source]),
                    ", ".join(dict.fromkeys(w for _m, _l, w in source)), parts)


# ---------------------------------------------------------------------------
# Fetch / normalize
# ---------------------------------------------------------------------------

class GateStop(Exception):
    """The license gate said no. Exit 1: an answer, not a failure."""


class AdoptError(Exception):
    """The adoption could not run as asked. Exit 2."""


def is_url(source):
    return bool(re.match(r"^(https?://|git@|ssh://|git://|file://)", source))


# Never copied out of a source: a VCS dir would ship another repo's history into the marketplace
# skill dir, and bytecode is build output.
_COPY_IGNORE = shutil.ignore_patterns(".git", ".hg", ".svn", "__pycache__")


def fetch(source, subdir, workdir):
    """Return (tree_root, skill_dir). URL -> shallow clone; local path -> copy. No other network."""
    if is_url(source):
        if not shutil.which("git"):
            raise AdoptError("error: git not found on PATH; cannot clone a URL source.")
        tree = workdir / "src"
        rc = subprocess.run(["git", "clone", "--depth", "1", source, str(tree)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            raise AdoptError(f"error: git clone failed:\n{rc.stderr.strip()}")
    else:
        src = Path(source).expanduser().resolve()
        if not src.exists():
            raise AdoptError(f"error: source path does not exist: {src}")
        if src.is_file():  # a pasted SKILL.md
            tree = workdir / "src"
            tree.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tree / "SKILL.md")
        else:
            tree = workdir / "src"
            shutil.copytree(src, tree, ignore=_COPY_IGNORE)

    base = tree / subdir if subdir else tree
    skill_dir = _locate_skill_dir(base)
    return tree, skill_dir


def _locate_skill_dir(base):
    if (base / "SKILL.md").is_file():
        return base
    found = [p.parent for p in base.rglob("SKILL.md")]
    if len(found) == 1:
        return found[0]
    if not found:
        raise AdoptError("error: no SKILL.md found in the source; point --subdir at the skill.")
    raise AdoptError("error: multiple skills found; use --subdir to pick one:\n"
                     + "\n".join(f"  {p}" for p in found))


def normalize_name(raw):
    name = raw.strip().lower().replace("_", "-").replace(" ", "-")
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name


def derive_name(source, subdir):
    if subdir:
        return Path(subdir).name
    if is_url(source):
        return re.sub(r"\.git$", "", source.rstrip("/").split("/")[-1])
    p = Path(source)
    return p.stem if p.suffix == ".md" else p.name


# A skill name is [a-z0-9-]: a hyphen continues it, so `\b` would match "git" inside "git-worktrees".
_NAME_EDGE_L = r"(?<![A-Za-z0-9_-])"
_NAME_EDGE_R = r"(?![A-Za-z0-9_-])"


def _identity_patterns(old_name):
    """(pattern, replacement-template) for the places the name IS the skill: never plain prose.

    A skill named after its tool (`git`) shares its name with the word the body uses for that
    tool, so a whole-word rewrite turned `git commit` into `<new> commit`. Only a skill reference
    (`<namespace>:<name>`) and a path segment under `skills/` name the skill itself.
    """
    name = re.escape(old_name)
    spaces = "|".join(re.escape(ns) for ns in (*FOREIGN_NAMESPACES, "bitranox"))
    return [
        (rf"{_NAME_EDGE_L}(?:{spaces}):{name}{_NAME_EDGE_R}", "bitranox:{new}"),
        (rf"(?<=skills[/\\]){name}(?=[/\\]|{_NAME_EDGE_R})", "{new}"),
    ]


def rewrite_cross_refs(text, old_name, new_name):
    """Rewrite references to the skill and foreign namespaces to bitranox form. Returns (text, n).

    The skill's name is rewritten only where it identifies the skill (see _identity_patterns);
    the front matter `name:` and a title echoing it are rewrite_identity()'s job.
    """
    changes = 0
    if old_name and old_name != new_name:
        for pattern, template in _identity_patterns(old_name):
            replacement = template.format(new=new_name)
            text, n = re.subn(pattern, lambda _m, r=replacement: r, text)
            changes += n
    for ns in FOREIGN_NAMESPACES:
        new_text, n = re.subn(rf"{_NAME_EDGE_L}{re.escape(ns)}:", "bitranox:", text)
        text, changes = new_text, changes + n
    return text, changes


def count_bare_mentions(text, name):
    """How often `name` still appears as a whole word: prose the human decides about."""
    if not name:
        return 0
    return len(re.findall(rf"{_NAME_EDGE_L}{re.escape(name)}{_NAME_EDGE_R}", text))


def rewrite_identity(text, old_name, new_name):
    """Set the front matter `name:` and an H1 that is exactly the old name. Returns (text, n).

    A replaced line keeps its own "\r", so a CRLF file stays CRLF. A title that says more than
    the name is prose and stays.
    """
    lines = text.split("\n")
    changes = 0

    def replace(i, new_line):
        lines[i] = new_line + ("\r" if lines[i].endswith("\r") else "")

    body = _frontmatter_end(lines)
    for i in range(1, max(body - 1, 1)):
        if lines[i].startswith("name:") and lines[i][len("name:"):].strip().strip("\"'") != new_name:
            replace(i, f"name: {new_name}")
            changes += 1
    h1 = _h1_index(lines, body)
    if old_name and h1 is not None and lines[h1][2:].strip() == old_name:
        replace(h1, f"# {new_name}")
        changes += 1
    return "\n".join(lines), changes


# ---------------------------------------------------------------------------
# Scaffolding / attribution
# ---------------------------------------------------------------------------

CONFTEST = (
    '"""Pytest config: put the skill dir and its script dir on sys.path."""\n'
    "import sys\n"
    "from pathlib import Path\n\n"
    "SKILL_DIR = Path(__file__).resolve().parent.parent\n"
    "for _d in (SKILL_DIR, SKILL_DIR{script_dir}):\n"
    "    if str(_d) not in sys.path:\n"
    "        sys.path.insert(0, str(_d))\n"
)

# Loaded by PATH, not imported by name: a script in scripts/ is not on sys.path at collection,
# and a hyphenated file name is not an importable module name at all.
STUB = (
    "# TODO: replace with real behaviour tests (see bitranox:meta-skill-writer).\n"
    "import importlib.util\n"
    "import sys\n"
    "from pathlib import Path\n\n"
    "SCRIPT = Path(__file__).resolve().parent.parent{script_path}\n\n\n"
    "def _load():\n"
    '    spec = importlib.util.spec_from_file_location("{module}", SCRIPT)\n'
    "    module = importlib.util.module_from_spec(spec)\n"
    "    sys.modules[spec.name] = module\n"
    "    spec.loader.exec_module(module)\n"
    "    return module\n\n\n"
    "def test_the_script_loads():\n"
    "    assert _load() is not None\n"
)


def _path_expr(parts):
    """` / 'a' / 'b'` - a pathlib join expression for generated code."""
    return "".join(" / %r" % part for part in parts)


def ships_scripts(skill_dir):
    for p in skill_dir.rglob("*.py"):
        parts = set(p.relative_to(skill_dir).parts[:-1])
        if parts & {"tests", "demos", "examples", "__pycache__"} or p.name in {"conftest.py", "__init__.py"}:
            continue
        return p
    return None


def scaffold_tests(skill_dir, script):
    tests = skill_dir / "tests"
    if any(tests.glob("test_*.py")):
        return None
    tests.mkdir(parents=True, exist_ok=True)
    rel = script.relative_to(skill_dir).parts
    module = re.sub(r"\W", "_", script.stem)
    (tests / "conftest.py").write_text(CONFTEST.format(script_dir=_path_expr(rel[:-1])),
                                       encoding="utf-8", newline="\n")
    stub = tests / f"test_{module}.py"
    stub.write_text(STUB.format(script_path=_path_expr(rel), module=module),
                    encoding="utf-8", newline="\n")
    return stub


_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def _fence_opener(line):
    """The fence run that opens a code block on this line, or None (CommonMark)."""
    m = _FENCE_RE.match(line)
    if not m or (m.group(1)[0] == "`" and "`" in m.group(2)):
        return None
    return m.group(1)


def _closes(line, opener):
    m = _FENCE_RE.match(line)
    return bool(m and m.group(1)[0] == opener[0] and len(m.group(1)) >= len(opener)
                and not m.group(2).strip())


def _frontmatter_end(lines):
    """Index of the first line AFTER a leading `---` front matter block, else 0. A UTF-8 BOM
    before the opening `---` does not hide it (str.strip() keeps a BOM: it is not whitespace)."""
    if not lines or lines[0].lstrip(_BOM).strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return 0


def _h1_index(lines, start):
    """Index of the first `# ` heading at or after `start`, skipping fenced code; else None."""
    opener = None
    for i in range(start, len(lines)):
        if opener is not None:
            if _closes(lines[i], opener):
                opener = None
            continue
        opener = _fence_opener(lines[i])
        if opener is None and lines[i].startswith("# "):
            return i
    return None


def _read_keeping_eol(path):
    """(text with LF line ends, the file's own line ending) - so a rewrite keeps a CRLF file CRLF.

    A leading UTF-8 BOM is dropped: it sits in front of the `---` and hides the front matter from
    every reader that expects the file to start with it, and a rewrite must not carry it on."""
    raw = path.read_bytes().decode("utf-8")
    if raw.startswith(_BOM):
        raw = raw[len(_BOM):]
    return raw.replace("\r\n", "\n"), ("\r\n" if "\r\n" in raw else "\n")


def _write_keeping_eol(path, text, eol):
    path.write_bytes(text.replace("\n", eol).encode("utf-8"))


def add_credit_line(skill_md, source_desc, lic_id):
    """Insert the credit line after the H1, or after the front matter when there is no H1.

    Returns False when a credit line is already present. The front matter and fenced code are
    skipped when looking for the H1: a `# comment` in either is not a heading, and a credit line
    written into the front matter breaks it.
    """
    text, eol = _read_keeping_eol(skill_md)
    credit = f"> Adapted from {source_desc} ({lic_id})."
    if "> Adapted from " in text:
        return False
    lines = text.split("\n")
    body = _frontmatter_end(lines)
    h1 = _h1_index(lines, body)
    at = h1 + 1 if h1 is not None else body
    if at == 0:
        lines[:0] = [credit, ""]
    else:
        # A blank line after the quote too, or the next paragraph continues the blockquote.
        after = [""] if at < len(lines) and lines[at].strip() else []
        lines[at:at] = ["", credit] + after
    out = "\n".join(lines)
    _write_keeping_eol(skill_md, out if out.endswith("\n") else out + "\n", eol)
    return True


def append_notice(notices_path, name, source_desc, source_url, lic_id, copyright_line,
                  license_text, notice_text):
    entry = [f"### {name}", "",
             f"- Source: {source_desc}" + (f" ({source_url})" if source_url else ""),
             f"- License: {lic_id}",
             f"- Copyright: {copyright_line or 'see upstream'}",
             "- Modified: yes (adapted to bitranox conventions)", ""]
    if lic_id == "Apache-2.0" and notice_text.strip():
        entry += ["Upstream NOTICE:", "", "```", notice_text.strip(), "```", ""]
    if license_text.strip():
        entry += [f"{lic_id} License text:", "", "```", license_text.strip(), "```", ""]
    block = "\n".join(entry)
    if notices_path.is_file():
        existing, eol = _read_keeping_eol(notices_path)
    else:
        existing, eol = "# Third-Party Notices\n", "\n"
    if f"### {name}\n" in existing + "\n":
        return False
    _write_keeping_eol(notices_path, existing.rstrip() + "\n\n---\n\n" + block + "\n", eol)
    return True


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_gate_readonly(repo_root):
    gate = repo_root / "plugins" / "bitranox" / "hooks" / "repo-gate.py"
    if not gate.is_file():
        return "  (repo-gate.py not found; skipped)"
    try:
        # An explicit codec: without one the gate's output is decoded with the locale codec,
        # which fails differently per platform.
        out = subprocess.run([sys.executable, str(gate), "--ci"], cwd=str(repo_root),
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return f"  (could not run gate: {exc})"
    return ((out.stdout or "") + (out.stderr or "")).strip() or "  (no gate output)"


def validate_category(name, repo_root):
    """If a skill-taxonomy.json registry exists, the name's top-level prefix must be a known
    category (or a grandfathered legacy name). No registry -> no constraint (skip). A registry
    that exists but cannot be read stops the adoption: skipping it would silently turn the
    category rule off."""
    path = repo_root / "plugins" / "bitranox" / "skill-taxonomy.json"
    try:
        tax = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except (OSError, ValueError) as exc:
        raise AdoptError(f"error: cannot read {path}: {exc}") from exc
    cats = set((tax.get("categories") or {}).keys())
    if not cats:
        return
    if name in set(tax.get("legacy") or []) or name.split("-", 1)[0] in cats:
        return
    raise AdoptError(
        "error: skill name '%s' has no approved category prefix. Use <category>-[<sub>-]<name>; "
        "approved categories: %s. To open a new category, add it to "
        "plugins/bitranox/skill-taxonomy.json (see CONTRIBUTING.md), then pass --name accordingly."
        % (name, ", ".join(sorted(cats)))
    )


def frontmatter_name(skill_md):
    """The `name:` value of a SKILL.md's front matter, or "" when it has none."""
    try:
        text = skill_md.read_text(encoding="utf-8-sig", errors="replace")   # -sig: drop a BOM
        lines = text.replace("\r\n", "\n").split("\n")
    except OSError:
        return ""
    for line in lines[1:_frontmatter_end(lines)]:
        if line.startswith("name:"):
            return line[len("name:"):].strip().strip("\"'")
    return ""


def upstream_name(args, tree, src_skill):
    """The name the upstream skill calls itself, which its cross-references use.

    The front matter's `name:` first. Else the skill dir's own name - but never the temp copy's
    "src", which is what a SKILL.md at the source root sits in; there the source's own name
    stands in, and a pasted SKILL.md (a file source) has none to offer.
    """
    declared = frontmatter_name(src_skill / "SKILL.md")
    if declared:
        return normalize_name(declared)
    if src_skill != tree:
        return normalize_name(src_skill.name)
    if not is_url(args.source) and Path(args.source).expanduser().is_file():
        return ""
    return normalize_name(derive_name(args.source, args.subdir))


def _gate(lic):
    """Stop unless the license gate accepted."""
    if lic["status"] == "reject":
        raise GateStop("LICENSE GATE: REJECTED - copyleft/incompatible license "
                       f"({lic['where'] or 'detected'}). Cannot redistribute in an MIT "
                       "collection. Nothing was scaffolded.")
    if lic["status"] == "absent":
        raise GateStop("LICENSE GATE: NO LICENSE FOUND"
                       + (f" ({lic['where']})" if lic["where"] else "")
                       + ". A missing license is 'all rights reserved', not permissive - do NOT "
                       "assume MIT. Research the source online, present what you find, and get an "
                       "explicit user decision before adopting. Nothing was scaffolded.")


def _rewrite_tree(dest, old_name, new_name):
    """Rewrite cross-refs in every text file, keeping each file's line endings.

    Returns {relpath: (rewritten, left)}: `left` counts the old name still standing as a plain
    word, which a human must judge (a skill named `git` means the tool there as often as itself).
    """
    rewrites = {}
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".md", ".py", ".txt", ".json", ".yml", ".yaml"}:
            try:
                txt = f.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            is_skill_md = f == dest / "SKILL.md"
            # A BOM in front of SKILL.md's `---` hides the front matter (see _read_keeping_eol).
            had_bom = is_skill_md and txt.startswith(_BOM)
            if had_bom:
                txt = txt[len(_BOM):]
            new_txt, n = rewrite_cross_refs(txt, old_name, new_name)
            if is_skill_md:
                new_txt, m = rewrite_identity(new_txt, old_name, new_name)
                n += m
            if n or had_bom:
                f.write_bytes(new_txt.encode("utf-8"))
            left = count_bare_mentions(new_txt, old_name) if old_name != new_name else 0
            if n or left:
                rewrites[str(f.relative_to(dest))] = (n, left)
    return rewrites


def adopt(args, workdir):
    tree, src_skill = fetch(args.source, args.subdir, workdir)

    lic = find_license(tree, src_skill)
    _gate(lic)

    new_name = normalize_name(args.name or derive_name(args.source, args.subdir))
    if not _NAME_RX.match(new_name):
        raise AdoptError(f"error: could not derive a valid skill name from '{new_name}'. "
                         "Pass --name <lower-hyphen-name>.")
    old_name = upstream_name(args, tree, src_skill)

    repo_root = _find_repo_root(Path(args.dest).resolve())
    validate_category(new_name, repo_root)

    dest = Path(args.dest).resolve() / new_name
    if dest.exists():
        raise AdoptError(f"error: destination already exists: {dest}")
    shutil.copytree(src_skill, dest, ignore=_COPY_IGNORE)
    rewrites = _rewrite_tree(dest, old_name, new_name)

    # Attribution.
    source_desc = derive_name(args.source, args.subdir) + " (upstream)"
    source_url = args.source if is_url(args.source) else ""
    credited = add_credit_line(dest / "SKILL.md", source_desc, lic["id"])
    notices = repo_root / "plugins" / "bitranox" / "THIRD_PARTY_NOTICES.md"
    noticed = append_notice(notices, new_name, source_desc, source_url, lic["id"],
                            lic["copyright"], lic["text"], lic["notice"])

    # Tests scaffold.
    script = ships_scripts(dest)
    stub = scaffold_tests(dest, script) if script else None

    gate_out = run_gate_readonly(repo_root)
    _report(new_name, lic, dest, rewrites, stub, gate_out, credited=credited, noticed=noticed)


def _find_repo_root(dest):
    """The marketplace checkout holding `dest`. Checked before anything is copied: without it the
    notices path points at the filesystem root and the run dies half-way, leaving a credited
    skill dir behind that then blocks a retry."""
    for parent in [dest, *dest.parents]:
        if (parent / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json").is_file():
            return parent
    raise AdoptError(f"error: not inside a marketplace checkout: no ancestor of {dest} holds "
                     "plugins/bitranox/.claude-plugin/plugin.json. Clone the marketplace repo "
                     "and pass --dest <checkout>/plugins/bitranox/skills.")


def _report(name, lic, dest, rewrites, stub, gate_out, *, credited, noticed):
    print(f"LICENSE GATE: ACCEPTED ({lic['id']}; {lic['where'] or 'detected'}).")
    print(f"Adopted as: {dest}")
    if rewrites:
        print("Cross-ref rewrites (rewritten; plain-word mentions of the old name left for review):")
        for rel, (n, left) in sorted(rewrites.items()):
            print(f"  {rel}: {n} rewritten" + (f"; {left} left for review" if left else ""))
    else:
        print("Cross-ref rewrites: none")
    print(f"Tests stub: {stub if stub else 'not needed (no shipped .py) or already present'}")
    credit = "credit line written" if credited else "credit line SKIPPED (already present)"
    notice = (f"THIRD_PARTY_NOTICES.md entry '{name}' written" if noticed
              else f"THIRD_PARTY_NOTICES.md notice entry SKIPPED (already present) for '{name}'")
    print(f"Attribution: {credit}; {notice}.")
    print("\nGate (read-only) result:")
    print(gate_out)
    category = name.split("-", 1)[0]
    print("\nFOLLOW-UP (do these yourself; this script does NOT):")
    print(f"  1. Add the `{category}` category to the domains list in "
          "meta-using-bitranox-skills/SKILL.md only if it is not already there.")
    print("  2. Enhance the skill with bitranox:meta-skill-writer; replace the test stub with real tests.")
    print("  3. Bump plugins/bitranox/.claude-plugin/plugin.json one MINOR; add a CHANGELOG entry.")
    print("  4. Re-run: python3 plugins/bitranox/hooks/repo-gate.py --ci")
    print("  5. Offer the improvement upstream first (bitranox:meta-self-improve).")


def parse_args(argv):
    p = argparse.ArgumentParser(description="Adopt an external Claude Code skill (mechanical helper).")
    p.add_argument("source", help="git URL, local skill dir, or path to a SKILL.md")
    p.add_argument("--name", help="bitranox skill name (lowercase-hyphen); derived if omitted")
    p.add_argument("--dest", default="plugins/bitranox/skills", help="skills dir to adopt into")
    p.add_argument("--subdir", default="", help="path within the source that holds the skill")
    return p.parse_args(argv)


def _tolerant_stdio():
    """Replace what the console encoding cannot carry instead of crashing on it: a Windows pipe
    is cp1252, and a path or gate line outside it would end the report with a traceback."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    _tolerant_stdio()
    try:
        # ignore_cleanup_errors: a clone's read-only object files cannot be removed on Windows,
        # and a finished adoption must not turn into a traceback over temp-dir cleanup.
        with tempfile.TemporaryDirectory(prefix="adopt-skill-", ignore_cleanup_errors=True) as tmp:
            adopt(args, Path(tmp))
    except GateStop as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except AdoptError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - 1 is the gate's "no"; a crash must never read as that
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
