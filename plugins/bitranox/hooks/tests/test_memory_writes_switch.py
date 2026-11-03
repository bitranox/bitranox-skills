"""BITRANOX_MEMORY_WRITES=off: every write path refuses with one line, every nudge stays quiet.

One test per path. Each pair has a GREEN control (writes on) beside the RED arm (writes off), so a
test that passes because the path is broken for another reason cannot pass both.
"""
import io
import json
import sys

import pytest

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
