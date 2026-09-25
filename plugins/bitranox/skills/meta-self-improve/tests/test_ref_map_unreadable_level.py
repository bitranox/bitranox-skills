"""ref_map exits 2, not 1, when the level walk cannot read a level file.

Its docstring promises 2 for "a level file or fact body that cannot be read", and it caught
OSError for that. The engine's walk raises `TreeWalkError` for an undecodable level file, which is
not an OSError, so it escaped as a traceback and the process exited 1 - the code for "a slug is
unknown or has a dangling ref". All content ASCII.
"""
import io
import json
import sys
from pathlib import Path

import pytest

import ref_map

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store as US  # noqa: E402


@pytest.fixture
def tree(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    root = tmp_path / "t"
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    for rel, slug in (("", "top-rule"), ("sub", "sub-rule")):
        level = root / rel if rel else root
        level.mkdir(exist_ok=True)
        (level / "CLAUDE.local.md").write_text(
            "%s\n\n## Memory index\n- [%s](mem:%s) - When x, do y.\n%s\n"
            % (US.INDEX_BEGIN, slug, slug, US.INDEX_END), encoding="utf-8")
        (facts / (slug + ".md")).write_text("A rule.\n", encoding="utf-8")
    return root


def _run(args):
    out, err = io.StringIO(), io.StringIO()
    return ref_map.main(args, out=out, err=err), out.getvalue(), err.getvalue()


@pytest.mark.parametrize("as_json", [False, True])
def test_an_undecodable_level_file_exits_two_naming_it(tree, as_json):
    bad = tree / "sub" / "CLAUDE.local.md"
    bad.write_bytes(bad.read_bytes() + b"caf\xe9\n")
    code, out, err = _run(["--root", str(tree), "top-rule"] + (["--json"] if as_json else []))
    assert code == 2
    assert str(bad) in err and "UTF-8" in err
    if as_json:
        assert json.loads(out)["ok"] is False


def test_an_undecodable_body_exits_two_like_the_engine_scan(tree):
    """The engine's inbound scan (what `move` consults) refuses a body that is not UTF-8; ref_map
    replaced the bad bytes and answered anyway, so the two could disagree about one tree."""
    bad = tree / ".claude-memory" / "facts" / "sub-rule.md"
    bad.write_bytes(b"Cites [[top-rule]] caf\xe9.\n")
    code, _, err = _run(["--root", str(tree), "top-rule"])
    assert code == 2 and str(bad) in err


def test_control_the_same_tree_saved_as_utf8_maps(tree):
    code, out, _ = _run(["--root", str(tree), "top-rule"])
    assert code == 0 and "top-rule" in out
