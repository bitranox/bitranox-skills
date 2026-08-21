"""Tests for ref_map.py - the inbound/outbound reference map a placement decision needs.

`move` refuses a DOWN-move that would dangle an inbound `[[ref]]`, and does not check the
outbound refs a fact makes at all, so lifting one silently strands every ref it makes to a fact
left below. Both questions are about the same map; this tool answers them before the move.
"""
import io
import json

import pytest

import ref_map


def _tree(root, levels):
    """Build a curated tree: {level_relpath: {slug: body_text}} -> pointer blocks + central bodies."""
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = ["<!-- BITRANOX-MEMORY-INDEX:BEGIN managed -->", "", "## Memory index"]
        for slug in entries:
            lines.append("- [%s](mem:%s) - When something, do something." % (slug, slug))
        lines.append("<!-- BITRANOX-MEMORY-INDEX:END -->")
        (d / "CLAUDE.local.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        for slug, body in entries.items():
            (facts / ("%s.md" % slug)).write_text(body, encoding="utf-8")
    return root


@pytest.fixture
def tree(tmp_path):
    return _tree(tmp_path / "t", {
        "": {"top-general": "A general rule.\n"},
        "proj": {
            "leaf-cites-up": "Cites [[top-general]] for the general rule.\n",
            "leaf-plain": "No refs at all.\n",
        },
        "other": {"sibling-cites-leaf": "Cites [[leaf-plain]] sideways.\n"},
    })


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = ref_map.main(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_reports_the_level_a_slug_sits_at(tree):
    code, out, _ = _run(["--root", str(tree), "leaf-plain"])
    assert code == 0
    assert str(tree / "proj") in out


def test_reports_inbound_refs_which_is_what_blocks_a_down_move(tree):
    """A down-move is refused when something points AT the fact, so inbound must be listed."""
    _, out, _ = _run(["--root", str(tree), "leaf-plain"])
    assert "sibling-cites-leaf" in out


def test_reports_outbound_refs_which_move_does_not_guard(tree):
    """Promoting a fact strands the refs it MAKES; move never checks these, so the tool must."""
    _, out, _ = _run(["--root", str(tree), "leaf-cites-up"])
    assert "top-general" in out


def test_json_envelope_carries_levels_for_both_directions(tree):
    code, out, _ = _run(["--root", str(tree), "leaf-cites-up", "--json"])
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True and payload["command"] == "ref-map"
    entry = payload["data"]["entries"][0]
    assert entry["slug"] == "leaf-cites-up"
    assert entry["level"] == str(tree / "proj")
    assert entry["outbound"] == [{"slug": "top-general", "level": str(tree)}]
    assert entry["inbound"] == []


def test_an_unknown_slug_exits_1_and_says_so_rather_than_reporting_an_empty_map(tree):
    """'No refs' and 'no such fact' must not print the same, or the answer is worthless."""
    code, out, _ = _run(["--root", str(tree), "no-such-slug"])
    assert code == 1
    assert "no-such-slug" in out and "unknown" in out.lower()


def test_json_stays_parseable_on_the_failure_path(tree):
    code, out, _ = _run(["--root", str(tree), "no-such-slug", "--json"])
    assert code == 1
    payload = json.loads(out)
    assert payload["ok"] is False


def test_a_dangling_outbound_ref_is_reported_as_dangling(tmp_path):
    """A ref whose target exists nowhere is the defect the map has to surface."""
    root = _tree(tmp_path / "t", {"": {"a": "Cites [[nowhere]].\n"}})
    code, out, _ = _run(["--root", str(root), "a"])
    assert code == 1
    assert "nowhere" in out and "dangling" in out.lower()


def test_underscores_and_dashes_are_the_same_slug(tmp_path):
    """The engine canonicalises `_` to `-`, so a ref written with underscores is NOT dangling."""
    root = _tree(tmp_path / "t", {"": {"top-general": "x\n"}, "p": {"b": "Cites [[top_general]].\n"}})
    code, out, _ = _run(["--root", str(root), "b"])
    assert code == 0, out
    assert "dangling" not in out.lower()


def test_a_missing_root_is_an_error_not_an_empty_map(tmp_path):
    code, _, err = _run(["--root", str(tmp_path / "nope"), "a"])
    assert code == 2
    assert "nope" in err


def test_warnings_go_to_stderr_so_json_stays_parseable(tmp_path):
    code, out, err = _run(["--root", str(tmp_path / "nope"), "a", "--json"])
    assert code == 2
    json.loads(out)
    assert err.strip()


def test_quoted_syntax_in_a_code_span_is_not_an_outbound_ref(tmp_path):
    """A fact teaching TOML quotes `[[tool.importlinter.contracts]]`; that is syntax, not a ref."""
    root = _tree(tmp_path / "t", {"": {"a": "Declare `[[tool.importlinter.contracts]]` in pyproject.\n"}})
    code, out, _ = _run(["--root", str(root), "a"])
    assert code == 0, out
    assert "importlinter" not in out
