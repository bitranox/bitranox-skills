"""Tests for contrib_queue.py (the durable pending-upstream-contribution queue CLI). ASCII only."""
import pytest

import contrib_queue as Q
import self_improve_signals as S


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def test_add_queues_a_durable_intent(capsys):
    rc = Q.main(["add", "--what", "check-tree misses sideways refs",
                 "--target", "skill:meta-self-improve", "--why", "found in a real dream", "/p/x"])
    assert rc == 0 and "queued" in capsys.readouterr().out
    recs = S.read_contributions("/p/x")
    assert len(recs) == 1
    assert recs[0]["target"] == "skill:meta-self-improve" and recs[0]["why"] == "found in a real dream"


def test_list_shows_pending_without_consuming(capsys):
    Q.main(["add", "--what", "a gap", "--target", "skill:foo", "/p/x"])
    capsys.readouterr()
    assert Q.main(["list", "/p/x"]) == 0
    assert "a gap" in capsys.readouterr().out
    assert len(S.read_contributions("/p/x")) == 1        # listing is not shipping
    Q.main(["list", "/p/x"])
    assert "a gap" in capsys.readouterr().out            # still there


def test_list_is_quiet_when_empty(capsys):
    assert Q.main(["list", "/p/empty"]) == 0
    assert "no pending" in capsys.readouterr().out


def test_drain_clears_only_when_asked(capsys):
    Q.main(["add", "--what", "x", "/p/x"])
    capsys.readouterr()
    assert Q.main(["drain", "/p/x"]) == 0
    assert "drained" in capsys.readouterr().out
    assert S.read_contributions("/p/x") == []


def test_same_intent_twice_is_one_todo(capsys):
    Q.main(["add", "--what", "same", "--target", "skill:foo", "/p/x"])
    Q.main(["add", "--what", "same", "--target", "skill:foo", "/p/x"])
    assert len(S.read_contributions("/p/x")) == 1


def test_no_subcommand_is_usage_error():
    assert Q.main([]) == 2


# ---- drop: a disproven or stale intent must LEAVE the queue and not come back -----------------

def test_drop_removes_one_entry_and_leaves_the_rest(capsys):
    Q.main(["add", "--what", "keeper one", "--target", "skill:a", "/p/d"])
    Q.main(["add", "--what", "disproven", "--target", "skill:b", "/p/d"])
    Q.main(["add", "--what", "keeper two", "--target", "skill:c", "/p/d"])
    capsys.readouterr()
    assert Q.main(["drop", "--index", "2", "--reason", "verified false", "/p/d"]) == 0
    left = [r["what"] for r in S.read_contributions("/p/d")]
    assert left == ["keeper one", "keeper two"]


def test_dropped_intent_cannot_be_requeued(capsys):
    """The whole point: a disproven contribution must not be re-evaluated by every later dream."""
    Q.main(["add", "--what", "codes.OK is a tuple", "--target", "skill:libs", "/p/d2"])
    Q.main(["drop", "--index", "1", "--reason", "empirically false", "/p/d2"])
    capsys.readouterr()
    Q.main(["add", "--what", "codes.OK is a tuple", "--target", "skill:libs", "/p/d2"])
    assert S.read_contributions("/p/d2") == []          # refused, not silently re-queued
    assert "rejected" in capsys.readouterr().out.lower()


def test_drop_records_the_reason_for_later_readers():
    Q.main(["add", "--what", "stale thing", "--target", "skill:x", "/p/d3"])
    Q.main(["drop", "--index", "1", "--reason", "superseded by 5.104.0", "/p/d3"])
    rej = S.read_rejected("/p/d3")
    assert len(rej) == 1
    assert rej[0]["reason"] == "superseded by 5.104.0"
    assert rej[0]["what"] == "stale thing"


def test_drop_rejects_an_out_of_range_index(capsys):
    Q.main(["add", "--what", "only one", "--target", "skill:x", "/p/d4"])
    capsys.readouterr()
    assert Q.main(["drop", "--index", "7", "--reason", "nope", "/p/d4"]) != 0
    assert len(S.read_contributions("/p/d4")) == 1      # nothing removed on a bad index


def test_list_numbers_entries_so_drop_can_target_them(capsys):
    Q.main(["add", "--what", "first", "--target", "skill:x", "/p/d5"])
    Q.main(["add", "--what", "second", "--target", "skill:y", "/p/d5"])
    capsys.readouterr()
    Q.main(["list", "/p/d5"])
    out = capsys.readouterr().out
    assert "1." in out and "2." in out
