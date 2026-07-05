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

    Also chdir to a clean tmp dir: the run() helper sends no stdin, so _proj() falls back to
    os.getcwd(); without this it would resolve the REAL repo, whose in-tree curated store makes
    dream_due() fire and pollutes the context the non-nudge tests assert on. The nudge tests are
    unaffected - they pass an explicit cwd via run_with_stdin().
    """
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".bitranox-no-autoupdate-nudge").write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
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


def test_bare_project_emits_nothing(tmp_path, monkeypatch, capsys):
    # no anchor tree, no audit, no nudges -> the essentials hook emits nothing at all
    rc, out = run(monkeypatch, capsys, tmp_path)
    assert rc == 0
    assert out == ""


def test_output_is_valid_json_with_audit(tmp_path, monkeypatch, capsys):
    cwd = "/proj/jsoncheck"
    _write_audit(cwd, 'line with "quotes"\nand newline\tand tab\n')
    root = make_plugin_root(tmp_path)
    rc, out = run_with_stdin(monkeypatch, capsys, root, cwd)
    json.loads(out)  # raises if escaping is wrong


def test_banner_resolves_against_real_repo_skill(monkeypatch, capsys):
    # session-banner derives the skill path from the hook file location and finds the
    # real meta-using-bitranox-skills skill shipped in this repo.
    import session_banner as B
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    rc = B.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "meta-using-bitranox-skills" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_real_skill_is_where_the_hook_expects():
    assert (REPO_PLUGIN_ROOT / "skills" / "meta-using-bitranox-skills" / "SKILL.md").is_file()


# --------------------------------------------------------------------------
# SessionEnd audit surfacing (consumed once, appended to the skills context)
# --------------------------------------------------------------------------



def _ctx(out):
    """additionalContext from the hook output; '' when the hook emitted nothing."""
    if not out:
        return ""
    return json.loads(out).get("hookSpecificOutput", {}).get("additionalContext", "")


def _sysmsg(out):
    if not out:
        return ""
    return json.loads(out).get("systemMessage", "")


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
    ctx = _ctx(out)
    assert "review these misses" in ctx  # audit surfaced by the essentials hook
    assert not af.is_file()              # consumed (deleted) so it is not resurfaced


def test_audit_surfaces_even_without_skill(tmp_path, monkeypatch, capsys):
    cwd = "/proj/auditonly"
    _write_audit(cwd, "<SELF-IMPROVE-AUDIT>\nonly audit\n</SELF-IMPROVE-AUDIT>\n")
    rc, out = run_with_stdin(monkeypatch, capsys, tmp_path, cwd)  # tmp_path has no skill
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "only audit" in ctx


def test_no_audit_no_store_emits_nothing(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path)
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/none")
    assert rc == 0
    assert "SELF-IMPROVE-AUDIT" not in out and out == ""


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
    assert "auto-update" in _sysmsg(out)


def test_nudge_silent_when_autoupdate_on(tmp_path, monkeypatch, capsys, isolate_home):
    _optout(isolate_home).unlink()
    settings = isolate_home / ".claude" / "settings.json"
    settings.write_text(
        json.dumps({"extraKnownMarketplaces": {"bitranox-skills": {"autoUpdate": True}}}),
        encoding="utf-8")
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/x")
    assert _sysmsg(out) == ""


def test_nudge_silent_when_optout_present(tmp_path, monkeypatch, capsys):
    # the autouse fixture leaves the opt-out sentinel in place
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/x")
    assert _sysmsg(out) == ""


# --------------------------------------------------------------------------
# meta-dream-tree due nudge (additionalContext, self-silencing)
# --------------------------------------------------------------------------


def test_dream_nudge_fires_when_due(tmp_path, monkeypatch, capsys, isolate_home):
    mem = SIG.memory_dir("/proj/dream")
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")  # memory exists, no last-dream -> due
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/dream")
    ctx = _ctx(out)
    assert "BITRANOX-DREAM-DUE" in ctx and "meta-dream-tree" in ctx


def test_dream_nudge_silent_when_not_due(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/nomem")  # no memory dir -> not due
    assert "BITRANOX-DREAM-DUE" not in out


def test_dream_nudge_silent_when_off(tmp_path, monkeypatch, capsys, isolate_home):
    mem = SIG.memory_dir("/proj/dream")
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")
    SIG.save_config({"dream_mode": "off"})
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/dream")
    assert "BITRANOX-DREAM-DUE" not in out


# --------------------------------------------------------------------------
# new-project bootstrap nudge + the nudges config flag
# --------------------------------------------------------------------------


def _seed_some_other_knowledge():
    """Give the store SOMETHING to gather from (a sibling project's memory)."""
    other = SIG.memory_dir("/proj/other")
    other.mkdir(parents=True, exist_ok=True)
    (other / "b.md").write_text("a useful note", encoding="utf-8")


def _install_collect_skill(root):
    """The new-project nudge is gated on the Phase-2 meta-collect-knowledge skill being installed."""
    p = root / "skills" / "meta-collect-knowledge" / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\nname: meta-collect-knowledge\n---\n\nB\n", encoding="utf-8")


def test_newproject_nudge_fires_once_then_silent(tmp_path, monkeypatch, capsys, isolate_home):
    _seed_some_other_knowledge()
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    _install_collect_skill(root)
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/fresh")   # fresh, no memory
    ctx = _ctx(out)
    assert "BITRANOX-NEW-PROJECT" in ctx and "collect-knowledge" in ctx
    rc2, out2 = run_with_stdin(monkeypatch, capsys, root, "/proj/fresh")  # second time: silent
    assert "BITRANOX-NEW-PROJECT" not in out2


def test_newproject_nudge_silent_on_empty_store(tmp_path, monkeypatch, capsys, isolate_home):
    # nothing anywhere to seed from -> no nudge (fresh machine), even with the skill installed
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    _install_collect_skill(root)
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/fresh")
    assert "BITRANOX-NEW-PROJECT" not in out


def test_newproject_nudge_dormant_without_collect_skill(tmp_path, monkeypatch, capsys, isolate_home):
    # collect skill NOT installed (Phase 1 state) -> nudge stays dormant even for a fresh project
    _seed_some_other_knowledge()
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/fresh")
    assert "BITRANOX-NEW-PROJECT" not in out


def test_nudges_flag_off_suppresses_dream_and_newproject(tmp_path, monkeypatch, capsys, isolate_home):
    SIG.save_config({"nudges": False})
    mem = SIG.memory_dir("/proj/dream")          # a due dream
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")
    _seed_some_other_knowledge()
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/dream")
    assert "BITRANOX-DREAM-DUE" not in out        # nudges off -> suppressed
    rc2, out2 = run_with_stdin(monkeypatch, capsys, root, "/proj/fresh")
    assert "BITRANOX-NEW-PROJECT" not in out2


# --------------------------------------------------------------------------
# model-driven on-demand retrieval standing rule (BITRANOX-MEMORY-RETRIEVAL)
# --------------------------------------------------------------------------

import uuid_store as US  # noqa: E402


def _anchor_tree_with_fact(tmp_path):
    """An anchor (CLAUDE.md + central .claude-memory store with one body) -> a nested proj below it."""
    anchor = tmp_path / "atree"
    proj = anchor / "sub" / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    u = US.fact_uuid(str(anchor), "some-fact")
    US.put_body(str(anchor), u, "the fact body")          # creates anchor/.claude-memory/facts/<shard>/<u>.md
    return anchor, proj, u


def test_retrieval_context_emits_rule_with_anchor_and_slug_path(tmp_path):
    anchor, proj, _u = _anchor_tree_with_fact(tmp_path)
    block = S.retrieval_context(str(proj))
    assert block is not None
    assert "BITRANOX-MEMORY-RETRIEVAL" in block
    assert "%s/.claude-memory/facts/" % anchor in block   # concrete absolute anchor path
    assert "mem:" in block                                 # names the pointer scheme
    assert "<slug>.md" in block                            # the slug-named body rule


def test_retrieval_context_none_without_store(tmp_path):
    # a CLAUDE.md anchor but NO .claude-memory store yet -> nothing to retrieve
    anchor = tmp_path / "bare"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert S.retrieval_context(str(proj)) is None


def test_retrieval_context_none_without_anchor(tmp_path):
    d = tmp_path / "no" / "claude" / "md"
    d.mkdir(parents=True)
    assert S.retrieval_context(str(d)) is None


def test_main_includes_retrieval_block_when_store_exists(tmp_path, monkeypatch, capsys):
    anchor, proj, _u = _anchor_tree_with_fact(tmp_path)
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, str(proj))
    assert rc == 0
    ctx = _ctx(out)
    assert "BITRANOX-MEMORY-RETRIEVAL" in ctx and ("%s/.claude-memory/facts/" % anchor) in ctx


def test_main_omits_retrieval_when_no_store(tmp_path, monkeypatch, capsys):
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nB\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, "/proj/no-store")
    assert "BITRANOX-MEMORY-RETRIEVAL" not in out


# --------------------------------------------------------------------------
# inject split: session-start emits ONLY the small essentials (retrieval + audit + nudges);
# the big skills banner moved to session-banner.py. Root cause: the harness persists oversized
# additionalContext to a file with a ~2KB preview, so anything appended after the ~10KB banner
# (retrieval block, nudges, audit) never reached context.
# --------------------------------------------------------------------------


def test_session_start_no_longer_injects_the_banner(tmp_path, monkeypatch, capsys):
    anchor, proj, _u = _anchor_tree_with_fact(tmp_path)
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nBIGBANNER\n")
    rc, out = run_with_stdin(monkeypatch, capsys, root, str(proj))
    ctx = _ctx(out)
    assert "BIGBANNER" not in ctx and "EXTREMELY-IMPORTANT" not in ctx   # banner not here any more
    assert "BITRANOX-MEMORY-RETRIEVAL" in ctx                            # essentials still here


def test_session_start_small_context_stays_under_persist_cap(tmp_path, monkeypatch, capsys):
    # essentials (retrieval + audit + nudges) must stay comfortably below the harness persist
    # threshold, or they get buried in a file again. Defensive budget: 3500 bytes.
    anchor, proj, _u = _anchor_tree_with_fact(tmp_path)
    _write_audit(str(proj), "<SELF-IMPROVE-AUDIT>\nsome candidate misses\n</SELF-IMPROVE-AUDIT>\n")
    root = make_plugin_root(tmp_path)
    rc, out = run_with_stdin(monkeypatch, capsys, root, str(proj))
    ctx = _ctx(out)
    assert ctx and len(ctx.encode("utf-8")) < 3500


def test_session_banner_emits_the_skill_banner(tmp_path, monkeypatch, capsys):
    import session_banner as B
    root = make_plugin_root(tmp_path, skill_body="---\nname: meta-using-bitranox-skills\n---\n\nBIGBANNER\n")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(root))
    rc = B.main()
    out = capsys.readouterr().out
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "BIGBANNER" in ctx and ctx.startswith("<EXTREMELY-IMPORTANT>")


def test_session_banner_missing_skill_emits_nothing(tmp_path, monkeypatch, capsys):
    import session_banner as B
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path))
    rc = B.main()
    assert rc == 0 and capsys.readouterr().out == ""
