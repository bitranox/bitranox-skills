#!/usr/bin/env python3
"""PreToolUse(Write) nudge: you are authoring the Nth NEAR-DUPLICATE script this session.

Why this exists, next to toolbox-nudge.py: that hook matches a fixed catalogue of signatures for
chores a jig ALREADY exists for, so it answers "do we have a tool for this?". It cannot fire for a
chore with no jig yet - there is no signature to match - which is exactly when a jig is most worth
building. Measured: six near-identical delete scripts were authored in one session, each fixing a
defect the previous one shipped, and the catalogue hook stayed silent through all six because the
chore was new.

So this hook keys on REPETITION instead of on recognition. Rewriting the same logic a third time
is the evidence that it deserves a tested tool, and it is evidence no per-call category check can
see: it only exists ACROSS calls.

Non-blocking (additionalContext), once per session, silent on any error.
"""
import json
import re
import sys
from pathlib import Path

SCRIPT_SUFFIXES = {".ps1", ".py", ".sh", ".bash", ".psm1"}
VARIANTS_BEFORE_NUDGE = 3        # the third near-duplicate is the one that earns a tool
SIMILARITY = 0.25                # Jaccard over 3-token shingles; unrelated scripts score ~0

_COMMENT = re.compile(r"(^\s*#.*$)|(^\s*//.*$)", re.M)
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]{2,}")


def shingles(text):
    """Set of 3-token shingles from `text`, comments stripped. PURE - unit-testable.

    Shingles rather than a bag of words: two unrelated PowerShell scripts share plenty of single
    tokens (param, foreach, Write-Host) but almost no ordered triples, so this separates
    copy-paste lineage from "same language" instead of firing on every script pair.
    """
    body = _COMMENT.sub("", text or "")
    toks = [t.lower() for t in _TOKEN.findall(body)]
    return {tuple(toks[i:i + 3]) for i in range(len(toks) - 2)}


def similarity(a, b):
    """Jaccard overlap of two shingle sets. PURE."""
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _state_path(session):
    from self_improve_signals import _audit_dir           # noqa: PLC0415 - shared audit dir helper
    return _audit_dir() / (str(session) + ".jig-shingles.json")


def _load(session):
    try:
        return json.loads(_state_path(session).read_text(encoding="utf-8"))
    except Exception:                                     # noqa: BLE001 - absent/corrupt: start fresh
        return {}


def _save(session, data):
    try:
        p = _state_path(session)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
    except Exception:                                     # noqa: BLE001 - state must never break the hook
        pass


def count_kin(store, path, sh):
    """How many OTHER recorded scripts this one resembles, and their paths. PURE.

    Keyed by path so that iterating on ONE file replaces its entry instead of counting as a new
    variant - editing a script is not the same act as writing another one.
    """
    kin = [p for p, s in store.items() if p != path and similarity(sh, set(map(tuple, s))) >= SIMILARITY]
    return kin


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or event.get("tool_name") != "Write":
        return 0
    ti = event.get("tool_input") or {}
    path = str(ti.get("file_path") or "")
    content = ti.get("content") or ""
    if Path(path).suffix.lower() not in SCRIPT_SUFFIXES:
        return 0

    sh = shingles(content)
    if len(sh) < 20:                                      # too small to judge; not worth a tool
        return 0

    session = event.get("session_id") or ""
    if not session:
        return 0
    store = _load(session)
    nudged_key = "__nudged__"
    kin = count_kin({k: v for k, v in store.items() if k != nudged_key}, path, sh)

    store[path] = [list(t) for t in sh]
    already = store.get(nudged_key)
    if len(kin) + 1 >= VARIANTS_BEFORE_NUDGE and not already:
        store[nudged_key] = True
        _save(session, store)
        names = ", ".join(Path(p).name for p in (kin + [path])[:5])
        msg = ("This is variant %d of the same script this session (%s). Rewriting logic a third "
               "time is the signal it should be a TESTED JIG, not another throwaway: each rewrite "
               "so far has carried the previous one's defects forward. Build it as a script with "
               "pytest cases in the owning skill (bitranox:compuse-toolbox for a computer-use "
               "chore), then call that - and if an existing jig is close, ENHANCE it rather than "
               "forking a variant." % (len(kin) + 1, names))
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": msg}}) + "\n")
        return 0
    _save(session, store)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                     # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
