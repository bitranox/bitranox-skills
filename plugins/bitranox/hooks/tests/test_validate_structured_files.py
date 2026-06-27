"""Tests for validate-structured-files.py (the JSON/YAML/XML PostToolUse validator).

Two layers:
  - pure-function tests on the classifiers/validators (import the module directly);
  - end-to-end tests that drive main() with a stdin payload + a real temp file, and
    a subprocess smoke test through run-python.sh so the cross-platform shim wiring
    is exercised too.

All content is ASCII; any non-ASCII would be built via chr(), never pasted.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import validate_structured_files as V

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "validate-structured-files.py"
SHIM = HOOKS_DIR / "run-python.sh"

# Whether a JSON5 reader is installed decides whether JSONC validates or skips.
HAVE_JSON5 = any(__import__("importlib.util", fromlist=["util"]).find_spec(m) for m in ("pyjson5", "json5"))


# --------------------------------------------------------------------------
# classify: extension -> (kind, validator)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,kind",
    [
        ("a.json", "json"),
        ("a.JSON", "json"),
        ("a.yml", "yaml"),
        ("a.yaml", "yaml"),
        ("a.xml", "xml"),
        ("a.svg", "xml"),
        ("a.xsd", "xml"),
        ("a.txt", None),
        ("a.py", None),
        ("noext", None),
    ],
)
def test_classify(name, kind):
    got_kind, validator = V.classify(name)
    assert got_kind == kind
    assert (validator is None) == (kind is None)


# --------------------------------------------------------------------------
# looks_jsonc
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,text,expected",
    [
        ("tsconfig.json", "{}", True),
        ("tsconfig.build.json", "{}", True),
        ("/x/.vscode/settings.json", "{}", True),
        ("project.code-workspace", "{}", True),
        ("plain.json", "{\n  // c\n}", True),
        ("plain.json", "{ /* c */ }", True),
        ("plugin.json", '{"a": 1}', False),
    ],
)
def test_looks_jsonc(path, text, expected):
    assert V.looks_jsonc(path, text) is expected


# --------------------------------------------------------------------------
# validate_json
# --------------------------------------------------------------------------


def test_validate_json_good():
    assert V.validate_json("a.json", '{"a": 1}') == (True, None)


def test_validate_json_trailing_comma_blocks():
    ok, msg = V.validate_json("a.json", '{"a": 1,}')
    assert ok is False and msg


def test_validate_json_jsonc_never_blocks():
    # With a JSON5 reader -> (True, None); without -> (None, None). Never False.
    ok, _ = V.validate_json("tsconfig.json", "{\n  // comment\n  \"a\": 1,\n}")
    assert ok is not False
    assert ok is (True if HAVE_JSON5 else None)


# --------------------------------------------------------------------------
# validate_yaml
# --------------------------------------------------------------------------


def test_validate_yaml_good():
    assert V.validate_yaml("a.yml", "a: 1\nb: [1, 2]\n") == (True, None)


def test_validate_yaml_multi_document():
    assert V.validate_yaml("a.yml", "---\na: 1\n---\nb: 2\n") == (True, None)


def test_validate_yaml_bad_indent_blocks():
    ok, msg = V.validate_yaml("a.yml", "a: 1\n  b: 2\n")
    assert ok is False and msg


# --------------------------------------------------------------------------
# validate_xml
# --------------------------------------------------------------------------


def test_validate_xml_good():
    assert V.validate_xml("a.xml", "<r><a>1</a></r>") == (True, None)


def test_validate_xml_mismatched_tag_blocks():
    ok, msg = V.validate_xml("a.xml", "<r><a>1</r>")
    assert ok is False and msg


def test_validate_xml_entities_not_expanded():
    # A DOCTYPE with an internal entity must parse as well-formed WITHOUT the parser
    # expanding/resolving entities (the XXE / billion-laughs guard). It returns fast,
    # does not raise, and reports the document valid.
    doc = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE foo [ <!ENTITY a "expanded"> ]>\n'
        "<foo>&a;</foo>\n"
    )
    ok, _ = V.validate_xml("a.xml", doc)
    assert ok is True


# --------------------------------------------------------------------------
# main(): stdin payload -> exit code (+ stderr on block)
# --------------------------------------------------------------------------


def run_main(monkeypatch, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return V.main()


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_main_valid_passes(tmp_path, monkeypatch):
    fp = write(tmp_path, "good.json", '{"a": 1}')
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 0


def test_main_invalid_blocks_with_feedback(tmp_path, monkeypatch, capsys):
    fp = write(tmp_path, "bad.json", '{"a": 1,}')
    rc = run_main(monkeypatch, {"tool_input": {"file_path": fp}})
    assert rc == 2
    err = capsys.readouterr().err
    assert "BLOCKED" in err
    assert "bitranox:files-edit-json" in err


def test_main_invalid_yaml_blocks(tmp_path, monkeypatch):
    fp = write(tmp_path, "bad.yml", "a: 1\n  b: 2\n")
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 2


def test_main_invalid_xml_blocks(tmp_path, monkeypatch):
    fp = write(tmp_path, "bad.xml", "<r><a>1</r>")
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 2


def test_main_template_skips(tmp_path, monkeypatch):
    fp = write(tmp_path, "helm.yaml", "replicas: {{ .Values.x }}\n")
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 0


def test_main_empty_skips(tmp_path, monkeypatch):
    fp = write(tmp_path, "empty.json", "   \n")
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 0


def test_main_non_matching_extension_skips(tmp_path, monkeypatch):
    fp = write(tmp_path, "notes.txt", "{ not json but who cares")
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 0


def test_main_missing_file_path_skips(monkeypatch):
    assert run_main(monkeypatch, {"tool_input": {}}) == 0


def test_main_nonexistent_file_skips(monkeypatch):
    assert run_main(monkeypatch, {"tool_input": {"file_path": "/no/such/file.json"}}) == 0


def test_main_malformed_stdin_skips(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert V.main() == 0


# --------------------------------------------------------------------------
# Subprocess smoke test: exercises the real run-python.sh shim end to end.
# --------------------------------------------------------------------------


def _run_via_shim(payload):
    return subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def test_subprocess_valid_exit_0(tmp_path):
    fp = write(tmp_path, "good.json", '{"a": 1}')
    assert _run_via_shim({"tool_input": {"file_path": fp}}).returncode == 0


def test_subprocess_invalid_exit_2(tmp_path):
    fp = write(tmp_path, "bad.json", '{"a": 1,}')
    res = _run_via_shim({"tool_input": {"file_path": fp}})
    assert res.returncode == 2
    assert "BLOCKED" in res.stderr
