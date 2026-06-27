"""Tests for session-start.py (SessionStart context-injection hook).

Contract: on stdout, emit
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <skill+banner>}}
when meta-using-bitranox-skills/SKILL.md is readable; emit nothing when it is not. main()
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
import self_improve_signals as SIG

REPO_PLUGIN_ROOT = Path(__file__).resolve().parents[2]  # plugins/bitranox


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    """Point HOME at a clean tmp dir so audit-file lookup never sees a real report.

    Also drop the auto-update-nudge opt-out sentinel by default so the nudge stays silent for
    the non-nudge tests; the nudge tests remove it explicitly.
    """
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".bitranox-no-autoupdate-nudge").write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nBODY\n"):
    skill = tmp_path / "skills" / "meta-using-bitranox-skills" / "SKILL.md"
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
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nUNIQUE_MARKER_XYZ\n")
    rc, out = run(monkeypatch, capsys, root)
    assert rc == 0
    payload = json.loads(out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    ctx = hso["additionalContext"]
    assert "UNIQUE_MARKER_XYZ" in ctx          # the skill body is injected
    assert "meta-using-bitranox-skills" in ctx          # banner names the skill
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
    # real meta-using-bitranox-skills skill shipped in this repo.
    rc, out = run(monkeypatch, capsys, None)
    assert rc == 0
    assert "meta-using-bitranox-skills" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_real_skill_is_where_the_hook_expects():
    assert (REPO_PLUGIN_ROOT / "skills" / "meta-using-bitranox-skills" / "SKILL.md").is_file()


# --------------------------------------------------------------------------
# SessionEnd audit surfacing (consumed once, appended to the skills context)
# --------------------------------------------------------------------------


def run_with_stdin(monkeypatch, capsys, plugin_root, cwd):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": cwd})))
    rc = S.main()
    return rc, capsys.readouterr().out


def _write_audit(cwd, text):
    af = SIG.audit_file(cwd)
    af.parent.mkdir(parents=True, exist_ok=True)
    af.write_text(text, encoding="utf-8")
    return af


def test_audit_is_surfaced_and_consumed(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nSKILLBODY\n")
    cwd = "/proj/audit"
    af = _write_audit(cwd, "<SELF-IMPROVE-AUDIT>\nreview these misses\n</SELF-IMPROVE-AUDIT>\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, cwd)
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "SKILLBODY" in ctx            # skills banner still present
    assert "review these misses" in ctx  # audit appended
    assert not af.is_file()              # consumed (deleted) so it is not resurfaced


def test_audit_surfaces_even_without_skill(tmp_path, monkeypatch, capsys):
    cwd = "/proj/auditonly"
    _write_audit(cwd, "<SELF-IMPROVE-AUDIT>\nonly audit\n</SELF-IMPROVE-AUDIT>\n")
    rc, out = run_with_stdin(monkeypatch, capsys, tmp_path, cwd)  # tmp_path has no skill
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "only audit" in ctx


def test_no_audit_leaves_context_unchanged(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nSKILLBODY\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/none")
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "SKILLBODY" in ctx
    assert "SELF-IMPROVE-AUDIT" not in ctx


# --------------------------------------------------------------------------
# Auto-update nudge (self-silencing systemMessage)
# --------------------------------------------------------------------------


def _optout(home):
    return home / ".claude" / ".bitranox-no-autoupdate-nudge"


def test_nudge_fires_when_autoupdate_off(tmp_path, monkeypatch, capsys, isolate_home):
    _optout(isolate_home).unlink()  # remove the default opt-out so the nudge can fire
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/x")
    assert rc == 0
    assert "auto-update" in json.loads(out).get("systemMessage", "")


def test_nudge_silent_when_autoupdate_on(tmp_path, monkeypatch, capsys, isolate_home):
    _optout(isolate_home).unlink()
    settings = isolate_home / ".claude" / "settings.json"
    settings.write_text(
        json.dumps({"extraKnownMarketplaces": {"bitranox-skills": {"autoUpdate": True}}}),
        encoding="utf-8")
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/x")
    assert "systemMessage" not in json.loads(out)


def test_nudge_silent_when_optout_present(tmp_path, monkeypatch, capsys):
    # the autouse fixture leaves the opt-out sentinel in place
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/x")
    assert "systemMessage" not in json.loads(out)


# --------------------------------------------------------------------------
# meta-dream due nudge (additionalContext, self-silencing)
# --------------------------------------------------------------------------


def test_dream_nudge_fires_when_due(tmp_path, monkeypatch, capsys, isolate_home):
    mem = SIG.memory_dir("/proj/dream")
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")  # memory exists, no last-dream -> due
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/dream")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "BITRANOX-DREAM-DUE" in ctx and "meta-dream" in ctx


def test_dream_nudge_silent_when_not_due(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/nomem")  # no memory dir -> not due
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "BITRANOX-DREAM-DUE" not in ctx


def test_dream_nudge_silent_when_off(tmp_path, monkeypatch, capsys, isolate_home):
    mem = SIG.memory_dir("/proj/dream")
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")
    (isolate_home / ".claude" / ".bitranox-dream-off").write_text("", encoding="utf-8")
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/dream")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "BITRANOX-DREAM-DUE" not in ctx
