"""Tests that a legacy `uuid:` line keeps a fact from being placed by topic, whatever its body's
`topics:` line says, in the engine and in every tool that judges placement the engine's way.

A fact whose body is bound to a topic but which also has a legacy line at some level used to be
managed by the renderer: a tree render added its lines at the levels its topics place it at,
which no render or check could then account for beside the legacy line it never drops. The
engine's rule (`_unplaceable_slugs`, `_placed_slugs`, `_placed_copies`) now treats a legacy line
like a pinned one, and reconcile's --check-tree, mem_levels.py and ref_map.py follow it.
All content ASCII.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import uuid_store as us

HOOKS = Path(E.__file__).resolve().parent
SKILLS = HOOKS.parent / "skills"
HOOK = "When a rule is about one stack, bind it to that stack's topic."
UUID = "0f1e2d3c-4b5a-5968-8776-a5b4c3d2e1f0"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _main(*args):
    return E.main([str(a) for a in args])


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    listing = tmp_path / "list.json"
    listing.write_text(json.dumps({"tagger": "jev", "topics": {"python": "about python"}}),
                       encoding="utf-8")
    assert _main("topics-set-list", "--proj", anchor, "--from-file", listing) == 0
    assert _main("set-scope", "--proj", anchor, "--scope", "WHAT: the top") == 0
    out = {"": str(anchor)}
    for rel, topics in (("a", None), ("a/py", "python"), ("b", None), ("b/py", "python"),
                        ("c", None)):
        level = Path(anchor, *rel.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert _main("set-scope", "--proj", level, "--scope", "WHAT: " + rel) == 0
        if topics:
            assert _main("set-level-topics", "--proj", level, "--topics", topics) == 0
        out[rel] = str(level)
    return out


def _bound_with_a_legacy_line(L, slug="feedback-lg"):
    """`slug` written at c and bound to python, then its line at c turned into a legacy
    `uuid:` line (an old plugin's write) whose body sits at the legacy path."""
    assert _main("add", "--proj", L["c"], "--title", "T " + slug, "--hook", HOOK, "--body",
                 "body " + slug, "--type", "feedback", "--slug", slug) == 0
    assert _main("set-topics", "--proj", L["c"], "--slug", slug, "--topics", "python") == 0
    local = sig.claude_local_md_path(L["c"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers = [us.Pointer(slug=p.slug, title=p.title, hook=p.hook, uuid=UUID, legacy=True)
                if p.slug == slug else p for p in pointers]
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    legacy = us.legacy_body_path(L[""], UUID)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(us.body_path(L[""], slug).read_text(encoding="utf-8"), encoding="utf-8")
    assert E.read_body_topics(us.body_path(L[""], slug)) == ("python",)
    assert any(p.legacy and p.slug == slug for p in
               us.parse_pointer_index(local.read_text(encoding="utf-8"))[1])


def _levels_holding(anchor, slug):
    return sorted(str(level) for level, _ptr in E._copies_of(anchor, slug))


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _load(name, path):
    """The module at `path`, its own dir on sys.path while it loads (it imports siblings)."""
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


def test_a_legacy_line_keeps_a_bound_fact_unplaced_in_the_engine(tmp_path):
    L = _tree(tmp_path)
    _bound_with_a_legacy_line(L)
    assert E._placed_slugs(L[""], ["feedback-lg"]) == set()
    assert E._placed_copies(L[""], "feedback-lg") == []
    assert "feedback-lg" in E._unplaceable_slugs(E.curated_levels_under(L[""]))


def test_tree_and_chain_renders_leave_it_alone_and_agree(tmp_path):
    """Reviewer B's case: tree render then chain render then --check-tree, stable and clean."""
    L = _tree(tmp_path)
    _bound_with_a_legacy_line(L)
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    after_tree = _snapshot(L[""])
    assert _levels_holding(L[""], "feedback-lg") == [L["c"]]
    for proj in (L["c"], L["a/py"], L["b/py"]):
        assert _main("render-topics", "--proj", proj, "--scope", "chain") == 0
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    assert _snapshot(L[""]) == after_tree
    done = subprocess.run([sys.executable,
                           str(SKILLS / "meta-self-improve" / "reconcile_memory_index.py"),
                           "--check-tree", L[""]], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    assert done.returncode == 0 and "TOTAL tree problems: 0" in done.stdout, done.stdout + done.stderr


def test_mem_levels_and_ref_map_do_not_list_it_as_placed(tmp_path):
    L = _tree(tmp_path)
    _bound_with_a_legacy_line(L)
    # a second, non-legacy line at another level: placed would hide this pair as a duplicate
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    local = sig.claude_local_md_path(L["a"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(
        text, scope, pointers + [us.Pointer(slug="feedback-lg", title="T feedback-lg",
                                            hook=HOOK)]), encoding="utf-8")
    mem_levels = _load("mem_levels_r2", SKILLS / "compuse-toolbox" / "scripts" / "mem_levels.py")
    report = mem_levels.scan(L[""])
    assert "feedback-lg" not in report.placed
    assert "feedback-lg" in report.duplicates
    ref_map = _load("ref_map_r2", SKILLS / "meta-self-improve" / "ref_map.py")
    assert ref_map.read_placed(Path(L[""]), {"feedback-lg"}) == set()


def test_an_un_bind_leaves_the_lines_of_a_fact_with_a_legacy_line_where_they_are(tmp_path):
    """Never placed, so its lines are not copies a collapse may fold into one at the top."""
    L = _tree(tmp_path)
    _bound_with_a_legacy_line(L)
    local = sig.claude_local_md_path(L["a/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(
        text, scope, pointers + [us.Pointer(slug="feedback-lg", title="T feedback-lg",
                                            hook=HOOK)]), encoding="utf-8")
    rep = E.set_fact_topics(L[""], {"feedback-lg": None})
    assert rep["collapsed"] == [] and rep["set"] == ["feedback-lg"]
    assert _levels_holding(L[""], "feedback-lg") == sorted([L["a/py"], L["c"]])
    assert E.read_body_topics(us.body_path(L[""], "feedback-lg")) is None
