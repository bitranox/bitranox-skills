"""End-to-end tests for the Stop gate in DECIDE mode (`classifier_stop_signal = decide`).

The hook runs in-process exactly as Claude Code drives it (event JSON on stdin, the decision on
stdout), with a real config file, a real API key env var and the loopback base-URL override
pointing at a local fake TypeSafe server whose answer each test scripts. Nothing inside the hook is
patched.

What decide mode promises - the union adjudicated blind on 2026-09-25, at 0.8:

* the keyword patterns still block on their own, and Jev is not asked when they already do;
* on a turn they leave quiet, Jev is asked while the stop waits, and the gate blocks when any
  learning family scores at least the site threshold - `endorsement` is logged, never a firing;
* Jev does not answer (deadline, HTTP error, no key, malformed answer): the keyword verdict
  stands, so a quiet turn stays unblocked;
* a message already blocked once is not asked about again;
* `correction` counts only when the typed prompt is at least `MIN_PROMPT_CHARS` long: on a short
  steering prompt ("release first") it is logged, never a block, while every other family still
  blocks after a bare "yes", which is where most admissions and root causes are said;
* one comparison row per asked or regex-decided turn lands in the shadow log, naming the path.
"""

import io
import json
import sys
import time

import pytest

import classifier as cl
import self_improve_gate as G

# 40+ characters, so every family - `correction` included - can block after it.
QUIET_USER = "Please list every file in this repository for me."
QUIET_ASST = "Here are the files: a.py, b.py."
FIRING = ("correction", "remember_rule", "self_admission", "realization")


@pytest.fixture
def env(tmp_path, monkeypatch, fake_jev):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(state))
    fake = fake_jev()
    monkeypatch.setenv("TYPESAFE_API_KEY", "k" * 20)
    monkeypatch.setenv(cl.BASE_URL_ENV, fake.url)
    return {"home": home, "state": state, "fake": fake, "tmp": tmp_path}


def _config(home, **knobs):
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(knobs), encoding="utf-8")


def _decide(home):
    _config(home, classifier_backend="jev", classifier_stop_signal="decide")


def _answer(**scores):
    """A scripted Jev answer: every family at 0.05 unless named."""
    values = {q.id: scores.get(q.id, 0.05) for q in cl.stop_signal_questions()}
    return {"model": "jev-1.13.0", "usage": {"input_tokens": 321},
            "answers": {qid: {"type": "noul", "noul": v} for qid, v in values.items()}}


def _event(tmp, user=QUIET_USER, asst=QUIET_ASST, sid="s-decide"):
    t = tmp / ("transcript-%s.jsonl" % sid)
    t.write_text("\n".join([json.dumps({"type": "user", "message": {"content": user}}),
                            json.dumps({"type": "assistant", "message": {"content": asst}})])
                 + "\n", encoding="utf-8")
    return {"transcript_path": str(t), "cwd": str(tmp), "session_id": sid}


def _run(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert G.main() == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out).get("decision") if out else None


def _rows(home):
    audit = home / ".claude" / "self-improve-audit"
    return [json.loads(x) for f in cl.shadow_log_files(audit)
            for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_control_off_does_not_block_the_quiet_turn(env, monkeypatch, capsys):
    env["fake"].body = _answer(self_admission=0.95)
    _config(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"])) is None
    assert env["fake"].requests == []


@pytest.mark.parametrize("family", FIRING)
def test_decide_blocks_a_quiet_turn_when_a_learning_family_reaches_the_threshold(
        env, monkeypatch, capsys, family):
    env["fake"].body = _answer(**{family: cl.SITE_THRESHOLDS["stop_signal"]})
    _decide(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"], sid="s-" + family)) == "block"
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"]) == ("decide", "jev")


def test_decide_threshold_is_the_adjudicated_point_eight(env, monkeypatch, capsys):
    # 0.75 passes the old 0.7 reading and must not block: the user chose 0.8 on 2026-10-01.
    assert cl.SITE_THRESHOLDS["stop_signal"] == 0.8
    env["fake"].body = _answer(self_admission=0.75)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"])) is None
    [row] = _rows(env["home"])
    assert row["decide_path"] == "none"


def test_decide_never_blocks_on_endorsement_alone(env, monkeypatch, capsys):
    env["fake"].body = _answer(endorsement=0.99)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"])) is None


def test_decide_does_not_ask_jev_when_the_keywords_already_block(env, monkeypatch, capsys):
    env["fake"].body = _answer()
    _decide(env["home"])
    ev = _event(env["tmp"], user="No, that is wrong - always use uv.")
    assert _run(monkeypatch, capsys, ev) == "block"
    assert env["fake"].requests == []
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"], row["results"]) == ("decide", "regex", [])


@pytest.mark.parametrize("failure", ["deadline", "http", "no-key", "malformed"])
def test_decide_keeps_the_keyword_verdict_when_jev_does_not_answer(env, monkeypatch, capsys,
                                                                    failure):
    env["fake"].body = _answer(self_admission=0.95)
    if failure == "deadline":
        env["fake"].delay = cl.DEFAULT_DEADLINE + 1.0
    elif failure == "http":
        env["fake"].status = 500
    elif failure == "no-key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    else:
        env["fake"].body = b"not json"
    _decide(env["home"])
    t0 = time.monotonic()
    assert _run(monkeypatch, capsys, _event(env["tmp"], sid="s-" + failure)) is None
    assert time.monotonic() - t0 < cl.DEFAULT_DEADLINE + 1.0, "the deadline must bound the stop"
    [row] = _rows(env["home"])
    assert row["decide_path"].startswith("fallback")


def test_decide_does_not_ask_again_about_a_message_it_already_blocked(env, monkeypatch, capsys):
    env["fake"].body = _answer(correction=0.9)
    _decide(env["home"])
    ev = _event(env["tmp"])
    assert _run(monkeypatch, capsys, ev) == "block"
    assert _run(monkeypatch, capsys, ev) is None
    assert len(env["fake"].requests) == 1


def test_shadow_still_never_blocks_on_jev(env, monkeypatch, capsys):
    env["fake"].body = _answer(self_admission=0.95)
    _config(env["home"], classifier_backend="jev", classifier_stop_signal="shadow")
    assert _run(monkeypatch, capsys, _event(env["tmp"])) is None


def test_quiet_user_is_long_enough_for_every_family():
    assert len(QUIET_USER) >= cl.MIN_PROMPT_CHARS["correction"]


@pytest.mark.parametrize("prompt", ["release first", "yes, but dont release now", "B", ""])
def test_decide_does_not_block_on_correction_after_a_short_prompt(env, monkeypatch, capsys,
                                                                   prompt):
    # Adjudicated 2026-10-06: 8 of correction's 14 blocks were short steering prompts, not lessons.
    env["fake"].body = _answer(correction=0.95)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"], user=prompt, sid="s-short")) is None
    [row] = _rows(env["home"])
    assert (row["decide_path"], row["families"]) == ("none", [])
    assert row["results"], "the raw correction score must still be logged for re-measurement"


@pytest.mark.parametrize("length, blocks", [(39, None), (40, "block")])
def test_correction_prompt_length_boundary_is_forty(env, monkeypatch, capsys, length, blocks):
    env["fake"].body = _answer(correction=0.95)
    _decide(env["home"])
    prompt = ("please move the lookup somewhere else " * 3)[:length]
    assert len(prompt) == length
    assert _run(monkeypatch, capsys, _event(env["tmp"], user=prompt,
                                            sid="s-len%d" % length)) == blocks


def test_short_prompt_padding_does_not_count_toward_the_length(env, monkeypatch, capsys):
    env["fake"].body = _answer(correction=0.95)
    _decide(env["home"])
    prompt = "  release first" + " " * 40
    assert _run(monkeypatch, capsys, _event(env["tmp"], user=prompt)) is None


@pytest.mark.parametrize("family", ["self_admission", "realization", "remember_rule"])
def test_other_families_still_block_after_a_bare_yes(env, monkeypatch, capsys, family):
    # Most real lessons follow "yes" / "continue": the admission is in the reply, not the prompt.
    env["fake"].body = _answer(**{family: 0.95})
    _decide(env["home"])
    assert _run(monkeypatch, capsys, _event(env["tmp"], user="yes", sid="s-" + family)) == "block"
    [row] = _rows(env["home"])
    assert row["families"] == [family]
