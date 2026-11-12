"""Tests for `render-topics --scope tree`: a topic-bound fact gets a pointer line at each level
that has one of its topics while no level above it does, lines are added before any is removed,
and a pinned, untagged or unrenderable fact is never touched. All content ASCII.
"""

import json
import os
import re
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

import memory_engine as E
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


def _example(tmp_path):
    """The design's tree: python under a and b, rust at c, nothing at d; one python rule at the top."""
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()), ("c", ("rust",)), ("d", ()))}
    _fact(anchor, "feedback-py-rule", ("python",))
    return anchor, levels


def test_a_python_rule_is_read_under_both_python_levels_and_nowhere_else(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    assert E.main(["render-topics", "--proj", levels["d"], "--scope", "tree"]) == 0
    out = capsys.readouterr().out
    assert "render-topics (tree): 1 managed fact(s); changed 3 level(s)" in out
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule"]
    for rel in ("a", "a/other", "b", "b/other", "c", "d"):
        assert _slugs(levels[rel]) == []
    assert _slugs(anchor) == []
    rendered = sig.claude_local_md_path(levels["a/py"]).read_text(encoding="utf-8")
    assert "- [T feedback-py-rule](mem:feedback-py-rule) - %s\n" % HOOK in rendered


def test_a_second_render_changes_nothing(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    E.render_topics(anchor)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree", "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["levels"] == {} and rep["managed"] == 1 and _snapshot(anchor) == before


def test_a_topic_every_child_has_rolls_up_to_the_parent(tmp_path):
    anchor = _tree(tmp_path)
    parent = _level(anchor, "a", ())
    x1, x2 = _level(anchor, "a/x1", ("python",)), _level(anchor, "a/x2", ("python", "rust"))
    _fact(anchor, "feedback-py-rule", ("python",))
    _fact(anchor, "feedback-rust-rule", ("rust",))
    E.render_topics(anchor)
    assert _slugs(parent) == ["feedback-py-rule"]
    assert (_slugs(x1), _slugs(x2), _slugs(anchor)) == ([], ["feedback-rust-rule"], [])


def test_a_fact_whose_topic_no_level_has_falls_back_to_the_top(tmp_path):
    anchor = _tree(tmp_path)
    inner = _level(anchor, "c", ("rust",))
    _fact(anchor, "feedback-stays", ("git",))
    _fact(inner, "feedback-comes-up", ("git",))
    E.render_topics(anchor)
    assert _slugs(anchor) == ["feedback-comes-up", "feedback-stays"] and _slugs(inner) == []


def test_pinned_untagged_and_unbound_facts_stay_where_they_are(tmp_path):
    anchor, levels = _example(tmp_path)
    _fact(levels["c"], "feedback-untagged")
    _fact(levels["c"], "feedback-universal", ())
    _fact(levels["d"], "feedback-pinned", pin=True)
    pinned_body = us.body_path(anchor, "feedback-pinned")
    us.put_body(anchor, "feedback-pinned", E._with_topics(pinned_body.read_text(encoding="utf-8"), ("python",)))
    kept = {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in ("c", "d")}
    rep = E.render_topics(anchor)
    assert rep["managed"] == 1
    assert {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in ("c", "d")} == kept
    assert "feedback-pinned" not in _slugs(levels["a/py"])


def test_a_tagged_fact_whose_body_renders_no_line_is_reported_and_stays(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    _fact(levels["c"], "feedback-no-title", ("python",))
    path = us.body_path(anchor, "feedback-no-title")
    path.write_text(path.read_text(encoding="utf-8").replace("title: T feedback-no-title\n", ""),
                    encoding="utf-8")
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    out = capsys.readouterr().out
    assert "1 tagged fact(s) have a body without title: or description:" in out
    assert "feedback-no-title" in out and _slugs(levels["c"]) == ["feedback-no-title"]
    assert "feedback-no-title" not in _slugs(levels["a/py"])


def test_a_line_that_says_something_else_than_its_body_is_refreshed(tmp_path):
    anchor, levels = _example(tmp_path)
    E.render_topics(anchor)
    local = sig.claude_local_md_path(levels["b/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers[0].hook = "When this line went stale, it says this."
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    rep = E.render_topics(anchor)
    assert rep["levels"][levels["b/py"]]["refreshed"] == 1
    assert HOOK in local.read_text(encoding="utf-8")


def _recording(calls, fail_at=None):
    def write(path, text):
        if fail_at is not None and str(path) == str(fail_at):
            raise OSError(28, "No space left on device", str(path))
        calls.append(str(path))
        return us.write_if_changed(path, text)
    return write


def test_every_line_is_added_before_any_is_removed(tmp_path):
    anchor, levels = _example(tmp_path)
    calls = []
    E.render_topics(anchor, write=_recording(calls))
    top = str(sig.claude_local_md_path(anchor))
    assert calls[-1] == top and len(calls) == 3
    assert {calls[0], calls[1]} == {str(sig.claude_local_md_path(levels[rel])) for rel in ("a/py", "b/py")}


def test_a_failed_add_leaves_every_old_line(tmp_path):
    anchor, levels = _example(tmp_path)
    calls = []
    with pytest.raises(OSError):
        E.render_topics(anchor, write=_recording(calls, fail_at=sig.claude_local_md_path(levels["b/py"])))
    assert _slugs(anchor) == ["feedback-py-rule"] and _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert _slugs(levels["b/py"]) == []


def test_dry_run_reports_and_writes_nothing_even_with_writes_off(tmp_path, capsys, monkeypatch):
    anchor, levels = _example(tmp_path)
    before = _snapshot(anchor)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree", "--dry-run", "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["dry_run"] is True and rep["levels"][levels["a/py"]]["added"] == 1
    assert rep["levels"][anchor]["removed"] == 1 and _snapshot(anchor) == before
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    assert "! refused" in capsys.readouterr().out and _snapshot(anchor) == before


def test_the_function_itself_refuses_a_real_run_while_writes_are_off(tmp_path, monkeypatch):
    anchor, _levels = _example(tmp_path)
    before = _snapshot(anchor)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        E.render_topics(anchor)
    assert _snapshot(anchor) == before


def test_without_a_topic_list_the_verb_says_so_and_changes_nothing(tmp_path, capsys):
    anchor = _tree(tmp_path, with_list=False)
    _fact(anchor, "feedback-a")
    before = _snapshot(anchor)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert "no topic list in this tree" in capsys.readouterr().out
    assert _snapshot(anchor) == before and E.render_topics(anchor) == {"list": False}


def test_a_level_topics_line_that_does_not_parse_refuses_the_render_before_any_write(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    local = sig.claude_local_md_path(levels["c"])
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, SCOPE + "\nTOPICS: Not A Tag", []), encoding="utf-8")
    before = _snapshot(anchor)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and levels["c"] in out and _snapshot(anchor) == before


def test_a_tree_top_without_a_pointer_block_refuses_the_render(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    _level(str(anchor), "a", ("python",))
    with pytest.raises(E.TopicRefusal) as exc:
        E.render_topics(str(anchor))
    assert "has no pointer block" in str(exc.value)


def _plant_bodies(anchor, count, prose=200_000, description="d", tagged_every=10):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    filler = "x" * prose
    for i in range(count):
        topics = "topics: [python]\n" if i % tagged_every == 0 else ""
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: %s\ntitle: T\n%smetadata:\n  type: feedback\n"
            "---\n\n%s\n" % (i, description, topics, filler), encoding="utf-8")


def test_the_lines_of_one_level_are_capped_and_the_refusal_drops_nothing(tmp_path, capsys):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _fact(anchor, "feedback-py-rule", ("python",))
    _plant_bodies(anchor, 1200, prose=1, description="y" * 1000, tagged_every=1)
    before = _snapshot(anchor)
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(anchor)
    assert exc.value.level == level and exc.value.size > E.MAX_RENDER_BLOCK_BYTES
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    assert "! refused" in capsys.readouterr().out and _snapshot(anchor) == before


def _plant_tagged(anchor, prefix, topic, count, description):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (facts / ("feedback-%s%05d.md" % (prefix, i))).write_text(
            "---\nname: feedback-%s%05d\ndescription: %s\ntitle: T\ntopics: [%s]\nmetadata:\n"
            "  type: feedback\n---\n\nx\n" % (prefix, i, description, topic), encoding="utf-8")


def test_a_level_past_the_cap_refuses_before_an_earlier_level_is_written(tmp_path, capsys):
    """The levels are added top first, then by path: `a` fits and comes before `b`, which does
    not. The refusal must still leave every file as it was, `a` included."""
    anchor = _tree(tmp_path)
    first = _level(anchor, "a", ("python",))
    _level(anchor, "b", ("rust",))
    _plant_tagged(anchor, "py", "python", 2, "fits")
    _plant_tagged(anchor, "rs", "rust", 1200, "y" * 1000)
    before = _snapshot(anchor)
    calls = []
    with pytest.raises(E.RenderBlockTooLarge):
        E.render_topics(anchor, write=_recording(calls))
    assert calls == [] and _snapshot(anchor) == before and _slugs(first) == []
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    assert "! refused" in capsys.readouterr().out and _snapshot(anchor) == before


def test_a_body_that_grows_after_the_census_still_cannot_pass_the_cap(tmp_path):
    """Another writer grows the rust bodies while the render writes `a`: the census saw them fit,
    so the ADD pass's own check is what keeps `b`'s lines bounded. Nothing is dropped."""
    anchor = _tree(tmp_path)
    first, second = _level(anchor, "a", ("python",)), _level(anchor, "b", ("rust",))
    _fact(anchor, "feedback-stays-at-top", ("git",))
    _plant_tagged(anchor, "py", "python", 2, "fits")
    _plant_tagged(anchor, "rs", "rust", 1200, "short")
    top_before = sig.claude_local_md_path(anchor).read_bytes()
    second_before = sig.claude_local_md_path(second).read_bytes()
    calls = []

    def write(path, text):
        calls.append(str(path))
        _plant_tagged(anchor, "rs", "rust", 1200, "y" * 1000)
        return us.write_if_changed(path, text)

    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(anchor, write=write)
    assert exc.value.level == second and calls == [str(sig.claude_local_md_path(first))]
    assert sig.claude_local_md_path(second).read_bytes() == second_before
    assert sig.claude_local_md_path(anchor).read_bytes() == top_before


def test_the_route_the_missing_top_block_refusal_names_repairs_it(tmp_path, capsys):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    level = _level(str(anchor), "a", ("python",))
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", str(anchor), "--scope", "tree"]) == 2
    assert "ensure-memory-structure writes one" in capsys.readouterr().out
    assert E.main(["ensure-memory-structure", "--proj", str(anchor)]) == 0
    _fact(str(anchor), "feedback-py-rule", ("python",))
    assert E.main(["render-topics", "--proj", str(anchor), "--scope", "tree"]) == 0
    assert _slugs(level) == ["feedback-py-rule"] and _slugs(str(anchor)) == []


def test_the_route_the_block_cap_refusal_names_repairs_it(tmp_path, capsys):
    """The refusal names a set-topics batch: run it as the message gives it, from a directory
    outside the tree, and the next render goes through. The facts' lines sit at an untagged level
    `z`, so the batch has a level pointing at every slug it rebinds."""
    anchor = _tree(tmp_path)
    level, holder = _level(anchor, "a", ("python",)), _level(anchor, "z", ())
    slugs = ["feedback-py%05d" % i for i in range(1200)]
    _plant_tagged(anchor, "py", "python", len(slugs), "y" * 1000)
    local = sig.claude_local_md_path(holder)
    text = local.read_text(encoding="utf-8")
    pointers = [us.Pointer(slug=slug, title="T", hook="h") for slug in slugs]
    local.write_text(us.upsert_pointer_block(text, us.parse_pointer_index(text)[0], pointers),
                     encoding="utf-8")
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    out = capsys.readouterr().out
    route = re.search(r"(hooks/memory_engine\.py) (set-topics --proj \S+ --batch) <file>", out)
    assert route is not None and "a topic this level has (python)" in out
    assert "move --from-level" not in out
    assert route.group(2).split()[2] == level
    batch = tmp_path / "rebind.jsonl"
    batch.write_text("".join(json.dumps({"slug": slug, "topics": []}) + "\n" for slug in slugs),
                     encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    engine = Path(E.__file__).resolve().parents[1] / route.group(1)
    done = subprocess.run([sys.executable, str(engine), *route.group(2).split(), str(batch)],
                          cwd=str(outside), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert _slugs(level) == [] and _slugs(holder) == slugs


def _keep_lines(level, count):
    """Give `level` `count` lines of about 1 KB the render keeps: every other one pinned, the rest
    pointing at no body, so neither kind is a managed line."""
    kept = [us.Pointer(slug="feedback-kept%05d" % i, title="T", hook="k" * 1000, pin=i % 2 == 0)
            for i in range(count)]
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, us.parse_pointer_index(text)[0], kept),
                     encoding="utf-8")


def test_the_block_cap_counts_the_lines_a_level_keeps_beside_the_rendered_ones(tmp_path):
    """Pinned and unmanaged lines stay in the block through the ADD phase, so they count against
    the cap with the lines the render builds: either part alone fits, both together do not. The
    census refuses before `a`, ahead of `b` in the ADD order, is written."""
    anchor = _tree(tmp_path)
    first, second = _level(anchor, "a", ("python",)), _level(anchor, "b", ("rust",))
    _keep_lines(second, 600)
    _plant_tagged(anchor, "py", "python", 2, "fits")
    _plant_tagged(anchor, "rs", "rust", 600, "y" * 1000)
    before, calls = _snapshot(anchor), []
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(anchor, write=_recording(calls))
    assert exc.value.level == second and calls == [] and _snapshot(anchor) == before
    assert _slugs(first) == []


def test_lines_a_level_gains_after_the_census_still_count_against_the_cap(tmp_path):
    """Another writer fills `b`'s block while the render writes `a`: the census saw `b` fit, so
    the ADD pass must count the kept lines again before it writes `b`."""
    anchor = _tree(tmp_path)
    first, second = _level(anchor, "a", ("python",)), _level(anchor, "b", ("rust",))
    _plant_tagged(anchor, "py", "python", 2, "fits")
    _plant_tagged(anchor, "rs", "rust", 600, "y" * 1000)
    calls = []

    def write(path, text):
        calls.append(str(path))
        _keep_lines(second, 600)
        return us.write_if_changed(path, text)

    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(anchor, write=write)
    assert exc.value.level == second and calls == [str(sig.claude_local_md_path(first))]
    assert not any(slug.startswith("feedback-rs") for slug in _slugs(second))
    # the 600 kept lines are the larger part, so the route moves them; rebinding cannot help
    assert exc.value.kept >= exc.value.added > 0 and "move --from-level" in str(exc.value)


def _hold_lines(level, slugs, hook):
    """Append an unpinned line per slug to `level`'s block, each carrying `hook`."""
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers += [us.Pointer(slug=slug, title="T", hook=hook) for slug in slugs]
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def test_lines_this_render_moves_away_do_not_count_against_the_level_they_leave(tmp_path):
    """`b` still holds about 1.1 MB of python lines from before python moved to `z`. This render
    adds them to `z` and drops them from `b`, so they do not count against `b`'s cap when `b`
    gains its one rust line: the render goes through."""
    anchor = _tree(tmp_path)
    old, new = _level(anchor, "b", ("rust",)), _level(anchor, "z", ("python",))
    slugs = ["feedback-py%05d" % i for i in range(1100)]
    _plant_tagged(anchor, "py", "python", len(slugs), "short")
    _hold_lines(old, slugs, "y" * 1000)
    assert sig.claude_local_md_path(old).stat().st_size > E.MAX_RENDER_BLOCK_BYTES
    _fact(anchor, "feedback-rs-rule", ("rust",))
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert _slugs(new) == slugs and _slugs(old) == ["feedback-rs-rule"] and _slugs(anchor) == []


def test_a_line_already_where_the_render_places_it_counts_once(tmp_path):
    """About 730 KB of python lines already sit at `a`, where the render places them: the body's
    own line replaces each, so a re-render counts them once and goes through. Counted twice they
    would come to about 1.5 MB, past the cap."""
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _plant_tagged(anchor, "py", "python", 700, "y" * 1000)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert len(_slugs(level)) == 700
    before = _snapshot(anchor)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert _snapshot(anchor) == before


def _keep_three_kinds(anchor, level, count):
    """`count` lines of about 1 KB at `level` that no render places, a third of each kind:
    pinned, pointing at no body, and the line of an untagged fact. Returns their slugs."""
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    kept = []
    for i in range(count):
        slug = "feedback-kept%05d" % i
        if i % 3 == 2:
            (facts / (slug + ".md")).write_text(
                "---\nname: %s\ndescription: d\ntitle: T\nmetadata:\n  type: feedback\n---\n\nx\n"
                % slug, encoding="utf-8")
        kept.append(us.Pointer(slug=slug, title="T", hook="k" * 1000, pin=i % 3 == 0))
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, us.parse_pointer_index(text)[0], kept),
                     encoding="utf-8")
    return [p.slug for p in kept]


def _line_bytes(level):
    """{slug: bytes} of the lines in `level`'s block, each counting its line break."""
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return {p.slug: len(p.index_line().encode("utf-8")) + 1
            for p in us.parse_pointer_index(text)[1]}


def test_kept_lines_that_fill_the_block_are_refused_with_a_route_that_moves_them(tmp_path, capsys):
    """`b` keeps about 1.1 MB of lines no render places; three rust lines are to be added there.
    No rebinding can help, so the refusal names the kept bytes, how many bytes must leave the
    block, and a move route: run it as given, from a directory outside the tree, for kept lines
    totalling one line short of that figure and the render still refuses; add that one line and
    it goes through. The figure is the whole overflow, every rust line counted, not the overflow
    when the first one passed the cap. Each kind of kept line counts: without any one third the
    block would fit."""
    anchor = _tree(tmp_path)
    level = _level(anchor, "b", ("rust",))
    kept = _keep_three_kinds(anchor, level, 1100)
    rust = ["feedback-rs-rule%d" % i for i in range(3)]
    for slug in rust:
        _fact(anchor, slug, ("rust",))
    kept_bytes = _line_bytes(level)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    out = capsys.readouterr().out
    assert _snapshot(anchor) == before
    said = re.search(r"(\d+) bytes of pinned, legacy or unplaced lines stay at (\S+) and (\d+) "
                     r"bytes of lines placed there are to be added, (\d+) bytes over", out)
    assert said is not None and said.group(2) == level, out
    assert int(said.group(1)) == sum(kept_bytes.values()) > E.MAX_RENDER_BLOCK_BYTES
    assert E.MAX_RENDER_BLOCK_BYTES > int(said.group(3)) > 0
    over = re.search(r"Move kept lines totalling at least (\d+) bytes", out)
    assert over is not None and int(over.group(1)) == int(said.group(4)), out
    assert "set-topics" not in out
    assert "the level they go to is held to the same %d bytes" % E.MAX_RENDER_BLOCK_BYTES in out
    route = re.search(r"(hooks/memory_engine\.py) (move --from-level \S+ --to-level) <level> "
                      r"--slug <slug>", out)
    assert route is not None and route.group(2).split()[2] == level, out
    # the shortest run of kept lines that reaches the figure, then everything but its last line
    need, moved, total = int(over.group(1)), [], 0
    for slug in kept:
        moved.append(slug)
        total += kept_bytes[slug]
        if total >= need:
            break
    assert total - kept_bytes[moved[-1]] < need <= total and len(moved) < len(kept)
    outside = tmp_path / "outside"
    outside.mkdir()
    engine = Path(E.__file__).resolve().parents[1] / route.group(1)

    def move(slugs):
        done = subprocess.run([sys.executable, str(engine), *route.group(2).split(), anchor,
                               "--slug", *slugs],
                              cwd=str(outside), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False)
        assert done.returncode == 0, done.stdout + done.stderr

    move(moved[:-1])
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    short = re.search(r"stay at (\S+) and \d+ bytes of lines placed there are to be added, "
                      r"(\d+) bytes over", capsys.readouterr().out)
    assert short is not None and short.group(1) == level
    assert int(short.group(2)) == need - (total - kept_bytes[moved[-1]]) > 0
    move(moved[-1:])
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    placed = _line_bytes(level)
    # the real overflow, from the block the render left: what stayed plus what it placed
    real = (sum(kept_bytes.values()) + sum(placed[slug] for slug in rust)
            - E.MAX_RENDER_BLOCK_BYTES)
    assert need == real and int(said.group(3)) == sum(placed[slug] for slug in rust)
    assert _slugs(level) == sorted([s for s in kept if s not in moved] + rust)
    assert _slugs(anchor) == moved


def test_the_tagged_facts_without_a_title_are_all_counted_and_the_first_few_shown(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a", ("python",))
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    names = {"feedback-untitled%03d" % i for i in range(25)}
    for name in names:
        (facts / (name + ".md")).write_text(
            "---\nname: %s\ndescription: d\ntopics: [python]\nmetadata:\n  type: feedback\n"
            "---\n\nx\n" % name, encoding="utf-8")
    rep = E.render_topics(anchor)
    assert rep["incomplete_total"] == 25 and len(rep["incomplete"]) == 20
    assert set(rep["incomplete"]) <= names


def test_a_level_counts_every_added_line_and_shows_only_the_first_few(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _plant_tagged(anchor, "py", "python", 25, "d")
    row = E.render_topics(anchor)["levels"][level]
    assert row["added"] == 25 == len(_slugs(level))
    assert row["examples"]["added"] == ["feedback-py%05d" % i for i in range(20)]


def test_the_placement_cache_never_holds_more_topic_sets_than_its_cap(tmp_path):
    """Read through the placer's own count, with the tree's real LevelMap: 513 and more distinct
    topic sets leave at most 512 remembered, and every answer still matches the map's."""
    anchor, _levels = _example(tmp_path)
    level_map, _dirs = E.topic_level_map(anchor)
    place = E._Placer(level_map)
    for i in range(E._PLACEMENT_CACHE * 2 + 1):
        topics = ("t%04d" % i,)
        assert place(topics) == frozenset(level_map.placements(topics))
        assert place.remembered() <= E._PLACEMENT_CACHE
    assert place(("python",)) == frozenset(level_map.placements(("python",)))


def _render_peak(tmp_path, name, count):
    anchor = _tree(tmp_path / name)
    level = _level(anchor, "a", ("python",))
    _plant_bodies(anchor, count)
    tracemalloc.start()
    try:
        E.render_topics(anchor)
        return len(_slugs(level)), tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_render_holds_no_body_and_its_peak_does_not_grow_with_the_store(tmp_path):
    (tmp_path / "small").mkdir()
    (tmp_path / "large").mkdir()
    placed_small, peak_small = _render_peak(tmp_path, "small", 30)
    placed_large, peak_large = _render_peak(tmp_path, "large", 300)
    # a tagged body no level points at yet still gets its lines
    assert (placed_small, placed_large) == (3, 30)
    assert peak_large < 400_000                # two bodies of 200 KB would already pass this
    assert peak_large < peak_small * 2 + 100_000


def test_an_unknown_scope_is_a_usage_error(tmp_path, capsys):
    anchor = _tree(tmp_path)
    with pytest.raises(SystemExit) as exc:
        E.main(["render-topics", "--proj", anchor, "--scope", "sideways"])
    assert exc.value.code == 2
    with pytest.raises(ValueError):
        E.render_topics(anchor, scope="sideways")
