"""End-to-end tests for the skill router in DECIDE mode (`classifier_skill_router = decide`).

The hook runs in-process exactly as Claude Code drives it (event JSON on stdin, the nudge on
stdout), with a real config file, a real API key env var and the loopback base-URL override
pointing at a local fake TypeSafe server whose answer each test scripts. Nothing inside the hook
is patched.

What decide mode promises:

* Jev answers and the production rule `classifier.choice_pick` picks a skill: that ONE skill is
  nudged, and the keyword hits are not;
* Jev answers and picks nothing: nothing is nudged - "no skill" is an answer, not a failure;
* Jev does not answer (deadline, HTTP error, no key, malformed answer): the keyword nudge,
  byte for byte;
* one comparison row per prompt lands in the shadow log, saying which path decided.
"""

import io
import json
import sys
import time

import pytest

import classifier as cl
import skill_router as SR

# Keyword-matches `compuse-git` (5 hits), so a keyword nudge exists to be suppressed or kept.
PROMPT = "git commit fails with a CRLF line ending and the hook is not executable"
# A shipped skill the keywords do NOT match for PROMPT, so a Jev pick is distinguishable.
JEV_PICK = "process-debug-systematic"


@pytest.fixture
def env(tmp_path, monkeypatch, fake_jev):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    fake = fake_jev()
    monkeypatch.setenv("TYPESAFE_API_KEY", "k" * 20)
    monkeypatch.setenv(cl.BASE_URL_ENV, fake.url)
    return {"home": home, "fake": fake, "tmp": tmp_path}


def _config(home, **knobs):
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(knobs), encoding="utf-8")


def _decide(home):
    _config(home, classifier_backend="jev", classifier_skill_router="decide")


def _answer(gate, winner, prob):
    """A scripted Jev answer to the router's gate-plus-choice request."""
    return {"model": "jev-1.13.0", "usage": {"input_tokens": 321},
            "answers": {cl.NEW_TASK_ID: {"type": "noul", "noul": gate},
                        cl.PICK_ID: {"type": "choice", "choice": winner,
                                     "probabilities": {winner: prob}, "confidence": 0.7}}}


def _run(monkeypatch, capsys, sid, prompt=PROMPT, **extra):
    event = {"prompt": prompt, "cwd": "/p/x", "session_id": sid, **extra}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert SR.main() == 0
    return capsys.readouterr().out


def _nudged(out):
    """The skill names the router block tells the model to invoke, in order."""
    if not out:
        return []
    text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    return [line.split("`")[1] for line in text.splitlines() if "`" in line]


def _rows(home):
    audit = home / ".claude" / "self-improve-audit"
    return [json.loads(x) for f in cl.shadow_log_files(audit)
            for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def _keyword_output(env, monkeypatch, capsys):
    """Today's output for PROMPT with the classifier off, in a session of its own."""
    _config(env["home"])
    out = _run(monkeypatch, capsys, "s-keywords")
    assert _nudged(out) == ["bitranox:compuse-git"], "the baseline must actually nudge"
    return out


# ---- Jev decides ----------------------------------------------------------------------------

def test_decide_nudges_only_the_confident_jev_pick_and_not_the_keyword_hits(env, monkeypatch,
                                                                             capsys):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.8)
    _decide(env["home"])
    out = _run(monkeypatch, capsys, "s-pick")
    assert _nudged(out) == ["bitranox:" + JEV_PICK]
    assert "<BITRANOX-SKILL-ROUTER>" in out and "compuse-git" not in out


def test_decide_bypass_takes_a_sure_winner_past_a_failed_gate(env, monkeypatch, capsys):
    env["fake"].body = _answer(0.2, JEV_PICK, cl.CHOICE_BYPASS)
    _decide(env["home"])
    assert _nudged(_run(monkeypatch, capsys, "s-bypass")) == ["bitranox:" + JEV_PICK]


def test_decide_names_another_plugins_skill_by_its_full_name(env, monkeypatch, capsys):
    listing = {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": True, "skillCount": 2,
        "names": ["bitranox:files-edit-xml", "typesafe:typesafe-ai"],
        "content": "- bitranox:files-edit-xml: Use when editing XML.\n"
                   "- typesafe:typesafe-ai: Build AI-powered software with TypeSafe."}}
    t = env["tmp"] / "transcript.jsonl"
    t.write_text(json.dumps(listing) + "\n", encoding="utf-8")
    env["fake"].body = _answer(0.9, "typesafe:typesafe-ai", 0.9)
    _decide(env["home"])
    out = _run(monkeypatch, capsys, "s-other", prompt="add a TypeSafe classifier to this app",
               transcript_path=str(t))
    assert _nudged(out) == ["typesafe:typesafe-ai"]


def test_decide_injects_nothing_when_the_gate_fails_and_the_winner_is_unsure(env, monkeypatch,
                                                                              capsys):
    env["fake"].body = _answer(0.2, JEV_PICK, 0.6)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, "s-unsure") == ""


def test_decide_injects_nothing_when_jev_says_no_skill_is_needed(env, monkeypatch, capsys):
    env["fake"].body = _answer(0.9, cl.NO_SKILL_KEY, 0.95)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, "s-none") == ""


def test_decide_does_not_nudge_a_pick_already_nudged_this_session(env, monkeypatch, capsys):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.8)
    _decide(env["home"])
    assert _nudged(_run(monkeypatch, capsys, "s-twice")) == ["bitranox:" + JEV_PICK]
    # The second prompt still has keyword hits; a spent Jev pick must not fall back to them.
    assert _run(monkeypatch, capsys, "s-twice") == ""


# ---- Jev does not answer: today's keyword nudge, byte for byte -------------------------------

@pytest.mark.parametrize("failure", ["deadline", "http", "no-key", "malformed"])
def test_decide_falls_back_to_the_keyword_nudge_when_jev_does_not_answer(env, monkeypatch,
                                                                          capsys, failure):
    baseline = _keyword_output(env, monkeypatch, capsys)
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
    out = _run(monkeypatch, capsys, "s-fallback-" + failure)
    assert out == baseline
    assert time.monotonic() - t0 < cl.DEFAULT_DEADLINE + 1.0, "the deadline must bound the hook"


# ---- off and shadow are unchanged -------------------------------------------------------------

@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_off_and_shadow_keep_the_keyword_nudge_even_beside_a_confident_jev(env, monkeypatch,
                                                                           capsys, mode):
    baseline = _keyword_output(env, monkeypatch, capsys)
    env["fake"].body = _answer(0.9, JEV_PICK, 0.9)
    _config(env["home"], classifier_backend="jev", classifier_skill_router=mode)
    assert _run(monkeypatch, capsys, "s-" + mode) == baseline
    if mode == "shadow":  # let the detached child finish before the fixture tears down
        end = time.monotonic() + 20
        while not _rows(env["home"]) and time.monotonic() < end:
            time.sleep(0.1)
        assert [r.get("mode") for r in _rows(env["home"])] == [None]


# ---- the comparison row -----------------------------------------------------------------------

def test_decide_logs_one_row_saying_jev_decided_and_spawns_no_shadow_child(env, monkeypatch,
                                                                           capsys):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.8)
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-row")
    time.sleep(1.0)  # a detached shadow child, had one been spawned, would have asked by now
    assert len(env["fake"].requests) == 1
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"], row["nudged"]) == ("decide", "jev", [JEV_PICK])
    assert row["site"] == "skill_router" and row["session_id"] == "s-row"
    assert set(row["results"][0]["answers"]) == {cl.NEW_TASK_ID, cl.PICK_ID}
    assert row["regex"]["selected"] == ["compuse-git"]
    assert row["regex"]["question_view"] == SR.QUESTION_VIEW
    assert row["states"][0]["user_prompt"] == PROMPT
    assert row["reason"] is None and row["input_tokens"] == 321


@pytest.mark.parametrize("body,path,nudged", [
    (_answer(0.9, cl.NO_SKILL_KEY, 0.95), "none", []),
    (b"not json", "fallback-bad response: not json", ["compuse-git"]),
])
def test_decide_row_names_the_path_that_produced_the_nudge(env, monkeypatch, capsys, body, path,
                                                           nudged):
    env["fake"].body = body
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-path")
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"], row["nudged"]) == ("decide", path, nudged)
