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


# ---- the 14 head keywords crowd out the strings a user in trouble types verbatim -----------------
# A description is trigger-first, so its head is prose about the SITUATION and its tail holds the
# literal error codes and messages. Taking the first 14 by position therefore keeps generic words
# and drops the identifiers - measured across 80 shipped skills, `code` (shared by 14 of them)
# reaches the map while `0xc1900200`, `windows.old` and `rueckgaengig` do not.

def test_distinctive_admits_identifiers():
    for tok in ("0xc1900200", "setup.exe", "windows.old", "in-place", "non-constant-time", "utf-8"):
        assert B.distinctive(tok), tok


def test_distinctive_rejects_plain_words_however_long():
    # A length bar cannot separate these: `condition` and `description` are ordinary English and
    # ordinary in prompts (33 and 50 of 2146), and admitting them put coding-rust on a prompt about
    # reviewing skills. Only the identifier shape has zero such tokens.
    for tok in ("line", "report", "main", "sleep", "itself", "denied",
                "condition", "description", "interface", "documentation"):
        assert not B.distinctive(tok), tok


def test_select_keeps_the_head_in_order():
    toks = ["kw%02d" % i for i in range(20)]
    assert B.select(toks, {t: 1 for t in toks})[:14] == toks[:14]


def test_select_appends_a_unique_identifier_from_the_tail():
    toks = ["a%d" % i for i in range(14)] + ["0xc1900200"]
    got = B.select(toks, {t: 1 for t in toks})
    assert "0xc1900200" in got


def test_select_does_not_append_a_plain_tail_word():
    toks = ["a%d" % i for i in range(14)] + ["itself"]
    assert "itself" not in B.select(toks, {t: 1 for t in toks})


def test_select_does_not_append_a_token_another_skill_also_claims():
    # a shared token cannot discriminate, and it is what lets one skill out-count the rest
    toks = ["a%d" % i for i in range(14)] + ["0xc1900200"]
    assert "0xc1900200" not in B.select(toks, {"0xc1900200": 2})


def test_select_bounds_how_many_it_appends():
    tail = ["0xdead%04d" % i for i in range(30)]
    toks = ["a%d" % i for i in range(14)] + tail
    got = B.select(toks, {t: 1 for t in toks})
    assert len(got) == 24                       # 14 head + at most 10 appended


def test_build_lands_a_tail_error_code_in_the_map(tmp_path):
    _skill(tmp_path, "servicing", "Use when a Windows machine will not install a cumulative update, "
                                  "its component store is damaged, DISM fails with an opaque code "
                                  "and setup exits 0xc1900200 on the apply reboot")
    m = B.build(tmp_path)
    assert "0xc1900200" in m["servicing"]


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
