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
