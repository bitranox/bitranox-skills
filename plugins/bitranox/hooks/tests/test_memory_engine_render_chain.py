"""Tests for `render-topics --scope chain` (the nap's render: only the levels from a directory up
to the tree top are read for their lines or written) and for what `set-topics` does with the
lines of a fact it un-binds. All content ASCII.
"""

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


def _two_python_levels(tmp_path):
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()))}
    return anchor, levels


def _recording(calls, fail_at=None):
    def write(path, text):
        if fail_at is not None and str(path) == str(fail_at):
            raise OSError(28, "No space left on device", str(path))
        calls.append(str(path))
        return us.write_if_changed(path, text)
    return write


def _local(level):
    return str(sig.claude_local_md_path(level))


def _hold_lines(level, pointers):
    """Append `pointers` to `level`'s block as they are."""
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, held = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(text, scope, held + list(pointers)), encoding="utf-8")


def _plant_tagged(anchor, prefix, topic, count, description):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    slugs = []
    for i in range(count):
        slug = "feedback-%s%05d" % (prefix, i)
        (facts / (slug + ".md")).write_text(
            "---\nname: %s\ndescription: %s\ntitle: T\ntopics: [%s]\nmetadata:\n"
            "  type: feedback\n---\n\nx\n" % (slug, description, topic), encoding="utf-8")
        slugs.append(slug)
    return slugs


def _line_bytes(level):
    """{slug: bytes} of the lines in `level`'s block, each counting its line break."""
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return {p.slug: len(p.index_line().encode("utf-8")) + 1
            for p in us.parse_pointer_index(text)[1]}


def _engine_route(out, pattern):
    """(engine script path, argv words) of the route a refusal names, matched by `pattern`
    whose group 1 is the script's repo-relative path and group 2 the words after it."""
    route = re.search(pattern, out)
    assert route is not None, out
    return Path(E.__file__).resolve().parents[1] / route.group(1), route.group(2).split()


def _run_outside(tmp_path, argv):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    done = subprocess.run([sys.executable, *argv], cwd=str(outside), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False)
    assert done.returncode == 0, done.stdout + done.stderr


# ---- render-topics --scope chain ---------------------------------------------------------------

def test_a_chain_render_writes_only_its_own_levels(tmp_path, capsys):
    _anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/other"], "feedback-py-rule", ("python",))
    siblings = {rel: sig.claude_local_md_path(levels[rel]).read_bytes()
                for rel in ("a/other", "b", "b/py", "b/other")}
    assert E.main(["render-topics", "--proj", levels["a/py"], "--scope", "chain"]) == 0
    assert "render-topics (chain): 1 managed fact(s); changed 1 level(s)" in capsys.readouterr().out
    assert _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in siblings} == siblings
    calls = []
    E.render_topics(levels["b/py"], scope="chain", write=_recording(calls))
    assert calls == [_local(levels["b/py"])]


def test_a_chain_render_from_a_dir_that_is_no_level_renders_the_levels_above_it(tmp_path):
    _anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/other"], "feedback-py-rule", ("python",))
    inner = Path(levels["a/py"], "src", "pkg")
    inner.mkdir(parents=True)
    calls = []
    E.render_topics(str(inner), scope="chain", write=_recording(calls))
    assert calls == [_local(levels["a/py"])] and _slugs(levels["a/py"]) == ["feedback-py-rule"]


def test_a_line_a_level_above_holds_is_not_repeated_below(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    rep = E.render_topics(levels["a/py"], scope="chain")
    # the top still holds the line, so the chain reads it already; the tree render moves it
    assert rep["levels"] == {} and _slugs(levels["a/py"]) == [] and _slugs(anchor) == ["feedback-py-rule"]


def test_a_chain_render_never_drops_a_line_for_being_placed_elsewhere(tmp_path):
    _anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a"], "feedback-py-rule", ("python",))
    E.render_topics(levels["a/other"], scope="chain")
    assert _slugs(levels["a"]) == ["feedback-py-rule"]


def test_a_copy_below_a_level_that_now_holds_the_line_is_dropped(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule"]
    E.set_level_topics(levels["a"], ("python",))           # a itself is about python now
    other_subtree = sig.claude_local_md_path(levels["b/py"]).read_bytes()
    calls = []
    rep = E.render_topics(levels["a/py"], scope="chain", write=_recording(calls))
    assert calls == [_local(levels["a"]), _local(levels["a/py"])]      # the add, then the drop
    assert _slugs(levels["a"]) == ["feedback-py-rule"] and _slugs(levels["a/py"]) == []
    assert rep["levels"][levels["a/py"]]["removed"] == 1
    assert sig.claude_local_md_path(levels["b/py"]).read_bytes() == other_subtree


def test_a_failed_chain_add_drops_nothing(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    E.set_level_topics(levels["a"], ("python",))
    with pytest.raises(OSError):
        E.render_topics(levels["a/py"], scope="chain",
                        write=_recording([], fail_at=sig.claude_local_md_path(levels["a"])))
    assert _slugs(levels["a/py"]) == ["feedback-py-rule"] and _slugs(levels["a"]) == []


def test_a_pinned_or_untagged_copy_below_is_left_alone(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-plain")
    _fact(anchor, "feedback-pinned", pin=True)
    local = sig.claude_local_md_path(levels["a/py"])
    _hold_lines(levels["a/py"], [us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK),
                                 us.Pointer(slug="feedback-pinned", title="T feedback-pinned", hook=HOOK)])
    before = local.read_bytes()
    E.render_topics(levels["a/py"], scope="chain")
    assert local.read_bytes() == before


def test_a_chain_dry_run_writes_nothing_and_reports_its_drops(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/other"], "feedback-py-rule", ("python",))
    before = _snapshot(anchor)
    rep = E.render_topics(levels["a/py"], scope="chain", dry_run=True)
    assert rep["levels"][levels["a/py"]]["added"] == 1 and _snapshot(anchor) == before
    # the drop a real run would make below a level that only gains the line in this run
    _fact(anchor, "feedback-py-two", ("python",))
    E.render_topics(anchor)
    assert _slugs(levels["a/py"]) == ["feedback-py-rule", "feedback-py-two"]
    E.set_level_topics(levels["a"], ("python",))
    before = _snapshot(anchor)
    rep = E.render_topics(levels["a/py"], scope="chain", dry_run=True)
    assert rep["levels"][levels["a"]]["added"] == 2
    assert rep["levels"][levels["a/py"]]["removed"] == 2 and _snapshot(anchor) == before


def _bound(anchor, slugs):
    """{topics: count} of the bodies of `slugs`: which topics each is bound to now."""
    seen = {}
    for slug in slugs:
        topics = E.read_body_topics(us.body_path(anchor, slug))
        seen[topics] = seen.get(topics, 0) + 1
    return seen


def _sweep_route(out):
    """(engine, argv words) of the tree-scope render a refusal names."""
    return _engine_route(out, r"(hooks/memory_engine\.py) (render-topics --proj \S+ --scope tree)")


def _no_sweep_route(out):
    return re.search(r"render-topics --proj \S+ --scope tree", out) is None


def test_lines_placed_elsewhere_that_overfill_a_chain_level_are_refused_with_the_tree_sweep(
        tmp_path, capsys):
    """`a` fits and is written before `a/py` in the chain's order; `a/py` keeps lines of rust
    facts placed at `b`, off the chain, which a chain render never drops, so they count with the
    python lines it would add there (those sit at `c`, also placed elsewhere). Without the rust
    lines the block fits, so the refusal blames neither the python facts nor a kept line: it
    names the tree-scope render, the one render that drops a line placed elsewhere, and nothing
    is written first. Run as given from outside the tree, then the chain goes through, and no
    fact was un-bound on the way."""
    anchor = _tree(tmp_path)
    upper, level = _level(anchor, "a", ("git",)), _level(anchor, "a/py", ("python",))
    rust_level, side = _level(anchor, "b", ("rust",)), _level(anchor, "c")
    git = _plant_tagged(anchor, "git", "git", 2, "fits")
    rust = _plant_tagged(anchor, "rs", "rust", 700, "y" * 1000)
    _hold_lines(level, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in rust])
    python = _plant_tagged(anchor, "py", "python", 500, "y" * 1000)
    _hold_lines(side, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in python])
    before, calls = _snapshot(anchor), []
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and _snapshot(anchor) == before
    assert "move --from-level" not in out and "set-topics" not in out, out
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(level, scope="chain", write=_recording(calls))
    assert exc.value.level == level and calls == [] and _snapshot(anchor) == before
    assert exc.value.stale == sum(_line_bytes(level).values()) > 0 == exc.value.kept
    assert exc.value.need <= 0 < exc.value.over and exc.value.added > 0
    assert "%d bytes of lines placed by topic at another level stay at %s" % (
        exc.value.stale, level) in out
    engine, words = _sweep_route(out)
    assert words[2] == anchor
    _run_outside(tmp_path, [str(engine), *words])
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 0
    assert _slugs(level) == python and _slugs(rust_level) == rust and _slugs(upper) == git
    assert _slugs(side) == []
    assert _bound(anchor, python) == {("python",): 500} and _bound(anchor, rust) == {("rust",): 700}


def _kept_lines(count):
    """`count` lines of about 1 KB that no render places: they point at no body."""
    return [us.Pointer(slug="feedback-kept%05d" % i, title="T", hook="k" * 1000)
            for i in range(count)]


def _shortest_run(slugs, sizes, need):
    """The first slugs of `slugs` whose `sizes` reach `need` bytes."""
    run, total = [], 0
    for slug in slugs:
        if total >= need:
            break
        run.append(slug)
        total += sizes[slug]
    assert total >= need
    return run


def test_kept_lines_that_overfill_a_chain_level_are_refused_with_a_move_of_them(tmp_path, capsys):
    """`a/py` keeps about 720 KB of lines no render places; about 515 KB of python lines are to
    be added there. Nothing there is placed elsewhere and the kept lines are the larger part, so
    the route moves kept lines, at least the bytes the block is over. Run as given from outside
    the tree, for the shortest run of kept lines reaching that figure, the chain goes through."""
    anchor = _tree(tmp_path)
    level = _level(anchor, "a/py", ("python",))
    kept = _kept_lines(700)
    _hold_lines(level, kept)
    python = _plant_tagged(anchor, "py", "python", 500, "y" * 1000)
    sizes = _line_bytes(level)
    before = _snapshot(anchor)
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(level, scope="chain")
    assert exc.value.stale == 0 and exc.value.kept == sum(sizes.values()) >= exc.value.added > 0
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 2
    out = capsys.readouterr().out
    assert _snapshot(anchor) == before and "set-topics" not in out and _no_sweep_route(out), out
    need = re.search(r"Move kept lines totalling at least (\d+) bytes", out)
    assert need is not None and int(need.group(1)) == exc.value.over == exc.value.need, out
    engine, words = _engine_route(out, r"(hooks/memory_engine\.py) (move --from-level \S+ "
                                       r"--to-level) <level> --slug <slug>")
    assert words[2] == level
    moved = _shortest_run([p.slug for p in kept], sizes, int(need.group(1)))
    _run_outside(tmp_path, [str(engine), *words, anchor, "--slug", *moved])
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 0
    assert _slugs(level) == sorted(python + [p.slug for p in kept[len(moved):]])
    assert _slugs(anchor) == moved


def test_kept_and_placed_lines_that_overfill_a_chain_level_beside_stale_ones_name_a_rebind(
        tmp_path, capsys):
    """`a/py` keeps about 465 KB of lines no render places and about 620 KB of rust lines placed
    at `b`; about 620 KB of python lines are to be added there. Even without the rust lines the
    block is over, so the tree-scope render would refuse here too: the route rebinds python
    facts (the lines placed there are larger than the kept ones), the bytes over WITHOUT the rust
    lines, and never offers a move for a line placed by topic. Run as given from outside the
    tree, the next refusal names the tree-scope render; run that, and the chain goes through."""
    anchor = _tree(tmp_path)
    level = _level(anchor, "a/py", ("python",))
    rust_level, side = _level(anchor, "b", ("rust",)), _level(anchor, "c")
    kept = _kept_lines(450)
    _hold_lines(level, kept)
    rust = _plant_tagged(anchor, "rs", "rust", 600, "y" * 1000)
    _hold_lines(level, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in rust])
    python = _plant_tagged(anchor, "py", "python", 600, "y" * 1000)
    _hold_lines(side, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in python])
    sizes = _line_bytes(level)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 2
    out = capsys.readouterr().out
    assert _snapshot(anchor) == before and "move --from-level" not in out and _no_sweep_route(out)
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(level, scope="chain")
    assert exc.value.kept == sum(sizes[p.slug] for p in kept) < exc.value.added
    assert exc.value.stale == sum(sizes[slug] for slug in rust) and exc.value.need > 0
    assert exc.value.kept + exc.value.stale >= exc.value.added    # stale lines are no move's
    assert "%d bytes of lines placed by topic at another level" % exc.value.stale in out, out
    need = re.search(r"at least (\d+) bytes of their lines", out)
    assert need is not None and int(need.group(1)) == exc.value.need, out
    engine, words = _engine_route(out, r"(hooks/memory_engine\.py) (set-topics --proj \S+) "
                                       r"--batch <file>")
    assert words[2] == level
    lines = {slug: len(us.Pointer(slug=slug, title="T", hook="y" * 1000).index_line()) + 1
             for slug in python}
    unbound = _shortest_run(python, lines, int(need.group(1)))
    batch = tmp_path / "batch.jsonl"
    batch.write_text("".join('{"slug": "%s", "topics": []}\n' % slug for slug in unbound),
                     encoding="utf-8")
    _run_outside(tmp_path, [str(engine), *words, "--batch", str(batch)])
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 2
    out = capsys.readouterr().out
    assert "move --from-level" not in out and "set-topics" not in out, out
    engine, words = _sweep_route(out)
    _run_outside(tmp_path, [str(engine), *words])
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 0
    bound = python[len(unbound):]
    assert _slugs(level) == sorted([p.slug for p in kept] + bound)
    assert _slugs(rust_level) == rust and _slugs(side) == unbound
    assert _bound(anchor, bound) == {("python",): len(bound)}
    assert _bound(anchor, unbound) == {(): len(unbound)}


def test_lines_a_level_above_holds_do_not_count_where_the_chain_drops_them(tmp_path):
    """`a/py` still holds about 600 KB of rust lines from before `a` was about rust. The chain
    gives them to `a` and drops them from `a/py`, so they do not count against `a/py` when it
    gains about 600 KB of python lines: the render goes through."""
    anchor = _tree(tmp_path)
    upper, level = _level(anchor, "a", ()), _level(anchor, "a/py", ("python",))
    rust = _plant_tagged(anchor, "rs", "rust", 600, "y" * 1000)
    _hold_lines(level, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in rust])
    E.set_level_topics(upper, ("rust",))
    python = _plant_tagged(anchor, "py", "python", 600, "y" * 1000)
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 0
    assert _slugs(upper) == rust and _slugs(level) == python


def test_lines_the_top_still_holds_are_not_counted_where_the_chain_does_not_add_them(tmp_path):
    """The top holds about 600 KB of python lines from before the tree render moved them; a chain
    render reads them there and adds none of them at `a/py`, so only the 600 KB of new python
    lines count against `a/py`: the render goes through and the old lines stay at the top."""
    anchor = _tree(tmp_path)
    level = _level(anchor, "a/py", ("python",))
    old = _plant_tagged(anchor, "old", "python", 600, "y" * 1000)
    _hold_lines(anchor, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in old])
    new = _plant_tagged(anchor, "new", "python", 600, "y" * 1000)
    assert E.main(["render-topics", "--proj", level, "--scope", "chain"]) == 0
    assert _slugs(level) == new and _slugs(anchor) == old


def test_lines_a_chain_level_gains_after_the_census_still_count(tmp_path):
    """Another writer fills `a/py` while the chain writes `a`: the census saw `a/py` fit, so the
    ADD pass counts its kept lines again before it writes `a/py`. Nothing is dropped."""
    anchor = _tree(tmp_path)
    upper, level = _level(anchor, "a", ("git",)), _level(anchor, "a/py", ("python",))
    _plant_tagged(anchor, "git", "git", 2, "fits")
    _plant_tagged(anchor, "py", "python", 600, "y" * 1000)
    calls = []

    def write(path, text):
        calls.append(str(path))
        _hold_lines(level, [us.Pointer(slug="feedback-kept%05d" % i, title="T", hook="k" * 1000,
                                       pin=True) for i in range(600)])
        return us.write_if_changed(path, text)

    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(level, scope="chain", write=write)
    assert exc.value.level == level and calls == [_local(upper)]
    assert not any(slug.startswith("feedback-py") for slug in _slugs(level))


def test_lines_placed_elsewhere_a_chain_level_gains_after_the_census_still_count(tmp_path):
    """Another writer gives `a/py` about 720 KB of lines of rust facts placed at `b` while the
    chain writes `a`: the census saw `a/py` fit, so the ADD pass counts them again before it
    writes `a/py`, as lines placed elsewhere, and its refusal names the tree-scope render, not a
    move of them. Nothing is dropped."""
    anchor = _tree(tmp_path)
    upper, level = _level(anchor, "a", ("git",)), _level(anchor, "a/py", ("python",))
    _level(anchor, "b", ("rust",))
    _plant_tagged(anchor, "git", "git", 2, "fits")
    rust = _plant_tagged(anchor, "rs", "rust", 700, "y" * 1000)
    _plant_tagged(anchor, "py", "python", 500, "y" * 1000)
    calls = []

    def write(path, text):
        calls.append(str(path))
        _hold_lines(level, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in rust])
        return us.write_if_changed(path, text)

    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(level, scope="chain", write=write)
    assert exc.value.level == level and calls == [_local(upper)]
    assert exc.value.stale == sum(_line_bytes(level).values()) > 0 == exc.value.kept
    assert exc.value.added > 0 and exc.value.need <= 0 < exc.value.over
    said = str(exc.value)
    assert "render-topics --proj %s --scope tree" % anchor in said and "move --from-level" not in said
    assert _slugs(level) == rust


def _chain_peak(tmp_path, name, count):
    anchor = _tree(tmp_path / name)
    level = _level(anchor, "a", ("python",))
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        topics = "topics: [python]\n" if i % 10 == 0 else ""
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\n%smetadata:\n  type: feedback\n"
            "---\n\n%s\n" % (i, topics, "x" * 200_000), encoding="utf-8")
    tracemalloc.start()
    try:
        E.render_topics(level, scope="chain")
        return len(_slugs(level)), tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_chain_render_holds_no_body_and_its_peak_does_not_grow_with_the_store(tmp_path):
    (tmp_path / "small").mkdir()
    (tmp_path / "large").mkdir()
    placed_small, peak_small = _chain_peak(tmp_path, "small", 30)
    placed_large, peak_large = _chain_peak(tmp_path, "large", 300)
    assert (placed_small, placed_large) == (3, 30)
    assert peak_large < 400_000                # two bodies of 200 KB would already pass this
    assert peak_large < peak_small * 2 + 100_000


# ---- set-topics: a fact that is un-bound keeps one line -----------------------------------------

@pytest.mark.parametrize("how", ["--universal", "--clear"])
def test_un_binding_a_fact_with_several_lines_leaves_one_at_the_top(tmp_path, capsys, how):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    capsys.readouterr()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", how]) == 0
    assert ("1 un-bound fact(s) had a line at several levels; each now has one line, at the tree "
            "top: feedback-py-rule") in capsys.readouterr().out
    assert _slugs(anchor) == ["feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []
    assert HOOK in sig.claude_local_md_path(anchor).read_text(encoding="utf-8")


def test_the_top_line_is_written_before_the_others_are_dropped(tmp_path):
    """A level that cannot be written stops the collapse at its first drop: the top already holds
    the line, the body is still bound, and running the same call again finishes the collapse."""
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    calls = []
    with pytest.raises(OSError):
        E.set_fact_topics(anchor, {"feedback-py-rule": ()},
                          write=_recording(calls, fail_at=sig.claude_local_md_path(levels["a/py"])))
    assert calls == [_local(anchor)]
    assert _slugs(anchor) == ["feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule"]
    assert E.read_body_topics(us.body_path(anchor, "feedback-py-rule")) == ("python",)
    rep = E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert rep["collapsed"] == ["feedback-py-rule"] and rep["set"] == ["feedback-py-rule"]
    assert _slugs(anchor) == ["feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []


def test_un_binding_a_fact_with_one_line_leaves_it_where_it_is(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/py"], "feedback-py-rule", ("python",))
    rep = E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert rep["collapsed"] == [] and _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert _slugs(anchor) == []


def test_a_never_bound_duplicate_is_not_collapsed(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/py"], "feedback-plain")
    _hold_lines(levels["b/py"], [us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK)])
    rep = E.set_fact_topics(anchor, {"feedback-plain": ()})
    assert rep["collapsed"] == [] and _slugs(levels["b/py"]) == ["feedback-plain"]


def test_a_dry_run_names_the_collapse_and_writes_nothing(tmp_path, capsys):
    anchor, _levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--clear", "--dry-run"]) == 0
    assert "each would keep one line" in capsys.readouterr().out and _snapshot(anchor) == before


def _fill_top(anchor, room):
    """Give the tree top lines no render places (pointing at no body) until its block holds
    exactly MAX_RENDER_BLOCK_BYTES - `room` bytes of lines. Returns the slug of the largest."""
    plain = [us.Pointer(slug="feedback-kept%05d" % i, title="T", hook="k" * 1000) for i in range(900)]
    _hold_lines(anchor, plain)
    have = sum(_line_bytes(anchor).values())
    last = us.Pointer(slug="feedback-kept-last", title="T", hook="")
    base = len(last.index_line().encode("utf-8")) + 1
    last.hook = "k" * (E.MAX_RENDER_BLOCK_BYTES - room - have - base)
    _hold_lines(anchor, [last])
    assert sum(_line_bytes(anchor).values()) == E.MAX_RENDER_BLOCK_BYTES - room
    return last.slug


def test_a_collapse_past_the_top_block_cap_is_refused_before_any_write(tmp_path, capsys):
    """The collapse adds a line at the tree top, whose block is 10 bytes short of the cap. The
    whole call is refused, the dry run too, the body still bound and no file changed. The move
    the refusal names, run as given from outside the tree, makes room; then the call goes through."""
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    largest = _fill_top(anchor, 10)
    line = _line_bytes(levels["a/py"])["feedback-py-rule"]
    before = _snapshot(anchor)
    capsys.readouterr()
    for extra in ([], ["--dry-run"]):
        assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule",
                       "--universal", *extra]) == 2
        out = capsys.readouterr().out
        assert out.startswith("! refused") and _snapshot(anchor) == before, out
    said = re.search(r"(\d+) bytes of lines are there and (\d+) bytes would be added, (\d+) bytes "
                     r"over the (\d+) bytes", out)
    assert said is not None, out
    assert [int(g) for g in said.groups()] == [E.MAX_RENDER_BLOCK_BYTES - 10, line, line - 10,
                                               E.MAX_RENDER_BLOCK_BYTES]
    need = re.search(r"Move lines totalling at least (\d+) bytes", out)
    assert need is not None and int(need.group(1)) == line - 10, out
    engine, words = _engine_route(out, r"(hooks/memory_engine\.py) (move --from-level \S+ "
                                       r"--to-level) <level> --slug <slug>")
    assert words[2] == anchor
    _run_outside(tmp_path, [str(engine), *words, levels["a"], "--slug", largest])
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--universal"]) == 0
    assert "feedback-py-rule" in _slugs(anchor) and _slugs(levels["a"]) == [largest]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []


def test_a_collapse_that_needs_no_new_top_line_is_not_held_to_the_cap(tmp_path):
    """The top already holds the fact's line: un-binding it adds nothing there, so a full top
    block is no reason to refuse; the copies below are dropped."""
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    _hold_lines(anchor, [us.Pointer(slug="feedback-py-rule", title="T feedback-py-rule", hook=HOOK)])
    _fill_top(anchor, 0)
    rep = E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert rep["collapsed"] == ["feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []


def _refused_collapse(anchor, capsys, slug):
    """The set-topics refusal text for un-binding `slug`, real and dry run alike, after checking
    that neither writes a byte."""
    before = _snapshot(anchor)
    capsys.readouterr()
    out = None
    for extra in ([], ["--dry-run"]):
        assert E.main(["set-topics", "--proj", anchor, "--slug", slug, "--universal", *extra]) == 2
        out = capsys.readouterr().out
        assert out.startswith("! refused") and _snapshot(anchor) == before, out
    return out


def test_a_collapse_past_the_cap_because_of_lines_placed_below_the_top_names_the_tree_sweep(
        tmp_path, capsys):
    """The top holds about 52 KB of lines of rust facts placed at `c`, which only a tree-scope
    render drops, beside lines no render places; with the line the collapse adds it is past the
    cap, without the rust lines it fits. The refusal names the tree-scope render, not a move of a
    line placed by topic. Run as given from outside the tree, then the call goes through, and no
    rust fact was un-bound on the way."""
    anchor, levels = _two_python_levels(tmp_path)
    rust_level = _level(anchor, "c", ("rust",))
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    rust = _plant_tagged(anchor, "rs", "rust", 50, "y" * 1000)
    _hold_lines(anchor, [us.Pointer(slug=slug, title="T", hook="y" * 1000) for slug in rust])
    filler = _fill_top(anchor, 10)
    stale = sum(size for slug, size in _line_bytes(anchor).items() if slug in rust)
    out = _refused_collapse(anchor, capsys, "feedback-py-rule")
    assert "move --from-level" not in out and "set-topics --proj" not in out, out
    with pytest.raises(E.CollapseTooLarge) as exc:
        E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert (exc.value.stale, exc.value.placed) == (stale, 0)
    assert exc.value.need <= 0 < exc.value.over
    assert "%d bytes are placed by topic at a level below it" % stale in out, out
    engine, words = _sweep_route(out)
    assert words[2] == anchor
    _run_outside(tmp_path, [str(engine), *words])
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--universal"]) == 0
    assert "feedback-py-rule" in _slugs(anchor) and filler in _slugs(anchor)
    assert not set(rust) & set(_slugs(anchor)) and _slugs(rust_level) == rust
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []
    assert _bound(anchor, rust) == {("rust",): 50}


def test_a_collapse_past_the_cap_because_of_lines_placed_at_the_top_names_a_rebind(
        tmp_path, capsys):
    """The top holds about 1 MB of lines of git facts, placed there because no level below has
    git, and one line no render places; the collapse adds a line and passes the cap. The lines
    placed by topic at the top are the larger part, and a move is not theirs: the refusal names a
    set-topics batch that rebinds some to a topic a level below has, then the tree-scope render
    that moves them down. Both run as given from outside the tree; then the call goes through."""
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    git = _plant_tagged(anchor, "git", "git", 1000, "y" * 1000)
    E.render_topics(anchor)
    assert _slugs(anchor) == git
    have = sum(_line_bytes(anchor).values())
    pad = us.Pointer(slug="feedback-kept-pad", title="T", hook="")
    pad.hook = "k" * (E.MAX_RENDER_BLOCK_BYTES - 10 - have - len(pad.index_line().encode("utf-8")) - 1)
    _hold_lines(anchor, [pad])
    assert sum(_line_bytes(anchor).values()) == E.MAX_RENDER_BLOCK_BYTES - 10
    out = _refused_collapse(anchor, capsys, "feedback-py-rule")
    assert "move --from-level" not in out, out
    with pytest.raises(E.CollapseTooLarge) as exc:
        E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert exc.value.stale == 0 and exc.value.placed == have > exc.value.kept > 0
    need = re.search(r"rebind facts placed there whose lines total at least (\d+) bytes", out)
    assert need is not None and int(need.group(1)) == exc.value.need > 0, out
    engine, words = _engine_route(out, r"(hooks/memory_engine\.py) (set-topics --proj \S+) "
                                       r"--batch <file>")
    assert words[2] == anchor
    sizes = _line_bytes(anchor)
    moved = _shortest_run(git, sizes, int(need.group(1)))
    batch = tmp_path / "batch.jsonl"
    batch.write_text("".join('{"slug": "%s", "topics": ["python"]}\n' % slug for slug in moved),
                     encoding="utf-8")
    _run_outside(tmp_path, [str(engine), *words, "--batch", str(batch)])
    engine, words = _sweep_route(out)
    assert words[2] == anchor
    _run_outside(tmp_path, [str(engine), *words])
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--universal"]) == 0
    assert "feedback-py-rule" in _slugs(anchor) and not set(moved) & set(_slugs(anchor))
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == sorted(moved)


def test_the_top_line_of_a_fact_the_same_call_un_binds_counts_as_kept_not_as_placed_elsewhere(
        tmp_path, capsys):
    """Two facts are un-bound in one call. One already has a line at the top beside its lines
    below: that line stays, whatever its topics said, so it is kept, not a line a tree-scope
    render would drop. Counted as one, the block would fit without it and the refusal would name
    the sweep, after which the collapse would add that line again. The route is a move of kept
    lines; run as given from outside the tree, then the call goes through."""
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    _fact(anchor, "feedback-py-held", ("python",))
    E.render_topics(anchor)
    _hold_lines(anchor, [us.Pointer(slug="feedback-py-held", title="T", hook="h" * 60000)])
    _fill_top(anchor, 10)
    sizes = _line_bytes(anchor)
    rows = {"feedback-py-rule": (), "feedback-py-held": ()}
    batch = tmp_path / "unbind.jsonl"
    batch.write_text("".join('{"slug": "%s", "topics": []}\n' % slug for slug in rows),
                     encoding="utf-8")
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["set-topics", "--proj", anchor, "--batch", str(batch)]) == 2
    out = capsys.readouterr().out
    assert _snapshot(anchor) == before and _no_sweep_route(out), out
    with pytest.raises(E.CollapseTooLarge) as exc:
        E.set_fact_topics(anchor, rows)
    assert (exc.value.stale, exc.value.placed) == (0, 0) and exc.value.kept == sum(sizes.values())
    need = re.search(r"Move lines totalling at least (\d+) bytes", out)
    assert need is not None and int(need.group(1)) == exc.value.need > 0, out
    engine, words = _engine_route(out, r"(hooks/memory_engine\.py) (move --from-level \S+ "
                                       r"--to-level) <level> --slug <slug>")
    filler = [slug for slug in sizes if slug.startswith("feedback-kept")]
    moved = _shortest_run(filler, sizes, int(need.group(1)))
    _run_outside(tmp_path, [str(engine), *words, levels["a"], "--slug", *moved])
    assert E.main(["set-topics", "--proj", anchor, "--batch", str(batch)]) == 0
    assert {"feedback-py-rule", "feedback-py-held"} <= set(_slugs(anchor))
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []
