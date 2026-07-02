#!/usr/bin/env python3
"""Stage-1 of the inbound cross-tree gather: a fast, deterministic keyword grep (NO model).

The expensive (model) gather runs ONLY on a hit, so when nothing matches the cost is one cheap
scan. Given a topic / scope descriptor, derive keywords and grep them across OTHER projects' Auto
memory and the global rules layer, returning candidate files for the skill to inspect. The current
project is excluded (you gather FROM elsewhere). Global rules are scanned only so the skill can avoid
re-copying what an ancestor already provides.

Usage:
  gather_scan.py --topic "<text>" [--self <cwd>]

Imports the shared helpers from the plugin's hooks dir, like the meta-dream-project cadence CLI. Pure stdlib.
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

# self_improve_signals lives in the plugin's hooks dir: skills/meta-collect-knowledge -> skills -> bitranox -> hooks
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import self_improve_signals as sig  # noqa: E402

# Generic words that carry no topical signal - dropped so the grep stays specific.
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "use", "using", "used", "when",
    "then", "than", "your", "you", "our", "are", "was", "were", "has", "have", "had", "not", "but",
    "via", "per", "its", "it", "a", "an", "of", "to", "in", "on", "is", "be", "as", "at", "or", "by",
    "do", "does", "done", "run", "running", "set", "get", "all", "any", "one", "two", "new", "old",
    "how", "what", "why", "where", "which", "should", "must", "can", "will", "rule", "rules", "note",
}

# Opaque identifiers that are never a topical signal but slip past the token regex (they are valid
# [a-z0-9_-] runs): tool-use IDs, session UUIDs, long hex hashes, pure numbers, path slugs. Dropping
# them keeps the recall grep + the pending-keyword queue clean. Conservative on purpose - it must NOT
# drop a real multi-word technical term like "meta-dream-global-deep" (3 hyphens) or "px-websrv-media".
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_HEX_RE = re.compile(r"^[0-9a-f]{16,}$")   # long hex run: hashes, commit/id fragments
_DIGITS_RE = re.compile(r"^\d+$")


def _is_junk_token(tok):
    """True for opaque identifiers (tool-use IDs, UUIDs, long hex hashes, pure digits, path slugs,
    absurdly long tokens) - never a topical keyword. Must not drop real hyphenated terms (<=3 hyphens)."""
    return bool(
        "toolu" in tok                 # Claude tool-use IDs (toolu_01...)
        or _DIGITS_RE.match(tok)       # pure numbers
        or _UUID_RE.match(tok)         # session UUIDs
        or _HEX_RE.match(tok)          # long hex hashes / id fragments
        or tok.count("-") >= 4         # path slug (a-b-c-d-e-...); real terms top out ~3 hyphens
        or len(tok) >= 40              # nothing real is this long
    )


def extract_keywords(text, max_n=12, proj=None):
    """Deterministic keyword set from a topic / descriptor: lowercased significant tokens (>=3 chars,
    not stopwords / filler), de-duplicated in first-seen order, capped. No model. (Synonym recall is
    traded for speed; a richer pass can run later.)

    Filler words (generic/conversational tokens with no topical signal - the recall-precision bug) are
    dropped via `self_improve_signals.load_filler_words(proj)`: the GLOBAL shipped baseline UNION the
    PROJECT's learned filler (so one project's learned classification never suppresses another's recall).
    Pass `proj` (the current cwd) to get the per-project blacklist; omit it for baseline-only. Combined
    with the small structural `_STOP` set here."""
    try:
        drop = _STOP | sig.load_filler_words(proj)
    except Exception:  # noqa: BLE001 - missing/corrupt list must never break extraction
        drop = _STOP
    out = []
    for tok in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", (text or "").lower()):
        if tok in drop or len(tok) < 3 or tok in out or _is_junk_token(tok):
            continue
        out.append(tok)
        if len(out) >= max_n:
            break
    return out


def discover_files(exclude_proj=None):
    """Candidate scan targets: every `*.md` under other projects' Auto memory plus the global rules
    layer (recursive). The current project's own memory is excluded - you gather FROM elsewhere."""
    files = []
    try:
        exclude = str(sig.memory_dir(exclude_proj).resolve()) if exclude_proj else None
    except OSError:
        exclude = None
    projroot = Path.home() / ".claude" / "projects"
    try:
        for memdir in sorted(projroot.glob("*/memory")):
            try:
                if exclude and str(memdir.resolve()) == exclude:
                    continue
            except OSError:
                pass
            files += sorted(memdir.glob("*.md"))
    except OSError:
        pass
    g = sig.global_rules_dir()
    try:
        if g.exists():
            files += sorted(g.rglob("*.md"))
    except OSError:
        pass
    return files


# Dirs never worth walking for CLAUDE.md (vendored / build / VCS / cache).
_VENDOR = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "site-packages", ".mypy_cache",
    ".pytest_cache", ".tox", ".idea", ".ruff_cache", "dist", "build", ".eggs",
}


def _workspace_root(cwd, max_up=8):
    """The highest ancestor of `cwd` (within `max_up` levels, never above $HOME) that still holds a
    CLAUDE.md - the root of the knowledge tree to search. None if no ancestor has one."""
    try:
        p = Path(cwd).resolve()
    except OSError:
        return None
    home = Path.home()
    root = None
    for _ in range(max_up):
        try:
            if (p / "CLAUDE.md").is_file():
                root = p
        except OSError:
            pass
        if p.parent == p or p == home:
            break
        p = p.parent
    return root


def _find_claude_md(root):
    """Every CLAUDE.md under `root`, pruning vendored/build/hidden dirs. os.walk so we can prune."""
    out = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _VENDOR and not d.startswith(".")]
            if "CLAUDE.md" in filenames:
                out.append(str(Path(dirpath) / "CLAUDE.md"))
    except OSError:
        pass
    return out


def discover_claude_md(self_cwd, cache_ttl=3600):
    """OTHER projects' CLAUDE.md across the workspace tree, for the recall "check the notebook" pass.

    EXCLUDES the current project's ancestor chain (cwd up to the workspace root) - those CLAUDE.md
    cascade into the session already, so surfacing them would just echo loaded context. The expensive
    `os.walk` is CACHED per workspace root with a TTL (default 1h), so the per-prompt cost is reading a
    small path list, not a tree walk. Returns absolute path strings; empty if no workspace root found."""
    root = _workspace_root(self_cwd)
    if root is None:
        return []
    chain = set()
    try:
        p = Path(self_cwd).resolve()
        while True:
            chain.add(str(p / "CLAUDE.md"))
            if p == root or p.parent == p:
                break
            p = p.parent
    except OSError:
        pass
    h = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:12]
    cache = Path.home() / ".claude" / "self-improve-audit" / ("claude-md-paths.%s.txt" % h)
    paths = None
    try:
        if cache.is_file() and (time.time() - cache.stat().st_mtime) < cache_ttl:
            paths = [ln for ln in cache.read_text(encoding="utf-8").splitlines() if ln]
    except OSError:
        paths = None
    if paths is None:
        paths = _find_claude_md(root)
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("\n".join(paths), encoding="utf-8")
        except OSError:
            pass
    return [p for p in paths if p not in chain]


def _find_curated_stores(root):
    """Every `.claude-bx-selflearning/{memory.md, facts/*.md}` under `root`. Allow-lists that ONE
    dot-dir past the hidden-dir prune (else the walk would never find it), excludes vendored/other-
    hidden/backup dirs, and does not descend INTO a store (so `.archive`/backups are skipped)."""
    out = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == sig.CURATED_DIRNAME:
                d = Path(dirpath)
                if (d / "memory.md").is_file():
                    out.append(str(d / "memory.md"))
                fdir = d / "facts"
                if fdir.is_dir():
                    out += [str(p) for p in sorted(fdir.glob("*.md"))]
                dirnames[:] = []                      # do not descend into the store
                continue
            dirnames[:] = [x for x in dirnames
                           if (x == sig.CURATED_DIRNAME or (x not in _VENDOR and not x.startswith(".")))
                           and ".bak-" not in x and not x.endswith(".bak")]
    except OSError:
        pass
    return out


def discover_curated(self_cwd, exclude_proj=None, cache_ttl=3600):
    """OTHER projects' curated `.claude-bx-selflearning/` stores across the workspace tree (memory.md
    + facts/), for cross-project recall. EXCLUDES the current project's own `memory.md` (already
    @imported into this session) but KEEPS its `facts/` (eligible for push-when-relevant). Cached per
    workspace root (TTL); empty if no workspace root."""
    root = _workspace_root(self_cwd)
    if root is None:
        return []
    h = hashlib.sha1(("cur:" + str(root)).encode("utf-8")).hexdigest()[:12]
    cache = Path.home() / ".claude" / "self-improve-audit" / ("curated-paths.%s.txt" % h)
    paths = None
    try:
        if cache.is_file() and (time.time() - cache.stat().st_mtime) < cache_ttl:
            paths = [ln for ln in cache.read_text(encoding="utf-8").splitlines() if ln]
    except OSError:
        paths = None
    if paths is None:
        paths = _find_curated_stores(root)
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("\n".join(paths), encoding="utf-8")
        except OSError:
            pass
    own_mem = None
    if exclude_proj:
        try:
            own_mem = str(sig.curated_index(exclude_proj).resolve())
        except OSError:
            own_mem = None
    kept = []
    for p in paths:
        try:
            if own_mem and Path(p).name == "memory.md" and str(Path(p).resolve()) == own_mem:
                continue                              # own memory.md already loaded; keep its facts
        except OSError:
            pass
        kept.append(p)
    return kept


def scan(keywords, files):
    """Map each file that contains any keyword to the list of keywords it matched. Matching is
    WORD-BOUNDARY (a-z0-9 are word chars; `-`/`_` and punctuation are separators), case-insensitive -
    so `again` does NOT match `against` and `test` does NOT match `latest` (a substring match made
    recall match half the store). Files that read-fail are skipped."""
    pats = {}
    for k in keywords:
        k = (k or "").lower()
        if k and k not in pats:
            pats[k] = re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])")
    out = {}
    for p in files:
        try:
            text = Path(p).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        hits = [k for k, rx in pats.items() if rx.search(text)]
        if hits:
            out[str(p)] = hits
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cross-tree gather stage-1: keyword grep for candidates.")
    ap.add_argument("--topic", required=True, help="topic / scope-descriptor text to gather for")
    ap.add_argument("--self", dest="self_proj", default=None,
                    help="current project cwd to EXCLUDE (you gather from elsewhere)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    self_proj = args.self_proj or os.getcwd()
    keywords = extract_keywords(args.topic, proj=self_proj)   # per-project blacklist for the current proj
    if not keywords:
        print("no usable keywords from topic", file=sys.stderr)
        return 0
    files = discover_files(self_proj)
    if self_proj:                                 # also other projects' curated stores across the tree
        files += discover_curated(self_proj, self_proj)
    hits = scan(keywords, files)
    for path in sorted(hits):
        print("%s\t%s" % (path, ",".join(hits[path])))
    print("CANDIDATES: %d (keywords: %s)" % (len(hits), ", ".join(keywords)))
    # Optional: when a memory MCP (basic-memory) is enabled and its index covers this tree, add its
    # semantic/full-text hits as EXTRA candidates for the agent to read-note. Read-only; keyword scan
    # above is always the base, so this is a pure augmentation (absent/misconfigured MCP -> nothing).
    try:
        import mcp_search as _mx
        if _mx.enabled() and (self_proj is None or _mx.covers(self_proj)):
            mhits = _mx.search(args.topic)
            if mhits:
                for h in mhits:
                    print("MCP\t%s" % h)
                print("MCP-CANDIDATES: %d (via basic-memory search)" % len(mhits))
    except Exception:  # noqa: BLE001 - the MCP path must never break the keyword gather
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
