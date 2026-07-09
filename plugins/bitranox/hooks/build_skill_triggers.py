#!/usr/bin/env python3
"""Derive the skill router's trigger map from the skills' own descriptions (no hand-wiring).

Descriptions are trigger-first per the CSO rule (the repo-gate lints this), so they ARE the trigger
source: for every `skills/*/SKILL.md`, distill the frontmatter description into distinctive
keywords and write `skill_triggers.json` next to this script. A FUTURE skill is covered by
construction: adding it and rebuilding the map (part of the release routine; the repo-gate's CSO
lint guarantees its description is derivable) is all it takes.

    build_skill_triggers.py [--skills-dir DIR] [--out FILE] [--check]

`--check` verifies the committed map is in sync (exit 1 if stale) - wired into the repo-gate's
pytest suite. Pure standard library; ASCII.
"""
import argparse
import json
import re
import sys
from pathlib import Path

_STOP = {
    "use", "when", "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "were", "has", "have", "had", "not", "but", "via", "per", "its", "also", "such",
    "them", "then", "than", "each", "any", "all", "one", "two", "new", "old", "how", "what", "why",
    "where", "which", "should", "must", "can", "will", "does", "doing", "done", "being", "after",
    "before", "about", "only", "never", "always", "instead", "whether", "these", "those", "there",
    "their", "would", "could", "asked", "asks", "wants", "needs", "need", "like", "just", "even",
    "every", "some", "more", "most", "other", "another",
}


def distill(description, max_n=14):
    """Distinctive, order-preserved keywords from a trigger-first description."""
    out = []
    for tok in re.findall(r"[a-z0-9][a-z0-9_.+-]{3,}", (description or "").lower()):
        tok = tok.strip(".-")
        if tok in _STOP or len(tok) < 4 or tok in out or tok.isdigit():
            continue
        out.append(tok)
        if len(out) >= max_n:
            break
    return out


def _description(skill_md):
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    fm = text.split("---", 2)[1]
    m = re.search(r"^description:\s*(.+(?:\n(?![a-zA-Z_-]+:).*)*)", fm, re.M)
    return " ".join(m.group(1).split()) if m else None


def build(skills_dir):
    out = {}
    for skill_md in sorted(Path(skills_dir).glob("*/SKILL.md")):
        desc = _description(skill_md)
        if not desc:
            continue
        kws = distill(desc)
        if len(kws) >= 2:
            out[skill_md.parent.name] = kws
    return out


def main(argv=None):
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Derive skill_triggers.json from skill descriptions.")
    ap.add_argument("--skills-dir", default=str(here.parent / "skills"))
    ap.add_argument("--out", default=str(here / "skill_triggers.json"))
    ap.add_argument("--check", action="store_true", help="verify the committed map is in sync")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    triggers = build(args.skills_dir)
    text = json.dumps(triggers, indent=1, sort_keys=True) + "\n"
    out = Path(args.out)
    if args.check:
        try:
            if out.read_text(encoding="utf-8") == text:
                print("skill_triggers.json in sync (%d skills)" % len(triggers))
                return 0
        except OSError:
            pass
        print("skill_triggers.json is STALE - run build_skill_triggers.py", file=sys.stderr)
        return 1
    out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d skills)" % (out, len(triggers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
