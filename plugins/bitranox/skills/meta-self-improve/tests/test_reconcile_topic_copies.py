"""Tests for what the integrity checks say about facts placed by topic: their copies are no
duplicates, a tree whose lines differ from a fresh render has drift, and a ref to such a fact
resolves through its body wherever its lines stand. All content ASCII.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import reconcile_memory_index as R

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)
import self_improve_signals as sig  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/")) if rel else Path(anchor)
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert ME.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        ME.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False, body=None):
    ME.add_or_update_entry(level, title="T " + slug, hook=HOOK, body=body or "body of " + slug,
                           type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        ME.set_fact_topics(level, {slug: topics})


def _rendered(tmp_path):
    """A tree with python at a/py and b/py, one python rule rendered at both, one plain top rule."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    levels = {rel: _level(str(anchor), rel, topics) for rel, topics in (
        ("", None), ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()),
        ("b/py", ("python",)), ("b/other", ()))}
    _fact(levels[""], "feedback-py-rule", ("python",))
    _fact(levels[""], "feedback-top-rule")
    ME.render_topics(levels[""])
    return levels


def _plant_line(level, slug, hook=HOOK, pin=False):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers = [p for p in pointers if p.slug != slug]
    pointers.append(us.Pointer(slug=slug, title="T " + slug, hook=hook, pin=pin))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def _check_tree(levels, capsys):
    capsys.readouterr()
    rc = R.main(["--check-tree", levels[""]])
    return rc, capsys.readouterr().out


def test_a_rendered_tree_has_no_problem(tmp_path, capsys):
    levels = _rendered(tmp_path)
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "TOTAL tree problems: 0" in out and "duplicate pointer" not in out
    rep = R.check_tree(levels[""])
    assert rep["duplicates"] == {} and rep["render_drift"] == [] and rep["render_refused"] == ""


def test_a_missing_copy_is_render_drift(tmp_path, capsys):
    levels = _rendered(tmp_path)
    ME._drop_pointer(levels["b/py"], "feedback-py-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "TOTAL tree problems: 1" in out
    assert "! render drift: %s -> 1 line(s) missing, 0 differing from the body, 0 placed elsewhere " \
           "(feedback-py-rule)" % levels["b/py"] in out


def test_a_copy_that_differs_from_its_body_is_render_drift(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/py"], "feedback-py-rule", hook="When this line went stale, it says this.")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "0 line(s) missing, 1 differing from the body, 0 placed elsewhere" in out


def test_a_copy_at_a_level_it_is_not_placed_at_is_render_drift_not_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/other"], "feedback-py-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "duplicate pointer" not in out
    assert "! render drift: %s -> 0 line(s) missing, 0 differing from the body, 1 placed elsewhere" \
           % levels["a/other"] in out


def test_an_unbound_fact_at_two_levels_stays_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/other"], "feedback-top-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! duplicate pointer: feedback-top-rule at 2 levels" in out


def test_a_pinned_tagged_fact_at_two_levels_stays_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels["a"], "feedback-pinned", pin=True)
    path = us.body_path(levels[""], "feedback-pinned")
    us.put_body(levels[""], "feedback-pinned", ME._with_topics(path.read_text(encoding="utf-8"), ("python",)))
    _plant_line(levels["b"], "feedback-pinned", pin=True)
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! duplicate pointer: feedback-pinned at 2 levels" in out


def test_a_ref_to_a_topic_placed_fact_is_no_sideways_ref(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    _fact(levels["a/other"], "feedback-plain")
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "sideways/downward ref" not in out
    # a ref to a fact that is NOT placed by topic is still judged by its level
    _fact(levels[""], "feedback-citer-2", body="See [[feedback-plain]].")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "[[feedback-plain]] in feedback-citer-2" in out


def test_a_topics_line_that_does_not_parse_is_reported_as_an_unchecked_placement(tmp_path, capsys):
    levels = _rendered(tmp_path)
    local = sig.claude_local_md_path(levels["b"])
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, SCOPE + "\nTOPICS: Not A Tag", []), encoding="utf-8")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! the placement by topic could not be checked" in out and levels["b"] in out


# ---- --check over a chain -----------------------------------------------------------------------

def test_a_clean_chain_has_no_problem_and_a_ref_to_a_placed_fact_is_no_orphan(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 0
    assert R.main(["--check", levels[""]]) == 0
    assert "orphan ref" not in capsys.readouterr().out
    assert R.check_references([levels[""]])["checked"] == 1


def test_a_ref_from_above_to_a_placed_fact_is_no_downward_ref(tmp_path, capsys):
    """feedback-py-rule's lines stand at a/py and b/py, where python is: a citer at `a` cannot sit
    above them, so --check agrees with --check-tree that nothing is wrong. A ref from `a` to a fact
    NOT placed by topic, held only at a/py, is still a downward ref."""
    levels = _rendered(tmp_path)
    _fact(levels["a"], "feedback-citer-a", body="See [[feedback-py-rule]].")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"], levels["a"], levels[""]]) == 0
    out = capsys.readouterr().out
    assert "downward ref" not in out and "TOTAL problems: 0" in out, out
    assert R.check_references([levels["a/py"], levels["a"], levels[""]])["downward"] == []
    _fact(levels["a/py"], "feedback-plain-py")
    _fact(levels["a"], "feedback-citer-b", body="See [[feedback-plain-py]].")
    refs = R.check_references([levels["a/py"], levels["a"], levels[""]])
    assert refs["downward"] == [("feedback-citer-b", "feedback-plain-py")]
    rc, out = _check_tree(levels, capsys)
    assert "[[feedback-py-rule]]" not in out


def test_a_placed_line_a_level_above_also_holds_is_a_chain_problem(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a"], "feedback-py-rule")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 1
    out = capsys.readouterr().out
    assert "! repeated line: feedback-py-rule at %s is also held by %s above it" \
           % (levels["a/py"], levels["a"]) in out and "TOTAL problems: 1" in out
    # the other subtree's chain does not include a, so it is clean
    assert R.main(["--check", levels["b/py"]]) == 0


def test_an_unbound_line_repeated_above_is_left_to_check_tree(tmp_path):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/py"], "feedback-top-rule")
    assert R.chain_repeats([levels["a/py"]]) == []


def test_a_tree_without_a_topic_list_has_no_drift(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    level = _level(str(anchor), "")
    _fact(level, "feedback-a")
    assert R.render_drift(level) == ([], "")


# ---- every drift kind is counted, and the route the finding names repairs it ---------------------

_ROUTE_RX = re.compile(r"(hooks/memory_engine\.py) (render-topics --proj \S+ --scope (?:tree|chain))")


def _run_route(out, tmp_path):
    """Run the engine route a finding names, exactly as given, from a cwd outside the tree."""
    routes = set(_ROUTE_RX.findall(out))
    assert len(routes) == 1, out
    script, argv = routes.pop()
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    engine = Path(ME.__file__).resolve().parents[1] / script
    done = subprocess.run([sys.executable, str(engine), *argv.split()], cwd=str(outside),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    return argv


def test_each_drift_kind_is_counted_per_level_and_the_tree_route_repairs_all_of_them(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels[""], "feedback-py-two", ("python",))
    ME.render_topics(levels[""])
    ME._drop_pointer(levels["b/py"], "feedback-py-rule")
    ME._drop_pointer(levels["b/py"], "feedback-py-two")
    _plant_line(levels["a/py"], "feedback-py-rule", hook="When this line went stale, it says this.")
    _plant_line(levels["a/other"], "feedback-py-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "TOTAL tree problems: 3" in out and "duplicate pointer" not in out
    assert ("! render drift: %s -> 2 line(s) missing, 0 differing from the body, 0 placed "
            "elsewhere (feedback-py-rule, feedback-py-two)" % levels["b/py"]) in out
    assert ("! render drift: %s -> 0 line(s) missing, 1 differing from the body, 0 placed "
            "elsewhere (feedback-py-rule)" % levels["a/py"]) in out
    assert ("! render drift: %s -> 0 line(s) missing, 0 differing from the body, 1 placed "
            "elsewhere (feedback-py-rule)" % levels["a/other"]) in out
    argv = _run_route(out, tmp_path)
    assert argv.split()[2] == levels[""] and argv.endswith("--scope tree")
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "TOTAL tree problems: 0" in out


def test_a_level_with_many_missing_lines_shows_only_a_few_examples(tmp_path):
    levels = _rendered(tmp_path)
    slugs = ["feedback-many-%02d" % i for i in range(12)]
    for slug in slugs:
        _fact(levels[""], slug, ("python",))
    rows, refused = R.render_drift(levels[""])
    assert refused == ""
    by_level = {row[0]: row for row in rows}
    for rel in ("a/py", "b/py"):
        _level_dir, missing, differing, extra, examples = by_level[levels[rel]]
        assert (missing, differing, extra) == (12, 0, 0) and examples == slugs[:5]


# ---- a dry run that refuses is reported, never a crash or a clean result -------------------------

def _assert_unchecked(levels, capsys, *needles):
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "Traceback" not in out, out
    lines = [ln for ln in out.splitlines() if "! the placement by topic could not be checked: " in ln]
    assert len(lines) == 1 and all(n in lines[0] for n in needles), out
    assert lines[0].split("could not be checked: ", 1)[1].strip()
    assert "TOTAL tree problems: 1" in out
    return lines[0]


def test_a_tree_top_without_a_pointer_block_is_an_unchecked_placement(tmp_path, capsys):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    level = _level(str(anchor), "a", ("python",))
    _fact(level, "feedback-py-rule", ("python",))
    levels = {"": level}
    _assert_unchecked(levels, capsys, "has no pointer block")
    # the route the engine's refusal names (ensure-memory-structure) makes the placement checkable
    engine = Path(ME.__file__).resolve()
    outside = tmp_path / "outside"
    outside.mkdir()
    done = subprocess.run([sys.executable, str(engine), "ensure-memory-structure", "--proj",
                           str(anchor)], cwd=str(outside), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "TOTAL tree problems: 0" in out


def test_a_damaged_topic_file_is_an_unchecked_placement(tmp_path, capsys):
    levels = _rendered(tmp_path)
    topic_store.store_path(levels[""]).write_text("{not json", encoding="utf-8")
    _assert_unchecked(levels, capsys)


def test_a_level_over_the_block_cap_is_an_unchecked_placement(tmp_path, capsys):
    levels = _rendered(tmp_path)
    facts = us.central_facts_dir(levels[""])
    for i in range(1200):
        (facts / ("feedback-big%05d.md" % i)).write_text(
            "---\nname: feedback-big%05d\ndescription: %s\ntitle: T\ntopics: [python]\nmetadata:\n"
            "  type: feedback\n---\n\nx\n" % (i, "y" * 1000), encoding="utf-8")
    line = _assert_unchecked(levels, capsys, "bytes")
    # both python levels pass the cap; the census names the first in level order, whatever order
    # the store lists the bodies in
    assert levels["a/py"] in line and levels["b/py"] not in line


@pytest.mark.skipif(sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="a read-only directory refuses a lock file only for a non-root POSIX user")
def test_a_read_only_tree_checks_clean(tmp_path, capsys):
    """The drift check is a dry run, which takes no lock: a tree nobody may write is checked like
    any other, not reported as one the placement could not be checked in."""
    levels = _rendered(tmp_path)
    paths = [Path(levels[""]), *Path(levels[""]).rglob("*")]
    modes = {p: p.stat().st_mode for p in paths}
    for p in paths:
        p.chmod(modes[p] & ~0o222)
    try:
        rc, out = _check_tree(levels, capsys)
    finally:
        for p in paths:
            p.chmod(modes[p])
    assert rc == 0 and "TOTAL tree problems: 0" in out and "could not be checked" not in out, out


# ---- only a fact the renderer manages is placed by topic ----------------------------------------

def _untitled(level, slug):
    """A python-bound fact whose body has no `title:`: the renderer never places it."""
    _fact(level, slug, ("python",))
    path = us.body_path(ME._anchor(level), slug)
    text = path.read_text(encoding="utf-8")
    assert re.search(r"(?m)^title:.*\n", text)
    path.write_text(re.sub(r"(?m)^title:.*\n", "", text, count=1), encoding="utf-8")


def test_a_bound_fact_the_renderer_cannot_place_stays_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _untitled(levels["a"], "feedback-untitled")
    _plant_line(levels["b"], "feedback-untitled")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! duplicate pointer: feedback-untitled at 2 levels" in out
    assert "render drift" not in out


def test_a_ref_to_a_bound_fact_pinned_elsewhere_or_untitled_is_still_a_chain_orphan(tmp_path):
    levels = _rendered(tmp_path)
    _fact(levels["b/other"], "feedback-pinned-py", ("python",))
    _plant_line(levels["b/other"], "feedback-pinned-py", pin=True)
    _untitled(levels["b/other"], "feedback-untitled")
    _fact(levels["a/py"], "feedback-citer", body="See [[feedback-pinned-py]] and [[feedback-untitled]].")
    refs = R.check_references([levels["a/py"]])
    assert refs["orphans"] == [("feedback-citer", "feedback-pinned-py"),
                               ("feedback-citer", "feedback-untitled")]


def test_a_repeat_of_a_fact_pinned_elsewhere_or_untitled_is_left_to_check_tree(tmp_path):
    levels = _rendered(tmp_path)
    _fact(levels["b/other"], "feedback-pinned-py", ("python",))
    _plant_line(levels["b/other"], "feedback-pinned-py", pin=True)
    _untitled(levels["a/other"], "feedback-untitled")
    for slug in ("feedback-pinned-py", "feedback-untitled"):
        _plant_line(levels["a"], slug)
        _plant_line(levels["a/py"], slug)
    assert R.chain_repeats([levels["a/py"]]) == []


def test_the_chain_route_a_repeated_line_names_clears_the_chain(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a"], "feedback-py-rule")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 1
    argv = _run_route(capsys.readouterr().out, tmp_path)
    assert argv.split()[2] == levels["a/py"] and argv.endswith("--scope chain")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 0
    assert "TOTAL problems: 0" in capsys.readouterr().out
