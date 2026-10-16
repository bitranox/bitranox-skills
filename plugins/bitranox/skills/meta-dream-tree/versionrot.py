# /// script
# requires-python = ">=3.14"
# ///
"""Find memory facts bound to a version that a newer release has superseded.

Why: "fixed in bmk 3.13.0", "btx_lib_mail 1.5.0 streams delivery", "verified on Claude Code
2.1.198" are true sentences that stop being useful lessons once the package moves on. They pass
every other dream check - they contradict no other fact, the file they name still exists, and a
named version even reads as the re-testable kind of claim - so without this scan they stay in the
always-loaded index indefinitely.

What it does: reads every fact a set of levels points at (hook AND body), finds each version
number, works out which package it belongs to, and compares it with that package's CURRENT
version. Current versions come from the repos on disk (every `pyproject.toml` and
`.claude-plugin/plugin.json` under `--repos`, default: the memory tree's anchor), from
`--current NAME=VERSION`, and with `--pypi` from PyPI. Nothing is guessed: a package it cannot
resolve is reported `unresolved`, never compared.

A superseded claim is a CANDIDATE. The dream re-checks it against the current release and then
rewords it to the current state, archives it (a fixed bug, a finished migration, a test snapshot)
or merges it with its siblings - see the meta-dream-tree prune step.

Exit codes: 0 = nothing superseded, 1 = at least one fact names a superseded version, 2 = error
(no levels, a missing or unreadable level, a scan that found 0 facts to read). --json prints the
envelope {ok, command, data, skipped} on every exit, with an `error` key on exit 2.

Run (from the plugin root):
  `uv run skills/meta-dream-tree/versionrot.py scan --tree /path/to/project --json`
  `uv run skills/meta-dream-tree/versionrot.py scan --chain . --current "claude-code=2.1.300"`
Pure standard library; any Python 3.10+ runs it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import uuid_store  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from statusrot import (  # noqa: E402
    LevelUnreadable,
    TreeUnusable,
    _read_level,
    chain_levels,
    parse_pointers,
    tree_levels,
)
from tree_support import store_anchor, utf8_stdio  # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: read the two keys this tool needs by hand
    tomllib = None  # type: ignore[assignment]

__all__ = ["Claim", "Known", "Registry", "compare", "discover", "find_claims", "main", "normalize"]

# A version: two or three dotted parts, the third may be the wildcard x. Never part of a longer
# dotted run, so an IPv4 address (four parts) yields nothing rather than its first three.
_VERSION = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.(?:\d+|x))?)(?![\w]|\.\d|\.x)")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_.+-]*[A-Za-z0-9]|[A-Za-z]")
# Where a sentence ends, so a package named in the previous sentence is never borrowed.
_SENTENCE_END = re.compile(r"[.;!?](?=\s)|\n\s*\n|\n[-*] ")
# Words that sit between a package and its version without being the package. A LINKER binds
# the version to the word before it ("click floor 8.4.2" is click's); a PREPOSITION introduces a
# version that refers further back ("bmk processes (fixed in 3.13.0)" is bmk's), so only a
# preposition lets the search pass an unknown word.
_LINKERS = frozenset({"v", "version", "versions", "release", "plugin", "package", "library",
                      "lib", "floor", "pin"})
_PREPS = frozenset({"in", "on", "at", "from", "to", "since", "before", "after", "through", "up",
                    "as", "of", "is", "was", "and", "or", "the", "fixed", "pinned", "bumped",
                    "requires"})
_FILLER = _LINKERS | _PREPS
# A two-part number is a version only right beside a resolved package (within this many words);
# alone it is a score, a deadline, a Python minor.
_NEAR = 2
_LOOKBACK = 8
_SKIP_DIRS = frozenset({"node_modules", "__pycache__", "site-packages", "dist", "build", "target"})
# Names PyPI would answer for but that, in a fact, mean something else entirely.
_NOT_PYPI = frozenset({"python", "cpython", "kernel", "linux", "windows", "git", "node", "gh",
                       "powershell", "tpm", "uefi", "pve", "proxmox", "debian", "ubuntu"})


def normalize(name: str) -> str:
    """PEP 503 spelling: lower case, every run of - _ . collapsed to one hyphen."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


@dataclass(frozen=True)
class Known:
    version: str
    source: str


@dataclass
class Registry:
    """normalized package name -> its current version, plus aliases (a word -> a package)."""

    known: dict[str, Known] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    def lookup(self, name: str) -> Known | None:
        key = normalize(name)
        return self.known.get(self.aliases.get(key, key))

    def canonical(self, name: str) -> str:
        key = normalize(name)
        return self.aliases.get(key, key)

    def add(self, name: str, version: str, source: str) -> None:
        """Record `name` at `version`, keeping the newest when two copies disagree."""
        key = normalize(name)
        prior = self.known.get(key)
        if prior is None or compare(prior.version, version) == "superseded":
            self.known[key] = Known(version, source)


@dataclass(frozen=True)
class Claim:
    pkg: str | None
    named: str
    current: str | None
    status: str  # superseded | current | ahead | unresolved
    context: str
    where: str = ""


def _parts(version: str) -> list[int]:
    out: list[int] = []
    for piece in version.split("."):
        if not piece.isdigit():
            break
        out.append(int(piece))
    return out


def compare(named: str, current: str) -> str:
    """How `named` stands against `current`, compared over the parts `named` spells out.

    "3.20.x" and "2.13" say nothing below their last number, so only that prefix is compared.

    Examples:
        >>> compare("3.13.0", "3.21.1"), compare("3.21.x", "3.21.1"), compare("4.0", "3.9.9")
        ('superseded', 'current', 'ahead')
    """
    n = _parts(named)
    c = (_parts(current) + [0] * len(n))[: len(n)]
    if c > n:
        return "superseded"
    return "current" if c == n else "ahead"


def _sentence_prefix(text: str, start: int) -> str:
    cut = 0
    for m in _SENTENCE_END.finditer(text, 0, start):
        cut = m.end()
    return text[cut:start]


def _words(segment: str) -> list[str]:
    return [w.removesuffix("'s") for w in _WORD.findall(segment)][-_LOOKBACK:]


def _known_name(words: list[str], i: int, reg: Registry) -> str | None:
    """The package words[i] names - alone or as the end of a two-word name - or None."""
    if i > 0 and reg.lookup(f"{words[i - 1]}-{words[i]}") is not None:
        return reg.canonical(f"{words[i - 1]}-{words[i]}")
    key = normalize(words[i])
    if key in reg.aliases or (key not in _FILLER and reg.lookup(key) is not None):
        return reg.canonical(key)
    return None


def _resolve(words: list[str], reg: Registry) -> tuple[str | None, Known | None, int]:
    """The package a version belongs to: (name, its current version, word distance).

    Walks back from the version. A known package resolves it. An unknown word owns it - unless
    a preposition stood between, in which case the search goes on and the nearest unknown word is
    only the fallback name.
    """
    introduced = False
    nearest: str | None = None
    for dist, i in enumerate(range(len(words) - 1, -1, -1)):
        name = _known_name(words, i, reg)
        if name is not None:
            return name, reg.lookup(name), dist
        key = normalize(words[i])
        if key in _FILLER:
            introduced = introduced or key in _PREPS
            continue
        if not introduced:
            return key, None, dist
        nearest = nearest or key
    return nearest, None, _LOOKBACK


def find_claims(text: str, reg: Registry, where: str = "") -> list[Claim]:
    """Every version number in `text` that can be tied to a package, with its status. PURE."""
    claims: list[Claim] = []
    prev: tuple[int, str | None, Known | None] | None = None  # (end, pkg, known)
    for m in _VERSION.finditer(text):
        named = m.group(1)
        sentence = _sentence_prefix(text, m.start())
        sentence_start = m.start() - len(sentence)
        if prev is not None and prev[0] >= sentence_start:
            # Never look past the previous version: a run like "8.4.2 -> 8.5.0" or "from 3.13.0
            # to 3.21.1" belongs to the package that run started with.
            segment = text[prev[0]:m.start()]
            if all(normalize(w) in _FILLER for w in _words(segment)):
                pkg, known, dist = prev[1], prev[2], 0
            else:
                pkg, known, dist = _resolve(_words(segment), reg)
        else:
            pkg, known, dist = _resolve(_words(sentence), reg)
        prev = (m.end(), pkg, known)
        two_part = named.count(".") == 1
        if two_part and (known is None or dist > _NEAR):
            continue
        context = " ".join(text[max(0, m.start() - 60): m.end() + 30].split())
        if known is None:
            claims.append(Claim(pkg, named, None, "unresolved", context, where))
        else:
            claims.append(Claim(pkg, named, known.version, compare(named, known.version),
                                context, where))
    return claims


# -- current versions ------------------------------------------------------------------------

def _toml_project(path: Path) -> tuple[str | None, str | None]:
    """[project] name and version from a pyproject.toml; a missing or dynamic one is None."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if tomllib is not None:
        try:
            proj = tomllib.loads(text).get("project", {})
        except tomllib.TOMLDecodeError:
            return None, None
        name, ver = proj.get("name"), proj.get("version")
        return (name if isinstance(name, str) else None), (ver if isinstance(ver, str) else None)
    section = re.search(r"^\[project\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not section:
        return None, None
    found = dict(re.findall(r'^(name|version)\s*=\s*"([^"]*)"', section.group(1), re.M))
    return found.get("name"), found.get("version")


def _json(path: Path) -> dict:
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return blob if isinstance(blob, dict) else {}


def _record_plugin_dir(d: Path, reg: Registry) -> None:
    meta = d / ".claude-plugin"
    plugin = _json(meta / "plugin.json")
    if isinstance(plugin.get("name"), str) and isinstance(plugin.get("version"), str):
        reg.add(plugin["name"], plugin["version"], str(meta / "plugin.json"))
    market = _json(meta / "marketplace.json")
    entries = market.get("plugins")
    if isinstance(market.get("name"), str) and isinstance(entries, list) and len(entries) == 1:
        entry = entries[0]
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            reg.aliases[normalize(market["name"])] = normalize(entry["name"])


def discover(roots: Iterable[Path], max_depth: int = 7) -> Registry:
    """Current versions of every package whose repo sits under `roots`.

    Hidden and vendored dirs are not entered: a `.venv` or `node_modules` copy is somebody else's
    version, not the project's.
    """
    reg = Registry()
    for root in roots:
        base = Path(root).resolve()
        base_depth = len(base.parts)
        for dirpath, dirnames, filenames in os.walk(base):
            d = Path(dirpath)
            if len(d.parts) - base_depth >= max_depth:
                dirnames[:] = []
            dirnames[:] = [n for n in dirnames if not n.startswith(".") and n not in _SKIP_DIRS]
            if "pyproject.toml" in filenames:
                try:
                    name, ver = _toml_project(d / "pyproject.toml")
                except OSError:
                    name, ver = None, None
                if name and ver:
                    reg.add(name, ver, str(d / "pyproject.toml"))
            if (d / ".claude-plugin").is_dir():
                _record_plugin_dir(d, reg)
    return reg


def own_plugin(reg: Registry) -> None:
    """Make a bare "plugin" mean the plugin this script ships in, at no older than its own version.

    The running copy is a release that exists, so a checkout found on disk that is behind it (a
    main checkout not yet fast-forwarded) must not report the plugin one release old.
    """
    meta = _json(Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json")
    if isinstance(meta.get("name"), str) and isinstance(meta.get("version"), str):
        reg.add(meta["name"], meta["version"], "this plugin")
        reg.aliases.setdefault("plugin", normalize(meta["name"]))


def pypi_version(name: str, timeout: float = 5.0) -> str | None:
    """The latest release PyPI lists for `name`, or None on any failure."""
    url = f"https://pypi.org/pypi/{normalize(name)}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - fixed https host
            info = json.load(resp).get("info", {})
    except (urllib.error.URLError, OSError, ValueError):
        return None
    ver = info.get("version") if isinstance(info, dict) else None
    return ver if isinstance(ver, str) else None


# -- the scan --------------------------------------------------------------------------------

@dataclass
class FactReport:
    level: str
    slug: str
    claims: list[Claim]


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            return text[end + 4:]
    return text


def scan_facts(levels: list[Path], store: Path | None, reg: Registry,
               fetch: Callable[[str], str | None] | None = None) -> tuple[list[FactReport], list[str]]:
    """Every pointed-at fact's claims, and the slugs whose body could not be read."""
    reports: list[FactReport] = []
    missing: list[str] = []
    seen: set[str] = set()
    asked: set[str] = set()
    for path in levels:
        for ptr in parse_pointers(_read_level(path), level=str(Path(path).parent)):
            if ptr.slug in seen:
                continue
            seen.add(ptr.slug)
            body = ""
            body_path = store / ".claude-memory" / "facts" / f"{ptr.slug}.md" if store else None
            try:
                if body_path is not None:
                    body = _strip_frontmatter(body_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                missing.append(ptr.slug)
            if fetch is not None:
                _resolve_online([ptr.hook, body], reg, fetch, asked)
            claims = find_claims(ptr.hook, reg, "hook") + find_claims(body, reg, "body")
            reports.append(FactReport(ptr.level, ptr.slug, claims))
    return reports, missing


def _resolve_online(texts: list[str], reg: Registry, fetch: Callable[[str], str | None],
                    asked: set[str]) -> None:
    """Ask PyPI, once per name, about each unresolved package named before a version."""
    for text in texts:
        for claim in find_claims(text, reg):
            name = claim.pkg
            if claim.status != "unresolved" or not name or name in _NOT_PYPI or name in asked:
                continue
            asked.add(name)
            ver = fetch(name)
            if ver:
                reg.add(name, ver, "pypi")


def _envelope(ok: bool, data: dict, error: str | None = None) -> str:
    env: dict = {"ok": ok, "command": "scan", "data": data, "skipped": []}
    if error is not None:
        env["error"] = error
    return json.dumps(env, indent=2)


def _fail(args: argparse.Namespace, msg: str) -> int:
    if args.json:
        print(_envelope(False, {}, msg))
    else:
        print(f"error: {msg}", file=sys.stderr)
    return 2


def _claim_dict(c: Claim) -> dict:
    return {"pkg": c.pkg, "named": c.named, "current": c.current, "status": c.status,
            "where": c.where, "context": c.context}


def _render(reports: list[FactReport], stale: list[FactReport], counts: dict[str, int],
            missing: list[str]) -> str:
    lines = [f"scanned {len(reports)} fact(s); claims by status: "
             + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    lines.append(f"== SUPERSEDED: {len(stale)} fact(s) name a version a newer release replaced ==")
    for rep in stale:
        lines.append(f"   {rep.slug}   [{rep.level}]")
        for c in rep.claims:
            if c.status == "superseded":
                lines.append(f"        {c.pkg} {c.named} -> {c.current} ({c.where}): {c.context}")
    if missing:
        lines += ["", f"bodies not readable ({len(missing)}): " + ", ".join(missing)]
    lines += ["", "These are CANDIDATES: re-check each claim against the current release, then "
              "reword it to the current state, archive it, or merge it with its siblings."]
    return "\n".join(lines)


def _overrides(reg: Registry, pairs: list[str]) -> str | None:
    for pair in pairs:
        name, sep, ver = pair.partition("=")
        if not sep or not name.strip() or not _parts(ver.strip()):
            return f"--current {pair!r} is not NAME=VERSION"
        reg.known[normalize(name)] = Known(ver.strip(), "--current")
    return None


def _aliases(reg: Registry, pairs: list[str]) -> str | None:
    for pair in pairs:
        word, sep, name = pair.partition("=")
        if not sep or not word.strip() or not name.strip():
            return f"--alias {pair!r} is not WORD=PACKAGE"
        reg.aliases[normalize(word)] = normalize(name)
    return None


def _levels(args: argparse.Namespace) -> list[Path] | str:
    for flag in ("chain", "tree"):
        value = getattr(args, flag)
        if value and not Path(value).is_dir():
            return f"--{flag} {value} is not an existing directory"
    levels: list[Path] = list(dict.fromkeys(Path(p).resolve() for p in args.level))
    if args.chain:
        levels += [p for p in chain_levels(args.chain) if p not in levels]
    if args.tree:
        try:
            levels += [p for p in tree_levels(args.tree) if p not in levels]
        except TreeUnusable as exc:
            return str(exc)
    return levels or "no levels given (--level, --chain or --tree)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="list facts naming a superseded version")
    sc.add_argument("--level", action="append", default=[], type=Path,
                    help="a CLAUDE.local.md to scan (repeatable)")
    sc.add_argument("--chain", type=Path, help="every CLAUDE.local.md from this dir upward")
    sc.add_argument("--tree", type=Path, help="every curated level of the tree holding this dir")
    sc.add_argument("--repos", action="append", default=[], type=Path,
                    help="where to look for current versions (repeatable; default: the anchor)")
    sc.add_argument("--current", action="append", default=[], metavar="NAME=VERSION",
                    help="the current version of a package found in no repo (repeatable)")
    sc.add_argument("--alias", action="append", default=[], metavar="WORD=PACKAGE",
                    help="a word that names a package, e.g. plugin=bitranox (repeatable)")
    sc.add_argument("--pypi", action="store_true",
                    help="ask PyPI for packages no repo or --current resolves")
    sc.add_argument("--json", action="store_true", help="emit a JSON envelope")
    utf8_stdio()
    args = ap.parse_args(argv)

    levels = _levels(args)
    if isinstance(levels, str):
        return _fail(args, levels)
    start = args.chain or args.tree or levels[0].parent
    store = store_anchor(start, uuid_store.resolve_anchor)
    reg = discover(args.repos or ([store] if store else []))
    own_plugin(reg)
    err = _overrides(reg, args.current) or _aliases(reg, args.alias)
    if err:
        return _fail(args, err)
    try:
        reports, missing = scan_facts(levels, store, reg, pypi_version if args.pypi else None)
    except LevelUnreadable as exc:
        return _fail(args, str(exc))
    if not reports:
        return _fail(args, "scanned 0 facts - the levels hold no pointers, so nothing was checked")

    counts: dict[str, int] = {}
    for rep in reports:
        for c in rep.claims:
            counts[c.status] = counts.get(c.status, 0) + 1
    stale = [r for r in reports if any(c.status == "superseded" for c in r.claims)]
    if args.json:
        print(_envelope(True, {
            "facts_scanned": len(reports),
            "claims_by_status": counts,
            "superseded": [{"level": r.level, "slug": r.slug,
                            "claims": [_claim_dict(c) for c in r.claims
                                       if c.status == "superseded"]} for r in stale],
            "unresolved_packages": sorted({c.pkg for r in reports for c in r.claims
                                           if c.status == "unresolved" and c.pkg}),
            "unreadable_bodies": missing,
            "packages_known": len(reg.known),
        }))
    else:
        print(_render(reports, stale, counts, missing))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
