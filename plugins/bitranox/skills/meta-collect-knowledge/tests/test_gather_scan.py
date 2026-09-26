"""Tests for gather_scan.py (cross-tree gather stage-1: keyword grep). All content ASCII."""

import os
from pathlib import Path

import pytest

import gather_scan as G
import self_improve_signals as sig


def fwd(text):
    """Path text with forward slashes, so an assertion describes SHAPE, not the host's separator.

    gather_scan returns and prints NATIVE paths, which is right for whoever reads them. But an
    assertion spelled "/-p-other/" then means two different things per platform: on Windows the
    positive ones simply failed, and - worse - the NEGATIVE ones ("/-p-self/" not in out) passed
    VACUOUSLY, because a shape that can never appear can never be found missing. Normalising the
    text under test keeps one spelling honest on both.
    """
    return str(text).replace(os.sep, "/")


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
    assert any("/-p-other/" in fwd(f) for f in files)           # other trees included
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
    assert "/-p-other/" in fwd(out)     # found the other tree's note
    assert "/-p-self/" not in fwd(out)  # not the current project's own


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
    assert any(fwd(p).endswith("/.claude-memory/facts/fleet-ssh.md") for p in got)   # slug body surfaced
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
    assert "MCP\tnotes/relevant" in fwd(out) and "MCP-CANDIDATES: 1" in out


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
    assert any(fwd(p).endswith("/facts/ab/abcd1234-0000-5000-8000-000000000000.md") for p in got)


def _home_root(tmp_path, monkeypatch):
    """Isolate HOME (where the dir-cache lives) and return a fresh roots dir to seed stores under."""
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    root = tmp_path / "trees"
    root.mkdir()
    return root


def _seed_store(root, name, *facts):
    fdir = root / name / ".claude-memory" / "facts"
    fdir.mkdir(parents=True, exist_ok=True)
    for fn in facts:
        (fdir / fn).write_text("body of " + fn, encoding="utf-8")
    return fdir


def test_find_curated_stores_reglobs_fresh_facts_after_dir_cache(tmp_path, monkeypatch):
    # a fact dreamed AFTER the dir-walk is cached must still surface (facts are globbed fresh)
    root = _home_root(tmp_path, monkeypatch)
    _seed_store(root, "projA", "one.md")
    assert any(fwd(p).endswith("/facts/one.md") for p in G._find_curated_stores(str(root)))
    (root / "projA" / ".claude-memory" / "facts" / "two.md").write_text("second", encoding="utf-8")
    assert any(fwd(p).endswith("/facts/two.md") for p in G._find_curated_stores(str(root)))


def test_curated_store_dirs_caches_walk_within_ttl(tmp_path, monkeypatch):
    root = _home_root(tmp_path, monkeypatch)
    _seed_store(root, "projA", "one.md")
    calls = {"n": 0}
    real = G._walk_store_dirs
    monkeypatch.setattr(G, "_walk_store_dirs", lambda r: (calls.__setitem__("n", calls["n"] + 1), real(r))[1])
    G._curated_store_dirs(str(root))
    G._curated_store_dirs(str(root))
    assert calls["n"] == 1                                   # second call served from cache, no re-walk


def test_new_store_dir_busts_cache_only_on_generation_bump(tmp_path, monkeypatch):
    root = _home_root(tmp_path, monkeypatch)
    _seed_store(root, "projA", "one.md")
    assert len(G._curated_store_dirs(str(root))) == 1
    _seed_store(root, "projB", "two.md")                     # a brand-new store dir appears
    assert len(G._curated_store_dirs(str(root))) == 1        # still cached: new dir not yet seen
    sig.bump_stores_generation()                             # engine calls this when it creates a store
    assert len(G._curated_store_dirs(str(root))) == 2        # generation bump busts the cache -> re-walk


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


# ---- debounce store ------------------------------------------------------------------------------

def test_a_freshly_marked_pair_reads_back_as_gathered(tmp_path, monkeypatch):
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    assert G.already_gathered("/p/alpha", "zfs snapshots") is False
    G.mark_gathered("/p/alpha", "zfs snapshots")
    assert G.already_gathered("/p/alpha", "zfs snapshots") is True


def test_the_debounce_is_per_project_and_per_topic(tmp_path, monkeypatch):
    """The negative: marking one pair must not silence a different project or a different topic."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    G.mark_gathered("/p/alpha", "zfs snapshots")
    assert G.already_gathered("/p/beta", "zfs snapshots") is False
    assert G.already_gathered("/p/alpha", "pfsense rules") is False


def test_marking_twice_records_one_row(tmp_path, monkeypatch):
    """Re-gathering the same topic must not grow the file without bound."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    G.mark_gathered("/p/alpha", "zfs snapshots")
    G.mark_gathered("/p/alpha", "zfs snapshots")
    rows = [ln for ln in (tmp_path / G.GATHERED_FILE).read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 1


def test_a_topic_matches_regardless_of_case_and_surrounding_space(tmp_path, monkeypatch):
    """A topic is free text a caller retypes; exact-match would debounce almost nothing."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    G.mark_gathered("/p/alpha", "  ZFS Snapshots ")
    assert G.already_gathered("/p/alpha", "zfs snapshots") is True


def test_a_tab_in_the_topic_cannot_forge_a_second_field(tmp_path, monkeypatch):
    """The store is TSV; an unescaped tab in free text would split one row into a wrong pair."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    G.mark_gathered("/p/alpha", "zfs\tsnapshots")
    assert G.already_gathered("/p/alpha", "zfs\tsnapshots") is True
    assert G.already_gathered("/p/alpha", "snapshots") is False


def test_an_unreadable_store_reports_not_gathered_rather_than_raising(tmp_path, monkeypatch):
    """Debounce is an optimisation: losing it costs a re-grep, and must never break a gather."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path / "nonexistent")
    assert G.already_gathered("/p/alpha", "zfs snapshots") is False


def test_seen_exits_zero_when_marked_and_one_when_not(tmp_path, monkeypatch, capsys):
    """Exit-code contract: 0 = yes already gathered, 1 = no. Format-independent, per house rule."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--seen"]) == 1
    G.mark_gathered("/p/alpha", "zfs snapshots")
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--seen"]) == 0


def test_seen_answers_without_running_the_scan(tmp_path, monkeypatch):
    """--seen is the cheap pre-check; if it walked the tree it would defeat its own purpose."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    called = []
    monkeypatch.setattr(G, "discover_files", lambda *a, **k: called.append(1) or [])
    G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--seen"])
    assert called == [], "--seen ran the file discovery"


def test_mark_records_the_pair_and_exits_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--mark"]) == 0
    assert G.already_gathered("/p/alpha", "zfs snapshots") is True


def test_mark_does_not_run_a_scan_either(tmp_path, monkeypatch):
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    called = []
    monkeypatch.setattr(G, "discover_files", lambda *a, **k: called.append(1) or [])
    G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--mark"])
    assert called == []


def test_a_plain_scan_still_ignores_the_debounce(tmp_path, monkeypatch):
    """The negative that matters: marking a topic must NOT silently stop an explicit scan.

    Debounce is advice to the caller, not a gate on the tool - a scan asked for is a scan run."""
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    G.mark_gathered("/p/alpha", "zfs snapshots")
    called = []
    monkeypatch.setattr(G, "discover_files", lambda *a, **k: called.append(1) or [])
    monkeypatch.setattr(G, "discover_curated", lambda *a, **k: [])
    G.main(["--topic", "zfs snapshots", "--self", "/p/alpha"])
    assert called == [1], "a marked topic suppressed an explicitly requested scan"


# ---- one bad file must not end the gather -------------------------------------------------------

def test_scan_skips_an_undecodable_file_and_keeps_its_siblings(tmp_path):
    bad = tmp_path / "latin1.md"
    bad.write_bytes(b"zorblax caf\xe9 in latin-1")
    good = tmp_path / "good.md"
    good.write_text("zorblax in utf-8", encoding="utf-8")
    skipped = []
    hits = G.scan(["zorblax"], [bad, good], skipped=skipped)
    assert list(hits) == [str(good)]
    assert [p for p, _ in skipped] == [str(bad)]


def test_scan_without_a_skipped_list_still_skips_quietly(tmp_path):
    bad = tmp_path / "latin1.md"
    bad.write_bytes(b"zorblax caf\xe9")
    assert G.scan(["zorblax"], [bad]) == {}


def test_cli_warns_about_an_undecodable_note_and_still_reports_the_rest(home, capsys):
    d = _mem("/p/other", "o.md", "fleet ssh in another tree")
    (d / "latin1.md").write_bytes(b"fleet ssh caf\xe9")
    rc = G.main(["--topic", "fleet ssh access", "--self", "/p/self"])
    cap = capsys.readouterr()
    assert rc == 0
    assert "CANDIDATES: 1 in 1 tree(s)" in cap.out
    assert "latin1.md" in cap.err and "skipped" in cap.err


def test_a_bom_prefixed_note_still_matches(tmp_path):
    f = tmp_path / "bom.md"
    f.write_bytes(b"\xef\xbb\xbfzorblax at the very start")
    assert G.scan(["zorblax"], [f]) == {str(f): ["zorblax"]}


# ---- --self spelling: symlink, trailing separator, "." ------------------------------------------

def _symlinked_ws(tmp_path, monkeypatch):
    """A workspace reached through a symlink, with a same-tree sibling store and a tree-top fact."""
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    real = h / "real" / "ws"
    for sub in ("projA", "projB"):
        (real / sub).mkdir(parents=True)
        (real / sub / "CLAUDE.md").write_text(sub, encoding="utf-8")
    (real / "CLAUDE.md").write_text("root", encoding="utf-8")
    (real / ".claude-memory" / "facts").mkdir(parents=True)
    (real / ".claude-memory" / "facts" / "zorblax.md").write_text("zorblax top", encoding="utf-8")
    (real / "projB" / ".claude-memory" / "facts").mkdir(parents=True)
    (real / "projB" / ".claude-memory" / "facts" / "sib.md").write_text("zorblax sib",
                                                                         encoding="utf-8")
    link = h / "link"
    try:
        os.symlink(str(h / "real"), str(link), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable here")
    return h, real, link / "ws" / "projA"


def _cfg(home_dir, **kv):
    import json as _json
    (home_dir / ".claude" / ".bitranox-memory.json").write_text(_json.dumps(kv), encoding="utf-8")


def test_a_symlinked_self_reports_one_tree_once(tmp_path, monkeypatch, capsys):
    h, real, via_link = _symlinked_ws(tmp_path, monkeypatch)
    _cfg(h, discovery_roots=[str(real)])
    assert G.main(["--topic", "zorblax", "--self", str(via_link)]) == 0
    out = capsys.readouterr().out
    assert out.count("TREE: ") == 1, out
    assert out.count("zorblax.md") == 1, out
    assert "2 in 1 tree(s)" in out, out


def test_a_symlinked_self_keeps_same_tree_stores_when_walled(tmp_path, monkeypatch, capsys):
    h, real, via_link = _symlinked_ws(tmp_path, monkeypatch)
    _cfg(h, cross_tree_search=False)
    assert G.main(["--topic", "zorblax", "--self", str(via_link)]) == 0
    out = capsys.readouterr().out
    assert "sib.md" in out and "zorblax.md" in out, out
    assert "2 in 1 tree(s)" in out, out


def test_self_with_a_trailing_separator_still_excludes_own_memory(home, capsys, tmp_path):
    me = tmp_path / "p" / "self"
    me.mkdir(parents=True)
    _mem(str(me), "s.md", "fleet ssh self")
    _mem("/p/other", "o.md", "fleet ssh other")
    assert G.main(["--topic", "fleet ssh", "--self", str(me) + os.sep]) == 0
    out = fwd(capsys.readouterr().out)
    assert "s.md" not in out and "o.md" in out, out
    assert "CANDIDATES: 1 " in out


def test_self_given_as_dot_still_excludes_own_memory(home, capsys, tmp_path, monkeypatch):
    me = tmp_path / "p" / "self"
    me.mkdir(parents=True)
    _mem(str(me), "s.md", "fleet ssh self")
    _mem("/p/other", "o.md", "fleet ssh other")
    monkeypatch.chdir(me)
    assert G.main(["--topic", "fleet ssh", "--self", "."]) == 0
    out = fwd(capsys.readouterr().out)
    assert "s.md" not in out and "o.md" in out, out


# ---- non-ASCII topics ---------------------------------------------------------------------------

def test_extract_keywords_keeps_a_non_ascii_word_whole():
    assert G.extract_keywords("Schl\u00fcssel \u00dcbersetzung") == ["schl\u00fcssel",
                                                                    "\u00fcbersetzung"]


def test_extract_keywords_keeps_cyrillic_words():
    kws = G.extract_keywords("\u0441\u043d\u0438\u043c\u043e\u043a zfs")
    assert kws == ["\u0441\u043d\u0438\u043c\u043e\u043a", "zfs"]


def test_a_non_ascii_keyword_does_not_match_an_unrelated_word(tmp_path):
    key = tmp_path / "key.md"
    key.write_text("Der Schl\u00fcssel liegt im Tresor", encoding="utf-8")
    bowl = tmp_path / "bowl.md"
    bowl.write_text("Die Sch\u00fcssel ist voll", encoding="utf-8")
    kws = G.extract_keywords("Schl\u00fcssel")
    assert G.scan(kws, [key, bowl]) == {str(key): ["schl\u00fcssel"]}


def test_a_decomposed_spelling_in_a_note_still_matches(tmp_path):
    f = tmp_path / "nfd.md"
    f.write_text("Der Schlu\u0308ssel", encoding="utf-8")    # u + combining diaeresis
    assert G.scan(G.extract_keywords("Schl\u00fcssel"), [f]) == {str(f): ["schl\u00fcssel"]}


def test_ascii_boundaries_are_unchanged_by_unicode_matching(tmp_path):
    f = tmp_path / "c.md"
    f.write_text("fleet_ssh and fleet-ssh and fleetssh", encoding="utf-8")
    assert G.scan(["ssh"], [f]) == {str(f): ["ssh"]}           # _ and - still separate words
    g = tmp_path / "d.md"
    g.write_text("fleetssh only", encoding="utf-8")
    assert G.scan(["ssh"], [g]) == {}


# ---- exit codes and explicit outcomes -----------------------------------------------------------

def test_mark_exits_two_when_the_record_cannot_be_written(tmp_path, monkeypatch, capsys):
    blocker = tmp_path / "a-file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sig, "_audit_dir", lambda: blocker / "audit")   # parent is a FILE
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--mark"]) == 2
    assert "error" in capsys.readouterr().err


def test_mark_of_an_already_marked_pair_still_exits_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(sig, "_audit_dir", lambda: tmp_path)
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--mark"]) == 0
    assert G.main(["--topic", "zfs snapshots", "--self", "/p/alpha", "--mark"]) == 0


def test_no_usable_keywords_prints_an_explicit_zero_candidates_line(home, capsys):
    assert G.main(["--topic", "the rules", "--self", "/p/self"]) == 0
    out = capsys.readouterr().out
    assert "CANDIDATES: 0 (not scanned: no usable keywords from topic)" in out


def test_walled_without_an_anchor_prints_an_explicit_zero_candidates_line(home, capsys, tmp_path):
    _cfg(home, cross_tree_search=False)
    lonely = home / "nowhere"
    lonely.mkdir()
    assert G.main(["--topic", "zorblax", "--self", str(lonely)]) == 0
    out = capsys.readouterr().out
    assert "CANDIDATES: 0 (not scanned: no tree anchor" in out


def test_an_unexpected_error_exits_two_not_one(home, capsys, monkeypatch):
    # One is "not gathered" for --seen and must never double as "crashed". The fault is injected
    # at the discovery seam because no input crashes the scan on every platform: a NUL in --self
    # raises on POSIX but Windows' path functions accept it and the scan runs to 0 candidates.
    def boom(*args, **kwargs):
        raise RuntimeError("injected discovery fault")

    monkeypatch.setattr(G, "discover_files", boom)
    assert G.main(["--topic", "zorblax", "--self", "/p/a"]) == 2
    err = capsys.readouterr().err
    assert "error: RuntimeError: injected discovery fault" in err


def test_cp1252_stdout_does_not_crash_on_a_cjk_candidate(tmp_path):
    import subprocess
    import sys as _sys
    h = tmp_path / "home"
    d = h / ".claude" / "projects" / "-p-other" / "memory"
    d.mkdir(parents=True)
    (d / "n.md").write_text("\u65e5\u672c\u8a9e zorblax", encoding="utf-8")
    env = dict(os.environ, HOME=str(h), USERPROFILE=str(h), PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([_sys.executable, str(Path(G.__file__)), "--topic",
                        "\u65e5\u672c\u8a9e zorblax", "--self", "/p/self"],
                       capture_output=True, env=env, cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert b"CANDIDATES: 1" in r.stdout


# ---- Windows path case ---------------------------------------------------------------------------

def test_the_debounce_key_ignores_windows_path_case():
    import ntpath
    a = G._pair_key("C:\\Work\\Proj", "zfs", pathmod=ntpath)
    b = G._pair_key("c:\\work\\proj", "zfs", pathmod=ntpath)
    assert a == b


def test_the_tree_filter_ignores_windows_path_case():
    import ntpath
    files = ["c:\\work\\proj\\.claude-memory\\facts\\a.md", "c:\\other\\b.md"]
    assert G.within_tree(files, "C:\\Work\\Proj", pathmod=ntpath) == files[:1]


def test_the_tree_filter_does_not_take_a_sibling_sharing_a_prefix(tmp_path):
    (tmp_path / "proj").mkdir()
    (tmp_path / "project2").mkdir()
    files = [str(tmp_path / "proj" / "a.md"), str(tmp_path / "project2" / "b.md")]
    assert G.within_tree(files, str(tmp_path / "proj")) == files[:1]


# ---- line-oriented caches and unreadable dirs ---------------------------------------------------

@pytest.mark.parametrize("sep", [
    pytest.param("\x1c", marks=pytest.mark.skipif(
        os.name == "nt", reason="Windows forbids control characters 1-31 in a file name")),
    "\u2028",
    "\x85",
], ids=["x1c", "u2028", "x85"])
def test_a_cached_path_holding_a_line_separator_char_survives_the_cache(tmp_path, monkeypatch, sep):
    ws, cur = _ws(tmp_path, monkeypatch)
    odd = ws / ("odd%sname" % sep)                # each is a str.splitlines() boundary
    assert len(("a%sb" % sep).splitlines()) == 2
    odd.mkdir()
    (odd / "CLAUDE.md").write_text("odd", encoding="utf-8")
    first = sorted(G.discover_claude_md(str(cur)))
    second = sorted(G.discover_claude_md(str(cur)))    # served from the cache file
    assert str(odd / "CLAUDE.md") in first
    assert second == first


@pytest.mark.skipif(os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="needs POSIX permissions and a non-root user")
def test_an_unreadable_dir_is_reported_not_silently_dropped(tmp_path, monkeypatch, capsys):
    ws, cur = _ws(tmp_path, monkeypatch)
    locked = ws / "locked"
    (locked / "inner").mkdir(parents=True)
    locked.chmod(0)
    try:
        assert G.main(["--topic", "zorblax", "--self", str(cur)]) == 0
        err = capsys.readouterr().err
        assert G.main(["--topic", "zorblax", "--self", str(cur)]) == 0
        again = capsys.readouterr().err       # an incomplete walk is not cached as complete
    finally:
        locked.chmod(0o755)
    assert "locked" in err and "cannot list" in err
    assert "locked" in again and "cannot list" in again


@pytest.mark.skipif(os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="needs POSIX permissions and a non-root user")
def test_the_claude_md_walk_reports_an_unreadable_dir_every_time(tmp_path, monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    locked = ws / "locked"
    (locked / "inner").mkdir(parents=True)
    locked.chmod(0)
    G.take_walk_errors()
    try:
        G.discover_claude_md(str(cur))
        first = G.take_walk_errors()
        G.discover_claude_md(str(cur))          # served from the cache, which replays the skip
        second = G.take_walk_errors()
    finally:
        locked.chmod(0o755)
    assert [p for p, _ in first] == [str(locked)]
    assert [p for p, _ in second] == [str(locked)]


# --------------------------------------------------------------------------
# A walk that could not list one dir is still cached; the skip is replayed on every read
# --------------------------------------------------------------------------

_POSIX_NONROOT = pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="needs POSIX permissions and a non-root user")


@_POSIX_NONROOT
def test_a_claude_md_walk_with_an_unlistable_dir_is_cached_and_still_reports_it(tmp_path,
                                                                                monkeypatch):
    ws, cur = _ws(tmp_path, monkeypatch)
    locked = ws / "lost+found"
    (locked / "inner").mkdir(parents=True)
    locked.chmod(0)
    G.take_walk_errors()
    try:
        first = {Path(p).parent.name for p in G.discover_claude_md(str(cur))}
        first_errors = G.take_walk_errors()
        (ws / "projC").mkdir()
        (ws / "projC" / "CLAUDE.md").write_text("projC rules", encoding="utf-8")
        second = {Path(p).parent.name for p in G.discover_claude_md(str(cur))}
        second_errors = G.take_walk_errors()
        retried = {Path(p).parent.name for p in G.discover_claude_md(str(cur), cache_ttl=0)}
        retried_errors = G.take_walk_errors()
    finally:
        locked.chmod(0o755)
    assert "projB" in first and [p for p, _ in first_errors] == [str(locked)]
    assert second == first                     # served from the cache: projC unseen, no re-walk
    assert [p for p, _ in second_errors] == [str(locked)]   # the skip is still reported
    assert "projC" in retried                  # the TTL retries the walk like any cache
    assert [p for p, _ in retried_errors] == [str(locked)]


@_POSIX_NONROOT
def test_a_store_walk_with_an_unlistable_dir_is_cached_and_still_reports_it(tmp_path,
                                                                           monkeypatch):
    root = _home_root(tmp_path, monkeypatch)
    _seed_store(root, "projA", "one.md")
    locked = root / "lost+found"
    (locked / "inner").mkdir(parents=True)
    locked.chmod(0)
    G.take_walk_errors()
    try:
        first = G._curated_store_dirs(str(root))
        first_errors = G.take_walk_errors()
        _seed_store(root, "projB", "two.md")      # no generation bump: a cache must hide it
        second = G._curated_store_dirs(str(root))
        second_errors = G.take_walk_errors()
        sig.bump_stores_generation()
        third = G._curated_store_dirs(str(root))
        G.take_walk_errors()
    finally:
        locked.chmod(0o755)
    assert len(first) == 1 and [p for p, _ in first_errors] == [str(locked)]
    assert second == first                     # served from the cache, no re-walk
    assert [p for p, _ in second_errors] == [str(locked)]
    assert len(third) == 2                     # a generation bump still busts it


def test_a_claude_md_cache_without_the_format_header_is_rewalked(tmp_path, monkeypatch):
    # A cache written before the header existed holds bare paths; read as the new format its
    # first path would be taken for a header. It must be ignored and rebuilt, never trusted.
    ws, cur = _ws(tmp_path, monkeypatch)
    G.discover_claude_md(str(cur))
    cache = next((tmp_path / "home" / ".claude" / "self-improve-audit").glob("claude-md-paths.*"))
    bogus = str(ws / "bogus" / "CLAUDE.md")
    cache.write_text("\n".join([bogus, str(ws / "projB" / "CLAUDE.md")]), encoding="utf-8")
    got = G.discover_claude_md(str(cur))
    assert bogus not in got
    assert "projB" in {Path(p).parent.name for p in got}


@pytest.mark.skipif(os.name == "nt", reason="Windows forbids a newline in a file name")
def test_a_path_holding_the_record_separator_is_not_cached_as_two_paths(tmp_path, monkeypatch):
    # "\n" separates the cache records, so a path holding one cannot be read back as written:
    # such a walk is not cached, and every call still answers from a live walk.
    ws, cur = _ws(tmp_path, monkeypatch)
    odd = ws / "odd\nname"
    odd.mkdir()
    (odd / "CLAUDE.md").write_text("odd", encoding="utf-8")
    first = sorted(G.discover_claude_md(str(cur)))
    second = sorted(G.discover_claude_md(str(cur)))
    assert str(odd / "CLAUDE.md") in first
    assert second == first


def test_a_store_cache_in_the_old_format_is_rewalked(tmp_path, monkeypatch):
    root = _home_root(tmp_path, monkeypatch)
    _seed_store(root, "projA", "one.md")
    G._curated_store_dirs(str(root))
    cache = next(sig._audit_dir().glob("curated-dirs.*"))
    stamp = "gen:%d" % sig.stores_generation()
    cache.write_text("\n".join([stamp, str(root / "bogus" / ".claude-memory")]), encoding="utf-8")
    got = G._curated_store_dirs(str(root))
    assert [Path(p).parent.name for p in got] == ["projA"]
