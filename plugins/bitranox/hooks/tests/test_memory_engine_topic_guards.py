"""Tests for what the ordinary write verbs do with a fact that is placed by topic: move and
relocate refuse it, add writes it only from a level holding one of its lines and refreshes the
others, a bound fact cannot be pinned, and rename and retitle reach every line without calling
them duplicates. All content ASCII.
"""

import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import mod_bridge
import pytest
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, with_list=True):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _two_python_levels(tmp_path):
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()))}
    return anchor, levels


def _rendered(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    _fact(anchor, "feedback-plain")
    E.render_topics(anchor)
    return anchor, levels


def _line(level, slug):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return next(p for p in us.parse_pointer_index(text)[1] if p.slug == slug)


ENGINE_ROOT = Path(E.__file__).resolve().parents[1]


def _run_route(tmp_path, route, *extra):
    """Run a route a refusal named (`hooks/memory_engine.py <verb> ...`) as a subprocess from a
    cwd outside the tree, as a reader would. Returns (rc, output)."""
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    script, *args = route.split()
    done = subprocess.run([sys.executable, str(ENGINE_ROOT / script), *args, *extra],
                          cwd=str(outside), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    return done.returncode, done.stdout + done.stderr


# ---- move and relocate ---------------------------------------------------------------------------

def test_move_refuses_a_fact_placed_by_topic_and_moves_nothing(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    before = _snapshot(anchor)
    capsys.readouterr()
    rc = E.main(["move", "--from-level", levels["a/py"], "--to-level", levels["a"],
                 "--slug", "feedback-py-rule"])
    out = capsys.readouterr().out
    assert rc == 2 and "! refused" in out and "is placed by topic" in out
    route = re.search(r"(hooks/memory_engine\.py set-topics --proj \S+ --slug feedback-py-rule "
                      r"--clear)", out)
    assert route is not None and _snapshot(anchor) == before, out
    # the route, run as given from outside the tree, un-binds it; the lines collapse to the top,
    # and a move then takes the fact like any other
    rc, said = _run_route(tmp_path, route.group(1))
    assert rc == 0, said
    assert _slugs(anchor) == ["feedback-plain", "feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []
    assert E.main(["move", "--from-level", anchor, "--to-level", levels["a"],
                   "--slug", "feedback-py-rule"]) == 0
    assert _slugs(levels["a"]) == ["feedback-py-rule"]



def test_move_refusal_for_a_one_line_fact_says_its_line_stays_and_the_route_works(tmp_path, capsys):
    """A fact placed at one level only has one line: un-binding it collapses nothing, its line
    stays where it is. The refusal said its lines collapse to one at the tree top."""
    anchor, levels = _rendered(tmp_path)
    rs = _level(anchor, "a/rs", ("rust",))
    _fact(anchor, "feedback-rs-rule", ("rust",))
    E.render_topics(anchor)
    assert "feedback-rs-rule" in _slugs(rs) and "feedback-rs-rule" not in _slugs(anchor)
    capsys.readouterr()
    rc = E.main(["move", "--from-level", rs, "--to-level", levels["a"],
                 "--slug", "feedback-rs-rule"])
    out = capsys.readouterr().out
    assert rc == 2 and "is placed by topic" in out, out
    assert "collapse" not in out and "its one line stays at %s" % rs in out, out
    route = re.search(r"(hooks/memory_engine\.py set-topics --proj \S+ --slug feedback-rs-rule "
                      r"--clear)", out)
    assert route is not None, out
    rc, said = _run_route(tmp_path, route.group(1))
    assert rc == 0, said
    assert "feedback-rs-rule" in _slugs(rs) and "feedback-rs-rule" not in _slugs(anchor)
    assert E.main(["move", "--from-level", rs, "--to-level", levels["a"],
                   "--slug", "feedback-rs-rule"]) == 0
    assert "feedback-rs-rule" in _slugs(levels["a"])


def test_move_refusal_for_a_fact_with_several_lines_says_they_collapse_at_the_top(tmp_path,
                                                                                 capsys):
    anchor, levels = _rendered(tmp_path)
    capsys.readouterr()
    assert E.main(["move", "--from-level", levels["a/py"], "--to-level", levels["a"],
                   "--slug", "feedback-py-rule"]) == 2
    out = capsys.readouterr().out
    assert "its 2 lines collapse to one at the tree top" in out, out

def test_a_set_holding_one_placed_fact_is_refused_whole(tmp_path):
    _anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-local")
    rep = E.move_entry(levels["a/py"], levels["a"], ["feedback-local", "feedback-py-rule"])
    assert rep["moved"] is False and "placed by topic" in rep["refused"]
    assert _slugs(levels["a/py"]) == ["feedback-local", "feedback-py-rule"]


def test_move_still_moves_an_untagged_an_unbound_and_a_pinned_tagged_fact(tmp_path):
    anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-local")
    _fact(levels["a/py"], "feedback-universal", ())
    _fact(levels["a/py"], "feedback-pinned", pin=True)
    path = us.body_path(anchor, "feedback-pinned")
    us.put_body(anchor, "feedback-pinned", E._with_topics(path.read_text(encoding="utf-8"), ("python",)))
    for slug in ("feedback-local", "feedback-universal", "feedback-pinned"):
        rep = E.move_entry(levels["a/py"], levels["a"], slug)
        assert rep["moved"] is True and rep["refused"] is None, slug
    assert _slugs(levels["a"]) == ["feedback-local", "feedback-pinned", "feedback-universal"]


def _second_tree(tmp_path):
    other = tmp_path / "tree2"
    other.mkdir()
    (other / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (other / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(other), "--scope", "WHAT: another tree"]) == 0
    return str(other)


def test_a_cross_tree_relocate_refuses_a_fact_placed_by_topic(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    other = _second_tree(tmp_path)
    before = (_snapshot(anchor), _snapshot(other))
    capsys.readouterr()
    rc = E.main(["relocate", "--from-level", levels["a/py"], "--to-level", other,
                 "--slug", "feedback-py-rule"])
    out = capsys.readouterr().out
    assert rc == 2 and "is placed by topic" in out
    assert (_snapshot(anchor), _snapshot(other)) == before
    # un-bound with the route the refusal names, it relocates as any fact does
    route = re.search(r"(hooks/memory_engine\.py set-topics --proj \S+ --slug feedback-py-rule "
                      r"--clear)", out)
    assert route is not None, out
    rc, said = _run_route(tmp_path, route.group(1))
    assert rc == 0, said
    assert E.main(["relocate", "--from-level", anchor, "--to-level", other,
                   "--slug", "feedback-py-rule"]) == 0
    assert _slugs(other) == ["feedback-py-rule"]


# ---- add ------------------------------------------------------------------------------------------

def test_add_from_a_level_without_a_line_is_refused_and_writes_nothing(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    for where in (anchor, levels["a/other"], str(Path(anchor, "new-level"))):
        before = _snapshot(anchor)
        rc = E.main(["add", "--proj", where, "--title", "T feedback-py-rule", "--slug",
                     "feedback-py-rule", "--hook", "When this is the new hook, say so."])
        out = capsys.readouterr().out
        assert rc == 2 and "is placed by topic and has no line at this level" in out
        assert levels["a/py"] in out and levels["b/py"] in out and _snapshot(anchor) == before
    # the route it names writes the fact from a level that holds a line
    route = re.search(r"(hooks/memory_engine\.py add --proj \S+ --slug feedback-py-rule) \.\.\.", out)
    assert route is not None and route.group(1).split()[3] in (levels["a/py"], levels["b/py"]), out
    rc, said = _run_route(tmp_path, route.group(1), "--title", "T feedback-py-rule", "--hook",
                          "When this is the new hook, say so.")
    assert rc == 0, said
    for rel in ("a/py", "b/py"):
        assert _line(levels[rel], "feedback-py-rule").hook == "When this is the new hook, say so."
    assert E.render_topics(anchor, dry_run=True)["levels"] == {}
    with pytest.raises(E.SlugCollision) as exc:
        E.add_or_update_entry(anchor, title="T", hook=HOOK, slug="feedback-py-rule")
    assert isinstance(exc.value, E.PlacedElsewhere) and exc.value.suggestion is None
    assert issubclass(E.PlacedElsewhere, mod_bridge.REFUSALS)


def test_an_update_at_one_line_refreshes_the_others(tmp_path):
    anchor, levels = _rendered(tmp_path)
    new_hook = "When the rule changes, every level that reads it says the new thing."
    E.add_or_update_entry(levels["a/py"], title="New title", hook=new_hook, body="new body",
                          slug="feedback-py-rule")
    for rel in ("a/py", "b/py"):
        line = _line(levels[rel], "feedback-py-rule")
        assert (line.title, line.hook, line.pin) == ("New title", new_hook, False)
    body = us.body_path(anchor, "feedback-py-rule").read_text(encoding="utf-8")
    assert E._body_topics(body) == ("python",) and "new body" in body
    assert E.render_topics(anchor, dry_run=True)["levels"] == {}


def test_a_dangling_bound_body_is_still_adopted(tmp_path):
    _anchor, levels = _rendered(tmp_path)
    for rel in ("a/py", "b/py"):
        E._drop_pointer(levels[rel], "feedback-py-rule")
    E.add_or_update_entry(levels["a"], title="T feedback-py-rule", hook=HOOK, slug="feedback-py-rule")
    assert _slugs(levels["a"]) == ["feedback-py-rule"]


def test_pinning_a_bound_fact_is_refused_before_any_write(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    before = _snapshot(anchor)
    capsys.readouterr()
    rc = E.main(["add", "--proj", levels["a/py"], "--title", "T feedback-py-rule", "--slug",
                 "feedback-py-rule", "--hook", HOOK, "--pin"])
    out = capsys.readouterr().out
    assert rc == 2 and "a pinned fact is never placed by topic" in out and _snapshot(anchor) == before
    # un-bound first with the route it names, the pin goes through
    route = re.search(r"(hooks/memory_engine\.py set-topics --proj \S+ --slug feedback-py-rule "
                      r"--clear)", out)
    assert route is not None, out
    rc, said = _run_route(tmp_path, route.group(1))
    assert rc == 0, said
    assert E.main(["add", "--proj", anchor, "--title", "T feedback-py-rule", "--slug",
                   "feedback-py-rule", "--hook", HOOK, "--pin"]) == 0
    assert _line(anchor, "feedback-py-rule").pin is True


def test_an_ordinary_fact_is_written_as_before(tmp_path):
    anchor, _levels = _rendered(tmp_path)
    E.add_or_update_entry(anchor, title="T feedback-plain", hook="When plain, stay plain.",
                          slug="feedback-plain", pin=True)
    assert _line(anchor, "feedback-plain").pin is True


# ---- rename and retitle ---------------------------------------------------------------------------

def test_rename_reaches_every_line_without_calling_them_duplicates(tmp_path):
    anchor, levels = _rendered(tmp_path)
    rep = E.rename_entry(levels["a/py"], "feedback-py-rule", "feedback-py-rule-2")
    assert rep["refused"] is None and not any("duplicate" in w for w in rep["warnings"])
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule-2"]
    assert E.read_body_topics(us.body_path(anchor, "feedback-py-rule-2")) == ("python",)


def test_retitle_reaches_every_line_without_calling_them_duplicates(tmp_path):
    anchor, levels = _rendered(tmp_path)
    rep = E.retitle_entry(levels["a/py"], "feedback-py-rule", "A better title")
    assert rep["refused"] is None and not any("duplicate" in w for w in rep["warnings"])
    assert _line(levels["b/py"], "feedback-py-rule").title == "A better title"
    assert E.render_topics(anchor, dry_run=True)["levels"] == {}


def test_a_real_duplicate_is_still_named_by_rename(tmp_path):
    anchor, levels = _rendered(tmp_path)
    local = sig.claude_local_md_path(levels["b/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    rep = E.rename_entry(anchor, "feedback-plain", "feedback-plain-2")
    assert any("a pre-existing duplicate" in w for w in rep["warnings"])


# ---- what "placed by topic" means: what the renderer manages --------------------------------------

def _bind_raw(anchor, slug, topics):
    """Bind `slug`'s body to `topics` by writing its body, past set-topics' own checks: the
    shapes set-topics refuses to make can still be on disk."""
    path = us.body_path(anchor, slug)
    us.put_body(anchor, slug, E._with_topics(path.read_text(encoding="utf-8"), topics))


def test_a_bound_fact_pinned_at_another_level_still_moves(tmp_path):
    """The renderer leaves alone every line of a fact pinned at any level, so render-topics calls
    its unpinned line kept and offers to move it: move must take it."""
    anchor, levels = _rendered(tmp_path)
    _fact(levels["b"], "feedback-held")
    _bind_raw(anchor, "feedback-held", ("python",))
    us.add_pointer(levels["a/py"], "feedback-held", "T feedback-held", HOOK)
    us.add_pointer(levels["b"], "feedback-held", "T feedback-held", HOOK, pin=True)
    rep = E.move_entry(levels["a/py"], levels["a"], "feedback-held")
    assert rep["moved"] is True and rep["refused"] is None
    assert "feedback-held" in _slugs(levels["a"]) and _line(levels["b"], "feedback-held").pin


def test_a_bound_fact_with_no_title_in_its_body_still_moves(tmp_path):
    """A bound body a line cannot be built from is never rendered: its lines stay where they are,
    render-topics calls them unplaced and offers to move them, so move takes them."""
    anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-untitled")
    path = us.body_path(anchor, "feedback-untitled")
    text = path.read_text(encoding="utf-8")
    untitled = "\n".join(line for line in text.split("\n") if not line.startswith("title:"))
    us.put_body(anchor, "feedback-untitled", E._with_topics(untitled, ("python",)))
    assert E.read_body_topics(path) == ("python",)
    rep = E.move_entry(levels["a/py"], levels["a"], "feedback-untitled")
    assert rep["moved"] is True and rep["refused"] is None


def test_a_set_names_the_first_placed_member_in_the_order_given(tmp_path):
    anchor, levels = _rendered(tmp_path)
    _fact(anchor, "feedback-py-two", ("python",))
    E.render_topics(anchor)
    rep = E.move_entry(levels["a/py"], levels["a"], ["feedback-py-two", "feedback-py-rule"])
    assert rep["refused"].startswith("'feedback-py-two' is placed by topic")


@pytest.mark.parametrize("shape", ["pinned-elsewhere", "untitled"])
def test_add_of_a_bound_fact_the_renderer_does_not_manage_takes_the_path_any_fact_does(tmp_path,
                                                                                       shape):
    """Not placed by topic, so an add from a level without its line is not PlacedElsewhere: it
    takes the path any fact does. From the top, a level of the tree holds its line, so that add is
    SlugOwnedElsewhere and writes nothing; from the level holding the line it is an update."""
    anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-odd")
    if shape == "untitled":
        path = us.body_path(anchor, "feedback-odd")
        text = path.read_text(encoding="utf-8")
        text = "\n".join(line for line in text.split("\n") if not line.startswith("title:"))
        us.put_body(anchor, "feedback-odd", E._with_topics(text, ("python",)))
    else:
        _bind_raw(anchor, "feedback-odd", ("python",))
        us.add_pointer(levels["b"], "feedback-odd", "T feedback-odd", HOOK, pin=True)
    before = _snapshot(anchor)
    with pytest.raises(E.SlugOwnedElsewhere) as exc:
        E.add_or_update_entry(anchor, title="T feedback-odd", hook=HOOK, slug="feedback-odd")
    assert not isinstance(exc.value, E.PlacedElsewhere)
    assert str(levels["a/py"]) in exc.value.levels
    assert _snapshot(anchor) == before
    E.add_or_update_entry(levels["a/py"], title="T feedback-odd", hook=HOOK, slug="feedback-odd")
    assert "feedback-odd" in _slugs(levels["a/py"]) and "feedback-odd" not in _slugs(anchor)
