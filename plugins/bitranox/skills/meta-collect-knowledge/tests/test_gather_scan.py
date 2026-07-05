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
    kws = G.extract_keywords("run meta-dream-crosstree-deep against px-websrv-media")
    assert "meta-dream-crosstree-deep" in kws and "px-websrv-media" in kws


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
    ws = h / "ws"                     # inside fake HOME: the ancestor walk stops at $HOME (hermetic)
    ws.mkdir()
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
    lonely = h / "nowhere" / "proj"   # inside fake HOME (hermetic: the walk stops at $HOME)
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


def test_discover_excludes_self_includes_others_and_global(home, tmp_path):
    top = tmp_path / "top"                                  # topmost CLAUDE.md -> the global tier
    self_proj = top / "self"
    self_proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x", encoding="utf-8")
    _mem(str(self_proj), "s.md", "self only")
    _mem("/p/other", "o.md", "other tree")
    g = sig.global_rules_dir(str(self_proj))               # = top/.claude-memory (not ~/.claude)
    (g / "facts").mkdir(parents=True, exist_ok=True)
    (g / "facts" / "r.md").write_text("a global rule", encoding="utf-8")     # flat body
    (g / "facts" / "ab").mkdir()
    (g / "facts" / "ab" / "ab12.md").write_text("a sharded body", encoding="utf-8")
    (g / ".archive").mkdir()
    (g / ".archive" / "old.md").write_text("archived - must NOT be scanned", encoding="utf-8")
    files = [str(f) for f in G.discover_files(str(self_proj))]
    self_native = str(sig.memory_dir(str(self_proj)).resolve())
    assert not any(self_native in f for f in files)        # current project's own memory excluded
    assert any("/-p-other/" in f for f in files)           # other trees included
    assert any(str(g / "facts" / "r.md") == f for f in files)          # flat body included
    assert any(str(g / "facts" / "ab" / "ab12.md") == f for f in files)  # sharded body included
    assert not any(".archive" in f for f in files)                      # archive excluded


def test_main_reports_candidates_from_other_tree(home, capsys):
    _mem("/p/self", "s.md", "fleet ssh self")
    _mem("/p/other", "o.md", "fleet ssh in another tree")
    rc = G.main(["--topic", "fleet ssh access", "--self", "/p/self"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CANDIDATES:" in out
    assert "/-p-other/" in out          # found the other tree's note
    assert "/-p-self/" not in out       # not the current project's own


def test_discover_curated_finds_slug_stores_excludes_backups_and_archive(tmp_path, monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    facts = ws / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (facts / "fleet-ssh.md").write_text("fleet ssh keyfile body", encoding="utf-8")
    (ws / ".claude-memory" / ".archive").mkdir()                       # the real archive location
    (ws / ".claude-memory" / ".archive" / "dead.md").write_text("archived", encoding="utf-8")
    (facts / ".archive").mkdir()                                       # defensive: even a stray one
    (facts / ".archive" / "dead2.md").write_text("archived2", encoding="utf-8")
    bak = ws / ".claude-memory.bak-123"
    bak.mkdir()
    (bak / "stale.md").write_text("stale", encoding="utf-8")

    got = G.discover_curated(str(cur), str(cur))
    assert any(p.endswith("/.claude-memory/facts/fleet-ssh.md") for p in got)   # slug body surfaced
    assert not any(".archive" in p for p in got)                                # archive never scanned
    assert not any(".bak-" in p for p in got)                                   # backups ignored


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


def test_find_curated_stores_also_collects_central_uuid_store_bodies(tmp_path, monkeypatch):
    # the new mount-independent layout: bodies under <anchor>/.claude-memory/facts/<shard>/<uuid>.md
    ws, cur = _ws(tmp_path, monkeypatch)
    facts = ws / "projB" / ".claude-memory" / "facts" / "ab"
    facts.mkdir(parents=True)
    (facts / "abcd1234-0000-5000-8000-000000000000.md").write_text("central uuid body text", encoding="utf-8")
    got = G._find_curated_stores(str(ws))
    assert any(p.endswith("/facts/ab/abcd1234-0000-5000-8000-000000000000.md") for p in got)


def test_cli_groups_candidates_by_tree(tmp_path, monkeypatch, capsys):
    ws, cur = _ws(tmp_path, monkeypatch)
    facts = ws / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (facts / "zorblax-config.md").write_text("zorblax frobnicator configuration", encoding="utf-8")
    G.main(["--topic", "zorblax frobnicator", "--self", str(cur)])
    out = capsys.readouterr().out
    assert ("TREE: %s" % ws) in out                        # candidates carry their tree label
    assert "zorblax-config.md" in out and "1 tree(s)" in out


def test_cli_walled_scan_stays_in_tree_unless_cross_tree(tmp_path, monkeypatch, capsys):
    import json as _json
    ws, cur = _ws(tmp_path, monkeypatch)
    (ws / ".claude-memory").mkdir()                        # anchor colocation for THIS tree
    other = ws.parent / "othertree"
    (other / ".claude-memory" / "facts").mkdir(parents=True)
    (other / "CLAUDE.md").write_text("other top\n", encoding="utf-8")
    (other / ".claude-memory" / "facts" / "zorblax-note.md").write_text(
        "zorblax frobnicator elsewhere", encoding="utf-8")
    (Path(str(tmp_path)) / "home" / ".claude" / ".bitranox-memory.json").write_text(
        _json.dumps({"cross_tree_search": False}), encoding="utf-8")
    # walled: the other tree's hit must NOT appear (scan sources filtered to this tree's anchor)
    G.main(["--topic", "zorblax frobnicator", "--self", str(cur)])
    out = capsys.readouterr().out
    assert "othertree" not in out
    # explicit --cross-tree: the deliberate act crosses the wall, labeled
    G.main(["--topic", "zorblax frobnicator", "--self", str(cur), "--cross-tree"])
    out = capsys.readouterr().out
    assert "othertree" in out and "TREE:" in out
