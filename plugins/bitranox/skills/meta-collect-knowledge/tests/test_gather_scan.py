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


def test_extract_keywords_drops_opaque_ids():
    # tool-use IDs, UUIDs, long hex hashes, pure digits, and path slugs are not topical signal
    text = ("fix the bindsnap regression toolu_01wwyudqrf8jwnj7rk7xk2q5 "
            "e5b12557-c410-4fef-9212-ce9d71b146eb a367bb47f4cb34eb5 12345 "
            "home-user-projects-app-src-main-module")   # path slug: >=4 hyphens
    kws = G.extract_keywords(text)
    assert "bindsnap" in kws and "regression" in kws        # real terms kept
    assert not any(G._is_junk_token(k) for k in kws)        # no junk survives
    assert "12345" not in kws and "a367bb47f4cb34eb5" not in kws


def test_extract_keywords_keeps_real_hyphenated_terms():
    # the junk guard must NOT eat legitimate multi-word technical terms
    kws = G.extract_keywords("run meta-dream-global-deep against px-websrv-media")
    assert "meta-dream-global-deep" in kws and "px-websrv-media" in kws


def test_scan_matches_and_skips(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("Fleet SSH keyfile location and subnet", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("nothing relevant here", encoding="utf-8")
    hits = G.scan(["fleet", "ssh"], [a, b])
    assert set(hits[str(a)]) == {"fleet", "ssh"}     # case-insensitive
    assert str(b) not in hits


def _ws(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    ws = tmp_path / "ws"
    (ws).mkdir()
    (ws / "CLAUDE.md").write_text("root rules", encoding="utf-8")
    cur = ws / "projA"
    cur.mkdir()
    (cur / "CLAUDE.md").write_text("projA rules", encoding="utf-8")
    sib = ws / "projB"
    sib.mkdir()
    (sib / "CLAUDE.md").write_text("projB rules", encoding="utf-8")
    vend = ws / "node_modules" / "pkg"
    vend.mkdir(parents=True)
    (vend / "CLAUDE.md").write_text("vendor", encoding="utf-8")
    return ws, cur


def test_discover_claude_md_finds_siblings_excludes_chain_and_vendor(tmp_path, monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    names = {Path(p).parent.name for p in G.discover_claude_md(str(cur))}
    assert "projB" in names        # sibling project's CLAUDE.md surfaced
    assert "projA" not in names    # current project's own CLAUDE.md excluded (already loaded)
    assert "ws" not in names       # workspace-root CLAUDE.md is in the current chain -> excluded
    assert "pkg" not in names      # vendored dir pruned


def test_discover_claude_md_caches_until_ttl(tmp_path, monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    first = {Path(p).parent.name for p in G.discover_claude_md(str(cur))}
    newer = ws / "projC"
    newer.mkdir()
    (newer / "CLAUDE.md").write_text("projC rules", encoding="utf-8")
    assert {Path(p).parent.name for p in G.discover_claude_md(str(cur))} == first   # cached: projC unseen
    assert "projC" in {Path(p).parent.name for p in G.discover_claude_md(str(cur), cache_ttl=0)}  # rebuild


def test_discover_claude_md_no_workspace_root(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    lonely = tmp_path / "nowhere" / "proj"
    lonely.mkdir(parents=True)
    assert G.discover_claude_md(str(lonely)) == []   # no ancestor CLAUDE.md -> nothing


def test_scan_is_word_boundary_not_substring(tmp_path):
    # the recall-precision bug: substring matching made "again" match "against", "test" match "latest".
    f = tmp_path / "c.md"
    f.write_text("verify the contract against the latest broker; the test passed", encoding="utf-8")
    hits = G.scan(["again", "test"], [f])
    assert hits.get(str(f)) == ["test"]              # standalone "test" matches; "again" != "against"


def test_extract_keywords_drops_filler(monkeypatch):
    # filler words (generic/conversational) are dropped via load_filler_words(proj); topical tokens survive.
    monkeypatch.setattr(sig, "load_filler_words", lambda proj=None: frozenset({"again", "previous", "normal"}))
    kws = G.extract_keywords("again the previous rabbitmq timeout looked normal", proj="/p/x")
    assert "rabbitmq" in kws and "timeout" in kws
    assert "again" not in kws and "previous" not in kws and "normal" not in kws


def test_extract_keywords_uses_shipped_baseline():
    # smoke: the real shipped baseline drops obvious filler but keeps a real topic.
    kws = G.extract_keywords("got again hits on the previous bindsnap normal run")
    assert "bindsnap" in kws
    assert not ({"got", "again", "hits", "previous", "normal"} & set(kws))


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


def test_discover_curated_finds_sibling_excludes_own_and_backups(tmp_path, monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    scope = "<!-- bitranox:self-learning -->\ns\n<!-- /bitranox:self-learning -->\n\n# Memory index\n"
    sib = ws / "projB" / ".claude-bx-selflearning"
    (sib / "facts").mkdir(parents=True)
    (sib / "index.md").write_text(scope + "\n- [X](#x) - projB fact\n", encoding="utf-8")
    (sib / "facts" / "big.md").write_text("projB heavy body", encoding="utf-8")
    own = cur / ".claude-bx-selflearning"
    (own / "facts").mkdir(parents=True)
    (own / "index.md").write_text(scope, encoding="utf-8")
    (own / "facts" / "mine.md").write_text("own heavy", encoding="utf-8")
    bak = ws / "projB" / ".claude-bx-selflearning.bak-123"
    bak.mkdir()
    (bak / "index.md").write_text("stale", encoding="utf-8")

    got = G.discover_curated(str(cur), str(cur))
    assert any(p.endswith("projB/.claude-bx-selflearning/index.md") for p in got)   # sibling surfaced
    assert any(p.endswith("/facts/big.md") for p in got)
    assert str(own / "index.md") not in got                                          # own index.md excluded
    assert any(p.endswith("/facts/mine.md") for p in got)                             # own facts KEPT
    assert not any(".bak-" in p for p in got)                                         # backups ignored


def test_gather_cli_adds_mcp_candidates_when_enabled(tmp_path, monkeypatch, capsys):
    ws, cur = _ws(tmp_path, monkeypatch)
    (cur / "note.md").write_text("zorblax frobnicator config", encoding="utf-8")  # ensure a keyword exists
    import mcp_search
    monkeypatch.setattr(mcp_search, "enabled", lambda: True)
    monkeypatch.setattr(mcp_search, "covers", lambda p: True)
    monkeypatch.setattr(mcp_search, "search", lambda topic, **k: ["notes/relevant"])
    G.main(["--topic", "zorblax frobnicator", "--self", str(cur)])
    out = capsys.readouterr().out
    assert "MCP\tnotes/relevant" in out and "MCP-CANDIDATES: 1" in out


def test_gather_cli_no_mcp_when_disabled(tmp_path, monkeypatch, capsys):
    ws, cur = _ws(tmp_path, monkeypatch)
    import mcp_search
    monkeypatch.setattr(mcp_search, "enabled", lambda: False)
    G.main(["--topic", "zorblax frobnicator", "--self", str(cur)])
    out = capsys.readouterr().out
    assert "MCP-CANDIDATES" not in out
