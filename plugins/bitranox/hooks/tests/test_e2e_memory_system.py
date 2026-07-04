"""End-to-end INTEGRATION test for the bitranox self-learning / memory system.

The per-script unit tests check functions in isolation; this proves the components are wired
together by driving each through its REAL entry point - subprocess stdin/stdout for the hyphenated
hooks, CLI argv for the helper scripts - against an isolated sandbox HOME. It never touches the real
memory store. One ordered scenario (the steps depend on each other), many assertions. All content ASCII.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent
HOOKS = _TESTS.parent                          # plugins/bitranox/hooks
SK = HOOKS.parent / "skills"                   # plugins/bitranox/skills
sys.path.insert(0, str(SK / "meta-collect-knowledge"))

import self_improve_signals as sig             # on sys.path via the hooks-tests conftest
import gather_scan as gs


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def _hook(script, payload):
    p = subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(payload),
                       capture_output=True, text=True, env=dict(os.environ))
    return p.returncode, p.stdout.strip()


def _cli(path, *args):
    p = subprocess.run([sys.executable, str(path), *args],
                       capture_output=True, text=True, env=dict(os.environ))
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def _mem(proj, name, text):
    d = sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def _recall(prompt, cwd, sid):
    rc, out = _hook("recall-memory.py", {"prompt": prompt, "cwd": cwd, "session_id": sid})
    if not out:
        return []
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    return [l[4:] for l in ctx.splitlines() if l.startswith("### ")]


def test_memory_system_end_to_end(sandbox):
    proj_a = str(sandbox / "projA")            # the "current" project (recall excludes it)
    proj_b = str(sandbox / "projB")            # a sibling project holding reusable notes

    # store setup: a rare note + a corpus-common ("widget") cluster + one rare term among them
    _mem(proj_b, "zorblax.md", "Configure the zorblax frobnicator: set the zorblax flag before deploy.")
    for i in range(8):
        _mem(proj_b, "w%d.md" % i, "widget gadget item number %d here" % i)
    _mem(proj_b, "frob.md", "widget gadget frobnitz special and rare term")
    (sandbox / "CLAUDE.md").write_text("x", encoding="utf-8")   # topmost CLAUDE.md -> the global tier
    g = sig.global_rules_dir(proj_a); g.mkdir(parents=True, exist_ok=True)
    (g / "_scope.md").write_text("global bitranox rules layer", encoding="utf-8")

    # S1 - settings CLI: view / set / persist / reset
    settings = SK / "meta-memory-settings" / "settings.py"
    _, out, _ = _cli(settings, "view")
    assert "dream_mode" in out
    _cli(settings, "set", "dream_mode", "auto")
    assert sig.load_config().get("dream_mode") == "auto"
    _cli(settings, "reset")
    assert sig.load_config().get("dream_mode") == "propose"

    # S2 - model-hierarchy review marker
    assert sig.model_review_due() is True
    sig.mark_model_reviewed(now=1_000_000.0)
    assert sig.model_review_due(now=1_000_000.0) is False
    assert sig.model_review_due(now=1_000_000.0 + 31 * 86400) is True

    # S3 - session-start new-project nudge fires once, then self-silences (unique marker, not the
    # always-injected skills catalog which also mentions collect-knowledge)
    mark = "BITRANOX-NEW-PROJECT"
    _, out = _hook("session-start.py", {"cwd": proj_a, "session_id": "x", "source": "startup"})
    ctx = json.loads(out).get("hookSpecificOutput", {}).get("additionalContext", "") if out else ""
    assert mark in ctx
    _, out2 = _hook("session-start.py", {"cwd": proj_a, "session_id": "x2", "source": "startup"})
    ctx2 = json.loads(out2).get("hookSpecificOutput", {}).get("additionalContext", "") if out2 else ""
    assert mark not in ctx2

    # S4 - recall hook end to end (the headline)
    assert any("zorblax" in n for n in _recall("configure the zorblax frobnicator settings", proj_a, "r1"))
    assert _recall("configure the zorblax frobnicator settings", proj_a, "r1") == []   # session dedup
    assert any("zorblax" in n for n in _recall("configure the zorblax frobnicator settings", proj_a, "r2"))
    assert _recall("i got again hits on my previous answer is that normal", proj_a, "j1") == []  # filler
    cc = _recall("widget frobnitz", proj_a, "c1")                                       # corpus-common
    assert any("frob" in n for n in cc)
    assert not any(n.startswith("w") and n[1:].isdigit() for n in cc)
    _mem(proj_a, "own-zorblax.md", "my own zorblax note here")
    assert not any("own-zorblax" in n for n in _recall("zorblax frobnicator", proj_a, "o1"))  # self excluded

    # S5 - filler classification flow (per-prompt queue -> dream classifier), all PER-PROJECT
    pend = sig.load_pending_keywords(proj_a)
    assert "zorblax" in pend or "frobnicator" in pend
    sig.add_filler_words(["wibble"], proj_a); sig.add_topical_words(["zorblax"], proj_a)
    sig.clear_pending_keywords(proj_a)
    assert sig.load_pending_keywords(proj_a) == frozenset()
    assert "wibble" not in gs.extract_keywords("wibble zorblax test", proj=proj_a)
    assert "zorblax" in gs.extract_keywords("wibble zorblax test", proj=proj_a)
    # wibble is filler ONLY for proj_a -> kept (not dropped) for proj_b and for baseline-only
    assert "wibble" in gs.extract_keywords("wibble zorblax test", proj=proj_b)   # not leaked to proj B
    assert "wibble" in gs.extract_keywords("wibble zorblax test")                # nor to baseline-only

    # S6 - gather_scan CLI (cross-tree candidate grep)
    _, out, _ = _cli(SK / "meta-collect-knowledge" / "gather_scan.py",
                     "--topic", "zorblax frobnicator", "--self", proj_a)
    assert "zorblax" in out and "CANDIDATES:" in out
    assert "projA" not in out                                                            # current excluded

    # S7 - dream cadence CLI (mode / done / due)
    dream = SK / "meta-dream-project" / "dream_state.py"
    _, out, _ = _cli(dream, "mode", proj_b)
    assert out == "propose"
    _cli(dream, "done", proj_b)
    _, out, _ = _cli(dream, "due", proj_b)
    assert out == "not-due"

    # S8 - reconcile a CURATED altitude (UUID-native: pointer block + central bodies)
    import memory_engine as ME
    import uuid_store as us
    ME.add_or_update_entry(proj_b, "Zorblax config", "set the zorblax flag before deploy",
                           body="Configure the zorblax frobnicator.", scope_default="projB notes")
    recon = SK / "meta-self-improve" / "reconcile_memory_index.py"
    # a fact whose central body was deleted is reported as an orphan pointer, never fabricated
    slug = ME.slugify("Zorblax config")
    us.body_path(proj_b, slug).unlink()
    rc, out, err = _cli(recon, proj_b)
    assert "orphan" in (out + err).lower() and slug in (out + err)
    ME.add_or_update_entry(proj_b, "Zorblax config", "set the zorblax flag before deploy",
                           body="Configure the zorblax frobnicator.")    # restore the body
    ME.add_or_update_entry(proj_b, "Bad ref", "see [[does-not-exist-anywhere]]", body="x")
    rc, out, err = _cli(recon, "--check", proj_b)                 # orphan [[ref]] is flagged
    assert rc != 0 or "does-not-exist-anywhere" in (out + err)

    # S9 - self-improve-gate (Stop-hook learning detection)
    tr = sandbox / "transcript.jsonl"
    tr.write_text(
        json.dumps({"type": "user", "message": {"content": "remember this: always use word-boundary matching"}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"content": "Noted."}}) + "\n", encoding="utf-8")
    _, out = _hook("self-improve-gate.py", {"transcript_path": str(tr), "cwd": proj_a})
    assert out and json.loads(out).get("decision") == "block"
    clean = sandbox / "clean.jsonl"
    clean.write_text(
        json.dumps({"type": "user", "message": {"content": "what time is it in tokyo"}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"content": "Around noon."}}) + "\n", encoding="utf-8")
    _, out = _hook("self-improve-gate.py", {"transcript_path": str(clean), "cwd": proj_a})
    assert out == ""

    # S9 - multi-tree end to end: two independent trees discovered, scaffolded, isolated
    work = sandbox / "work"
    for name, sub in (("marketing", "campaigns"), ("bakery", "recipes")):
        top = work / name
        proj = top / sub / "proj1"
        proj.mkdir(parents=True)
        (top / "CLAUDE.md").write_text(name + "\n", encoding="utf-8")
        (proj / "CLAUDE.md").write_text("p\n", encoding="utf-8")
    engine = HOOKS / "memory_engine.py"
    rc, out, err = _cli(engine, "ensure-all-trees", "--roots", str(work))
    assert rc == 0 and "DRY-RUN" in out and "2 tree(s)" in out
    assert not (work / "marketing" / "campaigns" / "CLAUDE.local.md").exists()   # dry-run wrote nothing
    rc, out, err = _cli(engine, "ensure-all-trees", "--roots", str(work), "--apply")
    assert rc == 0 and "APPLIED" in out
    assert (work / "marketing" / "campaigns" / "CLAUDE.local.md").is_file()      # gap rung filled
    assert (work / "bakery" / "recipes" / "CLAUDE.local.md").is_file()
    # capture lands in the OWN tree's store only
    rc, out, err = _cli(engine, "add", "--proj", str(work / "marketing" / "campaigns" / "proj1"),
                        "--title", "Brand voice", "--hook",
                        "When writing campaign copy, check the brand voice guide first.", "--body", "B")
    assert rc == 0 and out.strip() == "brand-voice"
    assert (work / "marketing" / ".claude-memory" / "facts" / "brand-voice.md").is_file()
    assert not (work / "bakery" / ".claude-memory" / "facts" / "brand-voice.md").exists()
    rc, out, err = _cli(engine, "tree-top", "--proj", str(work / "bakery" / "recipes" / "proj1"))
    assert rc == 0 and str(work / "bakery") in out
