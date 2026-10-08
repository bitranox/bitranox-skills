"""add_with_advice: the CLI add and the mod bridge share one write path. ASCII only."""
import pytest

import memory_engine as ME


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def test_first_add_creates_and_a_second_updates(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    slug, created, _ = ME.add_with_advice(str(level), "Rule", "When x, do y.", body="Because z.")
    assert created is True
    slug2, created2, _ = ME.add_with_advice(str(level), "Rule", "When x, do y now.", body="Because z.")
    assert (slug2, created2) == (slug, False)


def test_a_trigger_less_hook_comes_back_as_advice_not_output(tmp_path, capsys):
    level = tmp_path / "proj"
    level.mkdir()
    _, _, advice = ME.add_with_advice(str(level), "Plain", "Do y.", body="Because z.")
    assert any("no trigger phrase" in a for a in advice)
    assert capsys.readouterr().out == ""


def test_an_over_cap_hook_raises_before_writing(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    with pytest.raises(ME.HookTooLong):
        ME.add_with_advice(str(level), "Long", "When x, " + "y" * 600, body="b")


def test_created_is_decided_from_the_store_read_under_the_lock(tmp_path):
    # a pointer lost while its body stays: the add adopts the body back, which is an update
    level = tmp_path / "proj"
    level.mkdir()
    slug, created, _ = ME.add_with_advice(str(level), "Rule", "When x, do y.", body="Because z.")
    assert created is True
    (level / "CLAUDE.local.md").unlink()
    again, created2, _ = ME.add_with_advice(str(level), "Rule", "When x, do y.", body="Because z.")
    assert (again, created2) == (slug, False)


def test_a_recurrence_count_is_warned_about(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    _, _, advice = ME.add_with_advice(str(level), "Again", "When x, do y.",
                                      body="It happened again. recurrence: 3")
    assert any("recurrence 3" in a and "Escalate" in a for a in advice)


def test_a_hook_past_the_soft_cap_is_advised_not_refused(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    hook = "When x, " + "y" * 400
    _, _, advice = ME.add_with_advice(str(level), "Soft", hook, body="b")
    assert any("soft cap" in a for a in advice)


def test_an_over_cap_add_writes_nothing(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))
    with pytest.raises(ME.HookTooLong):
        ME.add_with_advice(str(level), "Long", "When x, " + "y" * 600, body="b")
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == before
