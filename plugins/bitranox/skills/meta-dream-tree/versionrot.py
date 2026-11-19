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
resolve is reported `unresolved`, never compared. `--pypi` asks only about a name something
vouches for - a package a repo under `--repos` has or depends on (its pyproject, its uv.lock) or a
requirement the fact writes out (`foo==1.2.0`) - because PyPI has a project for almost every
English word, and "SDK 0.2.144" is not the project "sdk".

A claim that records evidence rather than asserts a current fact is reported `dated`, not
superseded: a version in a sentence carrying an ISO date or "measured" (an incident on the version
it happened on stays true) and a "since X" statement. With `--pypi`, a package PyPI knows is judged
against its newest RELEASE, so an unreleased version in a local pyproject cannot call a correct fact
stale.

A superseded claim is a CANDIDATE. The dream re-checks it against the current release and then
rewords it to the current state, archives it (a fixed bug, a finished migration, a test snapshot)
or merges it with its siblings - see the meta-dream-tree prune step.

Exit codes: 0 = nothing superseded, 1 = at least one fact names a superseded version, 2 = error
(no levels, a missing or unreadable level, a scan that found 0 facts to read). --json prints the
envelope {ok, command, data, skipped} on every exit, with an `error` key on exit 2.

Run (from the plugin root):
  `uv run skills/meta-dream-tree/versionrot.py scan --tree /path/to/project --json`
  `uv run skills/meta-dream-tree/versionrot.py scan --chain . --current "claude-code=2.1.300"`
Pure standard library; Python 3.14+.

Decisions:
    "Dated evidence" is a text rule, not a judgment: an ISO date or the word "measured" in the
    version's sentence, or "since" right before the version or its package. Words like "verified"
    or "confirmed" alone do not count, because "verified on Claude Code 2.1.198" is the stale claim
    this scan exists for. Why: a re-check of one chain's 57 superseded claims kept all 57, each a
    dated incident record or a "since X" statement. Reopen if a scan shows dated claims that were
    really stale and were hidden. Pinned by test_a_dated_or_since_claim_is_dated_not_superseded.

    `--pypi` asks only about a name something vouches for: a package a repo under `--repos` has
    or depends on (pyproject name, dependencies, optional dependencies, dependency groups, uv.lock
    packages) or a requirement written out in the fact (`foo==1.2.0`, `foo >= 1.2`). Why: asking
    about every word beside a version turned English words into PyPI projects - measured on an
    815-fact chain, 16 of 91 superseded claims were "only", "startup", "a", "sdk", "tag", "named"
    and "that"; vouched-only asking dropped exactly those 16 and kept all 75 real ones. A word-only
    match stays `unresolved`. Reopen if a real package the repos do not use is reported unresolved
    often enough to matter (pass it with --current then). Pinned by
    TestPypiAsksOnlyAboutPackageMentions.
"""

import argparse
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import cast

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

_NAME_SEP_RE = re.compile(r"[-_.]+")

__all__ = ["Claim", "ClaimStatus", "Known", "Registry", "compare", "discover", "find_claims", "main", "normalize"]

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
_EVIDENCE = re.compile(r"\b20\d\d-\d\d-\d\d\b|\bmeasured\b", re.IGNORECASE)
_SINCE = re.compile(r"\bsince\s+(?:[\w.-]+\s+)?v?$", re.IGNORECASE)
# A version these sources name is not a PyPI release question: the caller said so, or it is this
# plugin's own version.
_NOT_ASKED_SOURCES = frozenset({"--current", "this plugin"})
# The distribution name at the start of a PEP 508 requirement ("rich_click[extra]>=1 ; ..").
_REQ_NAME = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")
# A uv.lock package entry's own name line (unindented, directly in a [[package]] table).
_LOCK_NAME = re.compile(r'name = "([^"]+)"\s*$')
# A requirement written out in a fact ("foo-bar==1.2.0", "foo_bar >= 1.2"): the text itself says
# the word is a distribution, so PyPI may be asked about it even when no repo on disk uses it.
_PINNED = re.compile(r"([A-Za-z0-9][A-Za-z0-9._-]*[A-Za-z0-9]|[A-Za-z0-9])\s*(?:===?|>=|<=|~=|!=|@)\s*v?\d")
_NOT_PYPI = frozenset({"python", "cpython", "kernel", "linux", "windows", "git", "node", "gh",
                       "powershell", "tpm", "uefi", "pve", "proxmox", "debian", "ubuntu"})


def normalize(name: str) -> str:
    """PEP 503 spelling: lower case, every run of - _ . collapsed to one hyphen."""
    return _NAME_SEP_RE.sub("-", name.strip().lower())


@dataclass(frozen=True)
class Known:
    version: str
    source: str


@dataclass
class Registry:
    """normalized package name -> its current version, plus aliases (a word -> a package).

    `recognised` holds distribution names seen on disk WITHOUT a version worth trusting (a
    dependency of some project, a uv.lock entry): enough to say a word in a fact names a real
    package, so PyPI may be asked about it, never enough to compare against.
    """

    known: dict[str, Known] = field(default_factory=dict[str, Known])
    aliases: dict[str, str] = field(default_factory=dict[str, str])
    recognised: set[str] = field(default_factory=set[str])

    def is_package(self, name: str) -> bool:
        """True when `name` is a distribution the disk vouches for, with or without a version."""
        return self.lookup(name) is not None or self.canonical(name) in self.recognised

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
        if prior is None or compare(prior.version, version) == ClaimStatus.SUPERSEDED:
            self.known[key] = Known(version, source)


class ClaimStatus(StrEnum):
    """How a named version stands against the package's current one; the values are the wire form."""

    SUPERSEDED = "superseded"
    DATED = "dated"
    CURRENT = "current"
    AHEAD = "ahead"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class Claim:
    pkg: str | None
    named: str
    current: str | None
    status: ClaimStatus
    context: str
    where: str = ""

    def __post_init__(self) -> None:
        # Every report branch tests one status; a misspelled one would match none and vanish.
        object.__setattr__(self, "status", ClaimStatus(self.status))


def _parts(version: str) -> list[int]:
    out: list[int] = []
    for piece in version.split("."):
        if not piece.isdigit():
            break
        out.append(int(piece))
    return out


def compare(named: str, current: str) -> ClaimStatus:
    """How `named` stands against `current`, compared over the parts `named` spells out.

    "3.20.x" and "2.13" say nothing below their last number, so only that prefix is compared.

    Examples:
        >>> [str(s) for s in (compare("3.13.0", "3.21.1"), compare("3.21.x", "3.21.1"),
        ...                   compare("4.0", "3.9.9"))]
        ['superseded', 'current', 'ahead']
    """
    n = _parts(named)
    c = (_parts(current) + [0] * len(n))[: len(n)]
    if c > n:
        return ClaimStatus.SUPERSEDED
    return ClaimStatus.CURRENT if c == n else ClaimStatus.AHEAD


def _sentence_prefix(text: str, start: int) -> str:
    cut = 0
    for m in _SENTENCE_END.finditer(text, 0, start):
        cut = m.end()
    return text[cut:start]


def _is_evidence(text: str, m: re.Match[str], prefix: str) -> bool:
    """True when the version at `m` sits in a dated record or a "since X" statement."""
    end = _SENTENCE_END.search(text, m.end())
    sentence = prefix + text[m.start():end.start() if end else len(text)]
    return bool(_EVIDENCE.search(sentence) or _SINCE.search(prefix))


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
            claims.append(Claim(pkg, named, None, ClaimStatus.UNRESOLVED, context, where))
        else:
            status = compare(named, known.version)
            if status == ClaimStatus.SUPERSEDED and _is_evidence(text, m, sentence):
                status = ClaimStatus.DATED
            claims.append(Claim(pkg, named, known.version, status, context, where))
    return claims


# -- current versions ------------------------------------------------------------------------

def _table(value: object) -> dict[str, object]:
    """`value` when it is a TOML table, else an empty one: a pyproject is untrusted input."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _items(value: object) -> list[object]:
    """`value` when it is a TOML array, else an empty one."""
    return cast("list[object]", value) if isinstance(value, list) else []


def _requirement_names(lists: Iterable[object]) -> set[str]:
    """The distribution names a set of PEP 508 requirement lists name (a non-string entry, such as
    a dependency group's include-group table, is skipped)."""
    names: set[str] = set()
    for reqs in lists:
        for req in _items(reqs):
            m = _REQ_NAME.match(req) if isinstance(req, str) else None
            if m:
                names.add(normalize(m.group(1)))
    return names


def _record_pyproject(path: Path, reg: Registry) -> None:
    """Its [project] name at its version (a dynamic one is not guessed), and every name it depends
    on, recognised without a version."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, tomllib.TOMLDecodeError):
        return
    proj = _table(data.get("project"))
    name, ver = proj.get("name"), proj.get("version")
    if isinstance(name, str) and name and isinstance(ver, str) and ver:
        reg.add(name, ver, str(path))
    if isinstance(name, str) and name:
        reg.recognised.add(normalize(name))
    groups: list[object] = [proj.get("dependencies")]
    for table in (proj.get("optional-dependencies"), data.get("dependency-groups")):
        groups += list(_table(table).values())
    reg.recognised |= _requirement_names(groups)


def _record_uv_lock(path: Path, reg: Registry) -> None:
    """Every `[[package]]` name a uv.lock lists, read line by line so a large lock is not loaded
    whole. A `{ name = ... }` inside a dependency list is indented, so it is never taken."""
    section = ""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("["):
                    section = line.strip()
                elif section == "[[package]]" and (m := _LOCK_NAME.match(line)):
                    reg.recognised.add(normalize(m.group(1)))
    except OSError:
        return


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
    """Current versions of every package whose repo sits under `roots`, and the names they use.

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
                _record_pyproject(d / "pyproject.toml", reg)
            if "uv.lock" in filenames:
                _record_uv_lock(d / "uv.lock", reg)
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
    """Ask PyPI, once per name, about each package a claim calls unresolved or superseded.

    Only a name something vouches for is asked: a package a repo on disk has or depends on (a
    pyproject, a uv.lock), or one the text itself writes as a requirement ("foo==1.2.0"). A bare
    word that merely stands beside a version ("SDK 0.2.144", "no startup() in 0.2.139") stays
    unresolved, because PyPI holds a project for almost every English word.

    An answer REPLACES what the repos on disk said: the newest release is what "current" means,
    and a local pyproject can hold a version that was never published. No answer (not on PyPI, or
    offline) leaves the local version in place."""
    for text in texts:
        pinned = {normalize(m.group(1)) for m in _PINNED.finditer(text)}
        for claim in find_claims(text, reg):
            name = claim.pkg
            if claim.status not in (ClaimStatus.UNRESOLVED, ClaimStatus.SUPERSEDED):
                continue
            if not name or name in _NOT_PYPI or name in asked:
                continue
            if not (reg.is_package(name) or name in pinned):
                continue
            known = reg.lookup(name)
            if known is not None and known.source in _NOT_ASKED_SOURCES:
                continue
            asked.add(name)
            ver = fetch(name)
            if ver:
                reg.known[reg.canonical(name)] = Known(ver, "pypi")


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


def _render(reports: list[FactReport], stale: list[FactReport], counts: dict[ClaimStatus, int],
            missing: list[str]) -> str:
    lines = [f"scanned {len(reports)} fact(s); claims by status: "
             + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), ""]
    lines.append(f"== SUPERSEDED: {len(stale)} fact(s) name a version a newer release replaced ==")
    for rep in stale:
        lines.append(f"   {rep.slug}   [{rep.level}]")
        for c in rep.claims:
            if c.status == ClaimStatus.SUPERSEDED:
                lines.append(f"        {c.pkg} {c.named} -> {c.current} ({c.where}): {c.context}")
    if missing:
        lines += ["", f"bodies not readable ({len(missing)}): " + ", ".join(missing)]
    lines += ["", ("These are CANDIDATES: re-check each claim against the current release, then "
              "reword it to the current state, archive it, or merge it with its siblings.")]
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
                    help="ask PyPI for the newest release of every unresolved or superseded "
                         "package a repo under --repos has or depends on, or the fact writes as "
                         "a requirement (foo==1.2.0); its answer replaces a local checkout's "
                         "version. A bare word beside a version stays unresolved")
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

    counts: dict[ClaimStatus, int] = {}
    for rep in reports:
        for c in rep.claims:
            counts[c.status] = counts.get(c.status, 0) + 1
    stale = [r for r in reports if any(c.status == ClaimStatus.SUPERSEDED for c in r.claims)]
    if args.json:
        print(_envelope(True, {
            "facts_scanned": len(reports),
            "claims_by_status": counts,
            "superseded": [{"level": r.level, "slug": r.slug,
                            "claims": [_claim_dict(c) for c in r.claims
                                       if c.status == ClaimStatus.SUPERSEDED]} for r in stale],
            "unresolved_packages": sorted({c.pkg for r in reports for c in r.claims
                                           if c.status == ClaimStatus.UNRESOLVED and c.pkg}),
            "unreadable_bodies": missing,
            "packages_known": len(reg.known),
        }))
    else:
        print(_render(reports, stale, counts, missing))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
