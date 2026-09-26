"""Tests for session-banner.py (SessionStart hook: injects the meta-using-bitranox-skills body).

All content is ASCII.
"""

from pathlib import Path

import session_banner as B


def _plugin_root(tmp_path, skill_body):
    root = tmp_path / "plugin"
    skill = root / "skills" / "meta-using-bitranox-skills" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(skill_body, encoding="utf-8")
    return root


def test_build_context_wraps_a_real_skill_body(tmp_path, monkeypatch):
    root = _plugin_root(tmp_path, "the real skill body\n")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    ctx = B.build_context()
    assert ctx is not None
    assert "the real skill body" in ctx
    assert ctx.startswith("<EXTREMELY-IMPORTANT>")
    assert ctx.endswith("</EXTREMELY-IMPORTANT>")


def test_build_context_is_none_when_skill_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "nonexistent"))
    assert B.build_context() is None


# ---- D9: the guard is `if not text.strip()`, not `if not text` --------------------------------
# A regression from .strip() back to a bare truthiness check would still catch an empty file (""
# is falsy either way) but would SHIP an empty banner for a whitespace-only file, because
# "  \n\t\n  " is truthy. Only a whitespace-only body discriminates the two forms.

def test_whitespace_only_skill_md_is_treated_as_blank(tmp_path, monkeypatch):
    root = _plugin_root(tmp_path, "  \n\t\n  ")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    assert B.build_context() is None


def test_zero_byte_skill_md_is_also_treated_as_blank(tmp_path, monkeypatch):
    """Control: a regression to `if not text:` would also catch this one, so it cannot by itself
    discriminate the guard form - the whitespace-only case above is the one that can."""
    root = _plugin_root(tmp_path, "")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    assert B.build_context() is None
