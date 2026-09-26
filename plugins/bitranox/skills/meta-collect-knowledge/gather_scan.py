#!/usr/bin/env python3
"""Stage-1 of the inbound cross-tree gather: a fast, deterministic keyword grep (NO model).

The expensive (model) gather runs ONLY on a hit, so when nothing matches the cost is one cheap
scan. Given a topic / scope descriptor, derive keywords and grep them across OTHER projects' Auto
memory and the global rules layer, returning candidate files for the skill to inspect. The current
project is excluded (you gather FROM elsewhere). Global rules are scanned only so the skill can avoid
re-copying what an ancestor already provides.

Usage:
  gather_scan.py --topic "<text>" [--self <cwd>]

Exit codes: 0 scanned (or marked), 1 "not gathered yet" (--seen only), 2 error. A file that cannot
be read or decoded, and a directory that cannot be listed, is skipped with a warning on stderr.

Imports the shared helpers from the plugin's hooks dir, like the meta-dream-tree cadence CLI. Pure stdlib.
"""

import argparse
import hashlib
import datetime
import os
import re
import sys
import time
import unicodedata
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
# drop a real multi-word technical term like "meta-dream-crosstree-deep" (3 hyphens) or "px-websrv-media".
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


# A word is a run of letters/digits in ANY script. The first character must be a letter or digit;
# the rest may also hold "_" and "-" so hyphenated technical terms stay one token. An ASCII-only
# class split "Schluessel" spelled with an umlaut into fragments that matched unrelated words.
_TOKEN_RE = re.compile(r"[^\W_][\w-]{2,}")
_WORD_CHAR = r"[^\W_]"                      # what a keyword may not touch on either side in scan()


def _fold(text):
    """The one normalisation topic and note text share: NFC (so a decomposed umlaut equals the
    composed one) then casefold."""
    return unicodedata.normalize("NFC", text or "").casefold()


def extract_keywords(text, max_n=12, proj=None):
    """Deterministic keyword set from a topic / descriptor: casefolded significant tokens (>=3 chars,
    any script, not stopwords / filler), de-duplicated in first-seen order, capped. No model. (Synonym
    recall is traded for speed; a richer pass can run later.)

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
    for tok in _TOKEN_RE.findall(_fold(text)):
        if tok in drop or len(tok) < 3 or tok in out or _is_junk_token(tok):
            continue
        out.append(tok)
        if len(out) >= max_n:
            break
    return out


def _own_memory_dirs(proj):
    """The resolved native memory dirs that belong to `proj`, under every spelling Claude Code may
    have keyed it by: the spelling exactly as given when it is rooted, the absolute path (trailing
    separator and "." normalised away) and the symlink-free one. Empty for no project.

    The given spelling is kept because it is not always what abspath returns: on Windows abspath
    puts the current drive in front of a drive-less rooted path, so "/p/cur" becomes "D:\\p\\cur"
    and keys "D--p-cur" while the project the caller named keys "-p-cur". A relative spelling is
    not kept: "." would key "-", which is the project whose cwd is the filesystem root."""
    if not proj:
        return set()
    out = set()
    try:
        given = os.fspath(proj)
        spelled = os.path.abspath(given)
        spellings = {spelled, os.path.realpath(spelled)}
        if Path(given).root:
            spellings.add(given)
        for spelling in spellings:
            out.add(str(sig.memory_dir(spelling).resolve()))
    except (OSError, TypeError, ValueError):
        pass
    return out


def canonical(path, pathmod=os.path):
    """A comparison key for a path: symlinks resolved and, on Windows, case folded. Two spellings
    of one file compare equal, so one tree is never reported twice or filtered out of itself."""
    return pathmod.normcase(pathmod.realpath(os.fspath(path)))


def within_tree(files, anchor, pathmod=os.path):
    """The subset of `files` that lives under `anchor`, compared on `canonical` keys, so a cwd
    reached through a symlink or typed in another case still keeps its own tree's files."""
    pre = canonical(anchor, pathmod).rstrip(pathmod.sep) + pathmod.sep
    return [f for f in files if canonical(f, pathmod).startswith(pre)]


def discover_files(exclude_proj=None):
    """Candidate scan targets: every `*.md` under other projects' Auto memory plus the global rules
    layer (recursive). The current project's own memory is excluded - you gather FROM elsewhere."""
    files = []
    exclude = _own_memory_dirs(exclude_proj)
    projroot = Path.home() / ".claude" / "projects"
    try:
        for memdir in sorted(projroot.glob("*/memory")):
            try:
                if str(memdir.resolve()) in exclude:
                    continue
            except OSError:
                pass
            files += sorted(memdir.glob("*.md"))
    except OSError:
        pass
    g = sig.global_rules_dir(exclude_proj)   # tree-top central store: <anchor>/.claude-memory
    try:
        facts = g / "facts"
        if facts.is_dir():                    # bodies only; .archive/ and state/ excluded by construction
            files += sorted(facts.glob("*.md")) + sorted(facts.glob("*/*.md"))
    except OSError:
        pass
    return files


# Dirs never worth walking for CLAUDE.md (single source: self_improve_signals.VENDOR_DIRNAMES).
_VENDOR = sig.VENDOR_DIRNAMES


def _workspace_root(cwd, max_up=8):
    """The highest ancestor of `cwd` (within `max_up` levels, never above $HOME) that still holds a
    CLAUDE.md - the root of the knowledge tree to search. None if no ancestor has one. The dirs that
    must never be an altitude anchor (HOME itself, the system temp dir, the filesystem root - see
    self_improve_signals._excluded_anchor_dirs) are skipped: a stray CLAUDE.md at /tmp would
    otherwise turn ALL of the temp dir into one "workspace" and pollute recall with unrelated junk
    (bitten twice on 2026-07-05)."""
    try:
        p = Path(cwd).resolve()
    except OSError:
        return None
    home = Path.home()
    excluded = sig._excluded_anchor_dirs()
    root = None
    for _ in range(max_up):
        try:
            if p != Path(p.anchor) and p not in excluded and (p / "CLAUDE.md").is_file():
                root = p
        except OSError:
            pass
        if p.parent == p or p == home:
            break
        p = p.parent
    return root


# Directories a walk could not list since the last take_walk_errors(). An unlistable dir is a
# silent undercount otherwise: the walk just returns fewer paths. Module-level because the walks
# sit behind caches and several call layers; the CLI prints them, the recall hook logs them.
_WALK_ERRORS = []


def _note_walk_error(err):
    _WALK_ERRORS.append((getattr(err, "filename", None) or "?", str(err)))


def take_walk_errors():
    """[(path, reason)] of every directory a walk could not list since the last call; clears it."""
    out = list(_WALK_ERRORS)
    del _WALK_ERRORS[:]
    return out


def _read_lines(path):
    """The "\\n"-separated lines of a cache file, byte-exact. Not splitlines() and no newline
    translation: \\r, \\f, \\x1c-\\x1e and U+2028 are all legal inside a path, and a POSIX name
    that is not UTF-8 round-trips through surrogateescape. Raises OSError."""
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as fh:
        return fh.read().split("\n")


def _write_lines(path, lines):
    """Write `lines` joined by "\\n" with no newline translation. Raises OSError."""
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as fh:
        fh.write("\n".join(lines))


# A walk cache is: a stamp line, "skipped:<n>", n (path, reason) line pairs, then the result paths.
# A walk that could not list some dirs is cached like a complete one - otherwise one permanently
# unlistable dir (lost+found) re-walks the whole tree on every prompt - and the skipped pairs are
# REPLAYED as walk errors on every read, so the skip is reported each time, never cached away.
# Such a partial cache is retried on the normal schedule (TTL, or a stores-generation bump), which
# is also when a dir that became listable is picked up.
_SKIPPED = "skipped:"


def _walk_cache_lines(stamp, errors, paths):
    """The cache file lines for one walk, or None when a value holds a "\\n" (the record
    separator): such a record cannot be read back as written, so it is not cached at all."""
    lines = [stamp, "%s%d" % (_SKIPPED, len(errors))]
    for path, reason in errors:
        lines += [str(path), str(reason)]
    lines += paths
    return None if any("\n" in ln for ln in lines) else lines


def _parse_walk_cache(lines, stamp):
    """([(path, reason)] skipped by the cached walk, [paths]) or None when `lines` is not a
    cache of this `stamp` in this format (an older format is rebuilt, never guessed at)."""
    if len(lines) < 2 or lines[0] != stamp or not lines[1].startswith(_SKIPPED):
        return None
    try:
        n = int(lines[1][len(_SKIPPED):])
    except ValueError:
        return None
    if n < 0 or len(lines) < 2 + 2 * n:
        return None
    pairs = lines[2:2 + 2 * n]
    return list(zip(pairs[0::2], pairs[1::2])), [ln for ln in lines[2 + 2 * n:] if ln]


def _cached_walk(cache, stamp, cache_ttl, walk):
    """The paths `walk()` returns, served from `cache` while it is younger than `cache_ttl` and
    carries `stamp`. Every dir the walk could not list is in _WALK_ERRORS after this call,
    whether the walk ran now or its record was read back. Any cache IO error means a live walk."""
    try:
        if cache.is_file() and (time.time() - cache.stat().st_mtime) < cache_ttl:
            cached = _parse_walk_cache(_read_lines(cache), stamp)
            if cached is not None:
                _WALK_ERRORS.extend(cached[0])
                return cached[1]
    except (OSError, ValueError):
        pass
    before = len(_WALK_ERRORS)
    paths = walk()
    lines = _walk_cache_lines(stamp, _WALK_ERRORS[before:], paths)
    if lines is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            _write_lines(cache, lines)
        except (OSError, ValueError):                 # ValueError: an unencodable path
            pass
    return paths


def _find_claude_md(root):
    """Every CLAUDE.md under `root`, pruning vendored/build/hidden dirs. os.walk so we can prune."""
    out = []
    try:
        for dirpath, dirnames, filenames in os.walk(root, onerror=_note_walk_error):
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
    h = hashlib.sha1(str(root).encode("utf-8", "surrogatepass")).hexdigest()[:12]
    cache = Path.home() / ".claude" / "self-improve-audit" / ("claude-md-paths.%s.txt" % h)
    paths = _cached_walk(cache, "claude-md:v2", cache_ttl, lambda: _find_claude_md(root))
    return [p for p in paths if p not in chain]


_STORE_DIRNAME = sig.MEMORY_DIRNAME               # the central slug body-store (.claude-memory)


def _walk_store_dirs(root):
    """os.walk `root` for `.claude-memory` store DIRS - allow-listing the store dot-dir past the
    hidden-dir prune, excluding vendored / other-hidden / backup dirs, not descending INTO a store.
    This walk is the EXPENSIVE part (on a big tree it dominates recall); _curated_store_dirs caches
    it. Facts are globbed FRESH by _find_curated_stores, so a newly added fact is never hidden by the
    cache - only the appearance of a brand-new store dir needs a refresh (TTL or generation bump)."""
    dirs = []
    try:
        for dirpath, dirnames, filenames in os.walk(root, onerror=_note_walk_error):
            base = os.path.basename(dirpath)
            if base == _STORE_DIRNAME:
                dirs.append(dirpath)
                dirnames[:] = []                      # do not descend into the store
                continue
            dirnames[:] = [x for x in dirnames
                           if (x == _STORE_DIRNAME
                               or (x not in _VENDOR and not x.startswith(".")))
                           and ".bak-" not in x and not x.endswith(".bak")]
    except OSError:
        pass
    return dirs


def _curated_store_dirs(root, cache_ttl=3600):
    """Store DIRS under `root`, from a per-root cache of the expensive walk. The cache is valid while
    it is younger than `cache_ttl` AND stamped with the current stores-generation - so a newly created
    store dir (which bumps the generation) invalidates it immediately, while unchanged roots skip the
    walk entirely. Cache sits with the other recall caches; any IO error falls back to a live walk."""
    key = hashlib.sha1(("dirs:" + str(root)).encode("utf-8", "surrogatepass")).hexdigest()[:12]
    cache = sig._audit_dir() / ("curated-dirs.%s.txt" % key)
    stamp = "v2 gen:%d" % sig.stores_generation()
    return _cached_walk(cache, stamp, cache_ttl, lambda: _walk_store_dirs(root))


def _find_curated_stores(root, cache_ttl=3600):
    """Every curated body under `root`: the central slug store's `facts/*.md` (flat, slug-named;
    a transitional sharded remnant `facts/<shard>/<uuid>.md` is still read). The store-dir WALK is
    cached (see _curated_store_dirs); the facts are re-globbed FRESH here, so a just-dreamed fact
    surfaces immediately. Excludes the archive dot-dir (`.archive` starts with a dot, so the parent
    filter drops it)."""
    out = []
    for sdir in _curated_store_dirs(root, cache_ttl=cache_ttl):
        fdir = Path(sdir) / "facts"
        out += [str(p) for p in sorted(fdir.glob("*.md")) + sorted(fdir.glob("*/*.md"))
                if not p.parent.name.startswith(".")]   # pathlib * matches dotfiles
    return out


def discover_curated(self_cwd, exclude_proj=None, cache_ttl=3600):
    """Curated slug-store bodies across the workspace tree, for cross-project recall/gather. The
    bodies are CENTRAL per tree (one store at each tree top), so there is no per-project store to
    exclude; the current project's pointer LINES are already in context, but a body is read on
    demand either way. Cached per workspace root (TTL); empty if no workspace root."""
    root = _workspace_root(self_cwd)
    if root is None:
        return []
    # The expensive store-dir WALK is cached (TTL + stores-generation) inside _find_curated_stores,
    # which re-globs facts FRESH - so a newly dreamed fact is never stale (unlike a cached file list).
    return _find_curated_stores(root, cache_ttl=cache_ttl)


def scan(keywords, files, skipped=None):
    """Map each file that contains any keyword to the list of keywords it matched. Matching is
    WORD-BOUNDARY (letters and digits of any script are word chars; `-`/`_` and punctuation are
    separators), case-insensitive - so `again` does NOT match `against` and `test` does NOT match
    `latest` (a substring match made recall match half the store).

    A file that cannot be read OR decoded as UTF-8 is skipped, never raised: one stray latin-1 note
    must not end the scan for every other file. Pass a list as `skipped` to receive a
    (path, reason) pair per skipped file."""
    pats = {}
    for k in keywords:
        k = _fold(k)
        if k and k not in pats:
            pats[k] = re.compile("(?<!%s)%s(?!%s)" % (_WORD_CHAR, re.escape(k), _WORD_CHAR))
    out = {}
    for p in files:
        try:
            text = _fold(Path(p).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError) as exc:
            if skipped is not None:
                skipped.append((str(p), "%s: %s" % (type(exc).__name__, exc)))
            continue
        hits = [k for k, rx in pats.items() if rx.search(text)]
        if hits:
            out[str(p)] = hits
    return out


# ---- debounce -----------------------------------------------------------------------------------
# A (project, topic) pair already gathered should not be re-grepped on every trigger. The record
# lives OUT of the curated store on purpose: written into it, it would be a fact, and the next dream
# would dutifully tidy, promote or dedup a bookkeeping row. It sits beside the other out-of-store
# counters instead.

GATHERED_FILE = "gathered-topics.tsv"


def _gathered_path():
    return sig._audit_dir() / GATHERED_FILE


def _pair_key(proj, topic, pathmod=os.path):
    """The comparison key for a (project, topic) pair.

    Topic is free text a caller retypes, so an exact match would debounce almost nothing: it is
    casefolded and its whitespace collapsed. Tabs go with that collapse, which also keeps a topic
    from forging a second column in a TSV row. The project path is case-normalised the way the
    platform compares paths, so C:\\Work and c:\\work are one project on Windows."""
    return (pathmod.normcase(pathmod.abspath(str(proj))), " ".join(str(topic).split()).casefold())


def _read_pairs():
    """Every recorded pair. An unreadable store is an EMPTY one, never an error: debounce is an
    optimisation, and losing it costs a re-grep - it must not break a gather."""
    out = set()
    try:
        lines = _read_lines(_gathered_path())
    except (OSError, ValueError):
        return out
    for line in lines:
        parts = line.rstrip("\r").split("\t")
        if len(parts) >= 2:
            out.add(_pair_key(parts[0], parts[1]))
    return out


def already_gathered(proj, topic):
    """True when this (project, topic) pair was already marked."""
    return _pair_key(proj, topic) in _read_pairs()


def mark_gathered(proj, topic, when=None):
    """Record a (project, topic) pair as gathered. Idempotent - re-marking adds no row.

    Returns True when a row was written, False when the pair was already recorded. A failed write
    raises OSError: the caller asked for a record and must learn it was not made."""
    if already_gathered(proj, topic):
        return False
    path = _gathered_path()
    stamp = when or datetime.date.today().isoformat()
    row = "%s\t%s\t%s\n" % (os.path.abspath(str(proj)), " ".join(str(topic).split()), stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as fh:
        fh.write(row)
    return True


def _parse(argv):
    ap = argparse.ArgumentParser(description="Cross-tree gather stage-1: keyword grep for candidates.")
    ap.add_argument("--topic", required=True, help="topic / scope-descriptor text to gather for")
    ap.add_argument("--self", dest="self_proj", default=None,
                    help="current project cwd to EXCLUDE (you gather from elsewhere)")
    ap.add_argument("--cross-tree", action="store_true", dest="cross_tree",
                    help="deliberately gather across OTHER knowledge trees even when "
                         "cross_tree_search=false (import is always a labeled COPY)")
    ap.add_argument("--seen", action="store_true",
                    help="ask ONLY whether this (project, topic) pair was already gathered and "
                         "exit: 0 yes, 1 no, 2 error. Runs no scan - it is the cheap pre-check")
    ap.add_argument("--mark", action="store_true",
                    help="record this (project, topic) pair as gathered and exit: 0 recorded "
                         "(or already was), 2 the record could not be written. Runs no scan")
    return ap.parse_args(sys.argv[1:] if argv is None else argv)


def _tolerant_stdio():
    """Make stdout/stderr replace what their encoding cannot carry rather than crash: a Windows
    pipe is cp1252, and a CJK keyword or path would otherwise end the run mid-report."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def _not_scanned(reason):
    """The explicit empty result: the caller reads CANDIDATES either way, and learns why."""
    print(reason, file=sys.stderr)
    print("CANDIDATES: 0 (not scanned: %s)" % reason)
    return 0


def _candidate_files(self_proj, cross_allowed):
    """(files, None) to scan, or (None, reason) when the walled scan has no tree to stay in.

    Every path is symlink-resolved and de-duplicated, so a tree reached through two spellings is
    one tree, and the walled filter compares resolved paths on both sides."""
    files = [str(f) for f in discover_files(self_proj)]
    files += discover_curated(self_proj, self_proj)   # other projects' curated stores in this tree
    if cross_allowed:
        # OTHER knowledge trees are invisible to the workspace walk - discover them via the
        # configured discovery_roots (the multi-tree knob) and scan their stores too.
        for r in sig.discovery_roots():
            files += _find_curated_stores(str(r))
    files = sorted({os.path.realpath(f) for f in files})
    if cross_allowed:
        return files, None
    # gather walled into the CURRENT tree: sources outside its anchor (incl. the
    # path-unattributable native tier) are dropped; pass --cross-tree for a deliberate,
    # labeled cross-tree gather.
    anchor = sig.resolve_anchor(self_proj)
    if anchor is None:
        return None, "no tree anchor for %s and cross_tree_search=false" % os.path.abspath(self_proj)
    return within_tree(files, anchor), None


def _warn_skipped(skipped):
    for path, reason in take_walk_errors():
        print("warning: cannot list, skipping: %s: %s" % (path, reason), file=sys.stderr)
    for path, reason in skipped:
        print("warning: skipped unreadable file: %s (%s)" % (path, reason), file=sys.stderr)


def _print_candidates(hits, keywords):
    by_tree = {}
    for path in hits:
        top = sig.resolve_anchor(str(Path(path).parent))
        label = str(top) if top else "native-tier (machine-local)"
        by_tree.setdefault(label, []).append(path)
    for label in sorted(by_tree):
        print("TREE: %s" % label)                 # cross-tree import is ALWAYS a labeled COPY
        for path in sorted(by_tree[label]):
            print("  %s\t%s" % (path, ",".join(hits[path])))
    print("CANDIDATES: %d in %d tree(s) (keywords: %s)"
          % (len(hits), len(by_tree), ", ".join(keywords)))


def _print_mcp_candidates(self_proj, topic):
    """Optional: when a memory MCP (basic-memory) is enabled and its index covers this tree, add
    its semantic/full-text hits as EXTRA candidates for the agent to read-note. Read-only; the
    keyword scan is always the base, so this is a pure augmentation (absent/misconfigured MCP ->
    nothing)."""
    try:
        import mcp_search as _mx
        if _mx.enabled() and (self_proj is None or _mx.covers(self_proj)):
            mhits = _mx.search(topic)
            if mhits:
                for h in mhits:
                    print("MCP\t%s" % h)
                print("MCP-CANDIDATES: %d (via basic-memory search)" % len(mhits))
    except Exception:  # noqa: BLE001 - the MCP path must never break the keyword gather
        pass


def _run(args):
    given = args.self_proj or os.getcwd()
    # abspath: a trailing separator or "." must name the same project as the plain spelling.
    self_proj = os.path.abspath(given)

    # Both answer from the debounce record alone. Deliberately BEFORE any discovery: --seen exists
    # to avoid the walk, so a version that walked first would defeat its own purpose. And neither
    # gates a plain scan - a scan explicitly asked for is a scan run, whatever the record says.
    if args.seen:
        return 0 if already_gathered(self_proj, args.topic) else 1
    if args.mark:
        mark_gathered(self_proj, args.topic)
        return 0
    keywords = extract_keywords(args.topic, proj=self_proj)   # per-project blacklist for the current proj
    if not keywords:
        return _not_scanned("no usable keywords from topic")
    cross_allowed = args.cross_tree or sig.load_config().get("cross_tree_search", True)
    # The spelling as given, not the abspath: the own-memory exclusion needs every spelling the
    # project may be keyed by, and abspath can rewrite the one the caller named (see _own_memory_dirs).
    files, reason = _candidate_files(given, cross_allowed)
    if files is None:
        return _not_scanned(reason)
    skipped = []
    hits = scan(keywords, files, skipped=skipped)
    _warn_skipped(skipped)
    _print_candidates(hits, keywords)
    _print_mcp_candidates(self_proj, args.topic)
    return 0


def main(argv=None):
    args = _parse(argv)
    _tolerant_stdio()
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - exit 1 means "not gathered"; a crash must not say that
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
