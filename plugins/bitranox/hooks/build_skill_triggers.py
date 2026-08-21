#!/usr/bin/env python3
"""Derive the skill router's trigger map from the skills' own descriptions (no hand-wiring).

Descriptions are trigger-first per the CSO rule (the repo-gate lints this), so they ARE the trigger
source: for every `skills/*/SKILL.md`, distill the frontmatter description into distinctive
keywords and write `skill_triggers.json` next to this script. A description's head is prose
about the situation and its tail holds the literal error codes, so the map takes the first
`MAX_HEAD` in order plus up to `MAX_EXTRA` identifier-shaped tail tokens no other skill claims. A FUTURE skill is covered by
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


MAX_HEAD = 14                    # equal-length heads keep the router's raw hit COUNT comparable
MAX_EXTRA = 10                   # appended only for tokens that cannot match an unrelated prompt
_IDENT_RX = re.compile(r"[0-9._+-]")


def distill(description, max_n=None):
    """Distinctive, order-preserved keywords from a trigger-first description.

    `max_n=None` returns EVERY candidate; `select` decides which ones reach the map.
    """
    out = []
    for tok in re.findall(r"[a-z0-9][a-z0-9_.+-]{3,}", (description or "").lower()):
        tok = tok.strip(".-")
        if tok in _STOP or len(tok) < 4 or tok in out or tok.isdigit():
            continue
        out.append(tok)
        if max_n is not None and len(out) >= max_n:
            break
    return out


def distinctive(token):
    """True for a token shaped like a technical identifier - it carries a digit or punctuation.

    A description is trigger-first, so its HEAD is prose about the situation and its TAIL carries
    the literal error codes and paths - exactly the strings someone in trouble pastes verbatim.
    Those are safe to add beyond the head because they cannot match a prompt about anything else.

    Length is NOT a usable substitute, though it looks like one. Measured over 2146 real prompts,
    admitting any token of 9+ characters also admitted `description` (in 50 of them), `condition`
    (33) and `interface` (33) - ordinary English that put an unrelated skill on an unrelated
    prompt. The identifier shape admits 126 tokens across the shipped skills and NONE of them
    reaches 20 prompts; that is the whole reason the rule is shape and not size.
    """
    return bool(_IDENT_RX.search(token))


def select(tokens, doc_freq, max_head=MAX_HEAD, max_extra=MAX_EXTRA):
    """The keywords that reach the map: the head in order, plus distinctive tokens from the tail.

    `doc_freq` maps a token to how many skills' descriptions claim it. Only tokens claimed by ONE
    skill are appended - a shared token cannot discriminate between them, and adding shared words
    is what would let a long description out-count every other skill on an unrelated prompt.
    """
    head = list(tokens[:max_head])
    seen = set(head)
    extra = [t for t in tokens[max_head:]
             if t not in seen and doc_freq.get(t, 0) == 1 and distinctive(t)]
    return head + extra[:max_extra]


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
    candidates = {}
    for skill_md in sorted(Path(skills_dir).glob("*/SKILL.md")):
        desc = _description(skill_md)
        if desc:
            candidates[skill_md.parent.name] = distill(desc)
    doc_freq = {}
    for toks in candidates.values():
        for t in set(toks):
            doc_freq[t] = doc_freq.get(t, 0) + 1
    out = {}
    for skill, toks in candidates.items():
        kws = select(toks, doc_freq)
        if len(kws) >= 2:
            out[skill] = kws
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
