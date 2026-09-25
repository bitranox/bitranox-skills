"""Tombstones the pre-7.24.0 queue_key: close wrote under the wrong key, and the reads a tombstone
write depends on. ASCII only.

Before `_queue_file_key` existed, `rejected_file("queue_key:<H>")` hashed the pseudo-path itself -
`proj_key` made it absolute under the cwd of the close - so a ship or drop addressed by queue key
wrote its tombstone to a file no reader ever consults. The intent left the queue, the record that
it left went nowhere: `shipped` never listed it, and the next add of the same intent was accepted.
"""
import json
import os

import pytest

import contrib_queue as Q
import self_improve_signals as S

NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _old_bug_tombstone_file(proj, close_cwd, records):
    """Write `records` exactly where the pre-fix close put them: under the hash of the queue_key
    pseudo-path made absolute beneath the cwd the close ran from."""
    pseudo = S.QUEUE_KEY_PREFIX + S.proj_key(proj)
    wrong = S._audit_dir() / (S.proj_key(os.path.join(str(close_cwd), pseudo))
                              + ".contrib-rejected.jsonl")
    wrong.parent.mkdir(parents=True, exist_ok=True)
    wrong.write_text("\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n",
                     encoding="utf-8")
    return wrong


def _tomb(what, proj=None, outcome=S.SHIPPED, target="skill:x"):
    rec = {"what": what, "target": target, "outcome": outcome, "closed_ts": 1.0}
    if proj:
        rec["proj"] = proj
    return rec


@pytest.fixture
def orphan(tmp_path):
    proj = str(tmp_path / "proj")
    os.makedirs(proj)
    f = _old_bug_tombstone_file(proj, tmp_path / "elsewhere",
                                [_tomb("fixed the parser", proj),
                                 _tomb("an older unstamped close", None, S.REJECTED)])
    return proj, f


# ---- the defect: an orphaned tombstone is not honoured ------------------------------------------

def test_an_orphaned_tombstone_blocks_nothing_until_rehomed(orphan, capsys):
    proj, _f = orphan
    assert S.read_shipped(proj) == []                     # the record of the ship went nowhere
    assert Q.main(["add", "--what", "fixed the parser", "--target", "skill:x", proj]) == 0
    assert "queued:" in capsys.readouterr().out           # resurrected as a TODO


def test_rehome_apply_makes_the_orphaned_close_stick(orphan, capsys):
    proj, f = orphan
    assert Q.main(["rehome-tombstones", "--apply"]) == 0
    out = capsys.readouterr().out
    assert S.proj_key(proj) in out and "2 tombstone(s)" in out
    assert [r["what"] for r in S.read_shipped(proj)] == ["fixed the parser"]
    assert [r["what"] for r in S.read_rejected(proj)] == ["an older unstamped close"]
    assert Q.main(["add", "--what", "fixed the parser", "--target", "skill:x", proj]) == 0
    assert "not queued (shipped earlier)" in capsys.readouterr().out
    assert not f.exists() and f.with_name(f.name + ".rehomed").is_file()   # kept, not deleted


def test_rehome_without_apply_changes_nothing(orphan, capsys):
    proj, f = orphan
    before = f.read_bytes()
    assert Q.main(["rehome-tombstones"]) == 0
    out = capsys.readouterr().out
    assert "--apply" in out and S.proj_key(proj) in out
    assert f.read_bytes() == before and S.read_closed(proj) == []


def test_rehome_is_idempotent_and_does_not_duplicate(orphan, capsys):
    proj, _f = orphan
    Q.main(["rehome-tombstones", "--apply"])
    Q.main(["rehome-tombstones", "--apply"])
    assert len(S.read_closed(proj)) == 2
    assert "no orphaned tombstone" in capsys.readouterr().out


def test_rehome_skips_records_the_home_already_holds(orphan):
    proj, _f = orphan
    S.add_contribution(proj, {"what": "fixed the parser", "target": "skill:x"})
    S.ship_contribution(proj, match="fixed the parser")    # a genuine, correctly keyed close
    Q.main(["rehome-tombstones", "--apply"])
    assert [r["what"] for r in S.read_closed(proj)].count("fixed the parser") == 1


def test_queues_points_at_the_repair_when_orphans_exist(orphan, capsys):
    Q.main(["queues"])
    assert "rehome-tombstones" in capsys.readouterr().out


# ---- controls: what the repair must leave alone -------------------------------------------------

def test_a_correctly_keyed_tombstone_file_is_not_an_orphan(tmp_path, capsys):
    proj = str(tmp_path / "proj")
    S.add_contribution(proj, {"what": "a", "target": "skill:x"})
    S.ship_contribution(proj, match="a")
    before = S.rejected_file(proj).read_bytes()
    assert Q.main(["rehome-tombstones", "--apply"]) == 0
    assert "no orphaned tombstone" in capsys.readouterr().out
    assert S.rejected_file(proj).read_bytes() == before
    Q.main(["queues"])
    assert "rehome-tombstones" not in capsys.readouterr().out


def test_a_file_stamped_for_two_queues_is_reported_and_left(tmp_path, capsys):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    f = _old_bug_tombstone_file(a, tmp_path, [_tomb("one", a), _tomb("two", b)])
    before = f.read_bytes()
    assert Q.main(["rehome-tombstones", "--apply"]) == 0
    assert "left in place" in capsys.readouterr().out
    assert f.read_bytes() == before
    assert S.read_closed(a) == [] and S.read_closed(b) == []


def test_a_file_with_no_stamped_record_cannot_be_attributed(tmp_path, capsys):
    proj = str(tmp_path / "proj")
    f = _old_bug_tombstone_file(proj, tmp_path, [_tomb("unstamped", None)])
    before = f.read_bytes()
    Q.main(["rehome-tombstones", "--apply"])
    assert f.read_bytes() == before and S.read_closed(proj) == []


# ---- a tombstone write never replaces a closed set it could not read ----------------------------

@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a write-only file")
def test_an_unreadable_closed_set_is_not_clobbered_by_the_next_close(tmp_path, capsys):
    # read_closed answered [] for an unreadable file, and the close then REPLACED every earlier
    # tombstone with its own - so each earlier intent could be re-queued.
    proj = str(tmp_path / "proj")
    for what in ("old-1", "old-2", "new"):
        S.add_contribution(proj, {"what": what})
    S.drop_contribution(proj, match="old-1")
    S.drop_contribution(proj, match="old-2")
    rf = S.rejected_file(proj)
    before = rf.read_bytes()
    rf.chmod(0o200)
    try:
        assert Q.main(["drop", "--match", "new", proj]) == 1
    finally:
        rf.chmod(0o644)
    assert "failed" in capsys.readouterr().err
    assert rf.read_bytes() == before
    assert [r["what"] for r in S.read_contributions(proj)] == ["new"]   # still queued


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a write-only file")
def test_an_unreadable_queue_is_a_failed_close_not_a_bad_selector(tmp_path, capsys):
    proj = str(tmp_path / "proj")
    S.add_contribution(proj, {"what": "x"})
    qf = S.contrib_file(proj)
    qf.chmod(0o200)
    try:
        assert Q.main(["ship", "--match", "x", proj]) == 1
    finally:
        qf.chmod(0o644)
    err = capsys.readouterr().err
    assert "failed" in err and "no queued contribution" not in err
