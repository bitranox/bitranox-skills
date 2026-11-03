"""BITRANOX_MEMORY_WRITES=off: every write path refuses with one line, every nudge stays quiet.

One test per path. Each pair has a GREEN control (writes on) beside the RED arm (writes off), so a
test that passes because the path is broken for another reason cannot pass both.
"""
import io
import json
import sys

import pytest

import memory_engine as ME
import self_improve_signals as sig

OFF = {"BITRANOX_MEMORY_WRITES": "off"}


@pytest.mark.parametrize("value, expected", [
    ("off", True), ("OFF", True), (" off ", True),
    ("on", False), ("0", False), ("false", False), ("", False),
])
def test_memory_writes_off_reads_exactly_one_spelling(value, expected):
    assert sig.memory_writes_off({"BITRANOX_MEMORY_WRITES": value}) is expected


def test_memory_writes_off_unset_is_on():
    assert sig.memory_writes_off({}) is False


def test_refuse_raises_only_when_off(monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    sig.refuse_if_memory_writes_off()
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff) as exc:
        sig.refuse_if_memory_writes_off()
    assert "BITRANOX_MEMORY_WRITES=off" in str(exc.value)


FACT = dict(title="Probe fact", hook="When probing the switch, expect a refusal.", body="body", type_="feedback")


def test_engine_add_refuses_when_off_and_writes_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        ME.add_with_advice(str(tmp_path), **FACT)
    assert not (tmp_path / "CLAUDE.local.md").exists(), "the refusal must come before any write"
    argv = ["add", "--proj", str(tmp_path), "--title", FACT["title"], "--hook", FACT["hook"],
            "--body", FACT["body"], "--type", "feedback"]
    assert ME.main(argv) == 2
    assert sig.MEMORY_WRITES_OFF_LINE in capsys.readouterr().out
    assert not (tmp_path / "CLAUDE.local.md").exists()
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    assert ME.main(argv) == 0, "control: the same add works with the switch unset"
    assert (tmp_path / "CLAUDE.local.md").exists()


@pytest.mark.parametrize("verb", sorted(ME.WRITE_VERBS))
def test_every_write_verb_is_refused_at_the_cli(verb, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert ME.main([verb]) == 2, "the refusal precedes argparse, so required arguments never matter"
    assert "! refused:" in capsys.readouterr().out


def test_heal_is_a_silent_no_op_when_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    report = ME.heal(str(tmp_path))
    assert report["skipped"] == sig.MEMORY_WRITES_OFF_LINE and report["healed"] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fn, args", [
    (ME.move_entry, ("a", "b", "slug")),
    (ME.relocate_entry, ("a", "b", "slug")),
    (ME.rename_entry, ("a", "slug", "slug2")),
    (ME.retitle_entry, ("a", "slug", "Title")),
    (ME.ensure_all_trees, ()),
])
def test_library_write_functions_raise_first(fn, args, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        fn(*args)
