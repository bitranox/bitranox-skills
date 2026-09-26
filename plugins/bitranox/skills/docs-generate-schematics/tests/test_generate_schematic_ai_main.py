"""main()-level tests for generate_schematic_ai.py: the whole generate/review loop.

The network is the one edge replaced: ``httpx.post`` answers from a script of
canned OpenRouter responses, one per request, so each test states exactly which
calls happen. Everything between main() and that edge is the real code. The API
key is a fake from the environment; no test prints or uses a real one.
"""

import base64
import io
import json
import subprocess
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


def test_below_threshold_twice_keeps_the_second_image_when_it_scores_higher(
    gen_ai, scripted, monkeypatch, tmp_path
):
    """The control for the arm below: the last image IS the best one here. It still misses the
    journal threshold, so the run exits 1 with the image written."""
    calls = scripted(image("V1"), review("SCORE: 6.0"), image("V2"), review("SCORE: 7.0"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    assert rc == 1
    assert len(calls) == 4
    assert _out(tmp_path).read_bytes() == b"V2"
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["final_score"] == 7.0


def test_below_threshold_twice_keeps_the_best_scoring_image_not_the_last(
    gen_ai, scripted, monkeypatch, capsys, tmp_path
):
    """A retry can come back WORSE. Both images are paid for and reviewed, so the output is the
    better one, and the log and report name which iteration was kept and its score."""
    scripted(image("V1"), review("SCORE: 7.0"), image("V2"), review("SCORE: 6.0"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 1  # the best image still missed the threshold
    assert _out(tmp_path).read_bytes() == b"V1"
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["final_score"] == 7.0
    assert log["final_image"].endswith("out_v1.png")
    assert "v1" in stdout
    assert "Final Score: 7.0/10" in stdout


def test_a_failed_first_generation_keeps_the_only_reviewed_image(
    gen_ai, scripted, monkeypatch, capsys, tmp_path
):
    scripted(failure(429), image("V2"), review("SCORE: 6.0"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 1  # 6.0 is below the journal threshold
    assert _out(tmp_path).read_bytes() == b"V2"
    assert "last generation failed" not in stdout
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["kept_iteration"] == 2
    assert "fallback_iteration" not in log


def test_failed_retry_falls_back_to_the_reviewed_first_image(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    scripted(image("V1"), review("SCORE: 6.0"), failure(429))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 1  # 6.0 is below the journal threshold
    assert _out(tmp_path).read_bytes() == b"V1"
    assert "[WARN]" in stdout and "v1" in stdout
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["success"] is True
    assert log["final_score"] == 6.0


# ---- a kept image below the threshold is delivered, but the run says no (exit 1) ---------------
@pytest.mark.parametrize("iterations,script", [
    ("1", ("V1", "SCORE: 7.0")),
    ("2", ("V1", "SCORE: 6.0", "V2", "SCORE: 7.0")),
], ids=["one-iteration", "two-iterations"])
def test_a_kept_image_below_the_threshold_exits_1_and_names_score_and_threshold(
    gen_ai, scripted, monkeypatch, capsys, tmp_path, iterations, script
):
    """User decision 2026-09-26: the best image is still written, but a run whose best score
    missed the threshold is a "no", not "[OK] Success!"."""
    responses = [image(s) if s.startswith("V") else review(s) for s in script]
    scripted(*responses)

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal",
                  "--iterations", iterations)

    stdout = capsys.readouterr().out
    assert rc == 1
    assert _out(tmp_path).read_bytes() == script[-2].encode()
    assert "[OK] Success" not in stdout
    verdict = stdout.strip().splitlines()[-1]
    assert "threshold" in verdict and "7.0/10" in verdict and "8.5/10" in verdict
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["threshold_met"] is False


@pytest.mark.parametrize("script", [
    ("V1", "SCORE: 8.5"),                          # exactly at the threshold
    ("V1", "SCORE: 6.0", "V2", "SCORE: 9.0"),      # the retry meets it
], ids=["at-threshold", "retry-meets-it"])
def test_a_kept_image_meeting_the_threshold_still_exits_0(
    gen_ai, scripted, monkeypatch, capsys, tmp_path, script
):
    """The control for the arm above."""
    scripted(*[image(s) if s.startswith("V") else review(s) for s in script])

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 0
    assert "[OK] Success!" in stdout
    assert _out(tmp_path).read_bytes() == script[-2].encode()
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["threshold_met"] is True


def test_a_verdict_forced_retry_above_the_threshold_is_not_called_below_it(
    gen_ai, scripted, monkeypatch, capsys, tmp_path
):
    """A NEEDS_IMPROVEMENT verdict forces a retry even at 9.5 >= 8.5. The kept image then met the
    numeric threshold, so the report must not say "below" and the exit stays 0."""
    scripted(image("V1"), review("SCORE: 9.5\nVERDICT: NEEDS_IMPROVEMENT"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal",
                  "--iterations", "1")

    stdout = capsys.readouterr().out
    assert rc == 0
    assert "below the 8.5/10" not in stdout
    assert "at or above the 8.5/10 threshold" in stdout


def test_a_failed_retry_review_keeps_the_reviewed_first_image(
    gen_ai, scripted, monkeypatch, capsys, tmp_path
):
    """Keep-best chooses among REVIEWED images only: a retry whose review failed has an unknown
    quality, so it cannot displace the reviewed v1, and the run is judged on v1's score."""
    scripted(image("V1"), review("SCORE: 6.0"), image("V2"), failure(500))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 1  # v1's 6.0 is below the journal threshold
    assert _out(tmp_path).read_bytes() == b"V1"
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["final_score"] == 6.0
    assert log["kept_iteration"] == 1
    assert log["threshold_met"] is False
    assert log["review_skipped"] is False  # the delivered image WAS reviewed
    assert "review of v2 failed" in stdout
    assert "NOT verified" not in stdout
    verdict = stdout.strip().splitlines()[-1]
    assert "6.0/10" in verdict and "8.5/10" in verdict


def test_a_failed_retry_review_after_a_verdict_forced_retry_keeps_v1_and_exits_0(
    gen_ai, scripted, monkeypatch, capsys, tmp_path
):
    """The control: v1 met the numeric threshold (the verdict alone forced the retry), so keeping
    it after v2's review failed is a met threshold, exit 0."""
    scripted(image("V1"), review("SCORE: 9.0\nVERDICT: NEEDS_IMPROVEMENT"), image("V2"), failure(500))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    stdout = capsys.readouterr().out
    assert rc == 0
    assert _out(tmp_path).read_bytes() == b"V1"
    assert "review of v2 failed" in stdout
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert (log["kept_iteration"], log["threshold_met"]) == (1, True)


def test_exit_status_docs_name_the_missed_threshold(gen_ai):
    assert "threshold" in gen_ai.__doc__.split("Exit status:", 1)[1].split("Usage:", 1)[0]
    assert "threshold" in gen_ai.build_parser().epilog.split("Exit status:", 1)[1]


# ---- the TOTAL score is parsed, never a per-criterion one ---------------------------------------
_BREAKDOWN_THEN_TOTAL = (
    "1. **Scientific Accuracy** score: 2/2\n"
    "2. **Clarity and Readability** score: 1.5/2\n"
    "3. **Label Quality** score: 2/2\n"
    "4. **Layout and Composition** score: 1.5/2\n"
    "5. **Professional Appearance** score: 2/2\n\n"
    "SCORE: 9.0\n\nVERDICT: ACCEPTABLE"
)
_SUBSCORE_LINES_THEN_TOTAL = (
    "### Scientific Accuracy\nScore: 2/2\n### Clarity and Readability\nScore: 1.5/2\n"
    "### Label Quality\nScore: 2/2\n### Layout and Composition\nScore: 1.5/2\n"
    "### Professional Appearance\nScore: 2/2\n\nTotal Score: 9.0/10\n\nVERDICT: ACCEPTABLE"
)
_BULLETED_THEN_BOLD_TOTAL = (
    "- Scientific Accuracy: Score 2/2\n- Clarity: Score 1.5/2\n- Labels: Score 2/2\n"
    "- Layout: Score 1.5/2\n- Appearance: Score 2/2\n\n**Score:** 9/10\n\nVERDICT: ACCEPTABLE"
)
_POINTS_THEN_TOTAL = (
    "Scientific Accuracy score: 2 points\nClarity score: 1.5 points\nLabel score: 2 points\n"
    "Layout score: 1.5 points\nAppearance score: 2 points\nSCORE: 9.0\nVERDICT: ACCEPTABLE"
)
_ONE_LINE = "Accuracy score (2/2) ... SCORE: 9.0\nVERDICT: ACCEPTABLE"


@pytest.mark.parametrize("text", [
    _BREAKDOWN_THEN_TOTAL, _SUBSCORE_LINES_THEN_TOTAL, _BULLETED_THEN_BOLD_TOTAL, _POINTS_THEN_TOTAL,
    _ONE_LINE,
], ids=["breakdown-then-total", "subscore-lines", "bulleted-bold-total", "points", "one-line"])
def test_a_multi_criterion_review_is_scored_by_its_total(gen_ai, scripted, monkeypatch, tmp_path, text):
    """The review prompt grades five criteria 0-2 each and asks for "SCORE: [total score 0-10]".
    A reviewer that lists the criteria first must not be read as scoring 2/10: that paid for a
    needless regeneration and fed keep-best a wrong number."""
    calls = scripted(image("V1"), review(text))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--doc-type", "journal")

    assert rc == 0
    assert len(calls) == 2  # one image, one review: no paid regeneration
    log = json.loads((tmp_path / "out_review_log.json").read_text(encoding="utf-8"))
    assert log["final_score"] == 9.0


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


# ---- refusals go to stderr, and a bad argument is a usage error (exit 2) ------------------------
def test_a_missing_key_is_reported_on_stderr(gen_ai, monkeypatch, capsys, tmp_path):
    """The error, and its remedy, went to STDOUT beside the run's progress lines."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", "o.png")

    captured = capsys.readouterr()
    assert rc == 1
    assert "OPENROUTER_API_KEY environment variable not set" in captured.err
    assert "export OPENROUTER_API_KEY" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("count", ["0", "3", "-1"])
def test_iterations_out_of_range_is_a_usage_error(gen_ai, scripted, monkeypatch, capsys, tmp_path,
                                                  count):
    """The contract says 2 for a usage error; an out-of-range --iterations exited 1, the code for
    a failed generation, and printed its reason to stdout."""
    calls = scripted()

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--iterations", count)

    captured = capsys.readouterr()
    assert rc == 2
    assert "between 1 and 2" in captured.err
    assert "between 1 and 2" not in captured.out
    assert calls == []


def test_iterations_in_range_still_runs(gen_ai, scripted, monkeypatch, tmp_path):
    """The control for the refusal: --iterations 1 is accepted and generates."""
    calls = scripted(image("V1"), review("SCORE: 9.0"))

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(_out(tmp_path)), "--iterations", "1")

    assert rc == 0
    assert len(calls) == 2


def test_an_unexpected_error_is_reported_on_stderr(gen_ai, scripted, monkeypatch, capsys, tmp_path):
    """An output path under a regular FILE cannot be created; the failure must reach stderr."""
    scripted(image("V1"), review("SCORE: 9.0"))
    (tmp_path / "a-file").write_text("x", encoding="utf-8")

    rc = run_main(gen_ai, monkeypatch, "diagram", "-o", str(tmp_path / "a-file" / "out.png"))

    captured = capsys.readouterr()
    assert rc == 1
    assert "[FAIL] Error:" in captured.err
    assert "[FAIL] Error:" not in captured.out


def test_a_missing_httpx2_is_reported_on_stderr(gen_ai, tmp_path):
    """-S drops site-packages, where httpx2 lives, so the import guard is the one that runs."""
    script = gen_ai.__file__
    probe = subprocess.run([sys.executable, "-S", "-c", "import httpx2"], capture_output=True,
                           check=False)
    if probe.returncode == 0:
        pytest.skip("httpx2 is importable without site-packages here, so the guard cannot fire")
    proc = subprocess.run([sys.executable, "-S", script, "--help"], capture_output=True,
                          cwd=str(tmp_path), timeout=60, check=False)
    assert proc.returncode == 1
    assert b"httpx2 library not found" in proc.stderr
    assert proc.stdout == b""
