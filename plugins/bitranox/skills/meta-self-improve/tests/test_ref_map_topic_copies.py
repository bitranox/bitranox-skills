"""Tests for ref_map on a fact held at several levels (the engine places it by topic): the map
names every level, a planned move of it is a conflict, and a ref to it is not judged by one of
its levels. All content ASCII.
"""
import io
import json
import sys
from pathlib import Path

import pytest

import ref_map

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store as US  # noqa: E402


# a body the engine places by topic: framed, bound to a topic, with the title and description
# its pointer line is built from
PLACED = ("---\nname: py-rule\ntitle: Py rule\ndescription: When python, do this.\n"
          "topics: [python]\n---\n\nA python rule.\n")


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "t"
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    levels = {"": {"top-citer": "Cites [[py-rule]].\n"},
              "a": {"py-rule": PLACED, "a-citer": "Cites [[py-rule]].\n"},
              "b": {"py-rule": PLACED}}
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        lines += ["- [%s](mem:%s) - When something, do something." % (s, s) for s in entries]
        (d / "CLAUDE.local.md").write_text("\n".join(lines + [US.INDEX_END]) + "\n", encoding="utf-8")
        for slug, body in entries.items():
            (facts / (slug + ".md")).write_text(body, encoding="utf-8")
    return root


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    return ref_map.main(argv, out=out, err=err), out.getvalue(), err.getvalue()


def test_the_map_names_every_level_holding_a_line(tree):
    assert ref_map.read_levels(tree)["py-rule"] == str(tree / "a")
    assert ref_map.read_copies(tree) == {"py-rule": [str(tree / "a"), str(tree / "b")]}
    code, out, _ = _run(["--root", str(tree), "--json", "py-rule"])
    entry = json.loads(out)["data"]["entries"][0]
    assert code == 0 and entry["level"] == str(tree / "a") and entry["also_at"] == [str(tree / "b")]
    _code, text, _ = _run(["--root", str(tree), "py-rule"])
    assert "also at  : %s" % (tree / "b") in text


def test_a_planned_move_of_a_fact_with_several_lines_is_a_conflict(tree, tmp_path):
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "py-rule", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 1 and "placed-by-topic" in out and "py-rule" in out


def test_moving_a_citer_does_not_strand_its_ref_to_a_fact_with_several_lines(tree, tmp_path):
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "a-citer", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 0 and "0 conflict(s)" in out


def _unbind(tree):
    """Make py-rule an ordinary duplicate: its body keeps no `topics:` line."""
    (tree / ".claude-memory" / "facts" / "py-rule.md").write_text("A python rule.\n", encoding="utf-8")


def test_a_planned_move_of_a_duplicate_is_a_duplicate_pointer_conflict(tree, tmp_path):
    _unbind(tree)
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "py-rule", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 1 and "duplicate-pointer" in out and "placed-by-topic" not in out


def test_a_fact_pinned_at_one_level_is_no_placed_fact(tree, tmp_path):
    local = tree / "b" / "CLAUDE.local.md"
    text = local.read_text(encoding="utf-8")
    local.write_text(text.replace("(mem:py-rule) - When something, do something.",
                                  "(mem:py-rule) - When something, do something. <!-- bx:pin -->"),
                     encoding="utf-8")
    assert ref_map.read_placed(tree, ref_map.read_copies(tree)) == set()
    _unbind(tree)
    assert ref_map.read_placed(tree, ref_map.read_copies(tree)) == set()


def test_lifting_a_citer_above_every_line_of_a_duplicate_strands_its_ref(tree, tmp_path):
    _unbind(tree)
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "a-citer", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 1 and "stranded-outbound" in out and "a-citer" in out


def test_a_citer_with_lines_at_two_levels_is_judged_at_each(tmp_path):
    root = tmp_path / "t"
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    levels = {"": {}, "a": {"target": "A target.\n", "citer": "Cites [[target]].\n"},
              "b": {"citer": "Cites [[target]].\n"}}
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        lines += ["- [%s](mem:%s) - When something, do something." % (s, s) for s in entries]
        (d / "CLAUDE.local.md").write_text("\n".join(lines + [US.INDEX_END]) + "\n", encoding="utf-8")
        for slug, body in entries.items():
            (facts / (slug + ".md")).write_text(body, encoding="utf-8")
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "target", "to": str(root / "a")}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(root), "--moves", str(plan)])
    assert code == 1 and "dangling-inbound" in out and str(root / "b") in out


def test_a_citer_moved_beside_one_line_of_a_duplicate_keeps_its_ref(tree, tmp_path):
    _unbind(tree)
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "a-citer", "to": str(tree / "b")}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 0 and "0 conflict(s)" in out


def _one_line_tree(tmp_path, body):
    """A tree whose `one-rule` has its only line at level `a`, its body `body`."""
    root = tmp_path / "t"
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    for rel, entries in {"": {}, "a": {"one-rule": body}}.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        lines += ["- [%s](mem:%s) - When something, do something." % (s, s) for s in entries]
        (d / "CLAUDE.local.md").write_text("\n".join(lines + [US.INDEX_END]) + "\n", encoding="utf-8")
        for slug, text in entries.items():
            (facts / (slug + ".md")).write_text(text, encoding="utf-8")
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "one-rule", "to": str(root)}) + "\n", encoding="utf-8")
    return root, plan


def test_a_planned_move_of_a_placed_fact_with_one_line_is_a_conflict(tmp_path):
    """The engine's move refuses a placed fact whatever its line count; a plan judged clean here
    was then refused by the move it planned."""
    root, plan = _one_line_tree(tmp_path, PLACED.replace("py-rule", "one-rule"))
    assert ref_map.read_copies(root) == {}
    code, out, _ = _run(["--root", str(root), "--moves", str(plan)])
    assert code == 1 and "placed-by-topic" in out and "one-rule" in out


def test_a_planned_move_of_an_unbound_fact_with_one_line_is_clean(tmp_path):
    root, plan = _one_line_tree(tmp_path, "A rule bound to no topic.\n")
    code, out, _ = _run(["--root", str(root), "--moves", str(plan)])
    assert code == 0 and "0 conflict(s)" in out and "placed-by-topic" not in out
