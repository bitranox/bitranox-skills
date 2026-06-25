"""Tests for session-start.py (SessionStart context-injection hook).

Contract: on stdout, emit
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <skill+banner>}}
when using-bitranox-skills/SKILL.md is readable; emit nothing when it is not. main()
always returns 0. The skill is located via CLAUDE_PLUGIN_ROOT (else relative to the
hook file).

All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import session_start as S

REPO_PLUGIN_ROOT = Path(__file__).resolve().parents[2]  # plugins/bitranox


def make_plugin_root(tmp_path, skill_body="---\nname: using-bitranox-skills\n---\n\nBODY\n"):
    skill = tmp_path / "skills" / "using-bitranox-skills" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(skill_body, encoding="utf-8")
    return tmp_path


def run(monkeypatch, capsys, plugin_root=None):
    if plugin_root is None:
        monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    else:
        monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    rc = S.main()
    return rc, capsys.readouterr().out


def test_emits_sessionstart_context_with_skill_body(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: using-bitranox-skills\n---\n\nUNIQUE_MARKER_XYZ\n")
    rc, out = run(monkeypatch, capsys, root)
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    ctx = hso["additionalContext"]
    assert "UNIQUE_MARKER_XYZ" in ctx          # the skill body is injected
    assert "using-bitranox-skills" in ctx          # banner names the skill
    assert ctx.startswith("<EXTREMELY-IMPORTANT>")
    assert ctx.rstrip().endswith("</EXTREMELY-IMPORTANT>")


def test_output_is_valid_json(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body='line with "quotes"\nand newline\tand tab\n')
    _, out = run(monkeypatch, capsys, root)
    json.loads(out)  # raises if escaping is wrong


def test_missing_skill_emits_nothing(tmp_path, monkeypatch, capsys):
    # plugin root exists but has no skill file
    rc, out = run(monkeypatch, capsys, tmp_path)
    assert rc == 0
    assert out == ""


def test_empty_skill_emits_nothing(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="   \n")
    rc, out = run(monkeypatch, capsys, root)
    assert rc == 0
    assert out == ""


def test_resolves_against_real_repo_skill(monkeypatch, capsys):
    # With no env var, it derives the path from the hook file location and finds the
    # real using-bitranox-skills skill shipped in this repo.
    rc, out = run(monkeypatch, capsys, None)
    assert rc == 0
    assert "using-bitranox-skills" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_real_skill_is_where_the_hook_expects():
    assert (REPO_PLUGIN_ROOT / "skills" / "using-bitranox-skills" / "SKILL.md").is_file()
