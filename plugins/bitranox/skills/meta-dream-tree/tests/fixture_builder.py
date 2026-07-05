#!/usr/bin/env python3
"""Build the planted-fixture tree for the dream acceptance test (deterministic, engine-written).

Creates under a given root:
  tree1/                    anchor (CLAUDE.md + .claude-memory)
    dept-a/proj-1, proj-2   two sibling projects (CLAUDE.md each)
    dept-b/                 a department with an EMPTY scope descriptor (SCOPE case)
  tree2/                    an independent control tree (must stay byte-identical, XTREE case)

Planted cases (expectations a dream run must satisfy; see fixture_asserter.py):
  DUP       near-identical fact in proj-1 AND proj-2 -> merged into ONE entry at dept-a
  MIS-HIGH  proj-1-specific fact planted at the ANCHOR -> moved DOWN to proj-1
  MIS-LOW   an all-dept-a fact planted in proj-1 -> moved UP to dept-a (NOT the anchor)
  OBS       an obsolete fact (references a deleted file) in proj-1 -> proposed for archive
  TASK      session task-state in proj-2 -> pruned
  VOICE     a trigger-less hook in proj-1 -> reworded trigger-first, slug STABLE
  PIN       an obsolete-LOOKING but PINNED fact at the anchor -> untouched (propose-only)
  SCOPE     dept-b descriptor left empty -> synthesized (template keys present)

Writes a fixture-manifest.json at the root recording the planted slugs and the control tree's
file hashes. Pure standard library + the plugin engine; ASCII output.
"""
import hashlib
import json
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parents[3] / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

import memory_engine as E   # noqa: E402
import uuid_store as us     # noqa: E402


def _tree_hash(root):
    """{relpath: sha256} for every file under root (the XTREE byte-identity check)."""
    out = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def build(root):
    root = Path(root)
    t1 = root / "tree1"
    dept_a = t1 / "dept-a"
    p1 = dept_a / "proj-1"
    p2 = dept_a / "proj-2"
    dept_b = t1 / "dept-b"
    t2 = root / "tree2" / "control-proj"
    for d in (p1, p2, dept_b, t2):
        d.mkdir(parents=True, exist_ok=True)
    for d in (t1, dept_a, p1, p2, dept_b, t2.parent, t2):
        (d / "CLAUDE.md").write_text("fixture level: %s\n" % d.name, encoding="utf-8")
    (t1 / us.STORE_DIRNAME).mkdir(exist_ok=True)
    (t2.parent / us.STORE_DIRNAME).mkdir(exist_ok=True)
    (p1 / "tooling.py").write_text("def fmt(v):\n    return str(v)\n", encoding="utf-8")

    scopes = {
        t1: ("WHAT: The umbrella of the fixture company; everything below is one org.\n"
             "STACK: mixed\nCHILDREN:\n- dept-a/: the tooling department (proj-1, proj-2)\n"
             "- dept-b/: the data department\n"
             "PLACE-HERE: rules true for the WHOLE org\nPLACE-ELSEWHERE: push dept- or "
             "project-specific knowledge down"),
        dept_a: ("WHAT: The tooling department; shared build conventions for its projects.\n"
                 "STACK: python, make\nCHILDREN:\n- proj-1/: the formatter tool\n"
                 "- proj-2/: the linter tool\nPLACE-HERE: rules true for ALL dept-a projects\n"
                 "PLACE-ELSEWHERE: push single-project facts down; org-wide rules up"),
        p1: ("WHAT: proj-1, the formatter tool (tooling.py).\nSTACK: python\nCHILDREN:\n- none\n"
             "PLACE-HERE: facts about proj-1's own files and flags\n"
             "PLACE-ELSEWHERE: anything shared with proj-2 goes to dept-a"),
        p2: ("WHAT: proj-2, the linter tool.\nSTACK: python\nCHILDREN:\n- none\n"
             "PLACE-HERE: facts about proj-2's own files and flags\n"
             "PLACE-ELSEWHERE: anything shared with proj-1 goes to dept-a"),
    }
    for lvl, scope in scopes.items():
        E.ensure_level(str(lvl), scope_default=scope)
    E.ensure_level(str(dept_b), scope_default="")          # SCOPE case: stays empty

    slugs = {}
    slugs["dup_a"] = E.add_or_update_entry(
        str(p1), "Builds need libfoo headers",
        "When building any dept-a tool, install libfoo-dev first or the build fails.",
        body="The dept-a build chain links against libfoo; libfoo-dev must be present.")
    slugs["dup_b"] = E.add_or_update_entry(
        str(p2), "Install libfoo before building",
        "When compiling a dept-a tool, the libfoo-dev package must be installed first.",
        body="Compiling links against libfoo; without libfoo-dev the build fails.")
    slugs["mis_high"] = E.add_or_update_entry(
        str(t1), "proj-1 formatter flag",
        "When editing proj-1's tooling.py, keep fmt() returning str (its CLI contract).",
        body="tooling.py fmt() is proj-1's CLI output contract; other projects do not use it.")
    slugs["mis_low"] = E.add_or_update_entry(
        str(p1), "Dept-a release naming",
        "When tagging ANY dept-a project release, use the vYYYY.MM.patch scheme (both proj-1 "
        "and proj-2 follow it).",
        body="All dept-a tools share the vYYYY.MM.patch tag scheme; org-wide tools do not.")
    slugs["obs"] = E.add_or_update_entry(
        str(p1), "Legacy config location",
        "When reading proj-1 config, use legacy_conf.ini in the project root.",
        body="legacy_conf.ini holds the settings. (The file was deleted in the current layout.)")
    slugs["task"] = E.add_or_update_entry(
        str(p2), "Build currently running",
        "When resuming, note the linter build from this session is still running on runner 3.",
        body="Session state: build #442 in flight; check back after lunch.")
    slugs["voice"] = E.add_or_update_entry(
        str(p1), "Formatter width rule",
        "Line width 100; fmt() must wrap.",       # deliberately trigger-less (VOICE case)
        body="proj-1 output wraps at 100 columns; fmt() enforces it.")
    slugs["pin"] = E.add_or_update_entry(
        str(t1), "Old escalation contact",
        "When an org-wide incident occurs, page the duty phone listed here first.",
        body="Duty phone: the rotation sheet on the intranet. (Looks stale; MUST stay pinned "
             "and untouched unless the user approves.)", pin=True)

    E.add_or_update_entry(
        str(t2), "Control tree fact",
        "When working in the control tree, know it must never be touched by tree1's dream.",
        body="XTREE control: byte-identical before/after a tree1 dream.")

    manifest = {
        "tree1": str(t1), "dept_a": str(dept_a), "proj1": str(p1), "proj2": str(p2),
        "dept_b": str(dept_b), "tree2": str(root / "tree2"), "slugs": slugs,
        "tree2_hash": _tree_hash(root / "tree2"),
        # sibling-branch snapshots: a CHAIN-scoped nap run from proj-1 must leave these
        # byte-identical (the parity matrix's inverse assertion); note the sibling POINTER
        # snapshots exclude the central store (bodies are shared at the anchor)
        "proj2_hash": _tree_hash(p2),
        "dept_b_hash": _tree_hash(dept_b),
        "voice_hook_before": "Line width 100; fmt() must wrap.",
        "pin_hook_before": "When an org-wide incident occurs, page the duty phone listed here first.",
    }
    (root / "fixture-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: fixture_builder.py <root-dir>")
        return 2
    m = build(args[0])
    print("fixture built at %s (%d planted facts)" % (args[0], len(m["slugs"]) + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
