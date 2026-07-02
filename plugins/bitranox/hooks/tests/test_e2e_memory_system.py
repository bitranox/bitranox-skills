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
    g = sig.global_rules_dir(); g.mkdir(parents=True, exist_ok=True)
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

    # S8 - reconcile a CURATED .claude-bx-selflearning store (backfill from facts/ + reference --check)
    import memory_engine as ME
    ME.add_or_update_entry(proj_b, "Zorblax config", "set the zorblax flag before deploy",
                           body="Configure the zorblax frobnicator.", scope_default="projB notes")
    cur_b = sig.claude_memory_dir(proj_b)
    (cur_b / "facts").mkdir(parents=True, exist_ok=True)
    (cur_b / "facts" / "extra.md").write_text(
        "---\nname: extra\ndescription: an extra widget note\n---\nbody", encoding="utf-8")
    recon = SK / "meta-self-improve" / "reconcile_memory_index.py"
    _cli(recon, str(cur_b))                                         # backfills the orphan facts file
    mindex = cur_b / "memory.md"
    assert mindex.is_file() and "extra" in mindex.read_text(encoding="utf-8")
    ME.add_or_update_entry(proj_b, "Bad ref", "see [[does-not-exist-anywhere]]", body="x")
    rc, out, err = _cli(recon, "--check", str(cur_b))              # orphan [[ref]] is flagged
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
