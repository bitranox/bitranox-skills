#!/usr/bin/env python3
"""Assert a dream run against the planted fixture (see fixture_builder.py).

HARD assertions (every run must pass ALL):
  XTREE      tree2 byte-identical to the manifest hashes
  PIN        the pinned anchor entry still present, still pinned, hook text unchanged
  VOICE-ID   the voice-case slug still exists somewhere in tree1 (slug-stable reword)
  RECONCILE  reference integrity over tree1's chains: 0 problems
  NO-LOSS    every planted slug still resolves somewhere in tree1 (except TASK/OBS, which may
             legitimately be pruned/archived)

JUDGMENT assertions (the bar: >= 5 of 6 on two consecutive runs):
  DUP        the two dup facts merged into ONE entry, homed at dept-a
  MIS-HIGH   the proj-1-specific fact moved DOWN to proj-1
  MIS-LOW    the dept-a-wide fact moved UP to dept-a (not the anchor, not proj-1)
  OBS        the obsolete fact archived (or explicitly proposed for archive)
  TASK       the task-state fact pruned
  SCOPE      dept-b's descriptor synthesized (WHAT:/PLACE-HERE: keys present)

Exit 0 when all HARD pass; the judgment score is reported either way. ASCII output.
"""
import json
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parents[3] / "hooks"
_SI = Path(__file__).resolve().parents[2] / "meta-self-improve"
for _d in (str(_HOOKS), str(_SI)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import self_improve_signals as sig            # noqa: E402
import uuid_store as us                        # noqa: E402
import reconcile_memory_index as R             # noqa: E402
from fixture_builder import _tree_hash         # noqa: E402


def _entries_at(level):
    try:
        text = sig.claude_local_md_path(str(level)).read_text(encoding="utf-8")
    except OSError:
        return {}
    _s, ptrs = us.parse_pointer_index(text)
    return {p.slug: p for p in ptrs}


def _levels(m):
    return [Path(m["tree1"]), Path(m["dept_a"]), Path(m["proj1"]), Path(m["proj2"]),
            Path(m["dept_b"])]


def _find(m, slug):
    """[(level, Pointer)] wherever slug is pointed at in tree1."""
    return [(lvl, es[slug]) for lvl in _levels(m) for es in [_entries_at(lvl)] if slug in es]


def check(root):
    root = Path(root)
    m = json.loads((root / "fixture-manifest.json").read_text(encoding="utf-8"))
    s = m["slugs"]
    hard, judgment = {}, {}

    hard["XTREE"] = _tree_hash(m["tree2"]) == m["tree2_hash"]

    pin_hits = _find(m, s["pin"])
    hard["PIN"] = (len(pin_hits) == 1 and str(pin_hits[0][0]) == m["tree1"]
                   and pin_hits[0][1].pin and pin_hits[0][1].hook == m["pin_hook_before"])

    hard["VOICE-ID"] = bool(_find(m, s["voice"]))

    problems = 0
    for proj in (m["proj1"], m["proj2"], m["dept_b"]):
        chain = [str(x) for x in sig.altitude_chain(proj)]
        refs = R.check_references(chain)
        problems += len(refs["orphans"]) + len(refs["downward"])
    hard["RECONCILE"] = problems == 0

    prunable = {s["task"], s["obs"]}
    dup_slugs = {s["dup_a"], s["dup_b"]}
    missing = [slug for slug in s.values()
               if slug not in prunable and not _find(m, slug)]
    # a merged dup may retire ONE of the two dup slugs - that is not a loss
    missing_real = [x for x in missing if not (x in dup_slugs and
                                               any(_find(m, d) for d in dup_slugs))]
    hard["NO-LOSS"] = not missing_real

    dup_hits = [(slug, lvl) for slug in dup_slugs for lvl, _p in _find(m, slug)]
    judgment["DUP"] = (len(dup_hits) == 1 and str(dup_hits[0][1]) == m["dept_a"])

    mh = _find(m, s["mis_high"])
    judgment["MIS-HIGH"] = (len(mh) == 1 and str(mh[0][0]) == m["proj1"])

    ml = _find(m, s["mis_low"])
    judgment["MIS-LOW"] = (len(ml) == 1 and str(ml[0][0]) == m["dept_a"])

    obs_gone = not _find(m, s["obs"])
    obs_archived = (Path(m["tree1"]) / us.STORE_DIRNAME / ".archive" / (s["obs"] + ".md")).is_file()
    judgment["OBS"] = obs_gone and obs_archived

    judgment["TASK"] = not _find(m, s["task"])

    scope = us.parse_pointer_index(
        sig.claude_local_md_path(m["dept_b"]).read_text(encoding="utf-8"))[0]
    judgment["SCOPE"] = "WHAT:" in scope and "PLACE-HERE:" in scope

    return hard, judgment


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: fixture_asserter.py <root-dir>")
        return 2
    hard, judgment = check(args[0])
    for name, ok in hard.items():
        print("HARD  %-9s %s" % (name, "PASS" if ok else "FAIL"))
    for name, ok in judgment.items():
        print("JUDGE %-9s %s" % (name, "PASS" if ok else "FAIL"))
    jscore = sum(judgment.values())
    print("hard: %d/%d  judgment: %d/%d (bar: all hard + >=5 judgment, two consecutive runs)"
          % (sum(hard.values()), len(hard), jscore, len(judgment)))
    return 0 if all(hard.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
