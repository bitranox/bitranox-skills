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
