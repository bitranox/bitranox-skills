"""Tests for context-watcher.py (Stop hook: offer a handover before the context wall).

Three things carry the weight here, and each is a failure this repo has shipped before.

The MEASUREMENT must include the cache legs. Almost all of a long session's context arrives as
`cache_read_input_tokens`, so a sum that omits them reports a few hundred tokens on a session
hundreds of thousands deep - a watcher that reads healthy while the session drowns.

The BOUNDARY must be tested from both sides. A watcher that fires on everything and one that fires
on nothing both pass a one-sided test.

The MISCONFIGURED case must speak. Measuring more context than the configured window means the
threshold can never be crossed, which is indistinguishable from a watcher that works.
"""

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

import context_watcher as W

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "context-watcher.py"
SHIM = HOOKS_DIR / "run-python.sh"


def _usage_line(input_tokens=0, cache_creation=0, cache_read=0):
    """One assistant transcript record carrying a usage block, built with json.dumps."""
    return json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "usage": {
            "input_tokens": input_tokens,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "output_tokens": 100,
        }},
    })


def _transcript(tmp_path, *lines):
    f = tmp_path / f"t-{uuid.uuid4().hex[:8]}.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(f)


# ---------------------------------------------------------------- context_tokens()

def test_the_cache_legs_are_counted(tmp_path):
    """Omitting them reports a trivial number on a huge session - the whole point of the sum."""
    t = _transcript(tmp_path, _usage_line(input_tokens=2, cache_creation=1231, cache_read=710842))
    assert W.context_tokens(t) == 712075


def test_the_LAST_usage_record_wins(tmp_path):
    """Context is what the most recent request carried, not the first or the biggest."""
    t = _transcript(tmp_path, _usage_line(cache_read=900000), _usage_line(cache_read=1000))
    assert W.context_tokens(t) == 1000


def test_a_compaction_is_self_correcting(tmp_path):
    """After a compact the next request's usage drops on its own; nothing has to reset state."""
    t = _transcript(tmp_path, _usage_line(cache_read=800000), _usage_line(cache_read=12000))
    assert W.context_tokens(t) == 12000


def test_records_without_usage_are_skipped(tmp_path):
    t = _transcript(tmp_path,
                    _usage_line(cache_read=5000),
                    json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}))
    assert W.context_tokens(t) == 5000


@pytest.mark.parametrize("lines", [
    (json.dumps({"type": "user", "message": {"content": "no usage anywhere"}}),),
    ("not json at all",),
    ("",),
])
def test_no_usage_reads_as_unknown_not_zero(tmp_path, lines):
    """None, never 0: zero would be 'under threshold' and would read as a healthy session."""
    assert W.context_tokens(_transcript(tmp_path, *lines)) is None


def test_an_unreadable_transcript_is_unknown(tmp_path):
    assert W.context_tokens(str(tmp_path / "missing.jsonl")) is None
    assert W.context_tokens(None) is None


def test_a_partial_first_line_from_the_tail_seek_is_survivable(tmp_path):
    """The seek lands mid-line; that fragment must be skipped, not crash the read.

    The tail is sized from the content rather than hard-coded: it has to land INSIDE the fragment
    and still contain the whole good line. Too small a tail seeks into the good line instead, and
    `readline()` correctly discards that - which is the read working, not failing.
    """
    fragment = 'e":"assistant","message":{"usage":{"cache_read_input_tokens":99}}}\n'
    good = _usage_line(cache_read=4321) + "\n"
    t = tmp_path / "big.jsonl"
    t.write_text(fragment + good, encoding="utf-8")
    tail = len(good) + 5                      # inside the fragment, past the start of `good`
    assert 0 < tail < len(fragment) + len(good)
    assert W.context_tokens(str(t), tail_bytes=tail) == 4321


# ---------------------------------------------------------------- threshold()

def test_the_percentage_leg_bites_on_a_small_window():
    assert W.threshold(200_000, 70, 400_000) == 140_000


def test_the_absolute_cap_bites_on_a_large_window():
    """70% of 1M would be 700k - twice the measured rot onset. The cap is why this leg exists."""
    assert W.threshold(1_000_000, 70, 400_000) == 400_000


def test_a_nonsense_config_cannot_produce_a_zero_threshold():
    """A threshold of 0 would fire on turn one of every session, forever."""
    assert W.threshold(0, 0, 0) == 1
    assert W.threshold("x", 70, 400_000) is None


# ---------------------------------------------------------------- verdict()

def test_below_the_threshold_is_quiet():
    state, _ = W.verdict(139_999, 200_000, 70, 400_000)
    assert state == "quiet"


def test_at_the_threshold_offers():
    """Boundary, from the other side of the previous test - one-sided proves nothing."""
    state, detail = W.verdict(140_000, 200_000, 70, 400_000)
    assert state == "offer"
    assert detail["limit"] == 140_000 and detail["tokens"] == 140_000


def test_measuring_more_than_the_window_is_reported_not_ignored():
    """A threshold nothing can cross looks exactly like a watcher that works."""
    state, detail = W.verdict(563_038, 200_000, 70, 400_000)
    assert state == "misconfigured"
    assert detail["tokens"] == 563_038


def test_the_same_reading_is_fine_on_a_correctly_configured_window():
    """The control for the case above: same number, right window, ordinary offer."""
    state, _ = W.verdict(563_038, 1_000_000, 70, 400_000)
    assert state == "offer"


def test_an_unknown_reading_is_quiet():
    assert W.verdict(None, 200_000, 70, 400_000)[0] == "quiet"


# ------------------------------------------------- window_for_model() / detect_window()
#
# The window is the denominator for BOTH the threshold and the 10% re-ask spacing, so getting it
# wrong mis-times every ask. It cannot be read from the transcript - `message.model` is the bare
# `claude-opus-5` - but ~/.claude.json keeps the full id, suffix included.

@pytest.mark.parametrize("model_id,expected", [
    ("claude-opus-5[1m]", 1_000_000),
    ("claude-fable-5[1m]", 1_000_000),
    ("claude-sonnet-5[1m]", 1_000_000),
    ("claude-opus-4-6[1m]", 1_000_000),
    ("claude-opus-5", 200_000),               # same model, 200k mode - the suffix is the whole signal
    ("claude-sonnet-5", 200_000),
    ("claude-haiku-4-5-20251001", 200_000),
    ("oss-128k-claude", 128_000),
    ("some-future-model", 200_000),           # unknown degrades to the safe default
    ("", 200_000),
    (None, 200_000),
])
def test_window_for_model(model_id, expected):
    assert W.window_for_model(model_id) == expected


def test_a_1m_suffix_on_haiku_is_refused():
    """Haiku is 200K with no 1M variant, so that id could only be a parse error - fail safe."""
    assert W.window_for_model("claude-haiku-4-5[1m]") == 200_000


def _claude_json(tmp_path, project_path, models):
    f = tmp_path / "claude.json"
    f.write_text(json.dumps({"projects": {project_path: {
        "lastModelUsage": {m: {"inputTokens": 1} for m in models}}}}), encoding="utf-8")
    return str(f)


def test_detect_takes_the_LARGEST_window_among_a_project_s_models(tmp_path):
    """Subagents run haiku and sonnet beside the main model; the biggest is the session's."""
    cfg = _claude_json(tmp_path, "/repo", ["claude-haiku-4-5-20251001", "claude-opus-5[1m]"])
    assert W.detect_window("/repo", config_path=cfg) == 1_000_000


def test_detect_matches_a_subdirectory_against_its_recorded_project(tmp_path):
    """A Stop hook can fire with cwd inside the repo, not at its root."""
    cfg = _claude_json(tmp_path, "/repo", ["claude-opus-5[1m]"])
    assert W.detect_window("/repo/plugins/hooks", config_path=cfg) == 1_000_000


def test_detect_does_not_match_a_mere_prefix_of_another_path(tmp_path):
    """`/repo-other` must not match a record for `/repo`."""
    cfg = _claude_json(tmp_path, "/repo", ["claude-opus-5[1m]"])
    assert W.detect_window("/repo-other", config_path=cfg) is None


@pytest.mark.parametrize("bad", ["missing.json", None])
def test_detect_returns_None_when_it_cannot_tell(tmp_path, bad):
    path = str(tmp_path / bad) if bad else str(tmp_path / "nope.json")
    assert W.detect_window("/repo", config_path=path) is None


def test_detect_returns_None_for_an_unknown_project(tmp_path):
    cfg = _claude_json(tmp_path, "/other", ["claude-opus-5[1m]"])
    assert W.detect_window("/repo", config_path=cfg) is None


# ------------------------------------------------------------------ resolve_window()

def test_an_explicit_window_beats_detection(tmp_path):
    assert W.resolve_window({"context_window": 500_000}, "/repo") == (500_000, "configured")


def test_zero_or_missing_falls_through_to_detection_then_default():
    assert W.resolve_window({"context_window": 0}, "/nonexistent-repo") == (200_000, "assumed")
    assert W.resolve_window({}, "/nonexistent-repo") == (200_000, "assumed")


# ------------------------------------------------------------------ due()

def test_the_first_ask_is_the_threshold():
    assert W.due(140_000, 140_000, 200_000, 0) is True


def test_under_the_threshold_never_asks():
    assert W.due(139_999, 140_000, 200_000, 0) is False


def test_a_re_ask_waits_a_full_tenth_of_the_window():
    """19,999 more is not enough on a 200k window; 20,000 is."""
    assert W.due(159_999, 140_000, 200_000, 140_000) is False
    assert W.due(160_000, 140_000, 200_000, 140_000) is True


def test_re_ask_spacing_scales_with_the_window():
    """On 1M the gap is 100k, so the same rise that re-asks at 200k stays silent here."""
    assert W.due(420_000, 400_000, 1_000_000, 400_000) is False
    assert W.due(500_000, 400_000, 1_000_000, 400_000) is True


# ---------------------------------------------------------------- messages

def test_the_offer_names_the_numbers_and_the_skill():
    _s, detail = W.verdict(140_000, 200_000, 70, 400_000)
    detail["source"] = "detected"
    msg = W._offer(detail)
    assert "140,000" in msg and "meta-context-watcher" in msg and "detected" in msg


def test_the_misconfigured_message_says_which_knob_to_set():
    _s, detail = W.verdict(563_038, 200_000, 70, 400_000)
    detail["source"] = "assumed"
    msg = W._misconfigured(detail)
    assert "context_window" in msg and "563,038" in msg


# ---------------------------------------------------------------- decide()

@pytest.fixture
def session(request):
    """A session id unique per test AND per run, with its flag removed afterwards.

    The hook persists a once-per-session flag. A fixed id would make these tests pass once and fail
    on every run after - the order-dependent shape that reads as a defect in the code under test.
    """
    name = f"ctxwatch-{request.node.name}-{uuid.uuid4().hex[:8]}"
    yield name
    try:
        W._asked_flag(name).unlink()
    except OSError:
        pass


CFG = {"nudges": True, "context_window": 200_000,
       "context_handover_pct": 70, "context_handover_cap": 400_000}


def _event(session, transcript, cwd):
    return {"session_id": session, "transcript_path": transcript, "cwd": str(cwd),
            "hook_event_name": "Stop"}


def test_over_threshold_blocks_then_waits_a_tenth_of_the_window(tmp_path, session):
    """First ask at the threshold; the next only after another 10% of the window."""
    first = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide(_event(session, first, tmp_path), CFG) is not None

    # same reading, and a small rise: still inside the 20,000-token gap, so silent
    assert W.decide(_event(session, first, tmp_path), CFG) is None
    near = _transcript(tmp_path, _usage_line(cache_read=165_000))
    assert W.decide(_event(session, near, tmp_path), CFG) is None

    # grown a full tenth of the 200k window past the last ask -> asks again
    far = _transcript(tmp_path, _usage_line(cache_read=170_000))
    assert W.decide(_event(session, far, tmp_path), CFG) is not None


def test_under_threshold_never_blocks(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=1000))
    assert W.decide(_event(session, t, tmp_path), CFG) is None


def test_nudges_off_silences_it(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    off = dict(CFG, nudges=False)
    assert W.decide(_event(session, t, tmp_path), off) is None


def test_an_event_without_a_session_or_transcript_is_quiet(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide({"session_id": "", "transcript_path": t, "cwd": str(tmp_path)}, CFG) is None
    assert W.decide({"session_id": session, "transcript_path": "", "cwd": str(tmp_path)}, CFG) is None


def test_it_yields_while_a_nap_is_owed(tmp_path, session, monkeypatch):
    """The Stop gate already refuses to stop on that obligation; two blocks would fight."""
    monkeypatch.setattr(W.sig, "is_nap_owed", lambda proj: True)
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide(_event(session, t, tmp_path), CFG) is None


def test_the_nap_check_failing_does_not_wedge_the_turn(tmp_path, session, monkeypatch):
    def boom(proj):
        raise RuntimeError("helper gone")
    monkeypatch.setattr(W.sig, "is_nap_owed", boom)
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide(_event(session, t, tmp_path), CFG) is not None


# ---------------------------------------------------------------- end to end through the shim

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_emits_a_stop_block(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=900_000))
    rc, out, _err = _run(_event(session, t, tmp_path))
    assert rc == 0, "a Stop hook signals through JSON, not through a non-zero exit"
    payload = json.loads(out)
    assert payload["decision"] == "block" and payload["reason"]


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_is_silent_under_threshold(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=1000))
    assert _run(_event(session, t, tmp_path)) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open(payload):
    rc, out, _err = _run(payload)
    assert (rc, out) == (0, "")
