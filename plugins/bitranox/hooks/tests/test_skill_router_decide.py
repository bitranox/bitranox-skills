"""End-to-end tests for the skill router in DECIDE mode (`classifier_skill_router = decide`).

The hook runs in-process exactly as Claude Code drives it (event JSON on stdin, the nudge on
stdout), with a real config file, a real API key env var and the loopback base-URL override
pointing at a local fake TypeSafe server whose answer each test scripts. Nothing inside the hook
is patched; the one substitution is `subprocess.Popen`, recorded (and still run) at the process
edge, to see whether a detached shadow child was started.

What decide mode promises:

* Jev answers and the production rule `classifier.choice_pick` picks a live skill: that ONE
  skill is nudged, and the keyword hits are not;
* Jev answers and picks nothing: nothing is nudged - "no skill" is an answer, not a failure;
* Jev does not answer (deadline, HTTP error, no key, malformed answer), or picks a skill the
  session may no longer have: the keyword nudge, byte for byte;
* a task notification is not a prompt: it is nudged as with the classifier off, and still handed
  to the shadow child, so Jev's answers on notifications keep being logged;
* one skill is nudged at most once per session whichever path nudged it;
* one comparison row per prompt lands in the shadow log, saying which path decided.
"""

import io
import json
import subprocess
import sys
import time

import pytest

import classifier as cl
import skill_router as SR

# Keyword-matches `compuse-git` (5 hits), so a keyword nudge exists to be suppressed or kept.
PROMPT = "git commit fails with a CRLF line ending and the hook is not executable"
# The router's output for PROMPT with the classifier off, as the hook printed it before decide
# mode existed. A literal, so a regression in the shared nudge code cannot move both sides.
KEYWORD_OUTPUT = (
    '{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": '
    '"<BITRANOX-SKILL-ROUTER>\\nThis prompt matches the skill `bitranox:compuse-git` - if it '
    'applies (even a 1% chance), invoke it via the Skill tool BEFORE responding.\\n'
    '</BITRANOX-SKILL-ROUTER>"}, "suppressOutput": true}')
# A shipped skill the keywords do NOT match for PROMPT, so a Jev pick is distinguishable.
JEV_PICK = "process-debug-systematic"
NOTIFICATION = ("<task-notification>\n<task-id>b6bgpwg53</task-id>\n"
                "<status>failed</status>\n<summary>Background command \"Run the repo CI-parity "
                "gate\" failed with exit code 1</summary>\n</task-notification>")


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


@pytest.fixture
def spawned(monkeypatch):
    """The argv of every process started, recorded at the process edge and still started."""
    calls, real = [], subprocess.Popen

    def recording(args, *a, **kw):
        calls.append([str(x) for x in args])
        return real(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", recording)
    return calls


def _shadow_children(calls):
    return [c for c in calls if "--shadow" in c]


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


def _listing(tmp, names_descs, name="transcript.jsonl"):
    """A transcript holding one full skill listing; returns its path."""
    att = {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": True, "skillCount": len(names_descs),
        "names": [n for n, _d in names_descs],
        "content": "\n".join("- %s: %s" % nd for nd in names_descs)}}
    t = tmp / name
    t.write_text(json.dumps(att) + "\n", encoding="utf-8")
    return str(t)


def test_the_literal_is_what_the_router_prints_with_the_classifier_off(env, monkeypatch, capsys):
    _config(env["home"])
    assert _run(monkeypatch, capsys, "s-literal") == KEYWORD_OUTPUT


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
    t = _listing(env["tmp"], [("bitranox:files-edit-xml", "Use when editing XML."),
                              ("typesafe:typesafe-ai", "Build AI-powered software.")])
    env["fake"].body = _answer(0.9, "typesafe:typesafe-ai", 0.9)
    _decide(env["home"])
    out = _run(monkeypatch, capsys, "s-other", prompt="add a TypeSafe classifier to this app",
               transcript_path=t)
    assert _nudged(out) == ["typesafe:typesafe-ai"]


def test_decide_injects_nothing_when_the_gate_fails_and_the_winner_is_unsure(env, monkeypatch,
                                                                              capsys):
    env["fake"].body = _answer(0.2, JEV_PICK, 0.6)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, "s-unsure") == ""
    [row] = _rows(env["home"])
    assert (row["decide_path"], row["nudged"]) == ("none", [])


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
    assert out == KEYWORD_OUTPUT
    assert time.monotonic() - t0 < cl.DEFAULT_DEADLINE + 1.0, "the deadline must bound the hook"


def test_decide_treats_a_cached_pick_the_session_may_not_have_as_no_answer(env, monkeypatch,
                                                                           capsys):
    # Session A's listing is cached for the project; it names a user skill since removed.
    t = _listing(env["tmp"], [("bitranox:compuse-git", "Use when running git."),
                              ("gone-skill", "A user skill that no longer exists.")])
    env["fake"].body = _answer(0.9, cl.NO_SKILL_KEY, 0.9)
    _decide(env["home"])
    assert _run(monkeypatch, capsys, "s-a", prompt="hello", transcript_path=t) == ""
    # Session B's first prompt has no listing on disk yet, so the roster is that cache.
    env["fake"].body = _answer(0.9, "gone-skill", 0.95)
    out = _run(monkeypatch, capsys, "s-b")
    assert out == KEYWORD_OUTPUT
    row = _rows(env["home"])[-1]
    assert row["regex"]["roster"] == "cache"
    assert (row["decide_path"], row["nudged"]) == ("fallback-stale pick", ["bitranox:compuse-git"])


def test_control_a_cached_pick_of_this_plugins_shipped_skill_is_still_nudged(env, monkeypatch,
                                                                             capsys):
    t = _listing(env["tmp"], [("bitranox:" + JEV_PICK, "Use when debugging."),
                              ("gone-skill", "A user skill that no longer exists.")])
    env["fake"].body = _answer(0.9, cl.NO_SKILL_KEY, 0.9)
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-a", prompt="hello", transcript_path=t)
    env["fake"].body = _answer(0.9, JEV_PICK, 0.95)
    assert _nudged(_run(monkeypatch, capsys, "s-b")) == ["bitranox:" + JEV_PICK]
    assert _rows(env["home"])[-1]["regex"]["roster"] == "cache"


# ---- a task notification is not a prompt ------------------------------------------------------

def test_decide_nudges_a_task_notification_exactly_as_off_does(env, monkeypatch, capsys,
                                                                spawned):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.95)
    _config(env["home"])
    off = _run(monkeypatch, capsys, "s-note-off", prompt=NOTIFICATION)
    assert env["fake"].requests == [] and _shadow_children(spawned) == []
    _decide(env["home"])
    # A confident Jev pick, and still nothing: decide acts on typed prompts only.
    assert _run(monkeypatch, capsys, "s-note", prompt=NOTIFICATION) == off == ""


def test_decide_still_shadows_a_task_notification_so_its_evidence_keeps_accruing(
        env, monkeypatch, capsys, spawned):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.95)
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-note-shadow", prompt=NOTIFICATION)
    assert len(_shadow_children(spawned)) == 1
    end = time.monotonic() + 20  # the detached child writes the row
    while not _rows(env["home"]) and time.monotonic() < end:
        time.sleep(0.1)
    [row] = _rows(env["home"])
    assert row.get("mode") is None and "decide_path" not in row  # a comparison, not a decision
    assert row["regex"]["notify_view"] == cl.NOTIFY_VIEW
    assert row["states"][0]["task_status"] == "failed"
    assert row["results"][0] is not None


# ---- one identity per skill, whichever path nudged it ------------------------------------------

# A user skill that shares this plugin's skill's bare name: the listing keeps ours prefixed.
COLLIDING = [("bitranox:compuse-git", "Use when running git."),
             ("compuse-git", "A user skill of the same name.")]


def test_a_jev_nudge_of_our_skill_spends_it_for_the_keyword_path_too(env, monkeypatch, capsys):
    t = _listing(env["tmp"], COLLIDING)
    env["fake"].body = _answer(0.9, "bitranox:compuse-git", 0.95)
    _decide(env["home"])
    assert _nudged(_run(monkeypatch, capsys, "s-id", transcript_path=t)) == ["bitranox:compuse-git"]
    env["fake"].status = 500  # Jev silent: the keyword path would nudge the same skill again
    assert _run(monkeypatch, capsys, "s-id", transcript_path=t) == ""


def test_a_jev_nudge_of_the_same_named_user_skill_does_not_spend_ours(env, monkeypatch, capsys):
    t = _listing(env["tmp"], COLLIDING)
    env["fake"].body = _answer(0.9, "compuse-git", 0.95)
    _decide(env["home"])
    assert _nudged(_run(monkeypatch, capsys, "s-id2", transcript_path=t)) == ["compuse-git"]
    env["fake"].status = 500
    assert _run(monkeypatch, capsys, "s-id2", transcript_path=t) == KEYWORD_OUTPUT


# ---- off and shadow are unchanged -------------------------------------------------------------

@pytest.mark.parametrize("mode", ["off", "shadow"])
def test_off_and_shadow_keep_the_keyword_nudge_even_beside_a_confident_jev(env, monkeypatch,
                                                                           capsys, spawned, mode):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.9)
    _config(env["home"], classifier_backend="jev", classifier_skill_router=mode)
    assert _run(monkeypatch, capsys, "s-" + mode) == KEYWORD_OUTPUT
    # The control for the decide row test: the recorder does see a shadow child when one starts.
    assert len(_shadow_children(spawned)) == (1 if mode == "shadow" else 0)
    if mode == "shadow":  # let the detached child finish before the fixture tears down
        end = time.monotonic() + 20
        while not _rows(env["home"]) and time.monotonic() < end:
            time.sleep(0.1)
        assert [r.get("mode") for r in _rows(env["home"])] == [None]


# ---- the comparison row -----------------------------------------------------------------------

def test_decide_logs_one_row_saying_jev_decided_and_spawns_no_shadow_child(env, monkeypatch,
                                                                           capsys, spawned):
    env["fake"].body = _answer(0.9, JEV_PICK, 0.8)
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-row")
    assert _shadow_children(spawned) == [] and len(env["fake"].requests) == 1
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"], row["nudged"]) == \
        ("decide", "jev", ["bitranox:" + JEV_PICK])
    assert row["site"] == "skill_router" and row["session_id"] == "s-row"
    assert set(row["results"][0]["answers"]) == {cl.NEW_TASK_ID, cl.PICK_ID}
    assert row["regex"]["selected"] == ["compuse-git"]
    assert row["regex"]["question_view"] == SR.QUESTION_VIEW
    assert row["states"][0]["user_prompt"] == PROMPT
    assert row["reason"] is None and row["input_tokens"] == 321


@pytest.mark.parametrize("body,path,nudged", [
    (_answer(0.9, cl.NO_SKILL_KEY, 0.95), "none", []),
    (b"not json", "fallback-bad response: not json", ["bitranox:compuse-git"]),
])
def test_decide_row_names_the_path_that_produced_the_nudge(env, monkeypatch, capsys, body, path,
                                                           nudged):
    env["fake"].body = body
    _decide(env["home"])
    _run(monkeypatch, capsys, "s-path")
    [row] = _rows(env["home"])
    assert (row["mode"], row["decide_path"], row["nudged"]) == ("decide", path, nudged)
