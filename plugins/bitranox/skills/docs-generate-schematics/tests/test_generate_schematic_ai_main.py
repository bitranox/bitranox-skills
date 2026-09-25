"""main()-level tests for generate_schematic_ai.py: the whole generate/review loop.

The network is the one edge replaced: ``httpx.post`` answers from a script of
canned OpenRouter responses, one per request, so each test states exactly which
calls happen. Everything between main() and that edge is the real code. The API
key is a fake from the environment; no test prints or uses a real one.
"""

import base64
import io
import json
import sys

import pytest

FAKE_KEY = "FAKE-KEY-NOT-REAL"


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def image(tag):
    url = "data:image/png;base64," + base64.b64encode(tag.encode()).decode()
    return _Resp(200, {"choices": [{"message": {"images": [{"type": "image_url", "image_url": {"url": url}}]}}]})


def review(text):
    return _Resp(200, {"choices": [{"message": {"content": text}}]})


def failure(status):
    return _Resp(status, {"error": {"message": "fake HTTP " + str(status)}})


@pytest.fixture
def scripted(gen_ai, monkeypatch, tmp_path):
    """Install a response script; returns the list of models each request named."""
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    monkeypatch.chdir(tmp_path)
    calls = []

    def install(*responses):
        queue = list(responses)

        def fake_post(url, headers=None, json=None, timeout=None):
            calls.append(json["model"])
            assert queue, "more requests than the test scripted"
            return queue.pop(0)

        monkeypatch.setattr(gen_ai.httpx, "post", fake_post)
        return calls

    return install


def run_main(gen_ai, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["generate_schematic_ai.py", *argv])
    try:
        return gen_ai.main()
    except SystemExit as exc:
        return exc.code


def _out(tmp_path):
    return tmp_path / "out.png"


def test_failed_review_never_claims_the_threshold_was_met(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    scripted(image("V1"), failure(500))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 1
    assert "meets" not in stdout
    assert "NOT verified" in stdout
    assert _out(tmp_path).read_bytes() == b"V1"  # the image is still delivered


def test_review_without_choices_does_not_crash(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    scripted(image("V1"), _Resp(200, {"choices": []}))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)))

    stdout = capsys.readouterr().out
    assert rc == 1
    assert "unpack" not in stdout
    assert _out(tmp_path).read_bytes() == b"V1"
    assert (tmp_path / "out_review_log.json").is_file()


def test_unparseable_review_is_not_scored(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    scripted(image("V1"), review("Looks nice overall, clear labels."))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "presentation")

    stdout = capsys.readouterr().out
    assert rc == 1
    assert "7.5" not in stdout
    assert "NOT verified" in stdout


@pytest.mark.parametrize("text", ["**SCORE:** 9.5/10", "SCORE: **9.5**", "Score - 9.5 / 10"])
def test_marked_up_score_is_parsed_and_stops_early(gen_ai, scripted, monkeypatch, tmp_path, text):
    calls = scripted(image("V1"), review(text + "\nVERDICT: ACCEPTABLE"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    assert rc == 0
    assert len(calls) == 2  # one image, one review: no paid regeneration
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["final_score"] == 9.5


def test_below_threshold_twice_keeps_the_last_image(gen_ai, scripted, monkeypatch, tmp_path):
    calls = scripted(image("V1"), review("SCORE: 6.0"), image("V2"), review("SCORE: 7.0"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    assert rc == 0
    assert len(calls) == 4
    assert _out(tmp_path).read_bytes() == b"V2"


def test_failed_retry_falls_back_to_the_reviewed_first_image(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    scripted(image("V1"), review("SCORE: 6.0"), failure(429))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 0
    assert _out(tmp_path).read_bytes() == b"V1"
    assert "[WARN]" in stdout and "v1" in stdout
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["success"] is True
    assert log["final_score"] == 6.0


def test_every_generation_failing_exits_1_without_output(gen_ai, scripted, monkeypatch, tmp_path):
    scripted(failure(429), failure(429))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)))

    assert rc == 1
    assert not _out(tmp_path).exists()


def test_cp1252_console_with_greek_prompt_runs(gen_ai, scripted, monkeypatch, tmp_path):
    calls = scripted(image("V1"), review("SCORE: 9.0"))
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", console)

    rc = run_main(gen_ai, monkeypatch, "Wnt/" + chr(0x03B2) + "-catenin pathway", "-o", str(_out(tmp_path)))

    assert rc == 0
    assert len(calls) == 2


def test_api_key_flag_is_refused_without_echoing_it(gen_ai, monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", "o.png", "--api-key", FAKE_KEY)

    err = capsys.readouterr().err
    assert rc == 2
    assert "OPENROUTER_API_KEY" in err
    assert FAKE_KEY not in err


def test_help_and_missing_key_message_do_not_offer_a_key_flag(gen_ai, monkeypatch, capsys, tmp_path):
    assert "--api-key" not in gen_ai.build_parser().format_help()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", "o.png")

    captured = capsys.readouterr()
    assert rc == 1
    assert "--api-key" not in captured.out + captured.err
