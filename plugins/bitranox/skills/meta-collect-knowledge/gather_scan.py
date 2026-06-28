#!/usr/bin/env python3
"""Stage-1 of the inbound cross-tree gather: a fast, deterministic keyword grep (NO model).

The expensive (model) gather runs ONLY on a hit, so when nothing matches the cost is one cheap
scan. Given a topic / scope descriptor, derive keywords and grep them across OTHER projects' Auto
memory and the global rules layer, returning candidate files for the skill to inspect. The current
project is excluded (you gather FROM elsewhere). Global rules are scanned only so the skill can avoid
re-copying what an ancestor already provides.

Usage:
  gather_scan.py --topic "<text>" [--self <cwd>]

Imports the shared helpers from the plugin's hooks dir, like the meta-dream cadence CLI. Pure stdlib.
"""

import argparse
import os
import re
import sys
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


def extract_keywords(text, max_n=12):
    """Deterministic keyword set from a topic / descriptor: lowercased significant tokens (>=3 chars,
    not stopwords), de-duplicated in first-seen order, capped. No model. (Synonym recall is traded
    for speed; a richer pass can run later.)"""
    out = []
    for tok in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", (text or "").lower()):
        if tok in _STOP or len(tok) < 3 or tok in out:
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


def scan(keywords, files):
    """Map each file that contains any keyword to the list of keywords it matched (case-insensitive
    substring - grep-like). Files that read-fail are skipped."""
    kws = [k.lower() for k in keywords if k]
    out = {}
    for p in files:
        try:
            text = Path(p).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        hits = [k for k in kws if k in text]
        if hits:
            out[str(p)] = hits
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cross-tree gather stage-1: keyword grep for candidates.")
    ap.add_argument("--topic", required=True, help="topic / scope-descriptor text to gather for")
    ap.add_argument("--self", dest="self_proj", default=None,
                    help="current project cwd to EXCLUDE (you gather from elsewhere)")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    keywords = extract_keywords(args.topic)
    if not keywords:
        print("no usable keywords from topic", file=sys.stderr)
        return 0
    self_proj = args.self_proj or os.getcwd()
    hits = scan(keywords, discover_files(self_proj))
    for path in sorted(hits):
        print("%s\t%s" % (path, ",".join(hits[path])))
    print("CANDIDATES: %d (keywords: %s)" % (len(hits), ", ".join(keywords)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
