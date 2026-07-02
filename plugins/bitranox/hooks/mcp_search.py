"""Optional memory-MCP (basic-memory) SEARCH integration for cross-project recall.

`basic-memory` ships a CLI (`basic-memory tool search-notes`) that queries its index READ-ONLY. When
present, enabled (`mcp_search: auto`), and it returns usable hits, recall/gather can use them to
sharpen cross-project results; otherwise they fall back to the built-in keyword scan. Never a hard
dependency - every path degrades to keyword (self-healing).

SAFETY: this module only READS (search-notes). basic-memory's file-writing SYNC is a SEPARATE,
user-driven step (`basic-memory project add <name> <path>` over the workspace) - nothing here triggers
it. If you point basic-memory at your live curated files, ensure ITS sync settings do not rewrite them
(verify against the installed basic-memory version; config keys drift between versions - do not assume
`ensure_frontmatter_on_sync`/`disable_permalinks`/`format_on_save` still exist).

Pure standard library; ASCII output.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import self_improve_signals as sig

_CLI = "basic-memory"


def available():
    """True if the basic-memory CLI is on PATH."""
    return shutil.which(_CLI) is not None


def enabled():
    """True if the `mcp_search` knob is `auto` AND the CLI is available. `off` -> keyword scan only."""
    return sig.load_config().get("mcp_search", "auto") == "auto" and available()


def _config():
    try:
        return json.loads((Path.home() / ".basic-memory" / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def watched_roots():
    """Filesystem paths basic-memory has a project for (so it would index files under them)."""
    projects = (_config().get("projects") or {})
    out = []
    for v in projects.values():
        if isinstance(v, dict) and v.get("path"):
            out.append(str(v["path"]))
    return out


def covers(path):
    """True if some basic-memory project path is an ANCESTOR of `path` (so search would index it).
    Used to decide whether the MCP index actually spans the curated tree we care about."""
    try:
        target = str(Path(path).resolve())
    except OSError:
        return False
    for root in watched_roots():
        try:
            r = str(Path(root).resolve())
            if os.path.commonpath([target, r]) == r:
                return True
        except (OSError, ValueError):
            continue
    return False


def search(query, limit=10, timeout=20):
    """Read-only cross-project search via `basic-memory tool search-notes`. Returns a ranked list of
    result identifiers (permalinks/paths/titles), or None on any failure/empty output/error (the caller
    then falls back to the keyword scan). Never raises; never writes."""
    if not query or not available():
        return None
    q = query if isinstance(query, str) else " ".join(str(k) for k in query if k)
    if not q.strip():
        return None
    try:
        r = subprocess.run([_CLI, "tool", "search-notes", q, "--page-size", str(int(limit))],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    out = (r.stdout or "").strip()
    low = out.lower()
    if not out or low.startswith("error") or "no projects" in low or "project not found" in low:
        return None
    try:                                     # some builds emit JSON
        data = json.loads(out)
        if isinstance(data, dict):
            data = data.get("results") or data.get("items") or data.get("notes") or []
        hits = [str(x.get("permalink") or x.get("file_path") or x.get("path") or x.get("title"))
                for x in data if isinstance(x, dict)]
        hits = [h for h in hits if h and h != "None"]
        return hits or None
    except (ValueError, TypeError):
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return lines or None
