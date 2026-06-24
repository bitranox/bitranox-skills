"""Tests for tell-sweep.py (the AI-writing-tell PostToolUse guard).

End-to-end tests drive main() with a stdin payload plus a real temp file, and a
subprocess smoke test through run-python.sh exercises the cross-platform shim. All
source is ASCII; tell characters are built via chr(), never pasted.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import tell_sweep as T

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "tell-sweep.py"
SHIM = HOOKS_DIR / "run-python.sh"

EM_DASH = chr(0x2014)
NBSP = chr(0x00A0)
CURLY_OPEN = chr(0x201C)
ARROW = chr(0x2192)  # allowed on purpose, must NOT trip


def _run(monkeypatch, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    return T.main()


def _md(tmp_path, text, name="a.md"):
    f = tmp_path / name
    f.write_text(text, encoding="utf-8")
    return {"tool_input": {"file_path": str(f)}}


def test_clean_prose_passes(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "Plain ASCII prose - no tells.\n")) == 0


def test_real_em_dash_caught(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "A real %s dash in prose.\n" % EM_DASH)) == 2


def test_curly_quote_caught(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "He said %shi.\n" % CURLY_OPEN)) == 2


def test_nbsp_caught(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "two%swords\n" % NBSP)) == 2


def test_inline_code_span_ignored(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "Use `%s` only in code.\n" % EM_DASH)) == 0


def test_fenced_block_ignored(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "```\n%s\n```\n" % EM_DASH)) == 0


def test_arrow_allowed(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "a %s b in prose.\n" % ARROW)) == 0


def test_code_file_skipped(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "x = '%s'\n" % EM_DASH, name="a.py")) == 0


def test_claude_md_scoped(tmp_path, monkeypatch):
    assert _run(monkeypatch, _md(tmp_path, "real %s dash\n" % EM_DASH, name="CLAUDE.md")) == 2


def test_missing_file_is_safe(tmp_path, monkeypatch):
    assert _run(monkeypatch, {"tool_input": {"file_path": str(tmp_path / "nope.md")}}) == 0


def test_bad_payload_is_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert T.main() == 0


def test_shim_smoke(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("A real %s dash.\n" % EM_DASH, encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(f)}})
    r = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True
    )
    assert r.returncode == 2
    assert "tell(s) found" in r.stderr
