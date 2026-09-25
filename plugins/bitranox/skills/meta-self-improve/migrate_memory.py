#!/usr/bin/env python3
"""Migrate native Auto-memory stores into the curated slug store (pointer blocks + central bodies).

For each `~/.claude/projects/<slug>/memory/` store: resolve the slug back to its project directory,
curate its `MEMORY.md` + topic files into that project's curated store via the write engine, back up
out-of-tree first, and write a receipt so a re-run is idempotent and a crash resumes. Never deletes
the native store (it stays as the raw tier); never auto-commits any repo.

The slug encoding maps BOTH `/` and `.` to `-` (verified: `.../skills/.claude/worktrees` ->
`...-skills--claude-worktrees`), so reversing a slug is ambiguous. `resolve_slug` walks the filesystem,
trying each `-` as `/` (descend), `.`, or literal `-`, and keeps only candidates that EXIST. A unique
existing candidate resolves; ambiguous/none is PARKED and reported - never guessed.

Usage:
    migrate_memory.py --dry-run [--slug <s> ...]   # report the full touch-list, write nothing
    migrate_memory.py --apply   [--slug <s> ...]   # back up + migrate (idempotent via receipts)

Exit codes: 0 every entry placed (or would be); 1 something was not (a parked store, an entry the
engine refused, an unreadable topic file, a failed backup or write); 2 usage error (--dry-run with
--apply, a malformed --redirect or one naming a missing dir, a --slug with no native store).

Pure standard library; ASCII output.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import self_improve_signals as sig       # noqa: E402
import memory_engine as ME               # noqa: E402
import reconcile_memory_index as R       # noqa: E402

def _projects_dir():
    return Path.home() / ".claude" / "projects"


def _backups_dir():
    return Path.home() / ".claude" / "self-improve-audit" / "backups"


def _parked_dir():
    return Path.home() / ".claude" / "self-improve-audit" / "migration-unresolved"


# ---- slug -> path resolution (filesystem-guided; `/` and `.` both encode to `-`) ---------------

def _children(d):
    try:
        return set(os.listdir(d))
    except OSError:
        return set()


# Claude Code encodes a project path into its ~/.claude/projects directory name with
#     h1r(e) = e.replace(/[^a-zA-Z0-9]/g, "-")
#     qY(e)  = h1r(e).length <= 200 ? h1r(e) : h1r(e).slice(0, 200) + "-" + hash(e)
# (transcribed from the CLI binary, 2.1.240). EVERY non-alphanumeric collapses to "-", not just
# "/", "." and "_" as this decoder used to assume - so a component holding a space, "+" or "@"
# was undecodable. A Windows path needs no special case beyond its root: ":" and both slashes
# are non-alphanumeric, so C:\Users\bob and C:/Users/bob both encode to "C--Users-bob".
SLUG_MAX = 200
_DRIVE_SLUG_RX = re.compile(r"^([A-Za-z])--(.*)$")


def slug_root_and_tokens(slug):
    """Split a project slug into the filesystem root it starts from and its "-" separated tokens.

    Returns (None, []) for a slug that encodes neither an absolute POSIX path nor a drive path.
    """
    drive = _DRIVE_SLUG_RX.match(slug)
    if drive:
        return drive.group(1).upper() + ":\\", [t for t in drive.group(2).split("-")]
    if slug.startswith("-"):
        return "/", slug[1:].split("-")
    return None, []


def is_truncated_slug(slug):
    """True if the slug hit the 200-character cap, so its tail is a hash and cannot be decoded."""
    return len(slug) > SLUG_MAX


def resolve_slug(slug, max_candidates=8):
    """Every existing directory a `<slug>` could decode to.

    DFS with filesystem pruning: a "/" only descends into a real child, and a continuation only
    survives if a child STARTS with the partial component. The separators tried at each step are
    read off the real children rather than guessed, which is what makes any non-alphanumeric
    character decodable. Returns a de-duplicated list of absolute dir paths (realpath), capped.
    """
    if is_truncated_slug(slug):
        # The tail is a hash, so the walk cannot succeed - measured: the pre-change DFS also
        # returned [] here, because the hash tokens match no real child. Refusing up front
        # states the limitation instead of rediscovering it by failing.
        return []
    base_root, tokens = slug_root_and_tokens(slug)
    if base_root is None or not tokens:
        return []
    out = []

    def dfs(idx, base, comp):
        # `comp` is a partial name of a child of `base`; `tokens[idx]` is the next token to attach.
        if len(out) >= max_candidates:
            return
        if idx == len(tokens):
            full = os.path.join(base, comp)
            if os.path.isdir(full):
                out.append(str(Path(full).resolve()))
            return
        kids = _children(base)
        tok = tokens[idx]
        # option "/": `comp` is a complete child -> descend, start a new component with `tok`
        if comp in kids and os.path.isdir(os.path.join(base, comp)):
            dfs(idx + 1, os.path.join(base, comp), tok)
        # extend the component: the encoder turned SOME non-alphanumeric into this "-", so read the
        # real candidates off the children instead of guessing a fixed set. Only a separator that
        # actually occurs at this position in a real child is tried, which keeps the fan-out small
        # while making a space, "+", "@" or any other punctuation decodable.
        seps = {k[len(comp)] for k in kids
                if len(k) > len(comp) and k.startswith(comp) and not k[len(comp)].isalnum()}
        for sep in sorted(seps):
            new_comp = comp + sep + tok
            if any(k.startswith(new_comp) for k in kids):
                dfs(idx + 1, base, new_comp)

    dfs(1, base_root, tokens[0])
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def resolve_one(slug):
    """A single resolved project dir for `slug`, or None if ambiguous/unresolved. Disambiguate ties by
    preferring a candidate that looks like a project root (`.git` or `CLAUDE.md` present)."""
    cands = resolve_slug(slug)
    if len(cands) == 1:
        return cands[0]
    if not cands:
        return None
    marked = [c for c in cands if (Path(c) / ".git").exists() or (Path(c) / "CLAUDE.md").is_file()]
    return marked[0] if len(marked) == 1 else None


# roots that resolve but are NOT real projects to seed a curated store into (transient / the home dir)
# The literal "/tmp" is not enough. On macOS /tmp is a symlink to /private/tmp, so a resolved
# path never starts with it and the transient root went entirely unexcluded there; on Windows the
# temp root is not /tmp at all. Resolve the candidates so the comparison is against what
# Path.resolve() actually returns on this platform.
def _exclude_roots():
    roots = set()
    for candidate in ("/tmp", tempfile.gettempdir()):
        try:
            roots.add(str(Path(candidate).resolve()))
        except OSError:
            continue
    return tuple(sorted(roots))


_EXCLUDE_PREFIXES = _exclude_roots()


def is_excluded(path):
    """True for a resolved path we should NOT create a curated store in: `$HOME` itself, or anything
    under a transient root (`/tmp`). Such native stores are skipped (not migrated, not parked)."""
    if not path:
        return False
    try:
        p = str(Path(path).resolve())
    except OSError:
        return False
    if p == str(Path.home().resolve()):
        return True
    return any(p == pref or p.startswith(pref + os.sep) or p.startswith(pref + "/")
               for pref in _EXCLUDE_PREFIXES)


# ---- reading a native store --------------------------------------------------------------------

_TYPES = ("feedback", "project", "reference", "user")


def _native_type(meta, raw, stem):
    """The fact's kind: a declared `type:` or nested `metadata:\\n  type:` first, then the name's
    prefix, then an inline `metadata:` value naming one. The nested form is what most native topic
    files carry, and parse_frontmatter drops indented keys, so reading only `meta` stored those
    facts untyped (as project)."""
    declared = str(meta.get("type") or "") or ME._body_type(raw)  # noqa: SLF001 - engine's reader
    if declared in _TYPES:
        return declared
    name = str(meta.get("name") or stem)
    for t in _TYPES:
        if name.startswith(t) or str(meta.get("metadata") or "").find(t) >= 0:
            return t
    return None


def read_native_entries(memdir, unreadable=None):
    """[{name, title, hook, body, source, type}] for each native topic `*.md` (not MEMORY.md).

    A topic file that cannot be read or decoded is skipped, and named in `unreadable` when that is
    a list: skipped in silence it read as migrated, while its fact was never placed anywhere."""
    out = []
    memdir = Path(memdir)
    try:
        topics = sorted(p for p in memdir.glob("*.md") if p.name != "MEMORY.md")
    except OSError:
        topics = []
    for p in topics:
        try:
            raw = p.read_text(encoding="utf-8-sig")        # -sig: a BOM hid the frontmatter
        except (OSError, UnicodeDecodeError) as exc:
            if unreadable is not None:
                unreadable.append("%s (%s)" % (p, exc))
            continue
        meta, body = R.parse_frontmatter(raw)
        title = R.derive_title(meta, body, p.name)
        hook = R.derive_hook(meta, body)
        src = meta.get("name") or p.stem
        out.append({"name": p.stem, "title": title, "hook": hook, "body": body.strip(),
                    "source": src, "type": _native_type(meta, raw, p.stem)})
    return out


def _placement_slug(anchor, entry):
    """The slug `entry` is placed under: its native NAME slugified, never its derived title.

    Titles collide - two topic files both opening with "# Notes" derived the same slug, and the
    second add silently UPDATED the first, losing its body. The native name is unique per store.
    A slug already holding a different body is suffixed rather than overwritten; one already
    holding this entry's body is the same fact (a resumed run) and is reused."""
    slug = ME.slugify(entry["name"], entry["type"])
    try:
        stored = ME.us.body_path(anchor, slug).read_text(encoding="utf-8")
    except FileNotFoundError:
        return slug
    if entry["body"] and entry["body"] in stored:
        return slug
    return ME._free_slug(anchor, slug)  # noqa: SLF001 - the engine's own collision suggestion


# ---- receipts (idempotency + resume) -----------------------------------------------------------

def _receipt_path(proj):
    import re as _re
    stem = _re.sub(r"[^A-Za-z0-9]+", "-", str(proj)).strip("-")
    return sig.curated_state_dir(proj) / "migration-receipts" / (stem + ".json")


def _legacy_receipt_path(proj):
    # pre-5.35 location, read-only fallback so old runs stay idempotent
    return sig.claude_memory_dir(proj) / "state" / "migration-receipt.json"


def _load_receipt(proj):
    try:
        try:
            return json.loads(_receipt_path(proj).read_text(encoding="utf-8"))
        except OSError:
            return json.loads(_legacy_receipt_path(proj).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"placed": [], "sources": [], "slugs": []}


def _save_receipt(proj, rec):
    p = _receipt_path(proj)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


# ---- gitignore safety (R11): keep the curated store out of git unless the user opts to track it ---

def _git(proj, *args):
    try:
        r = subprocess.run(["git", "-C", str(proj), *args], capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def ensure_gitignore(proj):
    """Ensure the memory wiring - the LIVE store (`.claude-memory/`), the legacy store dir, and
    `CLAUDE.local.md` - is gitignored in the repo owning `proj`. Honors `track_private` (if set,
    the user WANTS it tracked -> do nothing). Checks: non-git dir -> skip; already ignored ->
    no-op; a store already TRACKED -> WARN (a possible existing leak) and do NOT append; else
    append the ignore lines to the repo-root `.gitignore`. Returns a status string. Fail-open."""
    if sig.load_config().get("track_private"):
        return "track_private: left tracked"
    rc, top = _git(proj, "rev-parse", "--show-toplevel")
    if rc != 0 or not top:
        return "not a git repo: skipped"
    root = Path(top)
    for store in (sig.MEMORY_DIRNAME, sig.CURATED_DIRNAME):
        if _git(proj, "ls-files", "--error-unmatch", store + "/")[0] == 0:
            return "WARNING: %s is TRACKED (possible existing leak) - not modifying .gitignore" % store
    gi = root / ".gitignore"
    try:
        cur = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        have = set(cur.splitlines())
        wanted = [sig.MEMORY_DIRNAME + "/", sig.CURATED_DIRNAME + "/", "CLAUDE.local.md"]
        add = [w for w in wanted if w not in have and w.rstrip("/") not in have]
        if not add:
            return "already ignored"
        gi.write_text((cur.rstrip("\n") + "\n" if cur.strip() else "")
                      + "# bitranox curated self-learning memory (local wiring; engine-written)\n"
                      + "\n".join(add) + "\n", encoding="utf-8")
        return "gitignored"
    except OSError:
        return "gitignore write failed"


# ---- migrate one store -------------------------------------------------------------------------

def migrate_store(slug, dry_run=True, scope_default="", redirect=None):
    """Migrate one native store. Returns a report dict. On apply: backs up out-of-tree, curates each
    native entry into the resolved (or `redirect`-forced) project's curated store via the engine,
    records a receipt. Idempotent (receipt-skipped). Unresolved -> parked; an excluded target
    (`/tmp`, `$HOME`) -> skipped, not migrated. `redirect` forces the target for a renamed/moved slug."""
    memdir = _projects_dir() / slug / "memory"
    unreadable = []
    entries = read_native_entries(memdir, unreadable=unreadable)
    proj = redirect or resolve_one(slug)
    rep = {"slug": slug, "resolved": proj, "in": len(entries), "placed": 0, "skipped": 0,
           "parked": False, "excluded": False, "redirected": bool(redirect), "dry_run": dry_run,
           "failed": [], "unreadable": unreadable, "error": None}
    if proj and is_excluded(proj):
        rep["excluded"] = True
        return rep
    if proj is None:
        rep["parked"] = True
        if not dry_run and entries:
            try:
                dst = _parked_dir() / slug
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copytree(memdir, dst / "memory", dirs_exist_ok=True)
            except OSError:
                pass
        return rep
    if dry_run:
        rec = _load_receipt(proj)
        done = set(rec.get("sources", []))
        rep["placed"] = sum(1 for e in entries if e["source"] not in done)
        rep["skipped"] = len(entries) - rep["placed"]
        return rep

    # apply: back up both the native store and any existing curated store, out of tree. A backup
    # that fails ABORTS the store: migrating anyway wrote with no way back while reporting success.
    try:
        _backup(proj, memdir)
    except OSError as exc:
        rep["error"] = "backup failed, nothing written: %s" % exc
        return rep

    rec = _load_receipt(proj)
    done = set(rec.get("sources", []))
    rec["slugs"] = sorted(set(rec.get("slugs", []) + [slug]))
    anchor = ME._anchor(proj)  # noqa: SLF001 - the engine's anchor resolution
    for e in entries:
        if e["source"] in done:
            rep["skipped"] += 1
            continue
        try:
            # allow_over_cap_hook: migration carries pre-pivot text verbatim; a refusal here would
            # strand a legacy fact in a store that is being retired.
            ME.add_or_update_entry(proj, title=e["title"], hook=e["hook"], body=e["body"],
                                   type_=e["type"], scope_default=scope_default,
                                   slug=_placement_slug(anchor, e), allow_over_cap_hook=True)
        except ValueError as exc:
            # one entry the engine refuses (an empty body, a slug another level owns) used to
            # abort the whole run before the receipt, so every re-run died on it again
            rep["failed"].append("%s: %s" % (e["name"], exc))
            continue
        except OSError as exc:
            rep["error"] = "write failed at %s: %s" % (e["name"], exc)
            break
        done.add(e["source"])
        rep["placed"] += 1
        rec["sources"] = sorted(done)
        _save_receipt(proj, rec)                   # per entry, so a crash resumes exactly
    rec["sources"] = sorted(done)
    _save_receipt(proj, rec)
    rep["gitignore"] = ensure_gitignore(proj)   # keep the curated store out of git (R11)
    return rep


def _backup(proj, memdir):
    """Copy the native store and any legacy curated dir out of tree. Raises OSError on failure."""
    key = sig.proj_key(proj)
    stamp = _backups_dir() / ("%s-%d" % (key, int(time.time())))
    stamp.mkdir(parents=True, exist_ok=True)
    shutil.copytree(memdir, stamp / "native", dirs_exist_ok=True)
    cur = sig.claude_memory_dir(proj)
    if cur.exists():
        shutil.copytree(cur, stamp / "curated", dirs_exist_ok=True)


def enumerate_slugs():
    try:
        return sorted(p.name for p in _projects_dir().glob("*") if (p / "memory").is_dir())
    except OSError:
        return []


def _parse_redirects(items):
    """Parse `--redirect SLUG=TARGET` items into {slug: target_path}.

    Raises ValueError for an item without `=`, with an empty side, or whose TARGET is not an
    existing directory. A malformed item used to be dropped in silence (the slug then parked) and
    a missing target was created by the first write, planting a store in a directory nobody
    meant to exist."""
    out = {}
    for it in (items or []):
        slug, sep, target = it.partition("=")
        slug, target = slug.strip(), target.strip()
        if not sep or not slug or not target:
            raise ValueError("--redirect expects <slug>=<target-dir>, got %r" % it)
        if not Path(target).is_dir():
            raise ValueError("--redirect target is not an existing directory: %s" % target)
        out[slug] = target
    return out


def _parser():
    ap = argparse.ArgumentParser(description="Migrate native memory stores into the curated model.")
    mode = ap.add_mutually_exclusive_group()   # both at once used to WRITE
    mode.add_argument("--apply", action="store_true", help="write (default is dry-run/report-only)")
    mode.add_argument("--dry-run", action="store_true", help="report only; write nothing (default)")
    ap.add_argument("--slug", action="append", default=None,
                    help="limit to specific slug(s); slugs start with '-', so use the =form: --slug=-media-...")
    ap.add_argument("--redirect", action="append", default=None,
                    help="force a renamed/moved slug into a target dir: --redirect=<slug>=<target-path>")
    return ap


def _usage_problems(args):
    """(redirects, [problem]) - the argument errors that must stop the run before it starts."""
    problems = []
    try:
        redirects = _parse_redirects(args.redirect)
    except ValueError as exc:
        redirects = {}
        problems.append(str(exc))
    for slug in args.slug or []:
        if not (_projects_dir() / slug / "memory").is_dir():
            problems.append("no native store for slug %s (looked in %s)"
                            % (slug, _projects_dir() / slug / "memory"))
    return redirects, problems


def _report_store_problems(rep):
    """Print what one store did NOT migrate; True when there was anything."""
    for why in rep["failed"]:
        print("  ! NOT placed (%s): %s" % (rep["slug"], why))
    for why in rep["unreadable"]:
        print("  ! UNREADABLE topic file (%s): %s" % (rep["slug"], why))
    if rep["error"]:
        print("  ! FAILED (%s): %s" % (rep["slug"], rep["error"]))
    return bool(rep["failed"] or rep["unreadable"] or rep["error"])


def main(argv=None):
    """Exit codes: 0 every entry placed (or would be); 1 something was not - a parked store, an
    entry the engine refused, an unreadable topic file, a failed backup or write; 2 usage error."""
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    dry = not args.apply
    redirects, problems = _usage_problems(args)
    if problems:
        for problem in problems:
            print("migrate_memory: %s" % problem, file=sys.stderr)
        return 2

    slugs = args.slug if args.slug else enumerate_slugs()
    total_in = total_placed = total_parked = total_excluded = total_failed = 0
    parked = []
    incomplete = False
    print("%s %d store(s)%s" % ("DRY-RUN over" if dry else "MIGRATING", len(slugs),
                                "" if dry else " (writing)"))
    for slug in slugs:
        rep = migrate_store(slug, dry_run=dry, redirect=redirects.get(slug))
        total_in += rep["in"]
        total_placed += rep["placed"]
        if rep["excluded"]:
            total_excluded += rep["in"]
            if rep["in"]:
                print("  - excluded (transient/home): %s -> %s (%d entries skipped)"
                      % (slug, rep["resolved"], rep["in"]))
        elif rep["parked"]:
            total_parked += rep["in"]
            parked.append(slug)
            print("  ! PARKED (unresolved): %s (%d entries)" % (slug, rep["in"]))
        elif rep["in"] or rep["redirected"]:            # suppress 0-entry no-op noise
            print("  %s%s -> %s : in=%d %s=%d skip=%d"
                  % ("[redirect] " if rep["redirected"] else "", slug, rep["resolved"], rep["in"],
                     "would-place" if dry else "placed", rep["placed"], rep["skipped"]))
        incomplete |= _report_store_problems(rep)
        total_failed += len(rep["failed"])
    print("TOTAL in=%d %s=%d parked=%d excluded=%d failed=%d "
          "(in == placed+skipped+parked+excluded+failed)"
          % (total_in, "would-place" if dry else "placed", total_placed, total_parked,
             total_excluded, total_failed))
    if parked:
        print("PARKED slugs (redirect with --redirect=<slug>=<path>, or resolve manually): %s"
              % ", ".join(parked))
    return 1 if (parked or incomplete) else 0


def _reconfigure_stdout():
    """A cp1252 console (bare `python3` on Windows) crashed on a slug or path it could not
    encode. Escape instead; guarded, since a replaced stream may not support reconfigure."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass


if __name__ == "__main__":
    _reconfigure_stdout()
    sys.exit(main())
