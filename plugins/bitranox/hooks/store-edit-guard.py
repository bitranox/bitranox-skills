#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit) guard: the curated memory store is written ONLY by the engine.

Hand-editing anything inside a `.claude-bx-selflearning/` store - the `index.md` index or a
`facts/<slug>.md` body - is the exact miss this guard prevents. The write path is `memory_engine.py`
(via `run-python.sh`): it upserts by slug, decides inline-vs-`facts/` by size, maintains the `@import`
block + the `index.md` scope block, takes a lock, and is mtime-neutral. A hand-write bypasses all of
that AND makes the PostToolUse hooks churn the file every turn. The standing "use the engine, never a
hand-write" rule is advisory prose that loses under momentum, so this is the deterministic backstop.

Decision on an `Edit`/`Write`/`MultiEdit` whose target is inside a `.claude-bx-selflearning/` store:
  - BLOCK (exit 2): the tool call is denied and the reason is fed back to the MODEL, which then
    redirects itself to the engine. The user is NOT prompted (enforced, not asked).
  - UNLESS the env `BITRANOX_MEMORY_ENGINE` is set: a deliberate store-maintenance session opts out.
    NOTE: the engine itself writes via Python `open()`, NOT Claude's Edit/Write tools, so it is never
    caught by this hook regardless - the env is only for a human-directed hand-repair session. A shell
    `export` in a Bash tool call does NOT reach this hook (separate process); set it at session start.

Fail-open: any parse/IO error -> exit 0 (a broken guard must never wedge a turn). Pure standard
library; launched via run-python.sh so it works on Windows too.
"""
import json
import os
import re
import sys

# any path segment `.claude-bx-selflearning/` - the curated store dir (index.md + facts/<slug>.md)
_STORE = re.compile(r"(?:^|/)\.claude-bx-selflearning/")
_TOOLS = {"Edit", "Write", "MultiEdit"}
_BYPASS_ENV = "BITRANOX_MEMORY_ENGINE"


def decide(event, env):
    """Pure: (event, env) -> a block-reason string (deny the tool call), or None to allow silently."""
    if (event.get("tool_name") or "") not in _TOOLS:
        return None
    path = ((event.get("tool_input") or {}).get("file_path") or "").replace("\\", "/")
    if not _STORE.search(path):
        return None
    if env.get(_BYPASS_ENV):
        return None                                    # deliberately-declared store-maintenance session
    return (
        "Editing the curated memory store by hand is blocked. The store "
        "(.claude-bx-selflearning/: index.md + facts/) is written ONLY by hooks/memory_engine.py "
        "(via run-python.sh) - it upserts by slug, sizes inline-vs-facts/, maintains the @import + "
        "scope blocks, locks, and stays mtime-neutral; a hand-write bypasses that and makes the "
        "PostToolUse hooks churn the file. Capture with `memory_engine.py add ...` (or `heal` / "
        "`set-scope`). For a deliberate hand-repair session, relaunch with %s=1 set in the environment "
        "(a shell `export` in a Bash tool call does NOT reach this hook - set it at session start). "
        "File: %s" % (_BYPASS_ENV, path))


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    reason = decide(event, os.environ)
    if reason is not None:
        sys.stderr.write("STORE-EDIT GUARD: " + reason + "\n")
        return 2  # PreToolUse: non-zero blocks the tool call and feeds stderr back to the model
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
