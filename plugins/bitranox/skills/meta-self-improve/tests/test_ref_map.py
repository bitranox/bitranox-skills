"""Tests for ref_map.py - the inbound/outbound reference map a placement decision needs.

`move` refuses a DOWN-move that would dangle an inbound `[[ref]]`, and does not check the
outbound refs a fact makes at all, so lifting one silently strands every ref it makes to a fact
left below. Both questions are about the same map; this tool answers them before the move.
"""
import io
import json

import os
import sys
from pathlib import Path

import pytest

import ref_map

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store as US  # noqa: E402


def _tree(root, levels):
    """Build a curated tree: {level_relpath: {slug: body_text}} -> pointer blocks + central bodies."""
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        for slug in entries:
            lines.append("- [%s](mem:%s) - When something, do something." % (slug, slug))
        lines.append(US.INDEX_END)
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


def _plain_tree(tmp_path):
    return _tree(tmp_path / "t", {"": {"top-general": "A general rule.\n"},
                                  "p": {"leaf": "No refs.\n"}})


@pytest.mark.parametrize("ref", ["[[top-general|the general rule]]", "[[top general]]",
                                 "[[reference:top-general]]", "[[Top_General]]"])
def test_every_ref_spelling_the_engine_resolves_resolves_here_too(tmp_path, ref):
    """ref_map and the engine must agree on what a ref names: the engine strips a `|label` and
    folds whitespace, and ref_map reported both as DANGLING with no inbound edge."""
    root = _tree(tmp_path / "t", {"": {"top-general": "A general rule.\n"},
                                  "p": {"leaf": "Cites %s here.\n" % ref}})
    code, out, _ = _run(["--root", str(root), "leaf", "top-general", "--json"])
    entries = {e["slug"]: e for e in json.loads(out)["data"]["entries"]}
    assert code == 0, out
    assert entries["leaf"]["outbound"] == [{"slug": "top-general", "level": str(root)}]
    assert [r["slug"] for r in entries["top-general"]["inbound"]] == ["leaf"]


def test_a_ref_carried_only_by_the_pointer_hook_is_an_inbound_edge(tmp_path):
    """The engine's move guard reads the hook AND the body; a hook-only ref (the body's copy
    edited away) was invisible here, so the map said 'safe to move' where move refuses."""
    root = _plain_tree(tmp_path)
    level = root / "p" / "CLAUDE.local.md"
    text = level.read_text(encoding="utf-8")
    level.write_text(text.replace("- [leaf](mem:leaf) - When something, do something.",
                                  "- [leaf](mem:leaf) - When something, see [[top-general]]."),
                     encoding="utf-8")
    code, out, _ = _run(["--root", str(root), "top-general", "--json"])
    entry = json.loads(out)["data"]["entries"][0]
    assert code == 0
    assert [r["slug"] for r in entry["inbound"]] == ["leaf"]


def test_a_level_copied_under_a_vendor_dir_does_not_override_the_real_one(tmp_path):
    root = _plain_tree(tmp_path)
    vendored = root / "venv" / "lib"
    vendored.mkdir(parents=True)
    (vendored / "CLAUDE.local.md").write_text(
        (root / "p" / "CLAUDE.local.md").read_text(encoding="utf-8"), encoding="utf-8")
    code, out, _ = _run(["--root", str(root), "leaf", "--json"])
    assert code == 0
    assert json.loads(out)["data"]["entries"][0]["level"] == str(root / "p")


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="needs a non-root POSIX user for chmod 000 to deny a read")
def test_an_unreadable_body_is_an_error_not_a_missing_edge(tmp_path):
    root = _tree(tmp_path / "t", {"": {"top-general": "A general rule.\n"},
                                  "p": {"leaf": "Cites [[top-general]].\n"}})
    body = root / ".claude-memory" / "facts" / "leaf.md"
    body.chmod(0)
    try:
        code, out, err = _run(["--root", str(root), "top-general", "--json"])
    finally:
        body.chmod(0o644)
    assert code == 2
    assert json.loads(out)["ok"] is False
    assert "leaf.md" in err


def test_a_plain_dir_root_without_a_store_exits_2_with_a_json_envelope(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    code, out, err = _run(["--root", str(plain), "a", "--json"])
    assert code == 2
    payload = json.loads(out)
    assert payload["ok"] is False and ".claude-memory/facts" in payload["error"]
    assert "anchor" in err


def test_a_cp1252_console_survives_a_path_it_cannot_encode(tmp_path):
    import subprocess
    root = _tree(tmp_path / "日本", {"": {"a": "No refs.\n"}})
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONIOENCODING"] = "cp1252"
    r = subprocess.run([sys.executable, ref_map.__file__, "--root", str(root), "a"], env=env,
                       capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    assert "UnicodeEncodeError" not in r.stderr


def test_quoted_syntax_in_a_code_span_is_not_an_outbound_ref(tmp_path):
    """A fact teaching TOML quotes `[[tool.importlinter.contracts]]`; that is syntax, not a ref."""
    root = _tree(tmp_path / "t", {"": {"a": "Declare `[[tool.importlinter.contracts]]` in pyproject.\n"}})
    code, out, _ = _run(["--root", str(root), "a"])
    assert code == 0, out
    assert "importlinter" not in out
