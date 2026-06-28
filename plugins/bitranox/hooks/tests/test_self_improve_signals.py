"""Tests for self_improve_signals.py (shared strict + broad learning-signal patterns).

All content is ASCII.
"""

import pytest

import self_improve_signals as S


def test_strict_user_hit():
    assert S.strict_user_hit("no, that's wrong, the path is /etc")
    assert S.strict_user_hit("from now on always run the tests")
    assert S.strict_user_hit("good idea, let's do that")  # endorsement counts
    assert not S.strict_user_hit("please add a function to sum a list")


def test_strict_asst_hit():
    assert S.strict_asst_hit("You're right, my mistake.")
    assert S.strict_asst_hit("Now I understand the real topology.")
    assert S.strict_asst_hit("Good call - the gate belongs first.")  # endorsement counts
    assert not S.strict_asst_hit("Done, added the helper and a test.")


def test_broad_user_flags_near_miss_not_caught_by_strict():
    text = "why did you change that? it's not working again"
    assert S.broad_matches("user", text)          # broad flags it
    assert not S.strict_user_hit(text)            # strict misses it -> a candidate


def test_broad_assistant_flags_near_miss():
    text = "I missed the edge case in the parser"
    assert S.broad_matches("assistant", text)
    assert not S.strict_asst_hit(text)


def test_broad_quiet_on_neutral_turns():
    assert S.broad_matches("user", "thanks, ship it") == []
    assert S.broad_matches("assistant", "Done, added the helper function.") == []


def test_broad_matches_returns_sorted_lowercase_unique():
    m = S.broad_matches("assistant", "Wait, I missed it. I missed it again.")
    assert m == sorted(set(m))
    assert all(x == x.lower() for x in m)


def test_audit_file_path_is_deterministic():
    p1 = S.audit_file("/some/project")
    p2 = S.audit_file("/some/project")
    assert p1 == p2
    assert p1.suffix == ".md"
    assert "self-improve-audit" in str(p1)
    assert S.audit_file("/other/project") != p1


# --------------------------------------------------------------------------
# meta-dream cadence markers + mode
# --------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(home, proj="/p/x"):
    d = S.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.md").write_text("x", encoding="utf-8")
    return d


def test_dream_mode_default(home):
    assert S.dream_mode("/p/x") == "propose"


def test_dream_mode_off(home):
    (home / ".claude" / ".bitranox-dream-off").write_text("", encoding="utf-8")
    assert S.dream_mode("/p/x") == "off"


def test_dream_mode_auto(home):
    (home / ".claude" / ".bitranox-dream-auto").write_text("", encoding="utf-8")
    assert S.dream_mode("/p/x") == "auto"


def test_dream_due_no_memory(home):
    assert S.dream_due("/p/x") is False


def test_dream_due_memory_no_marker(home):
    _mem(home)
    assert S.dream_due("/p/x") is True


def test_dream_due_recent_not_due(home):
    _mem(home)
    S.mark_dream_done("/p/x")  # last == now
    assert S.dream_due("/p/x") is False


def test_dream_due_old_and_changed(home):
    _mem(home)
    f = S.last_dream_file("/p/x")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("1000.0", encoding="utf-8")  # ancient last-dream
    assert S.dream_due("/p/x", now=10_000_000_000) is True


def test_dream_due_off_mode_never(home):
    _mem(home)
    (home / ".claude" / ".bitranox-dream-off").write_text("", encoding="utf-8")
    assert S.dream_due("/p/x") is False


def test_mark_dream_done_writes_timestamp(home):
    assert S.mark_dream_done("/p/x", now=123.0) is True
    assert S.last_dream_file("/p/x").read_text(encoding="utf-8").strip() == "123.0"


# --------------------------------------------------------------------------
# machine-local config (informed-consent knobs)
# --------------------------------------------------------------------------


def test_load_config_defaults(home):
    cfg = S.load_config()
    assert cfg == S.DEFAULT_CONFIG
    assert cfg["dream_mode"] == "propose"


def test_load_config_migrates_legacy_sentinel(home):
    (home / ".claude" / ".bitranox-dream-auto").write_text("", encoding="utf-8")
    assert S.load_config()["dream_mode"] == "auto"


def test_config_file_authoritative_over_sentinel(home):
    # legacy sentinel says auto, but the written config says off -> the file wins
    (home / ".claude" / ".bitranox-dream-auto").write_text("", encoding="utf-8")
    S.save_config({"dream_mode": "off"})
    assert S.load_config()["dream_mode"] == "off"
    assert S.dream_mode("/p/x") == "off"


def test_save_config_roundtrip_and_ignores_unknown(home):
    saved = S.save_config({"privacy": "walled", "forget_idle_dreams": 5, "bogus": 1})
    assert saved["privacy"] == "walled" and saved["forget_idle_dreams"] == 5
    assert "bogus" not in saved
    reloaded = S.load_config()
    assert reloaded["privacy"] == "walled" and reloaded["forget_idle_dreams"] == 5
    assert "bogus" not in reloaded


def test_load_config_corrupt_file_returns_defaults(home):
    S._config_path().write_text("{not json", encoding="utf-8")
    assert S.load_config()["dream_mode"] == "propose"


# --------------------------------------------------------------------------
# altitude homes
# --------------------------------------------------------------------------


def test_global_rules_dir(home):
    g = S.global_rules_dir()
    assert g.name == "bitranox" and g.parent.name == "rules"
    assert ".claude" in str(g)


def test_altitude_chain_order_narrow_to_broad(home):
    chain = S.altitude_chain("/a/b/c")
    assert chain[0] == S.memory_dir("/a/b/c")          # narrowest: project memory
    assert chain[-1] == S.global_rules_dir()           # broadest: global rules
    from pathlib import Path
    assert Path("/a/b/c") in chain and Path("/a/b") in chain   # ancestor CLAUDE.md altitudes
    # project memory comes before its ancestors, ancestors before global (upward order)
    assert chain.index(S.memory_dir("/a/b/c")) < chain.index(Path("/a/b/c")) < chain.index(S.global_rules_dir())


# --------------------------------------------------------------------------
# new-project seeding
# --------------------------------------------------------------------------


def test_project_unseeded_fresh_then_marked(home):
    assert S.project_unseeded("/p/fresh") is True       # no memory, not nudged
    assert S.mark_seeded("/p/fresh") is True
    assert S.project_unseeded("/p/fresh") is False       # nudged once -> quiet


def test_project_unseeded_false_when_memory_exists(home):
    _mem(home, "/p/has")
    assert S.project_unseeded("/p/has") is False


# --------------------------------------------------------------------------
# quality / dwell gate for global promotion
# --------------------------------------------------------------------------


def test_note_promotion_candidate_increments(home):
    assert S.note_promotion_candidate("/p/x", "fleet-ssh") == 1
    assert S.note_promotion_candidate("/p/x", "fleet-ssh") == 2
    assert S.note_promotion_candidate("/p/x", "other") == 1   # independent per key


def test_should_promote_user_stated_is_eager(home):
    assert S.should_promote("user", 1) is True                # user rule promotes on first sight


def test_should_promote_inferred_needs_corroboration(home):
    assert S.should_promote("inferred", 1) is False           # one sighting: not yet
    assert S.should_promote("inferred", 2) is True            # corroborated across 2 dreams


def test_should_promote_eager_mode_overrides(home):
    S.save_config({"promotion": "eager"})
    assert S.should_promote("inferred", 1) is True            # config: promote eagerly


def test_clear_promotion_candidate(home):
    S.note_promotion_candidate("/p/x", "k")
    S.clear_promotion_candidate("/p/x", "k")
    assert S.note_promotion_candidate("/p/x", "k") == 1       # count was forgotten


# --------------------------------------------------------------------------
# scope-descriptor marked block + writer-race signature
# --------------------------------------------------------------------------


def test_read_scope_block_absent_and_present():
    assert S.read_scope_block("# hand-written\nrules here\n") is None
    text = "# c\n%s\nall my python work\n%s\n" % (S.SCOPE_MARK_BEGIN, S.SCOPE_MARK_END)
    assert S.read_scope_block(text) == "all my python work"


def test_upsert_scope_block_appends_preserving_handwritten():
    orig = "# Project rules\n- be concise\n"
    out = S.upsert_scope_block(orig, "this repo = the widget service")
    assert orig in out                                   # hand-written content untouched
    assert S.read_scope_block(out) == "this repo = the widget service"


def test_upsert_scope_block_replaces_in_place():
    text = S.upsert_scope_block("# c\n", "old scope")
    text2 = S.upsert_scope_block(text, "new scope")
    assert S.read_scope_block(text2) == "new scope"
    assert text2.count(S.SCOPE_MARK_BEGIN) == 1          # not duplicated


def test_upsert_scope_block_diff_free_when_unchanged():
    text = S.upsert_scope_block("# c\n", "same")
    assert S.upsert_scope_block(text, "same") == text    # no-change refresh writes nothing


def test_store_changed(home):
    d = _mem(home, "/p/sc")
    base = S._newest_mtime(d)
    assert S.store_changed(d, base) is False
    import os
    os.utime(d / "a.md", (base + 100, base + 100))
    assert S.store_changed(d, base) is True


# --------------------------------------------------------------------------
# forgetting / decay (idle counter)
# --------------------------------------------------------------------------


def test_bump_and_reset_idle(home):
    assert S.bump_idle("/p/x", "k") == 1
    assert S.bump_idle("/p/x", "k") == 2
    S.reset_idle("/p/x", "k")
    assert S.bump_idle("/p/x", "k") == 1                      # reset -> counted from zero again


def test_should_archive_modes(home):
    assert S.should_archive(5, mode="off") is False          # off: never forget
    assert S.should_archive(2, mode="conservative", n=3) is False
    assert S.should_archive(3, mode="conservative", n=3) is True
    assert S.should_archive(1, mode="aggressive") is True     # aggressive: forget quickly


def test_should_archive_reads_config(home):
    S.save_config({"forgetting": "off"})
    assert S.should_archive(99) is False                      # config off overrides default
