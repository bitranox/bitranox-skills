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
_SPDX_RX = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.\-+]+)")
_NAME_RX = re.compile(r"^[a-z][a-z0-9-]+$")


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


def classify_license_id(spdx):
    """Map an SPDX-ish id (from a manifest field or SPDX header) to accept/reject/None."""
    if not spdx:
        return None
    s = spdx.strip().strip('"').strip("'")
    norm = s.upper().replace("_", "-")
    for acc in ACCEPTED:
        if norm == acc.upper():
            return acc
    if norm in {"BSD", "BSD-LICENSE"}:
        return "BSD-3-Clause"
    if norm.startswith(("GPL", "LGPL", "AGPL", "MPL")):
        return "REJECT"
    return None


_MANIFESTS = ("plugin.json", "package.json", "pyproject.toml", ".claude-plugin/plugin.json",
              ".claude-plugin/marketplace.json")
_MANIFEST_RXS = (
    re.compile(r'"license"\s*:\s*"([^"]+)"'),                  # JSON: plugin.json / package.json
    re.compile(r'(?im)^\s*license\s*=\s*["\']([^"\']+)["\']'),  # TOML: pyproject
)
_SPDX_SUFFIXES = {".py", ".js", ".ts", ".sh", ".md"}
_VCS_DIRS = {".git", ".hg", ".svn"}
_LICENSE_FILES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt", "LICENCE",
                  "LICENSE-MIT")


def _manifest_license_fields(tree):
    """(license id, manifest name) for every license field in the known manifests."""
    found = []
    for mf in _MANIFESTS:
        fp = tree / mf
        if not fp.is_file():
            continue
        try:
            txt = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for rx in _MANIFEST_RXS:
            found += [(sid, mf) for sid in rx.findall(txt)]
    return found


def _spdx_headers(tree):
    """(license id, 'SPDX header in <file>') for EVERY file carrying one, in a stable order.

    Every file, not the first: a tree whose first-walked file says MIT and a later one says GPL
    is a GPL tree, and the walk order must never decide a legal verdict."""
    found = []
    for f in sorted(tree.rglob("*")):
        if f.suffix.lower() not in _SPDX_SUFFIXES or _VCS_DIRS & set(f.relative_to(tree).parts):
            continue
        try:
            if not f.is_file():
                continue
            head = f.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError:
            continue
        where = f"SPDX header in {f.relative_to(tree).as_posix()}"
        found += [(sid, where) for sid in _SPDX_RX.findall(head)]
    return found


def _read_license_file(tree):
    """(text, filename) of the first LICENSE/COPYING file at the tree root, or ("", "")."""
    for cand in _LICENSE_FILES:
        fp = tree / cand
        if fp.is_file():
            try:
                return fp.read_text(encoding="utf-8", errors="replace"), cand
            except OSError:
                pass
    return "", ""


def _license_file_id(text):
    """The id a LICENSE file's text states: its recognised wording, else the SPDX ids it holds
    (REJECT if any rejects, the first when all are accepted), else None."""
    lic_id = classify_license_text(text)
    if lic_id or not text:
        return lic_id
    mapped = [classify_license_id(sid) for sid in _SPDX_RX.findall(text)]
    if "REJECT" in mapped:
        return "REJECT"
    if mapped and all(m in ACCEPTED for m in mapped):
        return mapped[0]
    return None


def _verdict(status, lic_id, where, parts):
    return {"id": lic_id, "status": status, "where": where, **parts}


def find_license(tree):
    """Search a fetched tree (repo root) for a license, beyond any skill subdir.

    Every declared id counts: the LICENSE file, every SPDX header and every manifest field. ANY
    copyleft id rejects; a LICENSE file whose text is not recognised, or a declared id that is
    neither accepted nor rejected, stops the gate for a human ('absent') rather than letting a
    stray permissive header elsewhere decide. Returns a dict: {id, status, copyright, text,
    notice, where}; status is 'accept', 'reject', or 'absent'.
    """
    license_text, license_file = _read_license_file(tree)
    notice_text = ""
    notice_fp = tree / "NOTICE"
    if notice_fp.is_file():
        try:
            notice_text = notice_fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    match = _COPYRIGHT_RX.search(license_text) if license_text else None
    parts = {"copyright": match.group(1).strip() if match else "", "text": license_text,
             "notice": notice_text}

    file_id = _license_file_id(license_text)
    declared = [(classify_license_id(sid), sid, where)
                for sid, where in _manifest_license_fields(tree) + _spdx_headers(tree)]
    if file_id == "REJECT":
        return _verdict("reject", None, license_file, parts)
    for mapped, _sid, where in declared:
        if mapped == "REJECT":
            return _verdict("reject", None, where, parts)
    if license_text and file_id is None:
        return _verdict("absent", None, f"{license_file} (license text not recognised)", parts)
    for mapped, sid, where in declared:
        if mapped is None:
            return _verdict("absent", None, f"unrecognised license id {sid!r} ({where})", parts)
    if file_id:
        return _verdict("accept", file_id, license_file, parts)
    if declared:
        mapped, _sid, where = declared[0]
        return _verdict("accept", mapped, where, parts)
    return _verdict("absent", None, "", parts)


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


def rewrite_cross_refs(text, old_name, new_name):
    """Rewrite the skill's own name and foreign namespaces to bitranox form. Returns (text, n)."""
    changes = 0
    if old_name and old_name != new_name:
        new_text, n = re.subn(rf"\b{re.escape(old_name)}\b", new_name, text)
        text, changes = new_text, changes + n
    for ns in FOREIGN_NAMESPACES:
        new_text, n = re.subn(rf"\b{re.escape(ns)}:", "bitranox:", text)
        text, changes = new_text, changes + n
    return text, changes


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
    """Index of the first line AFTER a leading `---` front matter block, else 0."""
    if not lines or lines[0].strip() != "---":
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
    """(text with LF line ends, the file's own line ending) - so a rewrite keeps a CRLF file CRLF."""
    raw = path.read_bytes().decode("utf-8")
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
        lines = skill_md.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").split("\n")
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
    """Rewrite cross-refs in every text file, keeping each file's line endings. {relpath: n}."""
    rewrites = {}
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".md", ".py", ".txt", ".json", ".yml", ".yaml"}:
            try:
                txt = f.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new_txt, n = rewrite_cross_refs(txt, old_name, new_name)
            if n:
                f.write_bytes(new_txt.encode("utf-8"))
                rewrites[str(f.relative_to(dest))] = n
    return rewrites


def adopt(args, workdir):
    tree, src_skill = fetch(args.source, args.subdir, workdir)

    lic = find_license(tree)
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
        print("Cross-ref rewrites:")
        for rel, n in sorted(rewrites.items()):
            print(f"  {rel}: {n}")
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
