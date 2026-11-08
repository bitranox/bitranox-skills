"""Tests for context-watcher.py (Stop + PostToolUse hook: ask for a checkpoint before compaction).

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
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

import context_watcher as W

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "context-watcher.py"
SHIM = HOOKS_DIR / "run-python.sh"

# The harness auto-compact window that matches CFG's 140,000 limit (70% of 200,000), so a request
# carries no settings advice unless a test asks for it. The harness compacts about 33,000 below it
# (W._HARNESS_RESERVE), at 107,000, and the save point sits 40,000 below that, at 67,000.
ALIGNED = "140000"


@pytest.fixture(autouse=True)
def _aligned_harness(monkeypatch):
    """Pin CLAUDE_CODE_AUTO_COMPACT_WINDOW, so the outer environment never moves the numbers.

    A test about another window sets or deletes it itself; monkeypatch restores it either way.
    """
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", ALIGNED)


def _usage_line(input_tokens=0, cache_creation=0, cache_read=0, model="claude-opus-5"):
    """One assistant transcript record carrying a usage block, built with json.dumps."""
    return json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "model": model, "usage": {
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
    """The floor keeps the threshold above an empty reading; it does NOT stop an early ask.

    A zero threshold would count a reading of 0 tokens as crossed. A knob at 0 or 1 still asks on
    the first measured turn, which is what that setting asks for - the settings CLI accepts 1 as a
    valid value, so the hook does not second-guess it.
    """
    assert W.threshold(0, 0, 0) == 1
    assert W.threshold(200_000, 0, 400_000) == 1
    assert W.compact_verdict(0, 200_000, 0, 400_000, 0)[0] == "quiet"
    assert W.compact_verdict(502, 200_000, 0, 400_000, 0)[0] == "save"
    assert W.threshold("x", 70, 400_000) is None


# ---------------------------------------------------------------- compact_verdict()

def test_below_the_save_point_is_quiet():
    state, _ = W.compact_verdict(66_999, 200_000, 70, 400_000, 140_000)
    assert state == "quiet"


def test_at_the_save_point_asks_for_a_save():
    """Boundary, from the other side of the previous test - one-sided proves nothing."""
    state, detail = W.compact_verdict(67_000, 200_000, 70, 400_000, 140_000)
    assert state == "save"
    assert (detail["limit"], detail["compact_at"], detail["save_at"]) == (140_000, 107_000, 67_000)
    assert detail["tokens"] == 67_000


def test_measuring_more_than_the_window_is_reported_not_ignored():
    """A threshold nothing can cross looks exactly like a watcher that works."""
    state, detail = W.compact_verdict(563_038, 200_000, 70, 400_000, 0)
    assert state == "misconfigured"
    assert detail["tokens"] == 563_038


def test_the_same_reading_is_fine_on_a_correctly_configured_window():
    """The control for the case above: same number, right window, ordinary save request."""
    state, _ = W.compact_verdict(563_038, 1_000_000, 70, 400_000, 0)
    assert state == "save"


def test_an_unknown_reading_is_quiet():
    assert W.compact_verdict(None, 200_000, 70, 400_000, 0)[0] == "quiet"


# ------------------------------------------------- window_for_model() / resolve_window()
#
# The window comes from the model FAMILY in `message.model`. That was MEASURED, not inferred: over
# 1485 local transcripts every non-haiku family carried far more than a 200K window could hold
# (opus-5 999,946; opus-4-8 999,911; fable-5 997,450; sonnet-5 665,313) while haiku peaked at
# 119,393. Claude Code's `[1m]` suffix never appears in `message.model` and turns out to be
# redundant - the current families run 1M with or without it.

@pytest.mark.parametrize("model_id,expected", [
    ("claude-opus-5", 1_000_000),
    ("claude-opus-4-8", 1_000_000),
    ("claude-fable-5", 1_000_000),
    ("claude-mythos-5", 1_000_000),
    ("claude-sonnet-5", 1_000_000),
    ("claude-sonnet-4-6", 1_000_000),
    ("claude-opus-5[1m]", 1_000_000),         # the suffixed spelling agrees with the bare one
    ("claude-haiku-4-5-20251001", 200_000),
    ("claude-haiku-4-5[1m]", 200_000),        # haiku 4.5 has no 1M variant, suffix or not
    # haiku 5.5 runs 1M: its modelUsage reports contextWindow 1000000, and 73 local transcripts
    # carry a haiku-5-5 request above 200K (peak 301,763) that a 200K window could not hold.
    ("claude-haiku-5-5", 1_000_000),
    ("claude-haiku-5-5[1m]", 1_000_000),
    ("oss-128k-claude", 128_000),
    ("something-unreleased", 200_000),        # unknown errs SMALL - see the test below
    ("", 200_000),
    (None, 200_000),
])
def test_window_for_model(model_id, expected):
    assert W.window_for_model(model_id) == expected


def test_an_unknown_family_errs_SMALL_not_large():
    """Too small asks early and costs a decline; too large sets an unreachable threshold and the
    hook goes silently inert. Only one of those is recoverable."""
    assert W.window_for_model("claude-newthing-9") == 200_000


# ------------------------------------------------- the launcher's declared window
#
# A gateway model id (glm-5.3 behind ANTHROPIC_BASE_URL) is not in the family table, and its API
# advertises no window - so Claude Code defines CLAUDE_CODE_MAX_CONTEXT_TOKENS for the launcher to
# declare it (model-config docs, "correct the window for a gateway or custom model id"). Measured
# on 2.1.269: the variable reaches a Stop hook's subprocess env, and the bitranox glm launcher
# sets it to 1,000,000. Read ONLY for a family the table does not know.

_GLM_ENV = {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "1000000"}


def test_an_unknown_family_takes_the_launchers_declared_window():
    """glm-5.3 on a 1M endpoint: without this leg the 200K default asks at 140K - seven tenths
    early - and the misconfigured check cannot catch it because 140K < 200K reads as fine."""
    assert W.window_for_model("glm-5.3", _GLM_ENV) == 1_000_000
    assert W.resolve_window({}, "glm-5.3", _GLM_ENV) == (1_000_000, "declared")


def test_the_declared_window_must_be_a_positive_number():
    """A zero, negative, or non-numeric declaration is absent, not a window - fall back to small."""
    for bad in ("", "0", "-5", "one-million", None):
        env = {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": bad}
        assert W.window_for_model("glm-5.3", env) == 200_000, bad
        assert W.resolve_window({}, "glm-5.3", env) == (200_000, "assumed"), bad


def test_a_known_family_ignores_the_env_variable():
    """A globally-exported declaration left over from another model must not override a MEASURED
    family window - only an unknown family trusts it. This is the direction the guard must NOT
    apply in; without it every Claude session on a machine exporting the var would switch legs."""
    env = {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "128000"}
    assert W.window_for_model("claude-opus-5", env) == 1_000_000
    assert W.resolve_window({}, "claude-opus-5", env) == (1_000_000, "detected")
    assert W.window_for_model("claude-haiku-4-5", env) == 200_000


def test_an_unknown_family_without_a_declaration_still_errs_small():
    """No family, no declaration: the 200K default, labelled assumed so the message says so."""
    assert W.resolve_window({}, "glm-5.3", {}) == (200_000, "assumed")


def test_no_environ_at_all_is_the_default():
    """The harness passes the real env; a caller passing none gets the small-default contract."""
    assert W.resolve_window({}, "glm-5.3") == (200_000, "assumed")


def test_the_explicit_knob_still_wins_over_the_declaration():
    """context_window is the escape hatch for a declaration the user knows is wrong."""
    assert W.resolve_window({"context_window": 300_000}, "glm-5.3", _GLM_ENV) == (300_000, "configured")


def test_the_declared_window_gives_glm_the_real_threshold():
    """End to end on the numbers of the session that exposed this: 164k of context on glm-5.3
    is past the save point of a wrongly-assumed 200K window at 16% of the real 1M window; against
    the declared window the same reading is quiet."""
    declared_window = W.resolve_window({}, "glm-5.3", _GLM_ENV)[0]
    wrong_window = W.resolve_window({}, "glm-5.3", {})[0]
    assert W.compact_verdict(164_614, wrong_window, 70, 400_000, 0)[0] == "save"
    assert W.compact_verdict(164_614, declared_window, 70, 400_000, 0)[0] == "quiet"


def test_an_explicit_window_overrides_the_family():
    assert W.resolve_window({"context_window": 500_000}, "claude-opus-5") == (500_000, "configured")


def test_the_family_decides_when_no_knob_is_set():
    assert W.resolve_window({}, "claude-opus-5") == (1_000_000, "detected")
    assert W.resolve_window({}, "claude-haiku-4-5") == (200_000, "detected")


def test_no_model_at_all_falls_back_to_the_default():
    assert W.resolve_window({}, None) == (200_000, "assumed")
    assert W.resolve_window({"context_window": 0}, None) == (200_000, "assumed")


# ----------------------------------------------------------------- read_session()

def test_read_session_returns_the_current_reading_and_the_model(tmp_path):
    t = _transcript(tmp_path, _usage_line(cache_read=900_000), _usage_line(cache_read=12_000))
    assert W.read_session(t) == (12_000, "claude-opus-5")


def test_read_session_on_an_unreadable_transcript(tmp_path):
    assert W.read_session(str(tmp_path / "missing.jsonl")) == (None, None)


def test_read_session_carries_the_model_from_a_haiku_session(tmp_path):
    t = _transcript(tmp_path, _usage_line(cache_read=50_000, model="claude-haiku-4-5-20251001"))
    tokens, model = W.read_session(t)
    assert (tokens, W.window_for_model(model)) == (50_000, 200_000)


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

def test_the_save_request_names_the_numbers_and_the_skill():
    _s, detail = W.compact_verdict(150_000, 200_000, 70, 400_000, 140_000)
    detail["source"] = "detected"
    msg = W._save(detail)
    assert "150,000" in msg and "107,000" in msg and "meta-context-watcher" in msg


def test_the_save_request_says_to_replace_the_whole_handover():
    # A session once answered the request with an Edit that appended an update to a handover whose
    # first line still read `# STALE` from the previous hand-back; compact-resume then rightly
    # skipped it as already read, and the fresh checkpoint was lost. The request must say why the
    # whole file is replaced, since the reader acts on the request mid-task, not on the skill.
    _s, detail = W.compact_verdict(150_000, 200_000, 70, 400_000, 140_000)
    msg = W._save(detail)
    assert "Replace the whole file" in msg and "`# STALE`" in msg


def test_the_misconfigured_message_says_which_knob_to_set():
    _s, detail = W.compact_verdict(563_038, 200_000, 70, 400_000, 0)
    detail["source"] = "assumed"
    msg = W._misconfigured(detail)
    assert "context_window" in msg and "563,038" in msg
    # The window is DERIVED from the model, so the message must lead with that and offer the knob
    # only as the fallback. Asserting the knob alone passed against the pre-detection wording, which
    # told the reader to set it outright - and that stale text shipped live for 28 versions behind a
    # duplicate definition of this function.
    assert "derived from the model" in msg


# ---------------------------------------------------------------- is handover.md in git here?
# Whether the outgoing handover.md has an earlier version is a per-repo fact: some repos gitignore
# it, others track it, so the save request must not assert either case everywhere.

def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                   check=True, capture_output=True, env=_git_env())


def _git_env():
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for name in W._GIT_SCOPE_VARS:
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    (root / "sub").mkdir(parents=True)
    _git(root, "init", "-q")
    return root


def test_a_committed_handover_reads_as_tracked_even_from_a_subdirectory(repo):
    (repo / "handover.md").write_bytes(b"# handover\n")
    _git(repo, "add", "handover.md")
    _git(repo, "commit", "-qm", "h")
    assert W.handover_tracking(repo / "sub") == "tracked"


def test_a_gitignored_handover_reads_as_untracked(repo):
    (repo / ".gitignore").write_bytes(b"handover.md\n")
    (repo / "handover.md").write_bytes(b"# handover\n")
    assert W.handover_tracking(repo) == "untracked"


def test_a_handover_never_added_reads_as_untracked(repo):
    (repo / "handover.md").write_bytes(b"# handover\n")
    assert W.handover_tracking(repo) == "untracked"


def test_no_handover_at_all_reads_as_absent(repo):
    assert W.handover_tracking(repo) == "absent"


def test_outside_any_repo_an_existing_handover_has_no_history(tmp_path, monkeypatch):
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "handover.md").write_bytes(b"# handover\n")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert W.handover_tracking(loose) == "untracked"


def test_git_that_cannot_run_reads_as_unknown(repo, monkeypatch):
    def no_git(*_a, **_k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(W.subprocess, "run", no_git)
    assert W.handover_tracking(repo) == "unknown"


def _save_text(tracking):
    _s, detail = W.compact_verdict(150_000, 200_000, 70, 400_000, 140_000)
    detail["source"] = "detected"
    return W._save(detail, tracking)


def test_the_save_request_does_not_claim_a_tracked_handover_is_unrecoverable():
    msg = _save_text("tracked")
    assert "gitignored" not in msg and "no earlier version" not in msg
    assert "git history" in msg and "OPEN-WORK.md" in msg


def test_the_save_request_warns_an_untracked_handover_has_no_earlier_version():
    msg = _save_text("untracked")
    assert "no earlier version" in msg and "OPEN-WORK.md" in msg


def test_the_save_request_names_the_check_when_tracking_is_unknown():
    msg = _save_text("unknown")
    assert "git ls-files --error-unmatch handover.md" in msg
    assert "it is gitignored" not in msg


def test_the_save_request_skips_the_overwrite_warning_when_there_is_no_handover():
    msg = _save_text("absent")
    assert "OVERWRITING" not in msg and "meta-context-watcher" in msg


def test_decide_words_the_save_request_for_the_repo_it_is_in(tmp_path, repo, session):
    (repo / "handover.md").write_bytes(b"# handover\n")
    _git(repo, "add", "handover.md")
    _git(repo, "commit", "-qm", "h")
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    reason = W.decide(_event(session, t, repo), CFG)
    assert reason is not None and "git history" in reason


def test_no_top_level_name_is_defined_twice():
    """A second copy of a function silently wins over the first, and every gate stays green.

    5.218.0 added an updated copy of six functions ABOVE the originals instead of replacing them.
    Python keeps the LAST definition, so the update was dead and the older `_misconfigured` text
    kept firing. Nothing caught it: the copies parse, import and pass their own assertions.
    """
    import ast
    from collections import Counter

    module = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    defined = Counter(
        node.name for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    assert [name for name, seen in defined.items() if seen > 1] == []


# ---------------------------------------------------------------- decide()

@pytest.fixture
def session(request):
    """A session id unique per test AND per run, with its flag removed afterwards.

    The hook persists a once-per-session flag. A fixed id would make these tests pass once and fail
    on every run after - the order-dependent shape that reads as a defect in the code under test.
    """
    name = f"ctxwatch-{request.node.name}-{uuid.uuid4().hex[:8]}"
    yield name
    for flag in (W._asked_flag(name), W._misconfigured_flag(name),
                 W.sig.checkpoint_asked_file(name)):
        try:
            flag.unlink()
        except OSError:
            pass


# A 200,000 window with the harness aligned at its 140,000 limit (the autouse fixture): the save
# point is 67,000, and a repeat request waits a tenth of the window, 20,000 more.
CFG = {"nudges": True, "context_window": 200_000,
       "context_handover_pct": 70, "context_handover_cap": 400_000}


def _event(session, transcript, cwd):
    return {"session_id": session, "transcript_path": transcript, "cwd": str(cwd),
            "hook_event_name": "Stop"}


def test_over_the_save_point_asks_then_waits_a_tenth_of_the_window(tmp_path, session):
    """First ask past the save point; the next only after another 10% of the window."""
    first = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide(_event(session, first, tmp_path), CFG) is not None

    # same reading, and a small rise: still inside the 20,000-token gap, so silent
    assert W.decide(_event(session, first, tmp_path), CFG) is None
    near = _transcript(tmp_path, _usage_line(cache_read=165_000))
    assert W.decide(_event(session, near, tmp_path), CFG) is None

    # grown a full tenth of the 200k window past the last ask -> asks again
    far = _transcript(tmp_path, _usage_line(cache_read=170_000))
    assert W.decide(_event(session, far, tmp_path), CFG) is not None


def test_a_subagent_tool_call_neither_asks_nor_spends_the_main_sessions_request(tmp_path, session):
    """A subagent's PostToolUse carries the MAIN transcript and session plus its own agent_id."""
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    sub = dict(_event(session, t, tmp_path), hook_event_name="PostToolUse", agent_id="a59e0edd6e4a")
    assert W.decide(sub, CFG) is None
    # the main session's own next tool call still gets the request
    main = dict(_event(session, t, tmp_path), hook_event_name="PostToolUse")
    assert W.decide(main, CFG) is not None


def test_an_event_naming_a_subagent_transcript_is_quiet(tmp_path, session):
    sub_dir = tmp_path / "sess" / "subagents"
    sub_dir.mkdir(parents=True)
    t = sub_dir / "agent-a59e0edd6e4a.jsonl"
    t.write_text(_usage_line(cache_read=150_000) + "\n", encoding="utf-8")
    ev = dict(_event(session, str(t), tmp_path), hook_event_name="PostToolUse")
    assert W.decide(ev, CFG) is None


@pytest.mark.parametrize(("event", "expected"), [
    ({"agent_id": "abc"}, True),
    ({"agent_id": None, "transcript_path": "/p/s.jsonl"}, False),
    ({"agent_id": "", "transcript_path": "/p/s.jsonl"}, False),
    ({"transcript_path": "/p/s/subagents/agent-abc.jsonl"}, True),
    ({"transcript_path": "/p/agent-notes/s.jsonl"}, False),
    ({}, False),
])
def test_is_subagent_event(event, expected):
    assert W.is_subagent_event(event) is expected


def test_under_the_save_point_never_asks(tmp_path, session):
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


def test_it_does_not_yield_to_a_nap_the_user_declined(tmp_path, session, monkeypatch):
    """A declined nap no longer blocks at Stop, so yielding to it would silence this note for
    nothing. The owed-but-undeclined arm is the control: same state, no decline, it yields."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    W.sig.mark_nap_owed(str(tmp_path), session_id="sid-old")
    assert W.decide(_event(session, t, tmp_path), CFG) is None
    W.sig.decline_nap_owed(str(tmp_path), by="user")
    assert W.decide(_event(session, t, tmp_path), CFG) is not None


def test_the_nap_check_failing_does_not_wedge_the_turn(tmp_path, session, monkeypatch):
    def boom(proj):
        raise RuntimeError("helper gone")
    monkeypatch.setattr(W.sig, "is_nap_owed", boom)
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    assert W.decide(_event(session, t, tmp_path), CFG) is not None


def test_an_earlier_save_request_does_not_silence_the_misconfigured_notice(tmp_path, session):
    """The two answers are different questions, so an answer to one cannot latch the other.

    Asking for a save at 150k and then measuring MORE than the window means the window is wrong -
    the one thing the misconfigured notice exists to say. Were both on one flag, the request's flag
    would read as "already reported" and the notice would never speak for the rest of the session.
    """
    first = _transcript(tmp_path, _usage_line(cache_read=150_000))
    reason = W.decide(_event(session, first, tmp_path), CFG)
    assert reason is not None and "OPEN-WORK.md" in reason

    over = _transcript(tmp_path, _usage_line(cache_read=211_000))
    notice = W.decide(_event(session, over, tmp_path), CFG)
    assert notice is not None and "MORE than the 200,000" in notice


def test_the_misconfigured_notice_still_says_itself_only_once(tmp_path, session):
    """The control for the latch split: the notice keeps its own once-per-session latch."""
    over = _transcript(tmp_path, _usage_line(cache_read=211_000))
    assert W.decide(_event(session, over, tmp_path), CFG) is not None
    further = _transcript(tmp_path, _usage_line(cache_read=260_000))
    assert W.decide(_event(session, further, tmp_path), CFG) is None


def test_a_misconfigured_notice_does_not_consume_the_save_request(tmp_path, session):
    """The other direction of the split: a notice first leaves the request's re-ask level unset."""
    over = _transcript(tmp_path, _usage_line(cache_read=211_000))
    assert W.decide(_event(session, over, tmp_path), CFG) is not None
    assert W.asked_at(session) == 0


def test_a_continuation_another_stop_hook_forced_is_not_blocked_again(tmp_path, session):
    """`stop_hook_active` means a Stop hook already kept this turn going; blocking it again stacks
    a second interruption on the same turn and burns the consecutive-block budget."""
    t = _transcript(tmp_path, _usage_line(cache_read=150_000))
    forced = dict(_event(session, t, tmp_path), stop_hook_active=True)
    assert W.decide(forced, CFG) is None
    # control: the same reading on an ordinary Stop still asks, and the flag above consumed nothing
    assert W.decide(_event(session, t, tmp_path), CFG) is not None


@pytest.mark.parametrize("junk", ["plain string", 7, ["a", "list"]])
def test_a_non_object_message_is_skipped_not_fatal(tmp_path, session, junk):
    """A record whose `message` is not an object must be skipped, not end the scan.

    `.get` on a string raised AttributeError; main() swallowed it, so the watcher returned nothing
    for every later turn of a transcript holding one such line.
    """
    t = _transcript(tmp_path, _usage_line(cache_read=190_000),
                    json.dumps({"type": "user", "message": junk}))
    assert W.read_session(t) == (190_000, "claude-opus-5")
    assert W.context_tokens(t) == 190_000
    assert W.decide(_event(session, t, tmp_path), CFG) is not None


# ---------------------------------------------------------------- end to end through the shim

def _run(payload, home=None):
    """(rc, stdout, stderr) of the hook through the shim; `home` keeps the user's config out."""
    env = None
    if home is not None:
        (home / ".claude").mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_emits_a_stop_block(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=900_000))
    rc, out, _err = _run(_event(session, t, tmp_path), home=tmp_path / "home")
    assert rc == 0, "a Stop hook signals through JSON, not through a non-zero exit"
    payload = json.loads(out)
    assert payload["decision"] == "block" and "OPEN-WORK.md" in payload["reason"]


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_is_silent_under_the_save_point(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=1000))
    assert _run(_event(session, t, tmp_path), home=tmp_path / "home") == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open(payload):
    rc, out, _err = _run(payload)
    assert (rc, out) == (0, "")


# ---------------------------------------------------------------- the save point
#
# The limit is where the HARNESS compacts, so the watcher asks for a checkpoint early enough that the session can write it before the compaction arrives, then lets it continue.
# Measured on CLI 2.1.310 (scripted probes, CLAUDE_CODE_AUTO_COMPACT_WINDOW 100k and 200k): the
# harness compacts about 33k tokens BELOW that window, not at it and not at a fixed percentage.

CCFG = {"nudges": True, "context_window": 1_000_000,
        "context_handover_pct": 70, "context_handover_cap": 500_000}


def _compact_event(session, transcript, cwd, name="PostToolUse"):
    return {"session_id": session, "transcript_path": transcript, "cwd": str(cwd),
            "hook_event_name": name}


def test_the_compaction_point_sits_the_measured_reserve_below_the_window():
    assert W.compaction_point(500_000, 500_000) == 467_000
    # an unknown or larger harness window: the configured limit is what it should be set to
    assert W.compaction_point(500_000, 0) == 467_000
    assert W.compaction_point(500_000, 967_000) == 467_000
    # a SMALLER harness window compacts earlier, and that is where the save must come first
    assert W.compaction_point(500_000, 300_000) == 267_000


def test_the_save_point_leaves_room_before_the_compaction():
    assert W.save_point(467_000) == 420_300
    assert W.save_point(100_000) == 60_000
    assert W.save_point(10) == 1


def test_compact_mode_asks_for_a_checkpoint_mid_turn_and_says_continue(tmp_path, session,
                                                                        monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    t = _transcript(tmp_path, _usage_line(cache_read=430_000))
    text = W.decide(_compact_event(session, t, tmp_path), CCFG)
    assert text is not None
    assert "OPEN-WORK.md" in text and "handover.md" in text
    assert "CONTINUE" in text
    assert "/clear" not in text.replace("do not tell them to /clear", "")
    assert "start a fresh session" not in text
    assert "update-config" not in text, "an aligned harness needs no settings advice"
    assert W.sig.checkpoint_asked_at(session) > 0


def test_compact_mode_is_quiet_below_the_save_point(tmp_path, session, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    t = _transcript(tmp_path, _usage_line(cache_read=420_299))
    assert W.decide(_compact_event(session, t, tmp_path), CCFG) is None
    assert W.sig.checkpoint_asked_at(session) == 0


def test_compact_mode_asks_once_then_rearms_after_the_compaction(tmp_path, session, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    high = _transcript(tmp_path, _usage_line(cache_read=430_000))
    higher = _transcript(tmp_path, _usage_line(cache_read=460_000))
    after = _transcript(tmp_path, _usage_line(cache_read=40_000))
    assert W.decide(_compact_event(session, high, tmp_path), CCFG) is not None
    assert W.decide(_compact_event(session, higher, tmp_path), CCFG) is None
    assert W.decide(_compact_event(session, after, tmp_path), CCFG) is None   # compacted: re-arm
    assert W.decide(_compact_event(session, high, tmp_path), CCFG) is not None


def test_compact_mode_tells_how_to_align_an_unset_harness_window(tmp_path, session, monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", raising=False)
    t = _transcript(tmp_path, _usage_line(cache_read=430_000))
    text = W.decide(_compact_event(session, t, tmp_path), CCFG)
    assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" in text and "500000" in text
    assert "update-config" in text


def test_compact_mode_blocks_on_stop_with_the_same_request(tmp_path, session, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    t = _transcript(tmp_path, _usage_line(cache_read=430_000))
    text = W.decide(_compact_event(session, t, tmp_path, name="Stop"), CCFG)
    assert text is not None and "OPEN-WORK.md" in text


def test_a_stored_handover_mode_behaves_exactly_like_compact_mode(tmp_path, session,
                                                                   monkeypatch):
    """A stored `context_mode = handover` is not read: the watcher has one
    mode, so PostToolUse and Stop both carry the save request, word for word what a config
    without the key gets. `mark_asked(session, 0)` re-arms the request between the calls."""
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    t = _transcript(tmp_path, _usage_line(cache_read=430_000))
    old = dict(CCFG, context_mode="handover")
    post = W.decide(_compact_event(session, t, tmp_path), old)
    assert post is not None and "OPEN-WORK.md" in post and "CONTINUE" in post
    W.mark_asked(session, 0)
    stop = W.decide(_compact_event(session, t, tmp_path, name="Stop"), old)
    assert stop == post
    W.mark_asked(session, 0)
    assert W.decide(_compact_event(session, t, tmp_path, name="Stop"), CCFG) == stop
    # The stored key never reaches decide() through the real loader either.
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".bitranox-memory.json").write_text(
        json.dumps({"context_mode": "handover"}), encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    assert "context_mode" not in W.sig.load_config()


def test_a_posttooluse_nudge_is_not_silenced_by_an_owed_nap(tmp_path, session, monkeypatch):
    """The nap blocks only at Stop; a mid-turn context note cannot fight it over a turn."""
    monkeypatch.setenv("CLAUDE_CODE_AUTO_COMPACT_WINDOW", "500000")
    monkeypatch.setattr(W.sig, "is_nap_owed", lambda proj: True)
    t = _transcript(tmp_path, _usage_line(cache_read=430_000))
    assert W.decide(_compact_event(session, t, tmp_path), CCFG) is not None


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_posttooluse_emits_additional_context(tmp_path, session):
    t = _transcript(tmp_path, _usage_line(cache_read=900_000, model="claude-opus-5"))
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    env.pop("CLAUDE_CODE_AUTO_COMPACT_WINDOW", None)
    proc = subprocess.run(["bash", str(SHIM), str(SCRIPT)],
                          input=json.dumps(_compact_event(session, t, tmp_path)),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env)
    assert proc.returncode == 0
    hso = json.loads(proc.stdout)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PostToolUse" and "OPEN-WORK.md" in hso["additionalContext"]
