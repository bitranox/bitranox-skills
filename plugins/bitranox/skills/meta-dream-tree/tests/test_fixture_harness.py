"""Tests for fixture_builder.py + fixture_asserter.py (the dream acceptance harness). ASCII."""
import json
from pathlib import Path

import pytest

import fixture_builder as FB
import fixture_asserter as FA


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    root = tmp_path / "fx"
    root.mkdir()
    m = FB.build(root)
    return root, m


def test_builder_plants_all_cases(fixture):
    root, m = fixture
    import uuid_store as us
    anchor = Path(m["tree1"])
    assert len(m["slugs"]) == 8
    for slug in m["slugs"].values():
        assert us.body_path(anchor, slug).is_file() or slug == "control", slug
    # pinned decoy is pinned at the anchor; dept-b scope empty; control snapshot recorded
    hard, judgment = FA.check(root)
    assert hard["PIN"] and hard["XTREE"] and hard["VOICE-ID"] and hard["NO-LOSS"]
    assert m["tree2_hash"]


def test_untouched_fixture_fails_judgment_passes_hard(fixture):
    root, m = fixture
    hard, judgment = FA.check(root)
    assert all(hard.values())                      # nothing broke: hard all green pre-dream
    assert sum(judgment.values()) == 0             # no dream ran: every judgment red


def test_asserter_detects_simulated_dream_effects(fixture):
    root, m = fixture
    import memory_engine as E
    import reconcile_memory_index as R
    s = m["slugs"]
    # simulate the dream: merge dup at dept-a, move mis-placed facts, archive obs, prune task,
    # synthesize dept-b scope
    E.move_entry(m["tree1"], m["proj1"], s["mis_high"])
    E.move_entry(m["proj1"], m["dept_a"], s["mis_low"])
    E.move_entry(m["proj1"], m["dept_a"], s["dup_a"])
    E._drop_pointer(m["proj2"], s["dup_b"])
    R.archive_entry(m["proj1"], s["obs"])
    E._drop_pointer(m["proj2"], s["task"])
    rc = E.main(["set-scope", "--proj", m["dept_b"],
                 "--scope", "WHAT: the data department.\nPLACE-HERE: dept-b-wide rules"])
    assert rc == 0
    hard, judgment = FA.check(root)
    assert all(hard.values()), hard
    assert sum(judgment.values()) >= 5, judgment   # DUP/MIS-HIGH/MIS-LOW/OBS/TASK/SCOPE


def test_xtree_and_pin_violations_are_caught(fixture):
    root, m = fixture
    # touching the control tree breaks XTREE
    (Path(m["tree2"]) / "control-proj" / "CLAUDE.local.md").write_text("tampered\n",
                                                                        encoding="utf-8")
    hard, _ = FA.check(root)
    assert hard["XTREE"] is False


def test_nap_profile_parity_chain_effects_pass_siblings_guarded(fixture):
    root, m = fixture
    import memory_engine as E
    import reconcile_memory_index as R
    s = m["slugs"]
    # simulate a CHAIN-ONLY nap from proj-1: chain-internal basics only
    E.move_entry(m["tree1"], m["proj1"], s["mis_high"])
    E.move_entry(m["proj1"], m["dept_a"], s["mis_low"])
    R.archive_entry(m["proj1"], s["obs"])
    hard, judgment = FA.check(root, profile="nap")
    assert hard["SIBLINGS"] is True                  # proj-2 + dept-b byte-untouched
    assert all(hard.values()), hard
    assert judgment == {"MIS-HIGH": True, "MIS-LOW": True, "OBS": True}
    # DUP/TASK/SCOPE are absent: out of a nap's scope by design (the tree-wide profiles judge them)


def test_nap_profile_catches_sibling_touch(fixture):
    root, m = fixture
    import memory_engine as E
    E._drop_pointer(m["proj2"], m["slugs"]["task"])   # a nap must NOT touch the sibling
    hard, _ = FA.check(root, profile="nap")
    assert hard["SIBLINGS"] is False


def test_global_profile_invariants(fixture):
    root, m = fixture
    hard, judgment = FA.check(root, profile="global")
    assert hard["NO-XREF"] is True and hard["PIN"] is True and judgment == {}
