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


# ---- ship: a DELIVERED intent leaves the queue as shipped, not as rejected ----------------------

def test_ship_removes_one_entry_and_records_it_as_shipped(capsys):
    Q.main(["add", "--what", "first", "--target", "skill:x", "/p/s1"])
    Q.main(["add", "--what", "second", "--target", "skill:y", "/p/s1"])
    capsys.readouterr()
    assert Q.main(["ship", "--index", "1", "--note", "meta-skill-writer 5.123.0", "/p/s1"]) == 0
    assert "shipped" in capsys.readouterr().out
    left = S.read_contributions("/p/s1")
    assert [r["what"] for r in left] == ["second"]
    shipped = S.read_shipped("/p/s1")
    assert len(shipped) == 1
    assert shipped[0]["what"] == "first" and shipped[0]["note"] == "meta-skill-writer 5.123.0"


def test_a_shipped_intent_is_not_reported_as_rejected(capsys):
    Q.main(["add", "--what", "delivered thing", "--target", "skill:x", "/p/s2"])
    Q.main(["ship", "--index", "1", "--note", "v1.2.3", "/p/s2"])
    capsys.readouterr()
    assert S.read_rejected("/p/s2") == []                # the whole point: not a rejection
    assert Q.main(["rejected", "/p/s2"]) == 0
    assert "no dropped" in capsys.readouterr().out
    assert Q.main(["shipped", "/p/s2"]) == 0
    assert "delivered thing" in capsys.readouterr().out


def test_a_shipped_intent_is_never_requeued(capsys):
    Q.main(["add", "--what", "done gap", "--target", "skill:x", "/p/s3"])
    Q.main(["ship", "--index", "1", "/p/s3"])
    capsys.readouterr()
    Q.main(["add", "--what", "done gap", "--target", "skill:x", "/p/s3"])   # a later dream re-notices
    assert "not queued" in capsys.readouterr().out
    assert S.read_contributions("/p/s3") == []


def test_ship_and_drop_are_reported_separately(capsys):
    Q.main(["add", "--what", "shipped one", "--target", "skill:x", "/p/s4"])
    Q.main(["add", "--what", "wrong one", "--target", "skill:y", "/p/s4"])
    Q.main(["ship", "--index", "1", "--note", "v2", "/p/s4"])
    Q.main(["drop", "--index", "1", "--reason", "disproven", "/p/s4"])
    capsys.readouterr()
    Q.main(["rejected", "/p/s4"])
    out = capsys.readouterr().out
    assert "wrong one" in out and "shipped one" not in out
    Q.main(["shipped", "/p/s4"])
    out = capsys.readouterr().out
    assert "shipped one" in out and "wrong one" not in out


def test_ship_rejects_an_out_of_range_index(capsys):
    Q.main(["add", "--what", "only one", "--target", "skill:x", "/p/s5"])
    capsys.readouterr()
    assert Q.main(["ship", "--index", "9", "/p/s5"]) != 0
    assert len(S.read_contributions("/p/s5")) == 1      # nothing removed on a bad index


def test_a_closed_record_without_an_outcome_reads_as_rejected(capsys):
    """Records written before the outcome field existed carry no outcome and were all drops."""
    Q.main(["add", "--what", "old drop", "--target", "skill:x", "/p/s6"])
    Q.main(["drop", "--index", "1", "--reason", "stale", "/p/s6"])
    import json
    f = S.rejected_file("/p/s6")
    recs = [json.loads(ln) for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for r in recs:
        r.pop("outcome", None)
    f.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n", encoding="utf-8")
    assert [r["what"] for r in S.read_rejected("/p/s6")] == ["old drop"]
    assert S.read_shipped("/p/s6") == []


# ---- --match: a STABLE selector, because an index shifts under the previous close ---------------

def test_match_selects_by_text_so_order_does_not_matter(capsys):
    Q.main(["add", "--what", "wrong idea", "--target", "skill:a", "/p/m1"])
    Q.main(["add", "--what", "delivered idea", "--target", "skill:b", "/p/m1"])
    Q.main(["add", "--what", "keep me", "--target", "skill:c", "/p/m1"])
    capsys.readouterr()
    # close the EARLIER entry first: with --index this shifts the rest, with --match it cannot
    assert Q.main(["drop", "--match", "wrong", "--reason", "disproven", "/p/m1"]) == 0
    assert Q.main(["ship", "--match", "delivered", "--note", "5.122.0", "/p/m1"]) == 0
    assert [r["what"] for r in S.read_contributions("/p/m1")] == ["keep me"]
    assert [r["what"] for r in S.read_shipped("/p/m1")] == ["delivered idea"]
    assert [r["what"] for r in S.read_rejected("/p/m1")] == ["wrong idea"]


def test_match_refuses_an_ambiguous_selector(capsys):
    Q.main(["add", "--what", "cache the gate", "--target", "skill:a", "/p/m2"])
    Q.main(["add", "--what", "cache the store", "--target", "skill:b", "/p/m2"])
    capsys.readouterr()
    assert Q.main(["ship", "--match", "cache", "--note", "v1", "/p/m2"]) != 0
    assert len(S.read_contributions("/p/m2")) == 2      # nothing closed on an ambiguous match
    assert S.read_shipped("/p/m2") == []


def test_match_refuses_when_nothing_matches(capsys):
    Q.main(["add", "--what", "only entry", "--target", "skill:a", "/p/m3"])
    capsys.readouterr()
    assert Q.main(["drop", "--match", "absent", "--reason", "x", "/p/m3"]) != 0
    assert len(S.read_contributions("/p/m3")) == 1


def test_match_is_case_insensitive_and_matches_the_target_too(capsys):
    Q.main(["add", "--what", "some gap", "--target", "skill:meta-dream-tree", "/p/m4"])
    capsys.readouterr()
    assert Q.main(["ship", "--match", "DREAM-TREE", "--note", "v9", "/p/m4"]) == 0
    assert [r["what"] for r in S.read_shipped("/p/m4")] == ["some gap"]


def test_ship_needs_exactly_one_selector(capsys):
    Q.main(["add", "--what", "an entry", "--target", "skill:a", "/p/m5"])
    capsys.readouterr()
    assert Q.main(["ship", "/p/m5"]) != 0                                   # neither
    assert Q.main(["ship", "--index", "1", "--match", "entry", "/p/m5"]) != 0  # both
    assert len(S.read_contributions("/p/m5")) == 1


def test_requeue_of_a_shipped_intent_says_shipped_not_rejected(capsys):
    Q.main(["add", "--what", "already done", "--target", "skill:x", "/p/r1"])
    Q.main(["ship", "--match", "already done", "--note", "5.123.0", "/p/r1"])
    capsys.readouterr()
    Q.main(["add", "--what", "already done", "--target", "skill:x", "/p/r1"])
    out = capsys.readouterr().out
    assert "shipped" in out and "rejected" not in out    # it was delivered, not disproven
