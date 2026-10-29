"""ref_map: bare-slug prose mentions as their own inbound class, and a batch of planned moves
judged against where EVERY fact in the batch lands. ASCII only."""
import io
import json
import sys
from pathlib import Path

import pytest

import ref_map

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store as US  # noqa: E402


def _tree(root, levels):
    """{level_relpath: {slug: body_text}} -> pointer blocks + central bodies. Kept here rather than
    imported from test_ref_map: under --import-mode=importlib a sibling test module is not
    importable by name, so the import only worked when something else had put tests/ on sys.path."""
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        lines += ["- [%s](mem:%s) - When something, do something." % (s, s) for s in entries]
        lines.append(US.INDEX_END)
        (d / "CLAUDE.local.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for slug, body in entries.items():
            (facts / ("%s.md" % slug)).write_text(body, encoding="utf-8")
    return root


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = ref_map.main(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


# ---- prose mentions -------------------------------------------------------------------------------

@pytest.fixture
def prose_tree(tmp_path):
    return _tree(tmp_path / "t", {
        "": {"top-names-leaf": "See reference-leaf-target for the detail (deliberately unlinked).\n"},
        "proj": {"reference-leaf-target": "The leaf.\n",
                 "proj-linked": "Cites [[reference-leaf-target]] properly.\n"},
    })


def test_a_bare_slug_in_prose_is_reported_as_a_prose_mention(prose_tree):
    code, out, _ = _run(["--root", str(prose_tree), "reference-leaf-target", "--json"])
    assert code == 0, out
    entry = json.loads(out)["data"]["entries"][0]
    assert [r["slug"] for r in entry["prose"]] == ["top-names-leaf"]
    assert [r["slug"] for r in entry["inbound"]] == ["proj-linked"]


def test_a_linked_ref_is_not_counted_again_as_prose(prose_tree):
    code, out, _ = _run(["--root", str(prose_tree), "reference-leaf-target", "--json"])
    prose = json.loads(out)["data"]["entries"][0]["prose"]
    assert "proj-linked" not in [r["slug"] for r in prose]


def test_the_text_report_shows_the_prose_class(prose_tree):
    _code, out, _ = _run(["--root", str(prose_tree), "reference-leaf-target"])
    assert "prose" in out and "top-names-leaf" in out


def test_a_slug_that_is_only_a_prefix_of_a_longer_word_is_not_a_mention(tmp_path):
    root = _tree(tmp_path / "t", {"": {"a-b": "Mentions a-bc and xa-b only.\n", "x-y": "x\n"},
                                  "p": {"q-r": "nothing\n"}})
    code, out, _ = _run(["--root", str(root), "a-b", "--json"])
    assert json.loads(out)["data"]["entries"][0]["prose"] == []


# ---- a batch of planned moves -------------------------------------------------------------------

@pytest.fixture
def move_tree(tmp_path):
    return _tree(tmp_path / "t", {
        "": {"top-plain": "x\n"},
        "a": {"a-cites-b": "Cites [[b-target]].\n"},
        "b": {"b-target": "Target.\n", "b-cites-a": "Cites [[a-cites-b]].\n"},
    })


def _moves(tmp_path, rows):
    f = tmp_path / "moves.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return f


def test_a_mutual_pair_lifted_together_is_clean(move_tree, tmp_path):
    root = move_tree
    f = _moves(tmp_path, [{"slug": "a-cites-b", "to": str(root)},
                          {"slug": "b-target", "to": str(root)},
                          {"slug": "b-cites-a", "to": str(root)}])
    code, out, _ = _run(["--root", str(root), "--moves", str(f), "--json"])
    assert code == 0, out
    assert json.loads(out)["data"]["conflicts"] == []


def test_lifting_one_fact_that_cites_one_left_below_is_a_stranded_outbound(move_tree, tmp_path):
    root = move_tree
    f = _moves(tmp_path, [{"slug": "a-cites-b", "to": str(root)}])
    code, out, _ = _run(["--root", str(root), "--moves", str(f), "--json"])
    assert code == 1
    conflicts = json.loads(out)["data"]["conflicts"]
    assert {(c["kind"], c["slug"], c["other"]) for c in conflicts} == {
        ("stranded-outbound", "a-cites-b", "b-target")}


def test_a_down_move_below_a_citer_is_a_dangling_inbound(move_tree, tmp_path):
    root = move_tree
    f = _moves(tmp_path, [{"slug": "a-cites-b", "to": str(root / "a" / "deeper")}])
    (root / "a" / "deeper").mkdir()
    code, out, _ = _run(["--root", str(root), "--moves", str(f), "--json"])
    assert code == 1
    kinds = {(c["kind"], c["other"]) for c in json.loads(out)["data"]["conflicts"]}
    assert ("dangling-inbound", "b-cites-a") in kinds


def test_a_stale_from_level_in_the_plan_is_refused_per_row(move_tree, tmp_path):
    root = move_tree
    f = _moves(tmp_path, [{"slug": "top-plain", "from": str(root / "a"), "to": str(root / "b")}])
    code, out, _ = _run(["--root", str(root), "--moves", str(f), "--json"])
    assert code == 1
    assert json.loads(out)["data"]["conflicts"][0]["kind"] == "stale-from"


def test_a_malformed_moves_file_is_exit_2(move_tree, tmp_path):
    f = tmp_path / "moves.jsonl"
    f.write_text("not json\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(move_tree), "--moves", str(f), "--json"])
    assert code == 2 and json.loads(out)["ok"] is False


def test_slugs_or_moves_is_required(move_tree):
    with pytest.raises(SystemExit):
        _run(["--root", str(move_tree)])


def test_a_relative_root_judges_like_an_absolute_one(move_tree, tmp_path, monkeypatch):
    # The plan's targets are resolved; the levels read under a relative --root once were not, so a
    # citer at "t/a" never counted as below a resolved target and every lift read as a conflict.
    root = move_tree
    f = _moves(tmp_path, [{"slug": "b-target", "to": str(root)}])
    code, out, _ = _run(["--root", str(root), "--moves", str(f), "--json"])
    assert (code, json.loads(out)["data"]["conflicts"]) == (0, []), out
    monkeypatch.chdir(root.parent)
    code, out, _ = _run(["--root", root.name, "--moves", str(f), "--json"])
    assert (code, json.loads(out)["data"]["conflicts"]) == (0, []), out
