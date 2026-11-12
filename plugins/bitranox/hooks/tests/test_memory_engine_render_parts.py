"""Tests for the parts `render-topics` is built from: the streamed body heads, a level as path
parts, the line a body renders, the tree's level map, and the set-topics guard that keeps a
fact's stored line equal to what its body renders before the fact is bound. All content ASCII.
"""

import os
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

import memory_engine as E
import migrate_to_slug_store as mig
import self_improve_signals as sig
import topic_placement as tp
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


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None, scope=SCOPE):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    if scope:
        assert E.main(["set-scope", "--proj", str(level), "--scope", scope]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, pin=False):
    return E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                                 type_="feedback", slug=slug, pin=pin)


def _plant_scope(level, scope):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, scope, us.parse_pointer_index(text)[1]),
                     encoding="utf-8")


def _plant_bodies(anchor, count):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    prose = "x" * 200_000
    for i in range(count):
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\ntopics: [python]\nmetadata:\n"
            "  type: feedback\n---\n\n%s\n" % (i, prose), encoding="utf-8")


def _heads_peak(anchor):
    tracemalloc.start()
    try:
        longest = max(len(head) for _slug, head in E._iter_body_heads(anchor))
        return longest, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_body_heads_are_streamed_one_at_a_time_and_capped(tmp_path):
    small, large = tmp_path / "small", tmp_path / "large"
    _plant_bodies(small, 20)
    _plant_bodies(large, 200)
    (us.central_facts_dir(large) / "notes.txt").write_text("x", encoding="utf-8")
    longest, peak_small = _heads_peak(small)
    _longest, peak_large = _heads_peak(large)
    assert longest == E.FRONTMATTER_HEAD_BYTES
    assert sum(1 for _ in E._iter_body_heads(large)) == 200
    assert peak_large < 200_000 and peak_large < peak_small * 2 + 50_000
    assert list(E._iter_body_heads(tmp_path / "nothing")) == []


def test_a_level_is_its_path_parts_below_the_anchor(tmp_path):
    anchor = _tree(tmp_path)
    assert E._level_parts(anchor, anchor) == tp.TOP == ()
    assert E._level_parts(anchor, os.path.join(anchor, "a", "py")) == ("a", "py")
    with pytest.raises(topic_store.TopicStoreError):
        E._level_parts(anchor, str(tmp_path / "elsewhere"))


def test_a_line_is_built_from_the_body_alone(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    head = us.body_path(anchor, "feedback-a").read_text(encoding="utf-8")
    line = E._line_from_head("feedback-a", head)
    stored = us.parse_pointer_index(sig.claude_local_md_path(anchor).read_text(encoding="utf-8"))[1][0]
    assert line.index_line() == stored.index_line() and line.pin is False
    assert E._line_from_head("feedback-a", head.replace("title: T feedback-a\n", "")) is None
    assert E._line_from_head("feedback-a", head.replace("description: " + HOOK + "\n", "")) is None


def test_the_level_map_holds_described_levels_with_their_topics(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a/py", ("python",))
    _level(anchor, "c", ())
    _level(anchor, "d")                                   # a descriptor, never tagged
    bare = _level(anchor, "e", scope=None)
    _fact(bare, "feedback-at-bare")                       # a pointer block with no descriptor
    level_map, dirs = E.topic_level_map(anchor)
    assert level_map.levels() == [(), ("c",), ("d",), ("a", "py")]
    assert level_map.topics(("a", "py")) == {"python"} and level_map.topics(("d",)) == frozenset()
    assert dirs[("a", "py")] == os.path.join(anchor, "a", "py") and dirs[()] == anchor


def test_a_level_without_a_descriptor_does_not_block_a_roll_up(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a", ())
    _level(anchor, "a/x1", ("python",))
    _level(anchor, "a/x2", ("python",))
    _fact(_level(anchor, "a/x3", scope=None), "feedback-at-bare")
    level_map, _dirs = E.topic_level_map(anchor)
    assert level_map.placements(("python",)) == (("a",),)


def test_a_topics_line_that_does_not_parse_refuses_the_map_and_names_the_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _plant_scope(level, SCOPE + "\nTOPICS: Not A Tag")
    with pytest.raises(E.TopicRefusal) as exc:
        E.topic_level_map(anchor)
    assert level in str(exc.value) and "does not parse" in str(exc.value)


def test_pinned_slugs_are_found_at_any_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a")
    _fact(level, "feedback-pinned", pin=True)
    _fact(anchor, "feedback-free")
    assert E._pinned_slugs(E.curated_levels_under(anchor)) == {"feedback-pinned"}


# ---- set-topics: a fact is bound only when its line equals what its body renders ---------------

def _replant_pointer(level, slug, hook):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    for p in pointers:
        if p.slug == slug:
            p.hook = hook
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def test_binding_a_fact_whose_line_differs_from_its_body_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _replant_pointer(anchor, "feedback-a", "When the line was edited by hand, it says this.")
    body = us.body_path(anchor, "feedback-a").read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and "differs from what its body renders" in out
    assert us.body_path(anchor, "feedback-a").read_bytes() == body
    # un-binding hands nothing to the renderer, so it stays allowed
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--universal"]) == 0


def test_binding_a_fact_whose_body_has_no_title_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    path = us.body_path(anchor, "feedback-a")
    path.write_text(path.read_text(encoding="utf-8").replace("title: T feedback-a\n", ""),
                    encoding="utf-8")
    before = path.read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    assert "its body has no title:" in capsys.readouterr().out
    assert path.read_bytes() == before


def test_binding_a_fact_whose_line_equals_its_body_goes_through(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 0
    assert E.read_body_topics(us.body_path(anchor, "feedback-a")) == ("python",)
    assert list(E.iter_fact_topics(anchor)) == [("feedback-a", ("python",))]


# ---- each refusal names a repair that works: run the named route, then the bind goes through --

FACTEDIT = Path(E.__file__).parent.parent / "skills" / "meta-dream-tree" / "factedit.py"


def _bind(anchor, slug):
    return E.main(["set-topics", "--proj", anchor, "--slug", slug, "--topics", "python"])


def _refusal(anchor, slug, capsys):
    capsys.readouterr()
    assert _bind(anchor, slug) == 2
    out = capsys.readouterr().out
    assert "! refused" in out
    return out


def _factedit(anchor, *args):
    r = subprocess.run([sys.executable, str(FACTEDIT), "apply", "--from", anchor,
                        "--python", sys.executable, *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr


def _drop_frame_line(anchor, slug, line):
    path = us.body_path(anchor, slug)
    text = path.read_text(encoding="utf-8")
    assert text.count(line) == 1
    path.write_text(text.replace(line, ""), encoding="utf-8")


def test_a_missing_title_names_backfill_titles_and_that_repairs_it(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _drop_frame_line(anchor, "feedback-a", "title: T feedback-a\n")
    out = _refusal(anchor, "feedback-a", capsys)
    assert "heal --proj %s --backfill-titles" % anchor in out and "--title" in out
    assert "--body-file" not in out
    assert E.main(["heal", "--proj", anchor, "--backfill-titles"]) == 0
    assert _bind(anchor, "feedback-a") == 0


def test_a_missing_title_is_also_repaired_by_factedit_apply_title(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _drop_frame_line(anchor, "feedback-a", "title: T feedback-a\n")
    _refusal(anchor, "feedback-a", capsys)
    _factedit(anchor, "--slug", "feedback-a", "--title", "T feedback-a")
    assert _bind(anchor, "feedback-a") == 0


def test_a_missing_description_names_a_prose_body_file_and_that_repairs_it(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _drop_frame_line(anchor, "feedback-a", "description: " + HOOK + "\n")
    out = _refusal(anchor, "feedback-a", capsys)
    assert "its body has no description:" in out and "--body-file" in out
    assert "backfill-titles" not in out
    prose = tmp_path / "prose.md"
    prose.write_text("body of feedback-a\n", encoding="utf-8")
    _factedit(anchor, "--slug", "feedback-a", "--body-file", str(prose))
    assert _bind(anchor, "feedback-a") == 0


def test_a_missing_description_is_also_repaired_by_add_body_file(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _drop_frame_line(anchor, "feedback-a", "description: " + HOOK + "\n")
    _refusal(anchor, "feedback-a", capsys)
    prose, hook = tmp_path / "prose.md", tmp_path / "hook.txt"
    prose.write_text("body of feedback-a\n", encoding="utf-8")
    hook.write_text(HOOK + "\n", encoding="utf-8")
    assert E.main(["add", "--proj", anchor, "--slug", "feedback-a", "--title", "T feedback-a",
                   "--hook-file", str(hook), "--body-file", str(prose), "--type", "feedback"]) == 0
    assert _bind(anchor, "feedback-a") == 0


def test_a_differing_line_names_the_body_description_as_the_hook_and_that_repairs_it(tmp_path,
                                                                                    capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _replant_pointer(anchor, "feedback-a", "When the line was edited by hand, it says this.")
    out = _refusal(anchor, "feedback-a", capsys)
    assert "with the body's description: as the hook" in out and "factedit apply" in out
    assert "not the line's current one" in out
    hook = tmp_path / "hook.txt"
    hook.write_text(HOOK + "\n", encoding="utf-8")       # the body's description:
    _factedit(anchor, "--slug", "feedback-a", "--hook-file", str(hook))
    assert _bind(anchor, "feedback-a") == 0


def test_a_line_differing_only_in_whitespace_binds(tmp_path):
    anchor = _tree(tmp_path)
    hook, prose = tmp_path / "hook.txt", tmp_path / "prose.md"
    hook.write_text("When  a rule is about one stack,\tbind it to that stack's topic. \n",
                    encoding="utf-8")
    prose.write_text("body\n", encoding="utf-8")
    assert E.main(["add", "--proj", anchor, "--slug", "feedback-w", "--title", "T  w ",
                   "--hook-file", str(hook), "--body-file", str(prose), "--type", "feedback"]) == 0
    stored = us.parse_pointer_index(sig.claude_local_md_path(anchor).read_text(encoding="utf-8"))[1]
    assert "  " in [p for p in stored if p.slug == "feedback-w"][0].index_line()  # really drifted
    assert _bind(anchor, "feedback-w") == 0


def test_every_line_of_the_fact_is_checked_and_the_differing_level_is_named(tmp_path, capsys):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a")
    _fact(anchor, "feedback-a")
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-a", title="T feedback-a",
                               hook="When the second line was edited by hand, it says this."))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    out = _refusal(anchor, "feedback-a", capsys)
    assert "its line at %s differs" % level in out
    assert "its line at %s " % anchor not in out


def test_a_legacy_uuid_pointer_names_the_migration_and_that_repairs_it(tmp_path, capsys):
    anchor = _tree(tmp_path)
    uuid = us.fact_uuid(anchor, "feedback-l")
    body = us.legacy_body_path(anchor, uuid)
    body.parent.mkdir(parents=True, exist_ok=True)
    body.write_text("---\nname: feedback-l\ndescription: %s\ntitle: T feedback-l\nmetadata:\n"
                    "  type: feedback\n---\n\nbody\n" % HOOK, encoding="utf-8")
    local = sig.claude_local_md_path(anchor)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-l", title="T feedback-l", hook=HOOK, uuid=uuid,
                               legacy=True))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    out = _refusal(anchor, "feedback-l", capsys)
    assert "legacy uuid: pointer" in out
    assert "migrate_to_slug_store.py --root %s --apply" % anchor in out
    assert mig.main(["--root", anchor, "--apply"]) == 0
    # The migration leaves its backup (a copy of every pointer file, legacy lines included) under
    # the anchor, and the engine's level walk enters it as if it were a live level; that walk is
    # not this guard's to change, so the backup is moved out of the tree before the bind.
    for backup in Path(anchor).glob(mig.BACKUP_PREFIX + "*"):
        backup.rename(tmp_path / backup.name)
    assert _bind(anchor, "feedback-l") == 0
