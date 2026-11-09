"""raisesmatch: flag exception/warning arms whose match pattern any unrelated refusal would satisfy."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

import raisesmatch

TOOL = Path(raisesmatch.__file__)


def _kinds(source: str, **kwargs: bool) -> list[tuple[int, str, str]]:
    report = raisesmatch.scan_source(source, "t.py", **kwargs)
    return [(f.line, f.kind, f.pattern) for f in report.findings]


@pytest.mark.parametrize(
    ("pattern", "kind"),
    [
        ('"10"', "number"),
        ('r"0\\.5"', "number"),
        ('"-1"', "number"),
        ('"^10$"', "number"),
        ('"offset_along"', "single-token"),
        ('"Invalid"', "single-token"),
        ('""', "empty"),
    ],
)
def test_a_pattern_an_echoed_input_satisfies_is_flagged(pattern: str, kind: str) -> None:
    source = f"import pytest\nwith pytest.raises(ValueError, match={pattern}):\n    pass\n"
    assert _kinds(source) == [(2, kind, ast.literal_eval(pattern))]


@pytest.mark.parametrize(
    "pattern",
    [
        '"less than or equal to 10"',
        'r"(less|greater) than or equal to -?10"',
        '"needs --bottom"',
        'r"unknown\\s+printer"',
        'r"unknown.*printer"',
    ],
)
def test_a_phrase_of_the_rule_passes(pattern: str) -> None:
    source = f"import pytest\nwith pytest.raises(ValueError, match={pattern}):\n    pass\n"
    report = raisesmatch.scan_source(source, "t.py")
    assert report.findings == []
    assert report.calls == 1
    assert report.judged == 1


def test_every_spelling_of_the_call_is_found() -> None:
    source = (
        "import pytest\n"
        "import pytest as pt\n"
        "from pytest import raises, warns\n"
        "import unittest\n"
        "def t():\n"
        "    pytest.raises(ValueError, match='10')\n"
        "    pt.raises(ValueError, match='10')\n"
        "    raises(ValueError, match='10')\n"
        "    pytest.warns(UserWarning, match='10')\n"
        "    warns(UserWarning, match='10')\n"
        "class T(unittest.TestCase):\n"
        "    def test(self):\n"
        "        self.assertRaisesRegex(ValueError, '10')\n"
        "        self.assertWarnsRegex(UserWarning, expected_regex='10')\n"
    )
    assert [line for line, _, _ in _kinds(source)] == [6, 7, 8, 9, 10, 13, 14]


def test_an_unrelated_call_named_raises_is_not_a_pytest_arm() -> None:
    source = "import other\nother.raises(ValueError, match='10')\nraises(ValueError, match='10')\n"
    report = raisesmatch.scan_source(source, "t.py")
    assert report.findings == []
    assert report.calls == 0


def test_a_pattern_it_cannot_read_is_counted_not_judged() -> None:
    source = (
        "import pytest\n"
        "P = '10'\n"
        "pytest.raises(ValueError, match=P)\n"
        "pytest.raises(ValueError, match=f'{P}')\n"
    )
    report = raisesmatch.scan_source(source, "t.py")
    assert report.findings == []
    assert (report.calls, report.judged, report.unjudged) == (2, 0, 2)


def test_no_match_is_flagged_only_when_asked() -> None:
    source = "import pytest\npytest.raises(ValueError)\n"
    assert _kinds(source) == []
    assert _kinds(source, require_match=True) == [(2, "no-match", "")]


def test_a_waiver_needs_a_reason_and_sits_on_the_call_or_the_pattern_line() -> None:
    source = (
        "import pytest\n"
        "pytest.raises(KeyError, match='offset_along')  # raisesmatch: ok - KeyError carries only the key\n"
        "pytest.raises(\n"
        "    KeyError,\n"
        "    match='lager',  # raisesmatch: ok - the missing printer name is the whole message\n"
        ")\n"
        "pytest.raises(KeyError, match='lager')  # raisesmatch: ok\n"
    )
    report = raisesmatch.scan_source(source, "t.py")
    assert [(f.line, f.kind) for f in report.findings] == [(7, "single-token")]
    assert report.waived == 2


def test_cli_exit_codes_and_json_envelope(tmp_path: Path) -> None:
    bad = tmp_path / "tests" / "test_bad.py"
    bad.parent.mkdir()
    bad.write_text("import pytest\npytest.raises(ValueError, match='10')\n", encoding="utf-8")
    (tmp_path / "tests" / "test_broken.py").write_text("def (:\n", encoding="utf-8")

    run = subprocess.run(
        [sys.executable, str(TOOL), "--json", str(tmp_path / "tests")],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    assert run.returncode == 1, run.stderr
    envelope = json.loads(run.stdout)
    assert envelope["ok"] is True
    assert envelope["command"] == "raisesmatch"
    assert envelope["data"]["files"] == 2
    assert envelope["data"]["calls"] == 1
    assert envelope["data"]["findings"][0]["path"].endswith("test_bad.py")
    assert envelope["data"]["findings"][0]["kind"] == "number"
    assert envelope["skipped"][0]["path"].endswith("test_broken.py")

    bad.write_text("import pytest\npytest.raises(ValueError, match='must be positive')\n", encoding="utf-8")
    clean = subprocess.run([sys.executable, str(TOOL), str(tmp_path / "tests")], capture_output=True, text=True, check=False)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "1 arm" in clean.stdout


def test_cli_refuses_a_run_that_examined_nothing(tmp_path: Path) -> None:
    run = subprocess.run([sys.executable, str(TOOL), str(tmp_path)], capture_output=True, text=True, check=False)
    assert run.returncode == 2
    assert "no .py file" in run.stderr
