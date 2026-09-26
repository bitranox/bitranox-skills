"""Tests for generate_schematic_ai.py pure / offline logic.

No network is performed: _make_request is monkeypatched where a response is
needed. The module imports cleanly because its only third-party dependency is httpx2.
"""

import ast
import base64
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _placeholderless_fstrings(source: str) -> list[int]:
    """Line numbers of f-strings with no placeholder (ruff F541), read with the stdlib only.

    A format spec (the `.2f` in `f"{x:.2f}"`) is itself a placeholder-less JoinedStr, so specs
    are excluded rather than reported.
    """
    tree = ast.parse(source)
    specs = {id(n.format_spec) for n in ast.walk(tree)
             if isinstance(n, ast.FormattedValue) and n.format_spec is not None}
    return [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.JoinedStr) and id(n) not in specs
            and not any(isinstance(v, ast.FormattedValue) for v in n.values)]


def test_the_fstring_detector_finds_a_bare_fstring_and_passes_a_format_spec():
    assert _placeholderless_fstrings('a = f"plain"\nb = f"{x:.2f}"\nc = "s"\n') == [1]


@pytest.mark.parametrize("script", ["generate_schematic_ai.py", "generate_schematic.py"])
def test_no_fstring_without_a_placeholder(script):
    """ruff F541: an `f` prefix with nothing to format is noise, and it hides the one f-string
    that was MEANT to carry a placeholder and lost it."""
    source = (SCRIPTS / script).read_text(encoding="utf-8")
    assert _placeholderless_fstrings(source) == []


def test_constructor_raises_without_key(gen_ai, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        gen_ai.ScientificSchematicGenerator()


def test_constructor_reads_no_dotenv_file(gen_ai, monkeypatch, tmp_path):
    # The key comes from the environment only: a .env beside the run is not read, and the
    # error does not send the reader to one.
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=from-dotenv-fake\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError) as err:
        gen_ai.ScientificSchematicGenerator()
    assert ".env" not in str(err.value)


def test_constructor_accepts_explicit_key(generator):
    assert generator.api_key == "test-key-not-real"
    assert generator.verbose is False


def test_quality_thresholds_values(generator):
    t = generator.QUALITY_THRESHOLDS
    assert t["journal"] == 8.5
    assert t["presentation"] == 6.5
    assert t["default"] == 7.5
    # journal is the strictest tier.
    assert t["journal"] == max(t.values())


@pytest.mark.parametrize(
    "suffix,expected_mime",
    [
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".gif", "image/gif"),
        (".webp", "image/webp"),
        (".PNG", "image/png"),  # case-insensitive via .lower()
        (".bin", "image/png"),  # unknown extension falls back to png
    ],
)
def test_image_to_base64_mime(generator, tmp_path, suffix, expected_mime):
    payload = b"binary-image-bytes"
    f = tmp_path / ("img" + suffix)
    f.write_bytes(payload)

    url = generator._image_to_base64(str(f))

    prefix = "data:" + expected_mime + ";base64,"
    assert url.startswith(prefix)
    decoded = base64.b64decode(url[len(prefix):])
    assert decoded == payload


def _review_response(text):
    """Build a minimal OpenRouter-shaped chat response carrying text."""
    return {"choices": [{"message": {"content": text}}]}


@pytest.mark.parametrize("text,expected", [
    # the requested format, and marked-up spellings of it (controls)
    ("SCORE: 9.0\nSTRENGTHS:\n- clear", 9.0),
    ("**SCORE:** 9.5/10", 9.5),
    ("SCORE: **9.5**", 9.5),
    ("Score - 9.5 / 10", 9.5),
    ("SCORE: [8]", 8.0),
    ("## SCORE: 7.5", 7.5),
    ("SCORE: 9.0\n\nScientific accuracy score: 2/2", 9.0),
    # a per-criterion score ahead of the total (the arms)
    ("Accuracy score (2/2) ... SCORE: 9.0", 9.0),
    ("Accuracy score: 2/2\nClarity score: 2/2\nSCORE: 8", 8.0),
    ("Scientific Accuracy\nScore: 2/2\n\nTotal Score: 8.5/10", 8.5),
    ("Overall score: 7/10", 7.0),
    # the older fallback wording, still read
    ("Overall quality: 6 / 10. Looks fine.", 6.0),
    ("Rating: 7", 7.0),
    # the fallback wording out of anything but 10 is a criterion, never the total
    ("quality: 2/2", None),
    ("Rating: 3/5", None),
    ("Label quality: 2/2\nOverall quality: 7/10", 7.0),
    ("Rating: 85", None),
    # only per-criterion scores, or none at all: no total was stated
    ("Accuracy score: 2/2\nClarity score: 1/2", None),
    ("Looks nice overall, clear labels.", None),
    ("SCORE: 85", None),  # off the 0-10 scale the prompt asks for
])
def test_parse_score_reads_the_total_not_a_criterion(gen_ai, text, expected):
    assert gen_ai._parse_score(text) == expected


def test_review_image_parses_score_and_accepts(generator, tmp_path, monkeypatch):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"x")
    monkeypatch.setattr(
        generator,
        "_make_request",
        lambda **kw: _review_response("SCORE: 9.0\nVERDICT: ACCEPTABLE"),
    )

    critique, score, needs = generator.review_image(
        str(img), "a flowchart", iteration=1, doc_type="journal", max_iterations=2
    )

    assert score == 9.0
    assert needs is False
    assert "SCORE" in critique


def test_review_image_below_threshold_needs_improvement(generator, tmp_path, monkeypatch):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"x")
    # 8.0 < journal threshold 8.5 -> needs improvement even without verdict word.
    monkeypatch.setattr(
        generator,
        "_make_request",
        lambda **kw: _review_response("SCORE: 8.0\nSTRENGTHS:\n- ok"),
    )

    _, score, needs = generator.review_image(
        str(img), "p", iteration=1, doc_type="journal", max_iterations=2
    )

    assert score == 8.0
    assert needs is True


def test_review_image_verdict_keyword_forces_improvement(generator, tmp_path, monkeypatch):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"x")
    # High score but explicit NEEDS_IMPROVEMENT verdict must win.
    monkeypatch.setattr(
        generator,
        "_make_request",
        lambda **kw: _review_response("SCORE: 9.5\nVERDICT: NEEDS_IMPROVEMENT"),
    )

    _, score, needs = generator.review_image(
        str(img), "p", iteration=1, doc_type="presentation", max_iterations=2
    )

    assert score == 9.5
    assert needs is True


def test_review_image_fallback_score_pattern(generator, tmp_path, monkeypatch):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"x")
    monkeypatch.setattr(
        generator,
        "_make_request",
        lambda **kw: _review_response("Overall quality: 6 / 10. Looks fine."),
    )

    _, score, _ = generator.review_image(
        str(img), "p", iteration=1, doc_type="presentation", max_iterations=2
    )

    assert score == 6.0


def test_review_image_request_error_is_swallowed(generator, tmp_path, monkeypatch):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"x")

    def boom(**kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(generator, "_make_request", boom)

    critique, score, needs = generator.review_image(
        str(img), "p", iteration=1, doc_type="journal", max_iterations=2
    )

    # A failed review does not stop the pipeline, but it yields no score: nothing may claim
    # the image met a threshold nobody checked.
    assert needs is False
    assert score is None
    assert "skipped" in critique.lower()


def test_extract_image_from_images_field(generator):
    raw = b"PNG-DATA-HERE"
    data_url = "data:image/png;base64," + base64.b64encode(raw).decode()
    response = {
        "choices": [
            {
                "message": {
                    "images": [
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            }
        ]
    }
    assert generator._extract_image_from_response(response) == raw


def test_extract_image_from_content_string(generator):
    raw = b"another-image"
    data_url = "data:image/png;base64," + base64.b64encode(raw).decode()
    response = {"choices": [{"message": {"content": "here it is " + data_url}}]}
    assert generator._extract_image_from_response(response) == raw


def test_extract_image_none_when_absent(generator):
    response = {"choices": [{"message": {"content": "no image here"}}]}
    assert generator._extract_image_from_response(response) is None


def test_extract_image_no_choices(generator):
    assert generator._extract_image_from_response({"choices": []}) is None


def test_improve_prompt_includes_critique_and_guidelines(generator):
    out = generator.improve_prompt("draw a cell", "labels too small", iteration=2)
    assert "draw a cell" in out
    assert "labels too small" in out
    assert "ITERATION 2" in out
    # Guidelines block is embedded.
    assert "NO FIGURE NUMBERS" in out


def test_make_request_timeout_maps_to_runtimeerror(generator, gen_ai, monkeypatch):
    # Migrated requests->httpx2: a transport timeout must surface as RuntimeError,
    # which also proves httpx.TimeoutException / RequestError resolve at runtime.
    def boom_timeout(*a, **k):
        raise gen_ai.httpx.TimeoutException("slow")

    monkeypatch.setattr(gen_ai.httpx, "post", boom_timeout)
    with pytest.raises(RuntimeError) as e:
        generator._make_request("some/model", [{"role": "user", "content": "hi"}])
    assert "timed out" in str(e.value).lower()


def test_make_request_transport_error_maps_to_runtimeerror(generator, gen_ai, monkeypatch):
    def boom_conn(*a, **k):
        raise gen_ai.httpx.RequestError("conn reset")

    monkeypatch.setattr(gen_ai.httpx, "post", boom_conn)
    with pytest.raises(RuntimeError) as e:
        generator._make_request("some/model", [{"role": "user", "content": "hi"}])
    assert "failed" in str(e.value).lower()
