"""Tests for classifier: the opt-in Jev (TypeSafe System One) port the hooks use in shadow mode.

The HTTP side is exercised against a REAL local server (http.server on a thread) reached through
the injectable base URL, never a patched urllib: the request bytes, the status handling and the
deadline are what production runs.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import classifier as cl

HOOKS_DIR = Path(__file__).resolve().parent.parent
GHP = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


@pytest.fixture
def fake(fake_jev):
    return fake_jev()


def _jev(url, deadline=2.0):
    return cl.JevClassifier(key="k" * 20, model="jev-latest", base_url=url, deadline=deadline)


NOUL = cl.Question(id="correction", type="noul",
                   instructions="Does `user_message` correct the assistant?")
CHOICE = cl.Question(id="lang", type="choice", instructions="Which language is `user_message`?",
                     criteria={"en": "English", "de": "German"})


def test_request_carries_model_bearer_state_and_questions(fake):
    result = _jev(fake.url).ask({"user_message": "no, wrong"}, [NOUL])
    assert result is not None
    req = fake.requests[0]
    assert req["path"] == "/v1/systemone"
    assert req["headers"]["Authorization"] == "Bearer " + "k" * 20
    assert req["json"]["model"] == "jev-latest"
    assert req["json"]["state"] == {"user_message": "no, wrong"}
    assert req["json"]["questions"] == {
        "correction": {"type": "noul", "instructions": "Does `user_message` correct the assistant?"}}


def test_noul_and_choice_answers_are_typed(fake):
    result = _jev(fake.url).ask({"user_message": "x"}, [NOUL, CHOICE])
    assert result.answers["correction"].value == 0.9
    assert result.answers["lang"].value == "en"
    assert result.answers["lang"].confidence == 0.7
    assert result.input_tokens == 123 and result.model == "jev-1.13.0"


@pytest.mark.parametrize("status", [401, 422, 429, 529, 500])
def test_an_http_error_returns_none_and_names_the_status(fake_jev, status):
    c = _jev(fake_jev(status=status, body={"error": "x"}).url)
    assert c.ask({"user_message": "x"}, [NOUL]) is None
    assert c.last_reason == "http %d" % status


def test_a_malformed_body_returns_none(fake_jev):
    c = _jev(fake_jev(body=b"not json").url)
    assert c.ask({"user_message": "x"}, [NOUL]) is None
    assert c.last_reason.startswith("bad response")


def test_a_missing_answer_returns_none(fake_jev):
    c = _jev(fake_jev(body={"model": "m", "answers": {}, "usage": {}}).url)
    assert c.ask({"user_message": "x"}, [NOUL]) is None
    assert c.last_reason.startswith("bad response")


def test_the_overall_deadline_holds_against_a_trickling_server(fake_jev):
    # Every byte lands inside a per-socket timeout, so only an OVERALL deadline stops this.
    c = _jev(fake_jev(trickle=True).url, deadline=0.5)
    t = time.monotonic()
    assert c.ask({"user_message": "x"}, [NOUL]) is None
    assert time.monotonic() - t < 1.5
    assert c.last_reason == "deadline"


def test_ask_many_runs_requests_concurrently_and_keeps_order(fake_jev):
    # Asserted from the SERVER's overlap, not from the clock. A wall-time bound is a race with
    # whatever else the machine is doing: the old "< 1.6 s" (against 2.4 s serial) went red on a
    # windows-latest runner at 1.666 s, which says nothing about concurrency. Overlap is the
    # property itself - a serial client can never put two requests in flight at once - and the
    # echoed state proves the ORDER this test is named for, which nothing here checked before.
    fake = fake_jev(delay=0.4, echo_state=True)
    c = _jev(fake.url, deadline=5.0)
    out = c.ask_many([({"n": str(i)}, [NOUL]) for i in range(6)], workers=6)
    assert len(out) == 6 and all(r is not None for r in out)
    assert fake.max_in_flight > 1
    assert [r.model for r in out] == [str(i) for i in range(6)]


def test_null_classifier_answers_nothing():
    n = cl.NullClassifier("classifier_backend is off")
    assert n.ask({"a": "b"}, [NOUL]) is None
    assert n.ask_many([({"a": "b"}, [NOUL])]) == [None]
    assert n.last_reason == "classifier_backend is off"


# ---- key lookup ----------------------------------------------------------------------------

def _keyfile(home, text, mode=0o600):
    p = home / ".credentials" / "typesafe.key"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")
    os.chmod(p, mode)
    return p


def test_the_env_var_wins_over_the_keyfile(tmp_path):
    _keyfile(tmp_path, "fromfile")
    assert cl.load_key({"TYPESAFE_API_KEY": "fromenv"}, tmp_path) == ("fromenv", None)


def test_the_keyfile_is_read_and_stripped(tmp_path):
    _keyfile(tmp_path, "fromfile")
    assert cl.load_key({}, tmp_path) == ("fromfile", None)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits do not exist on Windows")
def test_a_keyfile_readable_by_others_is_refused(tmp_path):
    _keyfile(tmp_path, "fromfile", mode=0o644)
    assert cl.load_key({}, tmp_path) == (None, "keyfile permissions")


def test_no_key_anywhere_is_reported(tmp_path):
    assert cl.load_key({}, tmp_path) == (None, "no api key")


# ---- config -> adapter ---------------------------------------------------------------------

def test_get_classifier_is_null_unless_backend_and_site_are_on(tmp_path):
    cfg = {"classifier_backend": "off", "classifier_stop_signal": "shadow"}
    assert isinstance(cl.get_classifier(cfg, "stop_signal", env={}, home=tmp_path), cl.NullClassifier)
    cfg = {"classifier_backend": "jev", "classifier_stop_signal": "off"}
    assert isinstance(cl.get_classifier(cfg, "stop_signal", env={}, home=tmp_path), cl.NullClassifier)


def test_get_classifier_is_null_without_a_key(tmp_path):
    cfg = {"classifier_backend": "jev", "classifier_stop_signal": "shadow"}
    c = cl.get_classifier(cfg, "stop_signal", env={}, home=tmp_path)
    assert isinstance(c, cl.NullClassifier) and c.last_reason == "no api key"


def test_get_classifier_builds_jev_with_the_configured_model(tmp_path):
    cfg = {"classifier_backend": "jev", "classifier_stop_signal": "shadow",
           "classifier_model": "jev-9"}
    c = cl.get_classifier(cfg, "stop_signal", env={"TYPESAFE_API_KEY": "abc"}, home=tmp_path)
    assert isinstance(c, cl.JevClassifier) and c.model == "jev-9"


def test_a_non_loopback_base_url_override_is_ignored(tmp_path):
    # The override exists for tests; honouring any host would let an env var send the key away.
    cfg = {"classifier_backend": "jev", "classifier_stop_signal": "shadow"}
    env = {"TYPESAFE_API_KEY": "abc", "BITRANOX_CLASSIFIER_BASE_URL": "https://evil.example"}
    c = cl.get_classifier(cfg, "stop_signal", env=env, home=tmp_path)
    assert c.base_url == cl.DEFAULT_BASE_URL
    env["BITRANOX_CLASSIFIER_BASE_URL"] = "http://127.0.0.1:9"
    assert cl.get_classifier(cfg, "stop_signal", env=env, home=tmp_path).base_url == "http://127.0.0.1:9"


def test_shadow_enabled_needs_backend_and_site():
    assert cl.shadow_enabled({"classifier_backend": "jev", "classifier_skill_router": "shadow"},
                             "skill_router")
    assert not cl.shadow_enabled({"classifier_backend": "off", "classifier_skill_router": "shadow"},
                                 "skill_router")
    assert not cl.shadow_enabled({"classifier_backend": "jev"}, "skill_router")


# ---- egress preparation ------------------------------------------------------------------

def test_prepare_state_redacts_every_field_and_the_key_itself():
    key = "Z" * 40
    state, n = cl.prepare_state({"user_message": "token %s and %s" % (GHP, key),
                                 "tool_output": "DB_PASSWORD=hunter2"}, key=key)
    assert GHP not in state["user_message"] and key not in state["user_message"]
    assert "hunter2" not in state["tool_output"]
    assert n == 3


def test_prepare_state_caps_each_field_keeping_the_tail():
    state, _ = cl.prepare_state({"out": "a" * 100 + "END"}, cap=10)
    assert state["out"].endswith("END") and len(state["out"]) <= 10 + len(cl.CAP_MARK)


def test_detect_language():
    assert cl.detect_language("Nein, das ist falsch, bitte nimm immer uv und nicht pip") == "de"
    assert cl.detect_language("No, that is wrong, always use uv and not pip") == "en"
    assert cl.detect_language("") == "unknown"


# ---- stdlib only -----------------------------------------------------------------------------

def test_classifier_imports_on_a_bare_interpreter():
    # -I isolates from env and user site, -S drops site-packages: only the stdlib remains.
    code = "import sys; sys.path.insert(0, %r); import classifier, secret_patterns" % str(HOOKS_DIR)
    r = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr


# ---- the detached shadow child ---------------------------------------------------------------

def _run_child(tmp_path, fake_url, payload, config):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(config), encoding="utf-8")
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), TYPESAFE_API_KEY="k" * 20,
               BITRANOX_CLASSIFIER_BASE_URL=fake_url)
    r = subprocess.run([sys.executable, str(HOOKS_DIR / "classifier.py"), "--shadow"],
                       input=json.dumps(payload), capture_output=True, text=True, env=env,
                       encoding="utf-8", errors="replace", timeout=30)
    log = home / ".claude" / "self-improve-audit" / cl.SHADOW_LOG
    return r, log


def test_the_shadow_child_logs_both_verdicts_and_only_redacted_state(tmp_path, fake):
    payload = {"site": "stop_signal", "session_id": "s1", "regex": {"fires": True},
               "requests": [{"fields": {"user_message": "no! use %s" % GHP},
                             "questions": [NOUL.to_json()]}]}
    config = {"classifier_backend": "jev", "classifier_stop_signal": "shadow"}
    r, log = _run_child(tmp_path, fake.url, payload, config)
    assert r.returncode == 0, r.stderr
    line = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert line["site"] == "stop_signal" and line["regex"] == {"fires": True}
    assert line["results"][0]["answers"]["correction"]["value"] == 0.9
    assert GHP not in log.read_text(encoding="utf-8")
    assert GHP not in json.dumps(fake.requests)  # never left the machine either
    assert line["redactions"] == 1


def test_the_shadow_child_logs_the_skip_reason_when_the_site_is_off(tmp_path, fake):
    payload = {"site": "stop_signal", "session_id": "s1", "regex": {"fires": False},
               "requests": [{"fields": {"user_message": "hi"}, "questions": [NOUL.to_json()]}]}
    r, log = _run_child(tmp_path, fake.url, payload, {"classifier_backend": "off"})
    assert r.returncode == 0
    line = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert line["results"] == [None] and "off" in line["reason"]
    assert fake.requests == []
