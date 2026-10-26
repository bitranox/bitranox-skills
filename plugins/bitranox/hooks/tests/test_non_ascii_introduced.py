"""Tests for non-ascii-introduced.py (the PostToolUse guard for non-ASCII a write introduced).

End-to-end tests drive main() with a stdin payload plus a real temp file, the HEAD-blob cases use
a real git repository, and one smoke test runs the hook through run-python.sh. All source is
ASCII; every non-ASCII value is built with chr(), never pasted or typed as an escape.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import non_ascii_introduced as N
import tell_chars

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "non-ascii-introduced.py"
SHIM = HOOKS_DIR / "run-python.sh"

AR3 = chr(0x0663)        # ARABIC-INDIC DIGIT THREE: the slip this hook exists for
UMLAUT = chr(0x00E4)     # LATIN SMALL LETTER A WITH DIAERESIS: typical intended non-ASCII
UNASSIGNED = chr(0x0378)  # no Unicode name, exercises the fallback


def _run(monkeypatch, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return N.main()


def _edit(fp, old, new, replace_all=False):
    return {"tool_name": "Edit", "tool_input": {
        "file_path": str(fp), "old_string": old, "new_string": new, "replace_all": replace_all}}


def _write(fp, content, response=None):
    event = {"tool_name": "Write", "tool_input": {"file_path": str(fp), "content": content}}
    if response is not None:
        event["tool_response"] = response
    return event


def _git(cwd, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", *args], cwd=str(cwd), env=env, check=True, capture_output=True)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


# --- Edit -----------------------------------------------------------------------------------------

def test_edit_introducing_an_arabic_digit_fires_with_position_and_name(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("import x\na = '%s'\n" % AR3, encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "a = '3'", "a = '%s'" % AR3)) == 2
    err = capsys.readouterr().err
    assert "line 2, col 6: U+0663 ARABIC-INDIC DIGIT THREE" in err
    assert "chr(0x0663)" in err


def test_edit_adding_only_ascii_is_silent(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("a = '%s'\nb = 2\n" % UMLAUT, encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "b = 1", "b = 2")) == 0
    assert capsys.readouterr().err == ""


def test_edit_keeping_a_char_old_string_already_had_is_silent(tmp_path, monkeypatch):
    fp = tmp_path / "t.py"
    fp.write_text("msg = 'gr%sn'  # new\n" % UMLAUT, encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "msg = 'gr%sn'" % UMLAUT, "msg = 'gr%sn'  # new" % UMLAUT)) == 0


def test_edit_adding_a_char_the_rest_of_the_file_already_uses_is_silent(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("title = 'Gr%sn'\nlabel = 'Bl%st'\n" % (UMLAUT, UMLAUT), encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "label = 'Blat'", "label = 'Bl%st'" % UMLAUT)) == 0
    assert capsys.readouterr().err == ""


def test_edit_into_a_file_with_umlauts_still_flags_a_new_arabic_digit(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("title = 'Gr%sn'\nn = '%s%s'\n" % (UMLAUT, UMLAUT, AR3), encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "n = '3'", "n = '%s%s'" % (UMLAUT, AR3))) == 2
    err = capsys.readouterr().err
    assert "line 2, col 7: U+0663" in err
    assert "U+00E4" not in err


def test_replace_all_is_not_hidden_by_its_own_other_occurrences(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    new = "v = '%s'" % AR3
    fp.write_text("%s\nx = 1\n%s\n" % (new, new), encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "v = '3'", new, replace_all=True)) == 2
    assert "line 1, col 6: U+0663" in capsys.readouterr().err


def test_edit_whose_new_string_is_gone_from_the_file_reports_against_new_string(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("rewritten by someone else\n", encoding="utf-8")
    assert _run(monkeypatch, _edit(fp, "x", "x\ny%s" % AR3)) == 2
    assert "new_string line 2, col 2: U+0663" in capsys.readouterr().err


def test_multiedit_reports_per_edit(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "t.py"
    fp.write_text("a = '%s'\nb = '%s'\n" % (AR3, UMLAUT), encoding="utf-8")
    event = {"tool_name": "MultiEdit", "tool_input": {"file_path": str(fp), "edits": [
        {"old_string": "a = '3'", "new_string": "a = '%s'" % AR3},
        {"old_string": "b = 'a'", "new_string": "b = '%s'" % UMLAUT},
    ]}}
    assert _run(monkeypatch, event) == 2
    err = capsys.readouterr().err
    assert "line 1, col 6: U+0663" in err
    assert "line 2, col 6: U+00E4 LATIN SMALL LETTER A WITH DIAERESIS" in err


# --- Write ----------------------------------------------------------------------------------------

def test_write_of_a_new_python_file_with_a_non_ascii_char_fires(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "new.py"
    content = "x = 1\ny = '%s'\n" % AR3
    fp.write_text(content, encoding="utf-8")
    assert _run(monkeypatch, _write(fp, content, {"type": "create", "originalFile": None})) == 2
    assert "line 2, col 6: U+0663" in capsys.readouterr().err


def test_write_to_a_tracked_file_flags_the_new_digit_but_not_the_umlaut_head_had(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    fp = repo / "m.py"
    fp.write_text("x = '%s'\n" % UMLAUT, encoding="utf-8")
    _git(repo, "add", "m.py")
    _git(repo, "commit", "-q", "-m", "init")
    content = "x = '%s'\ny = '%s'\n" % (UMLAUT, AR3)
    fp.write_text(content, encoding="utf-8")
    # No originalFile in the response: the HEAD blob is the previous text.
    assert _run(monkeypatch, _write(fp, content, {"type": "update"})) == 2
    err = capsys.readouterr().err
    assert "line 2, col 6: U+0663" in err
    assert "U+00E4" not in err


def test_write_prefers_the_tool_responses_original_file_over_head(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    fp = repo / "m.py"
    fp.write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "m.py")
    _git(repo, "commit", "-q", "-m", "init")
    # The digit was already on disk before this call (an earlier, uncommitted write): not new now.
    content = "x = '%s'\n" % AR3
    fp.write_text(content, encoding="utf-8")
    response = {"type": "update", "originalFile": "x = '%s'  # old\n" % AR3}
    assert _run(monkeypatch, _write(fp, content, response)) == 0
    assert capsys.readouterr().err == ""


def test_write_of_an_untracked_existing_file_without_original_counts_everything(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    fp = repo / "loose.py"
    content = "x = '%s'\n" % UMLAUT
    fp.write_text(content, encoding="utf-8")
    assert _run(monkeypatch, _write(fp, content, {"type": "update"})) == 2
    assert "U+00E4" in capsys.readouterr().err


# --- scope, report shape, failure paths -----------------------------------------------------------

def test_a_prose_file_is_left_to_tell_sweep(tmp_path, monkeypatch, capsys):
    for name in ("notes.md", "README.markdown", "a.txt", "CLAUDE.md"):
        fp = tmp_path / name
        content = "x %s\n" % AR3
        fp.write_text(content, encoding="utf-8")
        assert tell_chars.is_prose_path(str(fp))
        assert _run(monkeypatch, _write(fp, content, {"type": "create"})) == 0
    assert capsys.readouterr().err == ""


def test_malformed_stdin_exits_0(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))
    assert N.main() == 0


def test_wrong_shapes_exit_0(monkeypatch):
    for event in ([], {"tool_input": "str"}, {"tool_name": "Edit", "tool_input": {"file_path": 3}},
                  {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.py", "edits": "x"}}):
        assert _run(monkeypatch, event) == 0


def test_the_report_never_quotes_the_line(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "s.py"
    content = "token = 'PRIVATEMARKER%s'\n" % AR3
    fp.write_text(content, encoding="utf-8")
    assert _run(monkeypatch, _write(fp, content, {"type": "create"})) == 2
    err = capsys.readouterr().err
    assert "PRIVATEMARKER" not in err
    assert AR3 not in err
    assert all(ord(c) < 128 for c in err)


def test_a_char_without_a_unicode_name_gets_a_fallback(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "u.py"
    content = "x = '%s'\n" % UNASSIGNED
    fp.write_text(content, encoding="utf-8")
    assert _run(monkeypatch, _write(fp, content, {"type": "create"})) == 2
    assert "U+0378 (no name, category Cn)" in capsys.readouterr().err


def test_the_list_is_capped_and_says_how_many_more(tmp_path, monkeypatch, capsys):
    fp = tmp_path / "many.py"
    content = "".join("x%d = '%s'\n" % (i, AR3) for i in range(N._MAX_LISTED + 5))
    fp.write_text(content, encoding="utf-8")
    assert _run(monkeypatch, _write(fp, content, {"type": "create"})) == 2
    err = capsys.readouterr().err
    assert "... and 5 more" in err
    assert err.count("U+0663 ARABIC-INDIC DIGIT THREE") == N._MAX_LISTED


def test_findings_counts_columns_in_characters_not_bytes():
    found = N.findings("Write", {"content": "%s%s\n" % (UMLAUT, AR3)}, previous=UMLAUT)
    assert [(f.line, f.col, f.char) for f in found] == [(1, 2, AR3)]


def test_smoke_through_the_shim(tmp_path):
    fp = tmp_path / "s.py"
    content = "v = '%s'\n" % AR3
    fp.write_text(content, encoding="utf-8")
    payload = json.dumps(_write(fp, content, {"type": "create"}))
    r = subprocess.run(["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 2
    assert "U+0663 ARABIC-INDIC DIGIT THREE" in r.stderr
