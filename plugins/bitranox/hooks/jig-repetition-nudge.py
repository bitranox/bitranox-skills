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

KNOWN LIMIT, measured, not assumed: this catches COPIES, not REWRITES. Scored against a real
86-script session, near-copies pair well above the threshold (0.58, 0.57, 0.46) but a lineage of
six scripts that solved the same problem by successively different means - Remove-Item, then
robocopy, then a gated strip - peaked at 0.30 and never reached three kin, so this hook would
have stayed silent through exactly the session that motivated it. Two alternative signals were
measured and rejected: rare-token overlap fires on the first cluster of a session and is then
spent, and per-cluster dedup smears transitively until one nudge covers everything. Treat a
silent session as no evidence. Widening this to rewrites needs a design, not another threshold.

Non-blocking (additionalContext), once per session, silent on any error.
"""
import json
import re
import sys
from pathlib import Path

from shell_text import HEREDOC_OPEN               # noqa: E402 - shared with the other command guards

SCRIPT_SUFFIXES = {".ps1", ".py", ".sh", ".bash", ".psm1"}
VARIANTS_BEFORE_NUDGE = 3        # the third near-duplicate is the one that earns a tool
SIMILARITY = 0.25                # Jaccard over 3-token shingles; unrelated scripts score ~0

# `cat > x.ps1 <<'EOS'` / `cat >> x.py <<EOF` - the redirect target on a heredoc opener line.
_REDIRECT = re.compile(r">>?\s*(['\"]?)([^\s'\";|&<>]+)\1")


def heredoc_writes(command):
    """[(path, body)] for every heredoc in `command` that writes a SCRIPT file. PURE.

    A guard is only as wide as its matcher, and a Bash event carries `command`, not a file_path.
    Scripts authored as `cat > f.ps1 <<'EOS' ... EOS` are therefore invisible to a Write-only
    hook - which is how six near-duplicate scripts were authored past this very nudge, since
    heredocs were how nearly all of them were written.
    """
    out = []
    lines = (command or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        opener = HEREDOC_OPEN.search(line)
        i += 1
        if not opener:
            continue
        delimiter = opener.group(2)
        body = []
        while i < len(lines) and lines[i].strip() != delimiter:
            body.append(lines[i])
            i += 1
        i += 1                                        # drop the terminator
        # The redirect target must come from the text BEFORE the `<<`, or `<<'EOS'` itself and any
        # redirect inside the body would be mistaken for the destination.
        head = line[:opener.start()]
        target = _REDIRECT.search(head)
        if not target:
            continue
        path = target.group(2)
        if Path(path).suffix.lower() in SCRIPT_SUFFIXES:
            out.append((path, "\n".join(body)))
    return out

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
    if not isinstance(event, dict):
        return 0
    tool = event.get("tool_name")
    ti = event.get("tool_input") or {}
    if tool == "Write":
        written = [(str(ti.get("file_path") or ""), ti.get("content") or "")]
    elif tool == "Bash":
        written = heredoc_writes(ti.get("command") or "")
    else:
        return 0

    candidates = [(p, c) for p, c in written if Path(p).suffix.lower() in SCRIPT_SUFFIXES]
    if not candidates:
        return 0

    session = event.get("session_id") or ""
    if not session:
        return 0
    store = _load(session)
    nudged_key = "__nudged__"
    path, content = candidates[-1]                        # judge the last script this call writes
    sh = shingles(content)
    # Record any earlier scripts from the same command so a multi-heredoc call still counts.
    for p, c in candidates[:-1]:
        s = shingles(c)
        if len(s) >= 20:
            store[p] = [list(t) for t in s]
    if len(sh) < 20:                                      # too small to judge; not worth a tool
        _save(session, store)
        return 0

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
