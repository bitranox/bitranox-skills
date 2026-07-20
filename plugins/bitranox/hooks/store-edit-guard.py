#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit) guard: the memory store is written ONLY by the engine.

Two protected surfaces:
  1. ANY path inside a store dir - the live `.claude-memory/` (slug-named bodies + .archive) or the
     legacy `.claude-bx-selflearning/` (kept for downstream installs mid-transition).
  2. The managed POINTER BLOCK inside any `CLAUDE.local.md` (both fence generations). The rest of a
     `CLAUDE.local.md` is the user's own text and stays freely editable - the guard denies only an
     edit that touches the fenced region, a write that changes/deletes it, or an edit/write that
     injects fence markers by hand.

The write path is `memory_engine.py` (via `run-python.sh`): add / heal / set-scope / move. It
upserts by slug, enforces tree-unique slugs, renders the block canonically (recipe + pinned-first),
takes a lock, and is mtime-neutral. A hand-write bypasses all of that AND makes the PostToolUse
hooks churn the file every turn. The standing "engine, never a hand-write" rule is advisory prose
that loses under momentum; this is the deterministic backstop. Denies apply to Task subagents too
(PreToolUse fires on their tool calls - probe-verified), which is the dream-safety guarantee.

Decision: BLOCK (exit 2; stderr reason feeds back to the MODEL, the user is not prompted) - UNLESS
the env `BITRANOX_MEMORY_ENGINE` is set (a deliberate store-maintenance session opts out; the
engine itself writes via Python `open()`, never Claude's tools, so it is never caught regardless.
A shell `export` in a Bash call does NOT reach this hook - set the env at session launch).

Fail-open: any parse/IO error -> allow (a broken guard must never wedge a turn). Pure standard
library; launched via run-python.sh so it works on Windows too.
"""
import json
import os
import re
import sys
from pathlib import Path

try:
    import uuid_store as _us
    _FENCES = ((_us.INDEX_BEGIN, _us.INDEX_END),
               (_us.LEGACY_INDEX_BEGIN, _us.LEGACY_INDEX_END))
except Exception:  # noqa: BLE001 - keep guarding even if the sibling module cannot load
    _FENCES = (
        ("<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->",
         "<!-- BITRANOX-MEMORY-INDEX:END -->"),
        ("<!-- BITRANOX-UUID-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->",
         "<!-- BITRANOX-UUID-INDEX:END -->"),
    )
# marker STEMS: an injected fence is denied even if hand-typed with different trailing prose
_MARKER_STEMS = ("BITRANOX-MEMORY-INDEX:", "BITRANOX-UUID-INDEX:")

# any path segment `.claude-memory/` (live store) or `.claude-bx-selflearning/` (legacy store)
_STORE = re.compile(r"(?:^|/)(?:\.claude-memory|\.claude-bx-selflearning)/")
_TOOLS = {"Edit", "Write", "MultiEdit"}
_BYPASS_ENV = "BITRANOX_MEMORY_ENGINE"

_DENY = (
    "The memory store is written ONLY by the engine (hooks/memory_engine.py via run-python.sh): "
    "capture with `add --proj <dir> --title ... --hook ... --body-file ...`, repair with `heal`, "
    "re-level with `move`, rename a wrong slug with `rename`, set a descriptor with `set-scope`. "
    "Hand-editing %s bypasses the lock, "
    "the canonical render, and tree-unique slug enforcement, and makes the PostToolUse hooks churn "
    "the file. For a deliberate hand-repair session, relaunch with %s=1 set at session start "
    "(a Bash `export` does not reach this hook). File: %s"
)


def _block_spans(text):
    """[(start, end)] of every managed pointer-block region in `text` (both fence generations).
    A BEGIN without its END spans to the end of text (malformed blocks stay protected)."""
    spans = []
    for begin, end in _FENCES:
        pos = 0
        while True:
            b = text.find(begin, pos)
            if b < 0:
                break
            e = text.find(end, b)
            e = len(text) if e < 0 else e + len(end)
            spans.append((b, e))
            pos = e
    return spans


def _block_region(text):
    """The concatenated managed-block bytes of `text` (order-stable) - the invariant a Write must
    preserve."""
    return "\n".join(text[b:e] for b, e in sorted(_block_spans(text)))


def _injects_marker(s):
    return any(stem in (s or "") for stem in _MARKER_STEMS)


def _overlaps_block(current, needle, spans):
    """True when any occurrence of `needle` in `current` intersects a managed-block span."""
    if not needle:
        return False
    pos = 0
    while True:
        i = current.find(needle, pos)
        if i < 0:
            return False
        j = i + len(needle)
        if any(b < j and i < e for b, e in spans):
            return True
        pos = i + 1


def _read(path):
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def decide(event, env):
    """Pure: (event, env) -> a deny-reason string, or None to allow silently. Never raises to the
    caller (main wraps it); internal file reads fail-open to ''."""
    if (event.get("tool_name") or "") not in _TOOLS:
        return None
    tool_input = event.get("tool_input") or {}
    raw = (tool_input.get("file_path") or "").replace("\\", "/")
    if not raw:
        return None
    if env.get(_BYPASS_ENV):
        return None                                    # deliberately-declared maintenance session

    if _STORE.search(raw):
        return _DENY % ("a store file", _BYPASS_ENV, raw)

    path = Path(raw)
    if not path.is_absolute():
        path = Path(event.get("cwd") or ".") / path
    if path.name != "CLAUDE.local.md":
        return None

    current = _read(path)
    tool = event["tool_name"]
    deny = _DENY % ("the managed pointer block in CLAUDE.local.md", _BYPASS_ENV, raw)

    if tool == "Write":
        new = tool_input.get("content") or ""
        if _block_region(new) != _block_region(current):
            return deny                                # block added, altered, or deleted by hand
        return None

    spans = _block_spans(current)
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    for e in edits or []:
        old_s = e.get("old_string") or ""
        new_s = e.get("new_string") or ""
        if _injects_marker(new_s) and not _injects_marker(old_s):
            return deny                                # hand-injecting a fence marker
        if _overlaps_block(current, old_s, spans):
            return deny                                # the edit target sits inside the block
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    try:
        reason = decide(event, os.environ)
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        return 0
    if reason is not None:
        sys.stderr.write("STORE-EDIT GUARD: " + reason + "\n")
        return 2  # PreToolUse: non-zero blocks the tool call and feeds stderr back to the model
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
