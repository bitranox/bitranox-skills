"""A long bare `sleep` is waiting on the CLOCK, which is the thing the wait rule forbids.

From `feedback-match-the-wait-to-the-event-s-actual-timing-do-not-over-wait` (recurrence 2): wait
on a concrete signal, or on a measured duration plus a small margin - never an arbitrary sleep,
and stop and investigate at roughly 2x the expected time rather than waiting longer.
"""
import importlib.util
import pathlib

import pytest

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "arbitrary-sleep-nudge.py"
_spec = importlib.util.spec_from_file_location("arbitrary_sleep_nudge", _HOOK)
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


@pytest.mark.parametrize("command", [
    "sleep 300",
    "sleep 120 && curl -s http://host/health",
    "ssh host 'sleep 600; systemctl status app'",
    "sleep 10m",
    "sleep 2h",
])
def test_a_long_bare_sleep_is_nudged(command):
    notice = N.notice(command)
    assert notice is not None
    assert "signal" in notice.lower()


@pytest.mark.parametrize("command", [
    "sleep 2",
    "sleep 30",
    "sleep 0.5",
])
def test_a_short_settle_pause_is_left_alone(command):
    """The negative must be reachable: a couple of seconds to let a service settle is not this."""
    assert N.notice(command) is None


def test_a_sleep_inside_a_polling_loop_is_the_right_shape_already():
    """Sleeping between CHECKS is waiting on a signal - exactly what the rule asks for."""
    assert N.notice("until curl -sf http://h/ready; do sleep 300; done") is None
    assert N.notice("while ! test -f /tmp/done; do sleep 600; done") is None
    assert N.notice("for i in $(seq 1 10); do check || sleep 120; done") is None


def test_prose_mentioning_sleep_does_not_fire():
    doc = "cat > note.md <<'EOF'\nnever write sleep 600 and hope\nEOF"
    assert N.notice(doc) is None


def test_junk_is_ignored():
    assert N.notice("") is None
    assert N.notice(None) is None
    assert N.notice("sleep") is None
