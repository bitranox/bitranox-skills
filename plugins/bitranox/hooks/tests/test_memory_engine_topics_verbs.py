"""Tests for the topic verbs: the closed list, a fact's topics, a level's TOPICS line.

Topics are data the placement of pointer lines is later computed from, so each write is checked
whole before anything is written, the tree top's topics have a verb of their own, and a rewritten
descriptor can neither drop nor change a level's topics. All content ASCII.
"""

import json
import tracemalloc

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python\nCHILDREN:\n- x/: y\nPLACE-HERE: a\nPLACE-ELSEWHERE: b"
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
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    return str(anchor), str(proj)


def _fact(proj, slug, pin=False):
    return E.add_or_update_entry(proj, title="T " + slug, hook=HOOK, body="body of " + slug,
                                 type_="feedback", slug=slug, pin=pin)


def _topics(anchor, slug):
    return E._body_topics(us.body_path(anchor, slug).read_text(encoding="utf-8"))


def _scope(level):
    return us.parse_pointer_index(sig.claude_local_md_path(level).read_text(encoding="utf-8"))[0]


def _list_file(tmp_path, topics, tagger="jev"):
    f = tmp_path / "list.json"
    f.write_text(json.dumps({"tagger": tagger, "topics": topics}), encoding="utf-8")
    return str(f)


# ---- the list ----------------------------------------------------------------------------------

def test_topics_show_exits_1_without_a_list_and_prints_it_with_one(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    assert E.main(["topics-show", "--proj", proj]) == 1
    assert "no topic list" in capsys.readouterr().out
    assert E.main(["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, LIST)]) == 0
    capsys.readouterr()
    assert E.main(["topics-show", "--proj", proj, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"tagger": "jev", "topics": LIST}


def test_a_list_that_drops_a_topic_in_use_is_refused_and_names_the_users(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-uses-python")
    E.set_fact_topics(proj, {"feedback-uses-python": ("python",)})
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.set_level_topics(proj, ("rust",))
    capsys.readouterr()
    rc = E.main(["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, {"git": "git"})])
    out = capsys.readouterr().out
    assert rc == 2 and "feedback-uses-python carries python" in out and "declares rust" in out
    assert topic_store.load(anchor)["topics"] == LIST


def test_a_list_file_that_is_not_the_expected_json_is_a_usage_error(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    bad = tmp_path / "bad.json"
    bad.write_text('{"tagger": "jev", "topics": ["python"]}', encoding="utf-8")
    assert E.main(["topics-set-list", "--proj", proj, "--from-file", str(bad)]) == 2
    assert "must be an object" in capsys.readouterr().err
    assert topic_store.load(anchor) is None


# ---- a fact's topics ---------------------------------------------------------------------------

def test_set_topics_writes_the_line_and_leaves_the_pointer_block_alone(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    before = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--topics", "rust,python"]) == 0
    assert "set topics on 1 fact(s); 0 unchanged" in capsys.readouterr().out
    assert _topics(anchor, "feedback-one") == ("python", "rust")
    assert sig.claude_local_md_path(proj).read_text(encoding="utf-8") == before


def test_universal_and_clear_are_different_states(tmp_path):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--universal"]) == 0
    assert _topics(anchor, "feedback-one") == ()
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--clear"]) == 0
    assert _topics(anchor, "feedback-one") is None


def test_set_topics_needs_exactly_one_way_to_say_which(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one"]) == 2
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--topics", "python",
                   "--universal"]) == 2
    assert "exactly one of" in capsys.readouterr().err
    assert _topics(anchor, "feedback-one") is None


def test_one_bad_row_refuses_the_whole_batch_and_writes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    for slug in ("feedback-a", "feedback-b"):
        _fact(proj, slug)
    _fact(proj, "feedback-pinned", pin=True)
    batch = tmp_path / "batch.jsonl"
    rows = [{"slug": "feedback-a", "topics": ["python"]}, {"slug": "feedback-b", "topics": ["cobol"]},
            {"slug": "feedback-pinned", "topics": ["git"]}, {"slug": "feedback-gone", "topics": []}]
    batch.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 2
    out = capsys.readouterr().out
    assert "feedback-b: cobol not in the topic list" in out
    assert "feedback-pinned is pinned" in out and "feedback-gone: no level points at it" in out
    assert _topics(anchor, "feedback-a") is None


def test_a_good_batch_applies_every_row_and_a_second_run_changes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    for slug in ("feedback-a", "feedback-b", "feedback-c"):
        _fact(proj, slug)
    E.set_fact_topics(proj, {"feedback-c": ("git",)})
    batch = tmp_path / "batch.jsonl"
    rows = [{"slug": "feedback-a", "topics": ["python"]}, {"slug": "feedback-b", "topics": []},
            {"slug": "feedback-c", "topics": None}]
    batch.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 0
    assert "set topics on 3 fact(s); 0 unchanged" in capsys.readouterr().out
    assert [_topics(anchor, s) for s in ("feedback-a", "feedback-b", "feedback-c")] == [("python",), (), None]
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 0
    assert "set topics on 0 fact(s); 3 unchanged" in capsys.readouterr().out


def test_a_dry_run_reports_and_writes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-a", "--topics", "python",
                   "--dry-run"]) == 0
    assert "would set topics on 1 fact(s)" in capsys.readouterr().out
    assert _topics(anchor, "feedback-a") is None


@pytest.mark.parametrize("line", ['{"slug": "feedback-a", "topics": "python"}', '{"slug": "feedback-a"}',
                                  'not json', '{"slug": 7, "topics": []}'])
def test_a_malformed_batch_line_is_a_usage_error_naming_the_line(tmp_path, capsys, line):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    batch = tmp_path / "batch.jsonl"
    batch.write_text('{"slug": "feedback-a", "topics": []}\n' + line + "\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 2
    assert "line 2" in capsys.readouterr().err
    assert _topics(anchor, "feedback-a") is None


def test_set_topics_without_a_list_is_refused(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    _fact(proj, "feedback-a")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-a", "--universal"]) == 2
    assert "no topic list yet" in capsys.readouterr().out


def test_the_topic_write_verbs_are_refused_when_memory_writes_are_off(tmp_path, monkeypatch, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    for argv in (["set-topics", "--proj", proj, "--slug", "feedback-a", "--universal"],
                 ["set-level-topics", "--proj", proj, "--topics", "python"],
                 ["set-top-topics", "--proj", anchor, "--topics", "git"],
                 ["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, LIST)]):
        assert E.main(argv) == 2
        assert "refused" in capsys.readouterr().out
    assert _topics(anchor, "feedback-a") is None


# ---- a level's topics --------------------------------------------------------------------------

def test_set_level_topics_writes_the_line_and_the_level_reads_fresh(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    assert E.main(["topics-stale", "--proj", proj]) == 1
    assert "never tagged" in capsys.readouterr().out
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "rust, python"]) == 0
    assert tp.descriptor_topics(_scope(proj)) == ("python", "rust")
    assert _scope(proj).replace("TOPICS: python, rust\n", "") == SCOPE
    capsys.readouterr()
    assert E.main(["topics-stale", "--proj", proj]) == 0
    assert capsys.readouterr().out.strip() == "fresh"


def test_the_tree_top_takes_its_topics_only_from_its_own_verb(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", anchor, "--scope", SCOPE])
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    capsys.readouterr()
    assert E.main(["set-level-topics", "--proj", anchor, "--topics", "git"]) == 2
    assert "is the tree top" in capsys.readouterr().out
    assert tp.descriptor_topics(_scope(anchor)) is None
    assert E.main(["set-top-topics", "--proj", proj, "--topics", "git"]) == 2
    assert "is not the tree top" in capsys.readouterr().out
    assert E.main(["set-top-topics", "--proj", anchor, "--topics", "git"]) == 0
    assert tp.descriptor_topics(_scope(anchor)) == ("git",)


def test_a_tag_outside_the_list_and_a_level_without_a_descriptor_are_refused(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.ensure_level(proj)
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "python"]) == 2
    assert "no descriptor yet" in capsys.readouterr().out
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    capsys.readouterr()
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "cobol"]) == 2
    assert "cobol not in the topic list" in capsys.readouterr().out
    assert tp.descriptor_topics(_scope(proj)) is None


def test_set_scope_keeps_the_stored_topics_and_the_level_then_reads_stale(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.main(["set-level-topics", "--proj", proj, "--topics", "python"])
    rewritten = SCOPE.replace("WHAT: a level", "WHAT: another level")
    assert E.main(["set-scope", "--proj", proj, "--scope", rewritten]) == 0
    assert tp.descriptor_topics(_scope(proj)) == ("python",)
    assert "WHAT: another level" in _scope(proj)
    capsys.readouterr()
    assert E.main(["topics-stale", "--proj", proj]) == 1
    assert "descriptor changed" in capsys.readouterr().out


def test_set_scope_refuses_a_text_that_changes_the_topics_line(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.main(["set-level-topics", "--proj", proj, "--topics", "python"])
    before = _scope(proj)
    capsys.readouterr()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS: rust"]) == 2
    assert "changes only through set-level-topics" in capsys.readouterr().out
    assert _scope(proj) == before
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS: python"]) == 0


def test_topics_stale_is_fresh_in_a_tree_without_a_list(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    assert E.main(["topics-stale", "--proj", proj]) == 0


# ---- the scan over every body ------------------------------------------------------------------

def _plant_bodies(anchor, count, tagged_every=10):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    prose = "x" * 200_000
    for i in range(count):
        topics = "topics: [python]\n" if i % tagged_every == 0 else ""
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\n%smetadata:\n  type: feedback\n---\n\n%s\n"
            % (i, topics, prose), encoding="utf-8")


def _scan_peak(anchor):
    tracemalloc.start()
    try:
        found = sum(1 for _ in E.iter_fact_topics(anchor))
        return found, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_the_scan_yields_only_tagged_bodies_and_its_peak_does_not_grow_with_the_store(tmp_path):
    small, large = tmp_path / "small", tmp_path / "large"
    _plant_bodies(small, 30)
    _plant_bodies(large, 300)
    found_small, peak_small = _scan_peak(small)
    found_large, peak_large = _scan_peak(large)
    assert (found_small, found_large) == (3, 30)
    assert peak_large < 200_000            # one body is 200 KB; the scan never holds one whole
    assert peak_large < peak_small * 2 + 50_000


def test_the_scan_skips_names_that_are_no_fact_and_a_missing_store_yields_nothing(tmp_path):
    anchor = tmp_path / "tree"
    assert list(E.iter_fact_topics(anchor)) == []
    _plant_bodies(anchor, 1)
    facts = us.central_facts_dir(anchor)
    (facts / "notes.txt").write_text("topics: [python]\n", encoding="utf-8")
    (facts / "Bad Name.md").write_text("---\nname: x\ntopics: [python]\n---\n", encoding="utf-8")
    assert list(E.iter_fact_topics(anchor)) == [("feedback-n00000", ("python",))]


# ---- what the verbs do with a list or a TOPICS line they cannot use ----------------------------

def _plant_scope(level, scope):
    """Write `scope` as `level`'s descriptor as it is, bypassing set-scope's checks: a stored line
    that does not parse can come from a hand edit or an older writer."""
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    pointers = us.parse_pointer_index(text)[1]
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def test_an_empty_topic_list_is_refused(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    rc = E.main(["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, {})])
    assert rc == 2 and "empty" in capsys.readouterr().out
    assert topic_store.load(anchor)["topics"] == LIST


def test_a_dropped_topic_is_judged_by_the_trimmed_name(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-uses-rust")
    E.set_fact_topics(proj, {"feedback-uses-rust": ("rust",)})
    capsys.readouterr()
    rc = E.main(["topics-set-list", "--proj", proj, "--from-file",
                 _list_file(tmp_path, {" rust ": "Rust code", "git": "git"})])
    assert rc == 0, capsys.readouterr().out
    assert set(topic_store.load(anchor)["topics"]) == {"rust", "git"}


def test_a_stored_topics_line_that_does_not_parse(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    _plant_scope(proj, SCOPE + "\nTOPICS: Not A Tag!")
    before = _scope(proj)
    capsys.readouterr()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE]) == 2
    assert "set-level-topics" in capsys.readouterr().out
    assert _scope(proj) == before
    assert E.main(["topics-stale", "--proj", proj]) == 1
    assert "does not parse" in capsys.readouterr().out
    # a list that drops a topic is not refused over a line that declares nothing readable
    assert E.main(["topics-set-list", "--proj", proj, "--from-file",
                   _list_file(tmp_path, {"python": "Python code"})]) == 0
    # the verb meant to change the line replaces it
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "python"]) == 0
    assert tp.descriptor_topics(_scope(proj)) == ("python",)


def test_set_scope_refuses_a_new_topics_line_that_does_not_parse(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    before = _scope(proj)
    capsys.readouterr()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS: Not A Tag!"]) == 2
    assert "refused" in capsys.readouterr().out
    assert _scope(proj) == before


def test_a_damaged_topic_file_is_an_error_for_the_read_verbs(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    topic_store.store_path(anchor).write_text("{not json", encoding="utf-8")
    capsys.readouterr()
    for verb in ("topics-show", "topics-stale"):
        assert E.main([verb, "--proj", proj]) == 2
        assert "! error" in capsys.readouterr().err


def test_set_scope_cannot_tag_a_never_tagged_level_even_as_universal(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    capsys.readouterr()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS:"]) == 2
    assert "changes only through set-level-topics" in capsys.readouterr().out
    assert tp.descriptor_topics(_scope(proj)) is None


@pytest.mark.parametrize("line", ["TOPICS: python", "TOPICS:", "TOPICS: Not A Tag!"])
def test_a_refused_set_scope_leaves_no_level_scaffolded_behind_it(tmp_path, capsys, line):
    # The topics check reads the level's current text (none yet) BEFORE ensure_level runs, so a
    # refusal on a directory that was never a level writes nothing at all.
    _anchor, proj = _tree(tmp_path)
    local = sig.claude_local_md_path(proj)
    assert not local.exists()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\n" + line]) == 2
    assert "! refused" in capsys.readouterr().out
    assert not local.exists()
