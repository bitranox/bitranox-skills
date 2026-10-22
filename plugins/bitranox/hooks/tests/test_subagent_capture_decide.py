"""End-to-end tests for the subagent capture in DECIDE mode (`classifier_subagent_signal = decide`).

The hook runs in-process exactly as Claude Code drives it (a SubagentStop event on stdin), with a
real config file, a real API key env var and the loopback base-URL override pointing at a local
fake TypeSafe server that answers per message. Nothing inside the hook is patched.

What decide mode promises - the site passed the pre-registered [96] rule on 2026-10-22 (blind
review: the patterns wrong on 24 of 30 disagreements, Jev on 6), and the user chose this design:

* Jev decides every message it answers: a message is buffered when either question scores at least
  the site threshold, whatever the patterns said - so a broad-only hit Jev leaves quiet is no
  longer buffered, and a message the patterns miss is;
* a message Jev does not answer (deadline, HTTP error, no key, malformed answer), and an earlier
  message the request cap left out, falls back to the STRICT patterns only, never the broad ones;
* the messages are asked in parallel, so the stop waits about one call, bounded by the deadline;
* one row per subagent lands in the shadow log, naming the path and each message's decision;
* off and shadow keep buffering exactly as before.
"""

import io
import json
import time

import pytest

import classifier as cl
import self_improve_signals as S
import subagent_capture as C

STRICT = "I was wrong - the real cause is the stale venv."
BROAD = "All gates green; committing it per the repo iron rule."
QUIET = "Here are the files: a.py, b.py."
LEARNING = "The cache key ignores the interpreter, which is why the stale wheel loaded."


@pytest.fixture
def env(tmp_path, monkeypatch, fake_jev):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("TYPESAFE_API_KEY", "k" * 20)
    scores = {}

    def answer(request):
        text = (request.get("state") or {}).get("assistant_reply", "")
        values = scores.get(text, {})
        return {"model": "jev-1.14.0", "usage": {"input_tokens": 300},
                "answers": {q.id: {"type": "noul", "noul": values.get(q.id, 0.05)}
                            for q in cl.subagent_signal_questions()}}

    fake = fake_jev(answer_fn=answer)
    monkeypatch.setenv(cl.BASE_URL_ENV, fake.url)
    return {"home": home, "fake": fake, "tmp": tmp_path, "scores": scores}


def _config(home, mode):
    knobs = {"classifier_backend": "jev", "classifier_subagent_signal": mode} if mode else {}
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(knobs), encoding="utf-8")


def _event(tmp, texts, session="s-dec"):
    path = tmp / "agent.jsonl"
    lines = [json.dumps({"type": "user", "message": {"content": "do the task"}})]
    lines += [json.dumps({"type": "assistant", "message": {"content": t}}) for t in texts]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    main = tmp / "main.jsonl"
    main.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n",
                    encoding="utf-8")
    return {"hook_event_name": "SubagentStop", "session_id": session, "agent_id": "a1",
            "agent_type": "general-purpose", "agent_transcript_path": str(path),
            "transcript_path": str(main)}


def _run(monkeypatch, event):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert C.main() == 0


def _buffered(session="s-dec"):
    return [h["snippet"] for h in S.read_subagent_learnings(session)]


def _rows(home):
    audit = home / ".claude" / "self-improve-audit"
    return [json.loads(x) for f in cl.shadow_log_files(audit)
            for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_fixtures_hit_the_pattern_kind_their_name_says():
    assert C._verdict(STRICT)["kind"] == "strict"
    assert C._verdict(BROAD)["kind"] == "broad_only"
    assert C._verdict(QUIET)["kind"] == "none"
    assert C._verdict(LEARNING)["kind"] == "none"


def test_control_off_buffers_a_broad_only_hit_and_asks_nothing(env, monkeypatch):
    _config(env["home"], None)
    _run(monkeypatch, _event(env["tmp"], [BROAD]))
    assert len(_buffered()) == 1
    assert env["fake"].requests == []


def test_decide_buffers_a_message_the_patterns_miss_when_jev_fires(env, monkeypatch):
    env["scores"][LEARNING] = {"realization": 0.9}
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [QUIET, LEARNING]))
    [hit] = S.read_subagent_learnings("s-dec")
    assert "stale wheel" in hit["snippet"]
    assert hit["matched"] == ["jev:realization"]


def test_decide_drops_a_broad_only_hit_jev_leaves_quiet(env, monkeypatch):
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [BROAD]))
    assert _buffered() == []


def test_decide_lets_jev_overrule_a_strict_hit_it_answers_quiet(env, monkeypatch):
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [STRICT]))
    assert _buffered() == []


def test_decide_threshold_is_the_site_threshold(env, monkeypatch):
    th = cl.SITE_THRESHOLDS["subagent_signal"]
    assert th == 0.8
    env["scores"][LEARNING] = {"self_admission": th}
    env["scores"][QUIET] = {"self_admission": 0.79}
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [QUIET, LEARNING]))
    assert len(_buffered()) == 1 and "stale wheel" in _buffered()[0]


@pytest.mark.parametrize("failure", ["deadline", "http", "no-key", "malformed"])
def test_decide_falls_back_to_the_strict_patterns_when_jev_does_not_answer(
        env, monkeypatch, failure):
    env["scores"][LEARNING] = {"realization": 0.95}
    if failure == "deadline":
        env["fake"].delay = cl.DEFAULT_DEADLINE + 1.0
    elif failure == "http":
        env["fake"].status = 500
    elif failure == "no-key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    else:
        env["fake"].answer_fn = lambda request: b"not json"
    _config(env["home"], "decide")
    t0 = time.monotonic()
    _run(monkeypatch, _event(env["tmp"], [STRICT, BROAD, LEARNING]))
    assert time.monotonic() - t0 < cl.DEFAULT_DEADLINE + 1.0, "the deadline must bound the stop"
    [hit] = S.read_subagent_learnings("s-dec")
    assert "stale venv" in hit["snippet"] and hit["matched"] == ["strict"]
    [row] = _rows(env["home"])
    assert row["mode"] == "decide" and row["decide_path"].startswith("fallback")


def test_decide_falls_back_to_strict_for_messages_the_cap_left_out(env, monkeypatch):
    cap = C.SHADOW_MAX_MESSAGES
    filler = ["Step %d is done." % i for i in range(cap)]
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [STRICT, BROAD] + filler))
    assert len(env["fake"].requests) == cap
    [hit] = S.read_subagent_learnings("s-dec")
    assert "stale venv" in hit["snippet"] and hit["matched"] == ["strict"]


def test_decide_asks_the_messages_in_parallel(env, monkeypatch):
    env["fake"].delay = 0.3
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], ["Message %d is here." % i for i in range(4)]))
    assert len(env["fake"].requests) == 4
    assert env["fake"].max_in_flight > 1


def test_decide_logs_one_row_naming_each_message_decision(env, monkeypatch):
    env["scores"][LEARNING] = {"self_admission": 0.9}
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [BROAD, LEARNING]))
    [row] = _rows(env["home"])
    assert row["site"] == "subagent_signal" and row["mode"] == "decide"
    assert row["decide_path"] == "jev"
    assert row["decided"] == ["none", "jev"]
    assert [m["kind"] for m in row["regex"]["messages"]] == ["broad_only", "none"]


def test_decide_logs_none_when_jev_answers_and_nothing_fires(env, monkeypatch):
    _config(env["home"], "decide")
    _run(monkeypatch, _event(env["tmp"], [QUIET]))
    [row] = _rows(env["home"])
    assert (row["decide_path"], row["decided"]) == ("none", ["none"])
