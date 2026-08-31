"""Tests for tell-sweep.py (the AI-writing-tell PostToolUse guard).

End-to-end tests drive main() with a stdin payload plus a real temp file, and a
subprocess smoke test through run-python.sh exercises the cross-platform shim. All
source is ASCII; tell characters are built via chr(), never pasted.
"""

import io
import json
import subprocess
import sys
import pytest
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


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_shim_smoke(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("A real %s dash.\n" % EM_DASH, encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(f)}})
    r = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True, text=True
    )
    assert r.returncode == 2
    assert "tell(s) found" in r.stderr


LEFT_ARROW = chr(0x2190)


def test_sweep_blocks_a_continuation_artifact_inside_a_code_fence(tmp_path, monkeypatch, capsys):
    """A split command is exactly what the tell scan exempts, so the hook must still catch it."""
    fp = tmp_path / "doc.md"
    fp.write_text("intro\n```bash\nwget https://example.com/k- %strixie.gpg\n```\n" % LEFT_ARROW,
                  encoding="utf-8")
    rc = _run(monkeypatch, {"tool_input": {"file_path": str(fp)}})
    assert rc == 2
    assert "line-continuation artifact" in capsys.readouterr().err


def test_sweep_allows_a_prose_arrow_followed_by_a_space(tmp_path, monkeypatch):
    fp = tmp_path / "doc.md"
    fp.write_text("git init runs in cwd() %s empty parameter\n" % LEFT_ARROW, encoding="utf-8")
    assert _run(monkeypatch, {"tool_input": {"file_path": str(fp)}}) == 0


def test_a_non_utf8_file_is_not_called_a_tell(tmp_path, monkeypatch):
    """The same defect the commit-side guard had, in this sibling.

    U+FFFD is a tell on purpose - it is mojibake - so decoding with errors="replace" MINTS one
    per undecodable byte and the reader manufactures exactly what the detector looks for. Here
    that is worse than a single false block: this hook blocks the whole file until it is clean,
    and a manufactured character cannot be edited out, so the file can never become clean.
    """
    f = tmp_path / "a.txt"
    f.write_bytes("Plain ASCII prose - no tells.\n".encode("utf-8") + b"\xff\xfe\x00\n")
    assert _run(monkeypatch, {"tool_input": {"file_path": str(f)}}) == 0


def test_a_genuine_replacement_character_is_still_a_tell(tmp_path, monkeypatch):
    """The direction the fix must NOT reach: real mojibake encoded in the file still blocks."""
    assert _run(monkeypatch, _md(tmp_path, "Subject %s tail\n" % chr(0xFFFD))) == 2
