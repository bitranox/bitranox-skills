"""Tests for gather_scan.py (cross-tree gather stage-1: keyword grep). All content ASCII."""

from pathlib import Path

import pytest

import gather_scan as G
import self_improve_signals as sig


def test_extract_keywords_drops_stopwords_and_dedups():
    kws = G.extract_keywords("Use the Shopify API with backoff for the Shopify API")
    assert "shopify" in kws and "backoff" in kws
    assert "the" not in kws and "for" not in kws and "use" not in kws
    assert kws.count("shopify") == 1


def test_extract_keywords_caps():
    kws = G.extract_keywords(" ".join("term%02d" % i for i in range(50)), max_n=5)
    assert len(kws) == 5


def test_scan_matches_and_skips(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("Fleet SSH keyfile location and subnet", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("nothing relevant here", encoding="utf-8")
    hits = G.scan(["fleet", "ssh"], [a, b])
    assert set(hits[str(a)]) == {"fleet", "ssh"}     # case-insensitive
    assert str(b) not in hits


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(proj, name, text):
    d = sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return d


def test_discover_excludes_self_includes_others_and_global(home):
    _mem("/p/self", "s.md", "self only")
    _mem("/p/other", "o.md", "other tree")
    g = sig.global_rules_dir()
    g.mkdir(parents=True, exist_ok=True)
    (g / "r.md").write_text("a global rule", encoding="utf-8")
    files = [str(f) for f in G.discover_files("/p/self")]
    assert not any("/-p-self/" in f for f in files)        # current project excluded
    assert any("/-p-other/" in f for f in files)           # other trees included
    assert any(str(g) in f for f in files)                 # global rules included


def test_main_reports_candidates_from_other_tree(home, capsys):
    _mem("/p/self", "s.md", "fleet ssh self")
    _mem("/p/other", "o.md", "fleet ssh in another tree")
    rc = G.main(["--topic", "fleet ssh access", "--self", "/p/self"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CANDIDATES:" in out
    assert "/-p-other/" in out          # found the other tree's note
    assert "/-p-self/" not in out       # not the current project's own
