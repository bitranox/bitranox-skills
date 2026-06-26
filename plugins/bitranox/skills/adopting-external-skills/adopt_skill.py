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

<source> is a git URL, a local path to a skill directory, or a path to a SKILL.md.

Pure standard library. Cross-platform: paths via pathlib, git via argv lists (never shell=True).
"""

import argparse
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


def _manifest_license_fields(tree):
    """License ids declared in package/plugin/pyproject manifests (text scan, no parsing deps)."""
    ids = []
    patterns = [
        re.compile(r'"license"\s*:\s*"([^"]+)"'),          # JSON: plugin.json / package.json
        re.compile(r'(?im)^\s*license\s*=\s*["\']([^"\']+)["\']'),  # TOML: pyproject
    ]
    for mf in ("plugin.json", "package.json", "pyproject.toml", ".claude-plugin/plugin.json",
               ".claude-plugin/marketplace.json"):
        fp = tree / mf
        if fp.is_file():
            try:
                txt = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for rx in patterns:
                ids += rx.findall(txt)
    return ids


def find_license(tree):
    """Search a fetched tree (repo root) for a license, beyond any skill subdir.

    Returns a dict: {id, status, copyright, text, notice, where}.
    status is 'accept', 'reject', or 'absent'.
    """
    license_text = ""
    copyright_line = ""
    notice_text = ""
    where = ""

    # 1. A real LICENSE/COPYING file carries both the text and the copyright line.
    for cand in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt",
                 "LICENCE", "LICENSE-MIT"):
        fp = tree / cand
        if fp.is_file():
            try:
                license_text = fp.read_text(encoding="utf-8", errors="replace")
                where = cand
                break
            except OSError:
                pass
    notice_fp = tree / "NOTICE"
    if notice_fp.is_file():
        try:
            notice_text = notice_fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    lic_id = classify_license_text(license_text)
    if license_text:
        m = _COPYRIGHT_RX.search(license_text)
        if m:
            copyright_line = m.group(1).strip()

    # 2. Fall back to SPDX headers and manifest fields for the id.
    if lic_id is None:
        spdx_ids = _SPDX_RX.findall(license_text) if license_text else []
        for f in tree.rglob("*"):
            if f.is_file() and f.suffix.lower() in {".py", ".js", ".ts", ".sh", ".md"}:
                try:
                    head = f.read_text(encoding="utf-8", errors="replace")[:2000]
                except OSError:
                    continue
                spdx_ids += _SPDX_RX.findall(head)
                if spdx_ids:
                    where = where or f"SPDX header in {f.relative_to(tree)}"
                    break
        for sid in spdx_ids + _manifest_license_fields(tree):
            mapped = classify_license_id(sid)
            if mapped:
                lic_id = mapped
                where = where or "manifest/SPDX license field"
                break

    if lic_id == "REJECT":
        return {"id": None, "status": "reject", "copyright": copyright_line,
                "text": license_text, "notice": notice_text, "where": where}
    if lic_id in ACCEPTED:
        return {"id": lic_id, "status": "accept", "copyright": copyright_line,
                "text": license_text, "notice": notice_text, "where": where}
    return {"id": None, "status": "absent", "copyright": copyright_line,
            "text": license_text, "notice": notice_text, "where": where}


# ---------------------------------------------------------------------------
# Fetch / normalize
# ---------------------------------------------------------------------------

def is_url(source):
    return bool(re.match(r"^(https?://|git@|ssh://|git://)", source))


def fetch(source, subdir, workdir):
    """Return (tree_root, skill_dir). URL -> shallow clone; local path -> copy. No other network."""
    if is_url(source):
        if not shutil.which("git"):
            raise SystemExit("error: git not found on PATH; cannot clone a URL source.")
        tree = workdir / "src"
        rc = subprocess.run(["git", "clone", "--depth", "1", source, str(tree)],
                            capture_output=True, text=True)
        if rc.returncode != 0:
            raise SystemExit(f"error: git clone failed:\n{rc.stderr.strip()}")
    else:
        src = Path(source).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"error: source path does not exist: {src}")
        if src.is_file():  # a pasted SKILL.md
            tree = workdir / "src"
            tree.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tree / "SKILL.md")
        else:
            tree = workdir / "src"
            shutil.copytree(src, tree)

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
        raise SystemExit("error: no SKILL.md found in the source; point --subdir at the skill.")
    raise SystemExit("error: multiple skills found; use --subdir to pick one:\n"
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
    '"""Pytest config: put the skill dir (parent of tests/) on sys.path."""\n'
    "import sys\n"
    "from pathlib import Path\n\n"
    "SKILL_DIR = Path(__file__).resolve().parent.parent\n"
    "if str(SKILL_DIR) not in sys.path:\n"
    "    sys.path.insert(0, str(SKILL_DIR))\n"
)


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
    (tests / "conftest.py").write_text(CONFTEST, encoding="utf-8")
    stub = tests / f"test_{script.stem}.py"
    stub.write_text(
        f"# TODO: replace with real behaviour tests (see bitranox:skill-writer).\n"
        f"import {script.stem}  # noqa: F401\n\n\n"
        f"def test_imports():\n    assert True\n",
        encoding="utf-8",
    )
    return stub


def add_credit_line(skill_md, source_desc, lic_id):
    text = skill_md.read_text(encoding="utf-8")
    credit = f"> Adapted from {source_desc} ({lic_id})."
    if "> Adapted from " in text:
        return False
    lines = text.splitlines()
    out, inserted = [], False
    for line in lines:
        out.append(line)
        if not inserted and line.startswith("# "):
            out.append("")
            out.append(credit)
            inserted = True
    if not inserted:  # no H1; prepend
        out = [credit, ""] + lines
    skill_md.write_text("\n".join(out) + "\n", encoding="utf-8")
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
        entry += [f"{lic_id} license text:", "", "```", license_text.strip(), "```", ""]
    block = "\n".join(entry)
    existing = notices_path.read_text(encoding="utf-8") if notices_path.is_file() else "# Third-Party Notices\n"
    if f"### {name}\n" in existing or f"### {name}\n" in existing + "\n":
        return False
    notices_path.write_text(existing.rstrip() + "\n\n---\n\n" + block + "\n", encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_gate_readonly(repo_root):
    gate = repo_root / "plugins" / "bitranox" / "hooks" / "repo-gate.py"
    if not gate.is_file():
        return "  (repo-gate.py not found; skipped)"
    try:
        out = subprocess.run([sys.executable, str(gate), "--ci"], cwd=str(repo_root),
                            capture_output=True, text=True)
    except Exception as exc:  # noqa: BLE001
        return f"  (could not run gate: {exc})"
    return (out.stdout + out.stderr).strip() or "  (no gate output)"


def adopt(args, workdir):
    tree, src_skill = fetch(args.source, args.subdir, workdir)

    lic = find_license(tree)
    if lic["status"] == "reject":
        raise SystemExit("LICENSE GATE: REJECTED - copyleft/incompatible license "
                         f"({lic['where'] or 'detected'}). Cannot redistribute in an MIT "
                         "collection. Nothing was scaffolded.")
    if lic["status"] == "absent":
        raise SystemExit("LICENSE GATE: NO LICENSE FOUND. A missing license is 'all rights "
                         "reserved', not permissive - do NOT assume MIT. Research the source "
                         "online, present what you find, and get an explicit user decision "
                         "before adopting. Nothing was scaffolded.")

    new_name = normalize_name(args.name or derive_name(args.source, args.subdir))
    if not _NAME_RX.match(new_name):
        raise SystemExit(f"error: could not derive a valid skill name from '{new_name}'. "
                         "Pass --name <lower-hyphen-name>.")
    old_name = normalize_name(src_skill.name)

    dest = Path(args.dest).resolve() / new_name
    if dest.exists():
        raise SystemExit(f"error: destination already exists: {dest}")
    shutil.copytree(src_skill, dest)

    # Rewrite cross-refs in every text file.
    rewrites = {}
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".md", ".py", ".txt", ".json", ".yml", ".yaml"}:
            try:
                txt = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            new_txt, n = rewrite_cross_refs(txt, old_name, new_name)
            if n:
                f.write_text(new_txt, encoding="utf-8")
                rewrites[str(f.relative_to(dest))] = n

    # Attribution.
    source_desc = derive_name(args.source, args.subdir) + " (upstream)"
    source_url = args.source if is_url(args.source) else ""
    add_credit_line(dest / "SKILL.md", source_desc, lic["id"])
    repo_root = _find_repo_root(Path(args.dest).resolve())
    notices = repo_root / "plugins" / "bitranox" / "THIRD_PARTY_NOTICES.md"
    append_notice(notices, new_name, source_desc, source_url, lic["id"],
                  lic["copyright"], lic["text"], lic["notice"])

    # Tests scaffold.
    script = ships_scripts(dest)
    stub = scaffold_tests(dest, script) if script else None

    gate_out = run_gate_readonly(repo_root)
    _report(new_name, lic, dest, rewrites, stub, gate_out)


def _find_repo_root(dest):
    for parent in [dest, *dest.parents]:
        if (parent / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json").is_file():
            return parent
    return dest.parents[-1]


def _report(name, lic, dest, rewrites, stub, gate_out):
    print(f"LICENSE GATE: ACCEPTED ({lic['id']}; {lic['where'] or 'detected'}).")
    print(f"Adopted as: {dest}")
    if rewrites:
        print("Cross-ref rewrites:")
        for rel, n in sorted(rewrites.items()):
            print(f"  {rel}: {n}")
    else:
        print("Cross-ref rewrites: none")
    print(f"Tests stub: {stub if stub else 'not needed (no shipped .py) or already present'}")
    print(f"Attribution: credit line + THIRD_PARTY_NOTICES.md entry '{name}' written.")
    print("\nGate (read-only) result:")
    print(gate_out)
    print("\nFOLLOW-UP (do these yourself; this script does NOT):")
    print(f"  1. Add `{name}` to the domains list in using-bitranox-skills/SKILL.md.")
    print("  2. Enhance the skill with bitranox:skill-writer; replace the test stub with real tests.")
    print("  3. Bump plugins/bitranox/.claude-plugin/plugin.json one MINOR; add a CHANGELOG entry.")
    print("  4. Re-run: python3 plugins/bitranox/hooks/repo-gate.py --ci")
    print("  5. Offer the improvement upstream first (bitranox:self-improve).")


def parse_args(argv):
    p = argparse.ArgumentParser(description="Adopt an external Claude Code skill (mechanical helper).")
    p.add_argument("source", help="git URL, local skill dir, or path to a SKILL.md")
    p.add_argument("--name", help="bitranox skill name (lowercase-hyphen); derived if omitted")
    p.add_argument("--dest", default="plugins/bitranox/skills", help="skills dir to adopt into")
    p.add_argument("--subdir", default="", help="path within the source that holds the skill")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    with tempfile.TemporaryDirectory(prefix="adopt-skill-") as tmp:
        adopt(args, Path(tmp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
