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
import types
from pathlib import Path

import pytest

import validate_structured_files as V

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "validate-structured-files.py"
SHIM = HOOKS_DIR / "run-python.sh"


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


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_subprocess_valid_exit_0(tmp_path):
    fp = write(tmp_path, "good.json", '{"a": 1}')
    assert _run_via_shim({"tool_input": {"file_path": fp}}).returncode == 0


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_subprocess_invalid_exit_2(tmp_path):
    fp = write(tmp_path, "bad.json", '{"a": 1,}')
    res = _run_via_shim({"tool_input": {"file_path": fp}})
    assert res.returncode == 2
    assert "BLOCKED" in res.stderr



# --- finding 3 from the 2026-08-28 script-wave audit of this hook -------------------------------

def _write(tmp_path, name, text):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return str(f)


@pytest.mark.parametrize("text", [
    '{{"a": 1}}',
    '{{"name": "x", "version": "1.0"}}',
    '{{{"a": 1}}}',
])
def test_a_doubled_brace_corruption_is_not_a_template(tmp_path, monkeypatch, text):
    """`{{` opens a Jinja/Helm tag AND is the signature of the commonest way an Edit breaks a JSON
    file - doubling its opening brace. Treating the bare digraph as a template marker meant the
    corruption skipped validation entirely, which is the one file shape this hook exists to catch.
    """
    fp = _write(tmp_path, "plugin.json", text)
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 2


@pytest.mark.parametrize("name,text", [
    ("values.json", '{"image": {{ .Values.image }}}'),
    ("values.yaml", "image: {{ .Values.image }}\ntag: {{- .Values.tag }}\n"),
    ("t.json", '{"greeting": {{name}}}'),
    ("t.yaml", "a: {% if x %}1{% endif %}\n"),
    ("t.json", '{"a": <%= b %>}'),
])
def test_a_real_template_is_still_skipped(tmp_path, monkeypatch, name, text):
    """The direction the discrimination must NOT reach. A template is not strict data and this
    hook must stay out of its way; the marker still counts whenever the tag opens on anything a
    template expression can start with."""
    fp = _write(tmp_path, name, text)
    assert run_main(monkeypatch, {"tool_input": {"file_path": fp}}) == 0


def test_plain_valid_and_plain_broken_json_are_unaffected(tmp_path, monkeypatch):
    """Control on both sides, so the narrowing cannot be satisfied by breaking the ordinary path."""
    assert run_main(monkeypatch, {"tool_input": {
        "file_path": _write(tmp_path, "ok.json", '{"a": 1}')}}) == 0
    assert run_main(monkeypatch, {"tool_input": {
        "file_path": _write(tmp_path, "bad.json", '{"a": 1,,}')}}) == 2


# --- rank 10 re-adjudication: string-aware signals, BOM, notebooks, library fallbacks ------------
#
# Library absence is simulated at the import system, the one seam this hook has for its optional
# dependencies: a None entry in sys.modules makes the next `import` of that name raise ImportError,
# and a module object placed there is what `import` returns. Nothing inside the hook is patched.


def _block_imports(monkeypatch, *names):
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


def _json5_stub(monkeypatch, *, accept):
    """Install a fake pyjson5 whose loads() accepts or rejects everything, and hide json5."""
    stub = types.ModuleType("pyjson5")

    def loads(text):
        if not accept:
            raise ValueError("stub json5 rejects this document")
        return {}

    stub.loads = loads
    monkeypatch.setitem(sys.modules, "pyjson5", stub)
    _block_imports(monkeypatch, "json5")


def _event(tmp_path, name, content, *, key="file_path", tool="Write"):
    p = tmp_path / name
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")
    return {"tool_name": tool, "tool_input": {key: str(p)}}


# A9: a // or /* inside a JSON string is data, not a comment.

@pytest.mark.parametrize("text", [
    '{"homepage": "https://github.com/bitranox/bitranox-skills"}',
    '{"include": ["src/**/*.py"]}',
    '{"a": "x\\"// still inside the string"}',
])
def test_a_comment_digraph_inside_a_string_is_not_jsonc(text):
    assert V.looks_jsonc("plain.json", text) is False


@pytest.mark.parametrize("text", [
    '{\n  // c\n  "a": 1\n}',
    '{ /* c */ "a": 1 }',
    '{"url": "https://x"} // trailing comment',
    '{"a": "ends in a backslash\\\\"} // c',
])
def test_a_real_comment_outside_strings_is_still_jsonc(text):
    assert V.looks_jsonc("plain.json", text) is True


@pytest.mark.parametrize("name", ["tsconfig.json", "tsconfig.build.json", "jsconfig.json", "devcontainer.json"])
def test_the_filename_allowlist_is_unchanged(name):
    assert V.looks_jsonc(name, '{"a": 1}') is True


def test_a_url_no_longer_exempts_a_broken_json_without_a_json5_reader(tmp_path, monkeypatch):
    _block_imports(monkeypatch, "pyjson5", "json5")
    broken = '{\n  "homepage": "https://github.com/bitranox/bitranox-skills",\n  "name": "x"\n'
    glob = '{"include": ["src/**/*.py"], "name": "x"\n'
    assert run_main(monkeypatch, _event(tmp_path, "url_broken.json", broken)) == 2
    assert run_main(monkeypatch, _event(tmp_path, "glob_broken.json", glob)) == 2


def test_a_url_no_longer_routes_strict_json_to_a_lenient_reader(tmp_path, monkeypatch):
    # The stub accepts anything, so reaching it would approve the trailing comma.
    _json5_stub(monkeypatch, accept=True)
    text = '{"repository": "https://github.com/x/y", "name": "x",}'
    assert run_main(monkeypatch, _event(tmp_path, "url_trailing.json", text)) == 2


# A10: the {{ template marker.

@pytest.mark.parametrize("text", [
    '{{\n  "name": "x"\n}\n',
    '{{ "name": "x"}\n',
    '{\n  "a": "{{VALUE}}",\n  "b": 1,,\n}\n',
    '{\n  "a": "{{ VALUE }}",\n  "b": 1,,\n}\n',
    '{\n  "a": "{% raw %}",\n  "b": 1,,\n}\n',
])
def test_a_brace_digraph_that_is_not_a_template_tag_does_not_skip(tmp_path, monkeypatch, text):
    assert run_main(monkeypatch, _event(tmp_path, "plugin.json", text)) == 2


@pytest.mark.parametrize("name,text", [
    ("values.yaml", 'name: {{ "foo" | quote }}\nkey: [unclosed\n'),
    ("t.json", '{"a": {{ "literal" }}}'),
    ("t.json", '{"a": "{{ "nested" | upper }}", "b": 1}'),
    ("t.json", '{"a": "{{VALUE}}"}'),
])
def test_a_real_template_or_valid_placeholder_still_passes(tmp_path, monkeypatch, name, text):
    assert run_main(monkeypatch, _event(tmp_path, name, text)) == 0


# A12: NotebookEdit sends notebook_path, and a notebook is JSON.

def test_classify_ipynb_as_json():
    assert V.classify("a.ipynb")[0] == "json"


def test_a_notebook_edit_is_validated(tmp_path, monkeypatch):
    bad = _event(tmp_path, "broken.ipynb", '{"cells": [,}\n', key="notebook_path", tool="NotebookEdit")
    good = _event(tmp_path, "good.ipynb", '{"cells": [], "metadata": {}}\n', key="notebook_path", tool="NotebookEdit")
    assert run_main(monkeypatch, bad) == 2
    assert run_main(monkeypatch, good) == 0


# B7: a UTF-8 byte-order mark is not a syntax error.

@pytest.mark.parametrize("name,body", [
    ("bom.json", b'{"name": "x"}\n'),
    ("bom.yml", b"name: x\n"),
    ("bom.xml", b'<?xml version="1.0" encoding="utf-8"?>\n<foo/>\n'),
])
def test_a_bom_prefixed_valid_file_passes(tmp_path, monkeypatch, name, body):
    assert run_main(monkeypatch, _event(tmp_path, name, b"\xef\xbb\xbf" + body)) == 0


def test_a_bom_prefixed_broken_json_still_blocks(tmp_path, monkeypatch):
    assert run_main(monkeypatch, _event(tmp_path, "bom_bad.json", b'\xef\xbb\xbf{"name": "x",,}\n')) == 2


# B8 + D3: the defusedxml fallback (lxml absent).

ENTITY_DOC = '<?xml version="1.0"?>\n<!DOCTYPE foo [ <!ENTITY a "expanded"> ]>\n<foo>&a;</foo>\n'


def test_defusedxml_fallback_accepts_valid_and_blocks_broken(monkeypatch):
    _block_imports(monkeypatch, "lxml", "lxml.etree")
    assert V.validate_xml("a.xml", "<foo>plain</foo>") == (True, None)
    ok, msg = V.validate_xml("a.xml", "<foo>plain</fooo>")
    assert ok is False and "mismatched tag" in msg


def test_defusedxml_fallback_skips_an_entity_document_it_refuses_to_parse(tmp_path, monkeypatch):
    _block_imports(monkeypatch, "lxml", "lxml.etree")
    assert V.validate_xml("ent.xml", ENTITY_DOC) == (None, None)
    assert run_main(monkeypatch, _event(tmp_path, "ent.xml", ENTITY_DOC)) == 0


def test_no_safe_xml_parser_skips(monkeypatch):
    _block_imports(monkeypatch, "lxml", "lxml.etree", "defusedxml", "defusedxml.ElementTree")
    assert V.validate_xml("a.xml", "<foo>plain</fooo>") == (None, None)


# D3: the ruamel.yaml fallback (PyYAML absent).

def test_ruamel_fallback_accepts_valid_and_blocks_broken(monkeypatch):
    _block_imports(monkeypatch, "yaml")
    assert V.validate_yaml("a.yml", "---\na: 1\n---\nb: [1, 2]\n") == (True, None)
    ok, msg = V.validate_yaml("a.yml", "a: 1\n  b: 2\n")
    assert ok is False and msg


def test_no_yaml_library_skips(monkeypatch):
    _block_imports(monkeypatch, "yaml", "ruamel", "ruamel.yaml")
    assert V.validate_yaml("a.yml", "a: 1\n  b: 2\n") == (None, None)


# D3: the JSON5 reader's accept and reject branches.

JSONC_DOC = '{\n  // comment\n  "a": 1,\n}'


def test_jsonc_with_no_json5_reader_skips(monkeypatch):
    _block_imports(monkeypatch, "pyjson5", "json5")
    assert V.validate_json("tsconfig.json", JSONC_DOC) == (None, None)


def test_jsonc_accepted_by_the_json5_reader_passes(monkeypatch):
    _json5_stub(monkeypatch, accept=True)
    assert V.validate_json("tsconfig.json", JSONC_DOC) == (True, None)


def test_jsonc_rejected_by_the_json5_reader_blocks(tmp_path, monkeypatch, capsys):
    _json5_stub(monkeypatch, accept=False)
    assert V.validate_json("tsconfig.json", JSONC_DOC) == (False, "stub json5 rejects this document")
    assert run_main(monkeypatch, _event(tmp_path, "tsconfig.json", JSONC_DOC)) == 2
    assert "stub json5 rejects" in capsys.readouterr().err


def test_the_json5_decode_spelling_is_used_when_there_is_no_loads(monkeypatch):
    stub = types.ModuleType("pyjson5")
    stub.decode = lambda text: {}
    monkeypatch.setitem(sys.modules, "pyjson5", stub)
    _block_imports(monkeypatch, "json5")
    assert V.validate_json("tsconfig.json", JSONC_DOC) == (True, None)


@pytest.mark.parametrize("text,expected", [
    ('"a"', [(True, '"a"')]),
    ('{"a": 1}', [(False, "{"), (True, '"a"'), (False, ": 1}")]),
    ('"a\\"b" x', [(True, '"a\\"b"'), (False, " x")]),
    # An unterminated string ends at the line break, so the next line is scanned as data again.
    ('{"a": "x\n}', [(False, "{"), (True, '"a"'), (False, ": "), (True, '"x'), (False, "\n}")]),
])
def test_json_segments(text, expected):
    assert V.json_segments(text) == expected


@pytest.mark.parametrize("text,expected", [
    ('"{{VALUE}}"', False),  # a placeholder string that is the whole document
    ('{"a": "{{ ""}}", "b": 1,,}', True),  # a quote inside the tag leaves two adjacent strings
    ('{"a": {{ .x }}}', True),
    ('{"a": "{{VALUE}}"}', False),
])
def test_json_is_template(text, expected):
    assert V.json_is_template(text) is expected


# ---- a template marker inside a QUOTED YAML/XML value is data ------------------------------------
#
# A placeholder in a quoted YAML scalar or an XML attribute value is ordinary data (Ansible files
# are full of them, and must parse as YAML before Jinja ever runs), so it must not exempt the file
# around it from validation - the same distinction JSON already drew. A marker anywhere else, or a
# quoted value cut short by a quote INSIDE a template expression, still means "template".

@pytest.mark.parametrize("name,text", [
    ("a.yaml", 'greeting: "Hello {{name}}"\nitems: [a, b\n'),
    ("a.yaml", "greeting: 'Hi {{ name }}'\nitems: [a, b\n"),
    ("a.yml", 'when: "{% if x %}y{% endif %}"\nitems: [a, b\n'),
    ("a.yaml", "tpl: |\n  {{ name }} here\nitems: [a, b\n"),
    ("a.xml", '<root><a title="{{ title }}">x</a><b></root>'),
    ("a.xml", "<root><a title='{% x %}'/><b></root>"),
])
def test_a_marker_in_a_quoted_value_does_not_exempt_a_broken_file(tmp_path, monkeypatch, name, text):
    assert run_main(monkeypatch, _event(tmp_path, name, text)) == 2


@pytest.mark.parametrize("name,text", [
    ("a.yaml", 'greeting: "Hello {{name}}"\nitems: [a, b]\n'),
    ("a.xml", '<root><a title="{{ title }}">x</a></root>'),
])
def test_a_valid_file_with_a_quoted_placeholder_passes(tmp_path, monkeypatch, name, text):
    assert run_main(monkeypatch, _event(tmp_path, name, text)) == 0


@pytest.mark.parametrize("name,text", [
    # a quote inside the template expression cuts the quoted value short
    ("chart.yaml", 'name: "{{ include "chart.name" . }}"\nitems: [a, b\n'),
    # a marker in a plain (unquoted) position
    ("chart.yaml", 'name: "x"\nlabels: {{- toYaml .Values.l | nindent 4 }}\n'),
    # a marker the scanner never reaches, behind a scan error
    ("chart.yaml", 'a: "{{ x }}"\nb: @bad {{ y }}\n'),
    # a quoted marker beside a plain one: the plain one decides
    ("chart.yaml", 'a: "{{ x }}"\n{{- if .Values.b }}\nb: [1\n{{- end }}\n'),
    ("t.xml", '<root>{% for x in y %}<a title="{{ x }}">{% endfor %}</root'),
    ("t.xml", '<root><a href="{{ "x" }}"></root>'),
    ("t.xml", "<root><%= b %></root"),
])
def test_a_real_yaml_or_xml_template_is_still_skipped(tmp_path, monkeypatch, name, text):
    assert run_main(monkeypatch, _event(tmp_path, name, text)) == 0


def test_without_pyyaml_any_yaml_marker_still_means_template(tmp_path, monkeypatch):
    """With no scanner to tell a value from structure, the hook stays out of the way rather than
    guess; the ruamel fallback still validates a file that carries no marker at all."""
    _block_imports(monkeypatch, "yaml")
    assert run_main(monkeypatch, _event(tmp_path, "a.yaml", 'g: "Hi {{n}}"\ni: [a, b\n')) == 0
    assert run_main(monkeypatch, _event(tmp_path, "b.yaml", 'g: "Hi n"\ni: [a, b\n')) == 2
