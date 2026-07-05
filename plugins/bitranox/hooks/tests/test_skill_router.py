"""Tests for build_skill_triggers.py + skill-router.py. ASCII."""
import io
import json
import sys

import pytest

import build_skill_triggers as B
import skill_router as R


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _skill(root, name, desc):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: %s\n---\n\n# x\n" % (name, desc),
                                encoding="utf-8")


def test_build_derives_keywords_from_descriptions(tmp_path):
    _skill(tmp_path, "frobnicate", "Use when frobnicating widgets fails with gasket errors")
    _skill(tmp_path, "nodesc", "Use when it is")            # too few keywords -> skipped
    m = B.build(tmp_path)
    assert "frobnicate" in m and "frobnicating" in m["frobnicate"] and "gasket" in m["frobnicate"]
    assert "nodesc" not in m


def test_build_check_detects_stale_map(tmp_path):
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "map.json"
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out)]) == 0
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 0
    _skill(tmp_path, "beta", "Use when beta gadgets rust in coastal climates")
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 1


def test_match_needs_two_distinct_hits_word_boundary():
    triggers = {"frob": ["frobnicating", "widgets", "gasket"]}
    assert R.match("my frobnicating widgets are broken", triggers) == [("frob", 2)]
    assert R.match("just one widgets mention", triggers) == []            # 1 hit < MIN_HITS
    assert R.match("megawidgetsx frobnicatingly", triggers) == []         # boundary: no substring hits


def test_router_injects_once_per_session(monkeypatch, capsys):
    trig = {"frob": ["frobnicating", "widgets"]}
    monkeypatch.setattr(R, "load_triggers", lambda: trig)

    def run(prompt, sid="s1"):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
            {"prompt": prompt, "cwd": "/p/x", "session_id": sid})))
        rc = R.main()
        return rc, capsys.readouterr().out

    rc, out = run("frobnicating the widgets broke")
    assert rc == 0 and "bitranox:frob" in out and "Skill tool" in out
    rc, out = run("frobnicating the widgets again")
    assert rc == 0 and out == ""                       # per-session dedup: nudged once
    rc, out = run("frobnicating the widgets anew", sid="s2")
    assert "bitranox:frob" in out                      # a new session nudges again


def test_router_silent_on_no_match(monkeypatch, capsys):
    monkeypatch.setattr(R, "load_triggers", lambda: {"frob": ["frobnicating", "widgets"]})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": "completely unrelated question", "cwd": "/p/x", "session_id": "s"})))
    assert R.main() == 0 and capsys.readouterr().out == ""


def test_shipped_trigger_map_in_sync_with_descriptions():
    # the committed map must match the skills' current descriptions (rebuild on description change)
    import build_skill_triggers as B2
    assert B2.main(["--check"]) == 0
