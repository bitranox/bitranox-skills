"""Shared learning-signal patterns for the self-improve hooks.

Single source of truth, imported by:
  * self-improve-gate.py  - the per-turn Stop hook (uses the STRICT patterns: high
    precision, fires a capture nudge on the last turn).
  * self-improve-audit.py - the SessionEnd hook (uses STRICT + the BROADER recall
    patterns to find CANDIDATE MISSES across the whole session: a turn the broad set
    flags but the strict set did not, i.e. a likely gate gap to review next session).

Signals cluster in FAMILIES; cover the family, do not wait to be fed one phrase at a time:
  (1) USER correction, (2) USER explicit "remember", (3) ENDORSEMENT of a good idea from
  EITHER side, (4) ASSISTANT self-admitted miss, (5) ASSISTANT realization/discovery.

Role split: correction/"remember" count only from the USER; self-admitted misses and
realizations only from the ASSISTANT; endorsement counts from either side. English + German.
"""

import contextlib
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

# ---- Audit-file location (shared by self-improve-audit.py writer + session-start reader) --

def proj_key(proj):
    """Stable per-project key (matches the gate's state-file scheme)."""
    return hashlib.sha1(proj.encode("utf-8", "replace")).hexdigest()[:16]


def audit_file(proj):
    """Where the SessionEnd audit writes candidate misses for the next SessionStart to read."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".md")


# ---- meta-dream-tree consolidation: cadence markers + mode (shared by session-start + dream_state) --

_DREAM_THRESHOLD_S = 24 * 3600  # do not nudge a fresh consolidation more often than this


def memory_dir(proj):
    """The native Auto-memory dir for a project cwd (Claude Code sanitizes '/' to '-')."""
    return Path.home() / ".claude" / "projects" / proj.replace("/", "-") / "memory"


# ---- curated store relocation: <proj>/.claude-bx-selflearning (the new per-project home) ----
# The curated tier lives IN the project tree (travels with it; gitignored on public repos) so a
# single `@import` line pulls its `index.md` into context. That line lives in the UNTRACKED
# `CLAUDE.local.md` by default (symmetric with the gitignored store), or the TRACKED `CLAUDE.md` when
# `track_private` is on. The native `memory_dir()` above stays as the raw second tier.

MEMORY_DIRNAME = ".claude-memory"             # the LIVE central body-store dir, co-located at a tree's
                                              # anchor; the store-colocation key for anchor resolution

# Dirs never worth walking for stores/CLAUDE.md (vendored / build / VCS / cache). Single source;
# gather_scan and the multi-tree walks alias this.
VENDOR_DIRNAMES = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "site-packages", ".mypy_cache",
    ".pytest_cache", ".tox", ".idea", ".ruff_cache", "dist", "build", ".eggs",
}

# LEGACY dirnames: the retired pre-UUID store layout. Kept ONLY for the one-shot migration tools
# (migrate_to_uuid_store, migrate_memory receipts) and gather_scan's transitional dual-read on
# downstream installs. Nothing else may key on these.
CURATED_DIRNAME = ".claude-bx-selflearning"
CURATED_INDEX = "index.md"                    # named `index.md` (not `memory.md`) so it is never
                                              # confused with Claude Code's native `MEMORY.md` tier


def claude_memory_dir(proj):
    """The project-local curated memory dir: `<proj>/.claude-bx-selflearning`.
    Holds `index.md` (the @imported index), `facts/<slug>.md` (lazy bodies), `state/`, `.archive/`."""
    return Path(proj) / CURATED_DIRNAME


def claude_md_path(proj):
    """The project's TRACKED CLAUDE.md. Carries the `@import` of `index.md` only when `track_private`
    is on (memory committed with the repo); otherwise the import lives in `claude_local_md_path`."""
    return Path(proj) / "CLAUDE.md"


def claude_local_md_path(proj):
    """The project's UNTRACKED `CLAUDE.local.md` - the DEFAULT home for the `@import` of `index.md`
    (track_private off). Symmetric with the gitignored store: the memory wiring never touches tracked
    git, a fresh clone has neither the wiring nor the store, and no commit is needed to set up memory."""
    return Path(proj) / "CLAUDE.local.md"


def ensure_gitignored(proj, *patterns):
    """Best-effort: on a git repo, ensure each `pattern` is in the repo-root `.gitignore`. Honors
    `track_private` (skip if set - the user wants memory committed). Non-git dir or any error -> skip
    (fail-open). Used by per-turn capture so a fresh untracked `CLAUDE.local.md` + curated store are
    never accidentally staged into a public repo."""
    if load_config().get("track_private"):
        return
    import subprocess
    try:
        top = subprocess.run(["git", "-C", str(proj), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return
    if not top:
        return
    try:
        gi = Path(top) / ".gitignore"
        cur = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        have = set(cur.splitlines())
        add = [p for p in patterns if p not in have and p.rstrip("/") not in have]
        if add:
            gi.write_text((cur.rstrip("\n") + "\n" if cur.strip() else "")
                          + "# bitranox curated memory (local; CLAUDE.local.md @imports it)\n"
                          + "\n".join(add) + "\n", encoding="utf-8")
    except OSError:
        pass


def curated_index(proj):
    """The always-@imported curated index file (`index.md`) for a project."""
    return claude_memory_dir(proj) / CURATED_INDEX


def curated_state_dir(proj):
    """Tree-shared state dir in the LIVE store: `<anchor>/.claude-memory/state`. Per-project files
    inside it encode the project in their filename (see migrate_memory's receipts)."""
    return global_rules_dir(proj) / "state"


# ---- Claude Code version gate (the @import load-path depends on a new-enough Claude Code) ---------
# @import is only honored by a new-enough Claude Code. Detect the running version from
# CLAUDE_CODE_EXECPATH (`.../versions/X.Y.Z`), fall back to AI_AGENT (`claude-code_X-Y-Z_agent`). No
# shell-out. Unknown version -> assume supported (fail-open toward functioning; the gate only catches
# a KNOWN-too-old Claude Code, where it tells the user to upgrade rather than silently misbehaving).

# Conservative floor: @import + the CLAUDE.md cascade predate the changelog's memory entries and work
# on 2.1.198 (Phase-0 verified). Keep this low; bump only if a real regression pins a higher floor.
MIN_IMPORT_VERSION = (2, 0, 0)


def claude_code_version(env=None):
    """(major, minor, patch) of the running Claude Code, or None if undetectable.
    Parses CLAUDE_CODE_EXECPATH then AI_AGENT; both are exposed to hooks (Phase-0 verified)."""
    env = os.environ if env is None else env
    m = re.search(r"versions[/\\](\d+)\.(\d+)\.(\d+)", env.get("CLAUDE_CODE_EXECPATH", ""))
    if not m:
        m = re.search(r"claude-code[_-](\d+)[._-](\d+)[._-](\d+)", env.get("AI_AGENT", ""))
    return tuple(int(g) for g in m.groups()) if m else None


def import_supported(env=None):
    """True if the running Claude Code is new enough to honor CLAUDE.md `@import`. Unknown -> True
    (fail-open). A hook uses this to decide whether to load/capture or to emit the upgrade notice."""
    v = claude_code_version(env)
    return True if v is None else v >= MIN_IMPORT_VERSION


IMPORT_UPGRADE_NOTICE = (
    "bitranox memory: this Claude Code is too old for CLAUDE.md `@import` "
    "(need >= %d.%d.%d); curated memory is not loaded/captured until you upgrade."
    % MIN_IMPORT_VERSION
)


# ---- cross-platform advisory lock for memory read-modify-write --------------------------------
# The write engine, dream, and migration all read-modify-write `index.md`/`facts/`; two sessions (or
# the migration fan-out) on a shared/NFS checkout can lost-update. An atomic O_EXCL lockfile is used
# (NOT fcntl/msvcrt) so this module imports cleanly on EVERY OS - a top-level `import fcntl` would
# ImportError on Windows and kill every hook. On contention past `timeout` we raise so the caller can
# skip-and-report the WHOLE target (never a partial write).

_LOCK_STALE_S = 120.0


@contextlib.contextmanager
def memory_lock(target_path, timeout=5.0, poll=0.05, now=None):
    """Advisory exclusive lock around a memory read-modify-write, via an atomic `<target>.lock`
    O_EXCL create (cross-platform, no fcntl/msvcrt). Raises TimeoutError on contention past `timeout`;
    reclaims a lock older than `_LOCK_STALE_S` (holder crashed). `now` injectable for tests."""
    clock = time.time if now is None else now
    lock = Path(str(target_path) + ".lock")
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    deadline = clock() + timeout
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                if clock() - lock.stat().st_mtime > _LOCK_STALE_S:
                    lock.unlink()
                    continue
            except OSError:
                pass
            if clock() >= deadline:
                raise TimeoutError("memory_lock: contention on %s" % lock)
            time.sleep(poll)
    try:
        yield
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            lock.unlink()
        except OSError:
            pass


def last_dream_file(proj):
    """Marker holding the unix timestamp of the last completed dream for this project."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".dream")


def dream_mode(proj=None):
    """Dream mode (single source of truth = the machine-local config; see load_config):
      off     -> no dream nudges; a manual dream consolidates memory only, no CLAUDE.md/skill proposals
      auto    -> dream applies CLAUDE.md edits and ships skill changes WITHOUT per-change prompts
      propose -> (default) dream asks before CLAUDE.md edits and routes skill changes to a self-PR
    Reads `~/.claude/.bitranox-memory.json`; without it, the recommended default applies.
    """
    return load_config().get("dream_mode", "propose")


def _newest_mtime(d):
    newest = 0.0
    try:
        for p in d.glob("*.md"):
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                continue
    except OSError:
        return 0.0
    return newest


# ---- real-fact accounting across BOTH tiers (native raw + curated) ------------------------------
# The dream cadence + new-project seeding must react to REAL facts, not file mtimes (gap-fill creates
# an empty scope-only `index.md`, and mtimes churn) and must see BOTH the native raw tier and the
# curated `.claude-bx-selflearning/` tier. `store_signature` is a content hash over the facts in both
# tiers, scope-block EXCLUDED - it changes only when a fact is added/edited/removed, so it is stable
# under gap-fill and non-content writes (and self_improve_signals does not import the memory engine,
# to avoid a cycle - it reads the curated store with a light, grammar-free scan).

def _strip_scope(text):
    b = (text or "").find(SCOPE_MARK_BEGIN)
    if b < 0:
        return text or ""
    e = text.find(SCOPE_MARK_END, b)
    if e < 0:
        return text
    return text[:b] + text[e + len(SCOPE_MARK_END):]


def _curated_fact_parts(proj):
    """Signature parts for the curated tier: the fact POINTER lines (`- [Title](uuid:..) - hook ...`)
    from this level's `CLAUDE.local.md` pointer block (scope descriptor excluded). Empty when the level
    holds no real facts (a scope-only block contributes nothing). A pointer line's title + hook + slug
    change whenever a fact is added, edited, or removed, so this is a stable fact fingerprint without
    reading every central body."""
    parts = []
    try:
        text = claude_local_md_path(proj).read_text(encoding="utf-8")
        region = "\n".join(ln for ln in text.splitlines() if ln.startswith("- ["))
        if region.strip():
            parts.append(region)
    except OSError:
        pass
    return parts


def _native_fact_parts(proj):
    """Signature parts for the native raw tier: each topic `*.md` (excluding the MEMORY.md index)."""
    parts = []
    try:
        for p in sorted(memory_dir(proj).glob("*.md")):
            if p.name == "MEMORY.md":
                continue
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except OSError:
                continue
    except OSError:
        pass
    return parts


def store_signature(proj):
    """Content hash over the REAL facts in BOTH tiers (scope block excluded). '' when there are none.
    Stable under gap-fill / mtime churn; changes only when a fact is added, edited, or removed."""
    parts = sorted(_native_fact_parts(proj) + _curated_fact_parts(proj))
    if not parts:
        return ""
    return hashlib.sha1("\x00".join(parts).encode("utf-8", "replace")).hexdigest()


def has_any_facts(proj):
    """True if the project holds at least one real fact in either tier (native or curated)."""
    return bool(_native_fact_parts(proj) or _curated_fact_parts(proj))


def _read_dream_record(proj):
    """(last_ts, last_sig) from the .dream marker, or None. New format = JSON {ts, sig}; a legacy
    bare-float timestamp yields (ts, '') so the first post-upgrade check re-dreams once."""
    try:
        raw = last_dream_file(proj).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    try:
        d = json.loads(raw)
        return float(d["ts"]), str(d.get("sig", ""))
    except (ValueError, KeyError, TypeError):
        try:
            return float(raw), ""
        except ValueError:
            return None


def dream_due(proj, threshold_s=_DREAM_THRESHOLD_S, now=None):
    """True if a memory consolidation is due: mode not off, the fact SIGNATURE changed since the last
    dream (real facts added/edited/removed - not mtime churn, not a gap-fill scope-only write), and
    the last dream is older than the threshold. No facts or mode off -> not due."""
    if dream_mode(proj) == "off":
        return False
    sig_now = store_signature(proj)
    if not sig_now:
        return False  # no facts to consolidate
    now = time.time() if now is None else now
    rec = _read_dream_record(proj)
    if rec is None:
        return True  # never dreamed but facts exist -> due
    last_ts, last_sig = rec
    return sig_now != last_sig and (now - last_ts) > threshold_s


def mark_dream_done(proj, now=None):
    """Record that a dream just completed: store the current timestamp AND fact signature, so the
    nudge stays silent until a real fact changes (not merely a file mtime)."""
    f = last_dream_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"ts": time.time() if now is None else now,
                                 "sig": store_signature(proj)}), encoding="utf-8")
        return True
    except OSError:
        return False


# ---- machine-local config: one JSON for all informed-consent knobs (recommended defaults) ----
# Every habit-dependent decision is recorded here and applied automatically (asked once, never
# re-nagged). The `meta-memory-settings` skill views / sets / resets it.

def _config_path():
    return Path.home() / ".claude" / ".bitranox-memory.json"


DEFAULT_CONFIG = {
    "dream_mode": "propose",       # off | auto | propose
    "privacy": "open",             # open (secret/PII scrub only) | walled (by privacy domain)
    "promotion": "corroborated",   # corroborated (inferred needs dwell) | eager
    "skill_placement": "lowest",   # lowest scope that fits; ask before the public marketplace
    "nudges": True,                # session-start nudges on/off
    "track_private": False,        # git-track .claude-bx-selflearning on a private repo? (public: never)
    "mcp_search": "auto",          # off | auto (use a full-text+graph MCP for cross-project recall if present)
    "cross_tree_search": True,     # per-prompt recall may scan OTHER knowledge trees (False: current tree only)
    "discovery_roots": [],         # extra roots to walk for curated stores; [] -> derive at runtime (never
                                   # ship hardcoded maintainer absolute paths in this tracked default)
}


def load_config():
    """Config merged over DEFAULT_CONFIG. Robust: a missing or corrupt file yields the
    recommended defaults."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(_config_path().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            cfg.update({k: raw[k] for k in raw if k in DEFAULT_CONFIG})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(updates):
    """Merge known keys from `updates` into the config file (created if missing); return the
    saved dict. Unknown keys are ignored so the file stays a clean, known schema."""
    cfg = load_config()
    cfg.update({k: updates[k] for k in updates if k in DEFAULT_CONFIG})
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    return cfg


# ---- altitude homes (always-present tiers, narrowest -> broadest) --------------------

def _excluded_anchor_dirs():
    """Dirs that must NEVER be a memory altitude anchor even if they carry a `CLAUDE.md` + store: the
    user's HOME and the system temp dir (the filesystem root is handled separately via `d.anchor`).
    Walking UP by `.parent` from a real project cwd never reaches these in practice - a project lives
    under a mount like `/media/.../projects`, not directly at `~` or `/tmp` - so this is a safety net,
    not the primary bound: it stops a stray `CLAUDE.md` left at `~` / `/tmp`, or a test/probe running
    under the temp dir, from hijacking the anchor. Read fresh each call so a monkeypatched HOME/TMPDIR
    is honored."""
    out = set()
    for env in ("HOME", "USERPROFILE"):
        h = os.environ.get(env)
        if h:
            try:
                out.add(Path(h))
            except (OSError, ValueError):
                pass
    try:
        out.add(Path(tempfile.gettempdir()))
    except (OSError, ValueError):
        pass
    return out


def resolve_anchor(proj):
    """THE canonical anchor resolver (single source; `uuid_store.resolve_anchor` delegates here).

    The anchor of `proj`'s knowledge TREE: the TOPMOST ancestor (including `proj`) that carries a
    `CLAUDE.md` AND the co-located central store (`.claude-memory/`). Tying the anchor to the store it
    must hold stops a STRAY `CLAUDE.md` higher up (nested workspaces routinely have `CLAUDE.md` at many
    levels) from hijacking the tree top - a real fragility a probe caught. Only at BOOTSTRAP, when no
    dir in the chain has a store yet, fall back to the topmost `CLAUDE.md` (the first write creates the
    store there and thereafter the colocation pins it). Never anchors at `/`, `~`, or the temp dir
    (see `_excluded_anchor_dirs`). Returns a Path, or None when no ancestor has a `CLAUDE.md` at all.
    With MULTIPLE independent trees on one machine, each cwd resolves to its OWN tree's anchor."""
    try:
        ladder = [Path(proj), *Path(proj).parents]
    except (TypeError, ValueError):
        return None
    excluded = _excluded_anchor_dirs()
    highest_both = None                              # topmost dir with a CLAUDE.md AND a store (robust)
    highest_md = None                                # topmost dir with a CLAUDE.md (bootstrap fallback)
    for d in ladder:
        try:
            if d == Path(d.anchor) or d in excluded:  # never anchor at /, ~, or the temp dir
                continue
            has_md = (d / "CLAUDE.md").is_file()
            has_store = (d / MEMORY_DIRNAME).is_dir()
        except OSError:
            continue
        if has_md:
            highest_md = d
        if has_md and has_store:
            highest_both = d
    return highest_both or highest_md


# The historical name; same resolver (kept so call sites and prose stay readable).
topmost_claude_md_dir = resolve_anchor


def global_rules_dir(proj=None):
    """The tree-top central store: `<anchor>/.claude-memory` for `proj`'s OWN tree (share-visible, so
    it reaches every machine that mounts the tree). NEVER `~/.claude` (machine-local, invisible from a
    remote mount). If no ancestor - nor `proj` itself - has a `CLAUDE.md`, `proj` IS the top level and
    accumulates everything. `proj` defaults to the current working directory."""
    base = proj if proj is not None else os.getcwd()
    return (resolve_anchor(base) or Path(base)) / MEMORY_DIRNAME


def discovery_roots():
    """Filesystem roots to WALK for other projects' curated `.claude-bx-selflearning/` stores (used by
    cross-project recall + as the MCP's watched roots). The config `discovery_roots` list (a machine-
    local override in ~/.claude/.bitranox-memory.json) UNION the DERIVED default `$HOME` - so the
    tracked DEFAULT_CONFIG never ships hardcoded maintainer absolute paths (public-plugin safe). The
    walk is additionally backstopped by reverse-resolving native slugs (see resolve_slug), so a
    project outside these roots is still discoverable. Deduped, existing dirs only."""
    roots = set()
    for r in (load_config().get("discovery_roots") or []):
        try:
            roots.add(Path(str(r)).expanduser())
        except (OSError, ValueError):
            continue
    roots.add(Path.home())
    return sorted({p for p in roots if _is_dir(p)}, key=str)


def _is_dir(p):
    try:
        return Path(p).is_dir()
    except OSError:
        return False


def find_claude_md_dirs(roots):
    """Every dir under `roots` that carries a `CLAUDE.md` - the raw material for tree discovery.
    Prunes vendor/hidden/backup dirs, the store dirs themselves, `~/.claude`, and the excluded
    anchor dirs; never follows symlinks (a link into another tree must not merge them)."""
    out = set()
    excluded = {str(d) for d in _excluded_anchor_dirs()}
    home_claude = str(Path.home() / ".claude")
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                base = os.path.basename(dirpath)
                if (base in VENDOR_DIRNAMES or base in (MEMORY_DIRNAME, CURATED_DIRNAME)
                        or ".bak-" in base or base.endswith(".bak")
                        or dirpath == home_claude):
                    dirnames[:] = []
                    continue
                dirnames[:] = [d for d in dirnames
                               if d not in VENDOR_DIRNAMES
                               and d not in (MEMORY_DIRNAME, CURATED_DIRNAME)
                               and not d.startswith(".")
                               and ".bak-" not in d and not d.endswith(".bak")]
                if "CLAUDE.md" in filenames and dirpath not in excluded:
                    out.add(Path(dirpath))
        except OSError:
            continue
    return sorted(out, key=str)


def tree_groups(md_dirs):
    """Group CLAUDE.md-bearing dirs into their knowledge TREES: {top_dir: [members]}, members
    deepest-first (lexicographic ties). The top is each member's `resolve_anchor` - so independent
    trees (a marketing company and a bakery share nothing) come out as separate groups, each with
    its own top and store."""
    groups = {}
    for d in md_dirs:
        top = resolve_anchor(str(d))
        if top is None:
            top = Path(d)
        groups.setdefault(top, []).append(Path(d))
    for top, members in groups.items():
        members.sort(key=lambda m: (-len(m.parts), str(m)))
    return groups


def altitude_chain(proj):
    """Ordered altitude LEVEL DIRS for `proj`, narrowest -> broadest: the project dir itself, then
    each ancestor directory up to and INCLUDING the tree's anchor (gap levels between are included so
    they can be filled). The LAST (broadest) position is the tree top - NEVER `~/.claude`. If no
    ancestor - nor `proj` - has a `CLAUDE.md`, the chain is just `[proj]` (it is the top; everything
    accumulates there). Each level's pointer block lives in `<level>/CLAUDE.local.md`; the bodies all
    live centrally at the anchor's `.claude-memory/`. Reference-integrity uses this: a `[[ref]]` must
    resolve to a target at the SAME or a LATER (higher) position - upward only."""
    try:
        here = Path(proj)
        ladder = [here, *here.parents]            # project dir up toward /
        top = resolve_anchor(proj)                # the tree's anchor, or None
        if top is None:                           # project is the top; single-tier chain
            return [here]
        highest = ladder.index(top)
        return ladder[:highest + 1]
    except (TypeError, ValueError):
        return [Path(proj)]


# ---- new-project seeding (one-time /collect-knowledge bootstrap nudge) ---------------

def seeded_file(proj):
    """Marker that this project has been seed-nudged (so the bootstrap nudge fires once)."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".seeded")


def mark_seeded(proj, now=None):
    f = seeded_file(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(time.time() if now is None else now), encoding="utf-8")
        return True
    except OSError:
        return False


def project_unseeded(proj):
    """True if this project has no REAL facts in EITHER tier yet AND has not been seed-nudged - a fresh
    project that could be bootstrapped from the existing knowledge tree via /collect-knowledge. Counts
    real facts (not a gap-fill scope-only index.md), so the nudge never misfires on an empty store."""
    if seeded_file(proj).exists():
        return False
    return not has_any_facts(proj)


# ---- quality / dwell gate for global promotion (high blast radius) -------------------
# The global layer loads into EVERY session, so a wrong entry there is high-blast. A user-stated
# concrete rule promotes eagerly; a model-INFERRED generalization must be corroborated (seen across
# >= threshold dreams) first. The dwell counter lives OUT of the dreamed store (here), so counting
# never bumps the store mtime - the convergence no-op holds.

def _promote_file(proj):
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".promote.json")


def _read_counts(path):
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def note_promotion_candidate(proj, key):
    """Record that this dream saw promotion-candidate `key`; return its dwell count (number of
    dreams it has appeared in). Out-of-store, so it does not affect convergence."""
    f = _promote_file(proj)
    counts = _read_counts(f)
    counts[key] = int(counts.get(key, 0)) + 1
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
    except OSError:
        pass
    return counts[key]


def clear_promotion_candidate(proj, key):
    """Forget a candidate's dwell count (call after it is promoted, so it is not re-counted)."""
    f = _promote_file(proj)
    counts = _read_counts(f)
    if key in counts:
        del counts[key]
        try:
            f.write_text(json.dumps(counts, sort_keys=True), encoding="utf-8")
        except OSError:
            pass


def should_promote(source, dwell_count, mode=None, threshold=2):
    """Whether a generalization may be promoted to the always-everywhere global layer.
    source is "user" (user-stated concrete rule -> eager) or "inferred" (model generalization ->
    needs corroboration). mode comes from the config (`promotion`: corroborated | eager)."""
    mode = load_config().get("promotion", "corroborated") if mode is None else mode
    if mode == "eager" or source == "user":
        return True
    return int(dwell_count) >= threshold


# ---- per-level scope descriptor: a bounded, marked block in a CLAUDE.md --------------
# Each altitude declares "what this level is about" so the classifier can route knowledge. The
# descriptor is a clearly-delimited block so it never touches the user's hand-written content, and
# the upsert is DIFF-FREE (a no-change refresh returns the text unchanged -> convergence holds).

SCOPE_MARK_BEGIN = "<!-- bitranox:self-learning -->"
SCOPE_MARK_END = "<!-- /bitranox:self-learning -->"


def read_scope_block(text):
    """Return the descriptor inside the bitranox:self-learning markers in `text`, or None."""
    b = (text or "").find(SCOPE_MARK_BEGIN)
    if b < 0:
        return None
    e = text.find(SCOPE_MARK_END, b)
    if e < 0:
        return None
    return text[b + len(SCOPE_MARK_BEGIN):e].strip()


def upsert_scope_block(text, descriptor):
    """Return CLAUDE.md `text` with the marked scope block set to `descriptor` (replaced in place if
    present, appended if absent). DIFF-FREE: if the block already holds `descriptor`, return `text`
    unchanged so a no-change refresh writes nothing."""
    text = text or ""
    descriptor = (descriptor or "").strip()
    block = "%s\n%s\n%s" % (SCOPE_MARK_BEGIN, descriptor, SCOPE_MARK_END)
    b = text.find(SCOPE_MARK_BEGIN)
    if b >= 0:
        e = text.find(SCOPE_MARK_END, b)
        if e >= 0:
            if text[b + len(SCOPE_MARK_BEGIN):e].strip() == descriptor:
                return text  # already current -> no write
            return text[:b] + block + text[e + len(SCOPE_MARK_END):]
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block + "\n"


def store_changed(memory_dir_path, since_mtime):
    """True if a memory dir changed since `since_mtime` (a 'store changed under me' guard for the
    dream's read-modify-write; pair with the pre-flight backup)."""
    return _newest_mtime(Path(memory_dir_path)) > float(since_mtime)


# NOTE: there is deliberately NO usage/age/size "forgetting" mechanism. Usage cannot be measured (the
# note sits in context; the model reasons over it silently), and age/size are not valid forget metrics
# (see the `forgetting-is-usage-based-only` memory). Removal happens only via dedup, obsolete/superseded
# pruning (model-judged, propose-first), or a manual request - the dream does that; no helper here.


def _model_review_file():
    return Path.home() / ".claude" / "self-improve-audit" / "model-review.txt"


def model_review_due(interval_days=30, now=None):
    """True if the periodic model-hierarchy review (run by meta-dream-tree) is due: no prior review, or the
    last one is older than `interval_days`. GLOBAL (not per-project) and OUT of any memory store, so it
    never bumps a store's mtime (convergence holds). Model releases are infrequent -> a monthly default."""
    import time as _time
    now = _time.time() if now is None else now
    try:
        last = float(_model_review_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= interval_days * 86400


def mark_model_reviewed(now=None):
    """Record that the model-hierarchy review just ran, so it does not re-fire until due again."""
    import time as _time
    now = _time.time() if now is None else now
    f = _model_review_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return now


def _backup_reminder_file():
    return Path.home() / ".claude" / "self-improve-audit" / "offsite-backup-reminder.txt"


def backup_reminder_due(interval_days=30, now=None):
    """True if the periodic off-machine-backup reminder (run by meta-dream-tree) is due: no prior
    reminder, or the last one is older than `interval_days`. The curated memory stores are LOCAL git
    repos (durable against rm/reset) but NOT against disk failure - so from time to time the dream
    reminds the user they can push the store repo(s) to a PRIVATE remote. GLOBAL and OUT of any store
    (never bumps a store's mtime, so convergence holds). Monthly default."""
    import time as _time
    now = _time.time() if now is None else now
    try:
        last = float(_backup_reminder_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return True
    return (now - last) >= interval_days * 86400


def mark_backup_reminded(now=None):
    """Record that the off-machine-backup reminder just fired, so it does not re-fire until due again."""
    import time as _time
    now = _time.time() if now is None else now
    f = _backup_reminder_file()
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(str(now), encoding="utf-8")
    except OSError:
        pass
    return now


# --- Recall filler words (memory-recall keyword precision) ---------------------------------------
# Generic/conversational words must not become recall search keywords (they match half the store).
# THREE lists, split by who is universal vs a project-specific judgment (so one project's learned
# classification never suppresses another project's recall - see the `recall-filler-per-project` memory):
#   - GLOBAL baseline blacklist: filler_words.json next to this module (generic English; grows via PRs).
#   - PER-PROJECT learned blacklist: filler the dream classified for THAT project.
#   - PER-PROJECT learned whitelist: topical/known-good words (so they are not re-queued).
# The per-prompt hook only USES these (deterministic, no model), keyed to the CURRENT project (the
# prompt's origin); GROWING them is a slow dream pass. See meta-dream-tree's "Filler-word classification".

def _filler_baseline_path():
    return Path(__file__).resolve().parent / "filler_words.json"


def _filler_local_path(proj):
    """PER-PROJECT learned filler blacklist (out-of-store, machine-local)."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".filler.json")


def _topical_words_path(proj):
    """PER-PROJECT learned topical whitelist - confirmed genuine topics, not re-queued for classification."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".topical.json")


def _recall_pending_path(proj):
    """PER-PROJECT queue of as-yet-unclassified recall keywords, drained by the dream classifier."""
    return Path.home() / ".claude" / "self-improve-audit" / (proj_key(proj) + ".recall-unknown.txt")


def _read_word_json(path):
    """Read a word-list JSON that may be a bare list or {"filler"/"words"/"topical": [...]}. Fail-open []."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, list):
        words = data
    elif isinstance(data, dict):
        words = data.get("filler") or data.get("words") or data.get("topical") or []
    else:
        words = []
    return [str(w).strip().lower() for w in words if isinstance(w, str) and str(w).strip()]


def _write_word_json(path, words, key="words"):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({key: sorted(set(words))}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def load_filler_words(proj=None):
    """The effective filler blacklist for `proj`: GLOBAL baseline UNION the project's LEARNED filler.
    Baseline is universal generic-English filler; learned filler is per-project so one project's
    classification never suppresses another's recall. With proj=None, baseline only. Lowercased frozenset."""
    words = list(_read_word_json(_filler_baseline_path()))
    if proj is not None:
        words += _read_word_json(_filler_local_path(proj))
    return frozenset(words)


def add_filler_words(words, proj):
    """Append classifier-confirmed filler to the PROJECT's learned blacklist (never the shipped baseline)."""
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _filler_local_path(proj)
    _write_word_json(p, set(_read_word_json(p)) | new, key="filler")


def load_topical_words(proj):
    """The project's learned topical whitelist (genuine topics, not re-queued). Lowercased frozenset."""
    return frozenset(_read_word_json(_topical_words_path(proj)))


def add_topical_words(words, proj):
    """Record classifier-confirmed topical words for THIS project so they are not re-queued."""
    new = {str(w).strip().lower() for w in words if str(w).strip()}
    if not new:
        return
    p = _topical_words_path(proj)
    _write_word_json(p, set(_read_word_json(p)) | new, key="topical")


def note_unknown_keywords(words, proj):
    """Per-prompt: queue this project's recall keywords that are NEITHER known filler NOR known-topical,
    for the dream classifier to judge. Deterministic, append-only, deduped; never calls a model."""
    known = load_filler_words(proj) | load_topical_words(proj)
    cur = load_pending_keywords(proj)
    add = {str(w).strip().lower() for w in words if str(w).strip()} - known - cur
    if not add:
        return
    f = _recall_pending_path(proj)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            for w in sorted(add):
                fh.write(w + "\n")
    except OSError:
        pass


def load_pending_keywords(proj):
    """The project's queued-but-unclassified recall keywords (for the dream classifier)."""
    try:
        return frozenset(w.strip().lower() for w in _recall_pending_path(proj).read_text(
            encoding="utf-8").splitlines() if w.strip())
    except OSError:
        return frozenset()


def clear_pending_keywords(proj):
    """Drain THIS project's queue after the dream classifier has processed it."""
    try:
        _recall_pending_path(proj).unlink()
    except OSError:
        pass


def knowledge_store_empty(proj=None):
    """True if there is nothing to seed a new project FROM. PER-TREE for the curated tier: only
    `proj`'s OWN tree top is consulted (an unrelated tree's facts are not this tree's seed corpus).
    The NATIVE tier scan stays MACHINE-GLOBAL by design - native memories are per-machine raw notes
    and a legitimate seed source across trees. Used to suppress the new-project bootstrap nudge."""
    try:
        if _curated_fact_parts(str(topmost_claude_md_dir(proj) or (proj or os.getcwd()))):
            return False
    except OSError:
        pass
    try:
        for memdir in (Path.home() / ".claude" / "projects").glob("*/memory"):
            for p in memdir.glob("*.md"):
                if p.name != "MEMORY.md":
                    return False
    except OSError:
        pass
    if proj is not None and _curated_fact_parts(proj):
        return False
    return True


# ---- STRICT patterns (the gate fires on these; tuned for precision) -----------------

# USER correction / explicit remember.
USER_PATTERN = re.compile(
    r"no,|nope|that.?s wrong|that is wrong|incorrect|don.?t do|do not do|stop doing"
    r"|you (forgot|missed|should have|shouldn.?t)|not what i|instead of|rather than"
    r"|that.?s not right|isn.?t right"
    r"|remember|note that|keep in mind|for next time|for the future|from now on"
    r"|make a (memory|rule|note)"
    r"|falsch|nein,|stattdessen|anstatt|anstelle|merke? dir|in zukunft|denk dran",
    re.IGNORECASE,
)

# ASSISTANT self-admitted miss (incl. a guard/hook blocking the assistant's own action).
ASST_PATTERN = re.compile(
    r"you(?:'?re| are| were) (?:right|correct)|my mistake|i was wrong|apolog"
    r"|\bmisdiagnos\w+|\bmy\b[^.\n]{0,40}\bwas (?:an? )?(?:misread|mistake|error|wrong|misjudged)\b"
    r"|\bi should(?: have|'?ve)\b|\bi (missed|overlooked|forgot|misread|misunderstood)\b"
    r"|\bi did(?:n'?t| not) (realize|notice|account|consider|catch)\b|\bin hindsight\b"
    r"|\b(from now on|going forward|next time)\b[^.\n]{0,20}\bi('?ll| will| should)\b"
    r"|\bi('?ll| will) (make sure|remember) (to|not)\b"
    r"|\b(hook|guard|gate)\b[^.\n]{0,30}\b(caught|blocked|stopped|flagged|rejected)\b"
    r"|\b(caught|blocked|stopped|flagged|rejected)\b[^.\n]{0,30}\b(hook|guard|gate)\b"
    r"|self.?match(ed|ing|es)?",
    re.IGNORECASE,
)

# ASSISTANT realization/discovery (how something really fits together).
REALIZATION_PATTERN = re.compile(
    r"now i (understand|see|realize|get it)\b"
    r"|i (now|finally) (understand|see|realize)\b"
    r"|i(.?ve| have)? figured (it |this )?out|i figured out\b"
    r"|(?<!not )(?<!n't )\bfound it\b"
    r"|\bfound (the|a|its) (bug|cause|culprit|problem|issue|leak|regression|reason|root cause)\b"
    r"|\bfound out (that|why|how|where)\b|\bthe culprit (is|was)\b"
    r"|the (real|actual) (topolog|architect|structure|setup|layout|wiring|flow|picture|story|design)"
    r"|it turns out\b|turns out (that|the)\b"
    r"|(that|this) explains (the|why|how|what)\b"
    r"|the (key|real|actual) (insight|issue|problem|cause|reason)\b|root cause is\b"
    r"|(actually|really) (runs|lives|sits|resides|is hosted|happens|is served) on\b"
    r"|clear(er)? picture|the (full|whole|complete|bigger) picture"
    r"|\b(now|it all|everything|it)('?s| is| are)? (clear|much clearer)\b"
    r"|\bmakes sense now\b|\bnow [^.\n]{0,20}makes sense\b"
    r"|jetzt (verstehe ich|wird klar|ergibt)|jetzt ist (alles |es )?klar|klares bild"
    r"|stellt sich heraus|herausgefunden"
    r"|\b(fehler|ursache|problem|grund|bug) gefunden\b|\bda (ist|war) (es|der fehler|das problem)\b",
    re.IGNORECASE,
)

# ENDORSEMENT of a good idea, from EITHER side (assistant judging the user's suggestion
# good -> adopt it; or the user endorsing the assistant's proposal -> confirmed approach).
ENDORSE_PATTERN = re.compile(
    r"(good|great|nice|smart|clever|brilliant|excellent) (idea|call|point|catch|thinking|suggestion)"
    r"|i like (that|this|your) (idea|approach|plan|suggestion)|let.?s do (that|it)"
    r"|gute idee|guter (punkt|einfall)|gut(er)? gedacht",
    re.IGNORECASE,
)

# ---- BROAD recall patterns (audit-only: catch likely MISSES the strict set skips) ----
# Deliberately wider and learning-flavoured. A turn that matches BROAD but not STRICT is a
# CANDIDATE MISS for review, never a live block. Tuned to stay off bare acknowledgements.

BROAD_USER_PATTERN = re.compile(
    r"\b(wrong|incorrect|broken|fails?|failing|not working|doesn.?t work|didn.?t work)\b"
    r"|\bwhy (did|are|is|do|does) (you|it|that|this)\b"
    r"|\byou (always|keep|still|again|never)\b"
    r"|\bi (told|asked) you\b|\bas i (said|mentioned|asked)\b"
    r"|\bnot (quite|what i|right|correct)\b|\b(revert|undo|rollback)\b"
    r"|\b(perfect|exactly right|spot on|love it|that.?s it|works now)\b",
    re.IGNORECASE,
)

BROAD_ASST_PATTERN = re.compile(
    r"\bi (missed|overlooked|forgot|misread|misunderstood|didn.?t (realize|notice|account))\b"
    r"|you(?:'?re| are| were) (?:right|correct)|\bmisdiagnos\w+|\bwas (?:an? )?(?:misread|mistake)\b"
    r"|\bi should (have|.?ve) \w+|\bon reflection\b|\blet me reconsider\b"
    r"|\bgood (point|catch)\b"
    r"|\bthe (issue|problem|bug|root cause|reason) (is|was|turned out|ended up)\b"
    r"|\b(in hindsight|as it turns out)\b"
    r"|\bi see (why|how|what|now|the)\b"
    r"|\bfound (it|the|out)\b|\bthe culprit\b|\bgefunden\b"
    r"|\blet me (stop|inspect|double.?check|re.?check|look (again|closer)|take a closer look)\b"
    r"|\bper the .{1,80}? rule\b|\bthe \".{1,80}?\" rule\b|\bfollowing the .{1,60}? (rule|convention)\b"
    r"|\b(ah|oh|oops|whoops)[, ]|\bwait[, ]",
    re.IGNORECASE,
)


def strict_user_hit(text):
    """A strict learning signal in a USER message (correction/remember/endorsement)."""
    return bool(USER_PATTERN.search(text) or ENDORSE_PATTERN.search(text))


def strict_asst_hit(text):
    """A strict learning signal in an ASSISTANT message (admission/realization/endorsement)."""
    return bool(ASST_PATTERN.search(text) or REALIZATION_PATTERN.search(text)
                or ENDORSE_PATTERN.search(text))


def broad_matches(role, text):
    """Lower-cased, de-duplicated broad-recall matches for a message; [] if none.

    role is "user" or "assistant"; selects the matching broad pattern.
    """
    rx = BROAD_USER_PATTERN if role == "user" else BROAD_ASST_PATTERN
    return sorted({m.group(0).strip().lower() for m in rx.finditer(text or "")})
