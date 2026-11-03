"""BITRANOX_MEMORY_WRITES=off: the store's write paths refuse with one line, the nudges stay quiet.

Covered here: the switch reading itself; the engine (its CLI write verbs, add_with_advice, the
library writers, upsert_entry and add_or_update_entry, the level writers); heal, which is a silent
no-op rather than a refusal because SessionStart calls it; the reconcile_memory_index and
migrate_memory skill scripts; the mod tools and the contribution queue; the capture hooks; and the
SessionStart nudges. Two writers are tested beside their own fixtures instead:
migrate_to_slug_store --apply in test_migrate_to_slug_store.py, and statusrot clear in the
meta-dream-tree skill's tests/test_statusrot_memory_writes.py.

Where a path writes when on, its OFF arm has a GREEN control (writes on) on the same input, in the
same test or the next one, so a test that passes because the path is broken for another reason
cannot pass both.
"""
import importlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import memory_engine as ME
import mod_bridge
import self_improve_audit
import self_improve_gate
import self_improve_signals as sig
import session_start
import subagent_capture


@pytest.mark.parametrize("value, expected", [
    ("off", True), ("OFF", True), (" off ", True),
    ("on", False), ("0", False), ("false", False), ("", False),
])
def test_memory_writes_off_reads_exactly_one_spelling(value, expected):
    assert sig.memory_writes_off({"BITRANOX_MEMORY_WRITES": value}) is expected


def test_memory_writes_off_unset_is_on():
    assert sig.memory_writes_off({}) is False


def test_refuse_raises_only_when_off(monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    sig.refuse_if_memory_writes_off()
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff) as exc:
        sig.refuse_if_memory_writes_off()
    assert "BITRANOX_MEMORY_WRITES=off" in str(exc.value)


FACT = {"title": "Probe fact", "hook": "When probing the switch, expect a refusal.",
        "body": "body", "type_": "feedback"}


def test_engine_add_refuses_when_off_and_writes_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        ME.add_with_advice(str(tmp_path), **FACT)
    assert not (tmp_path / "CLAUDE.local.md").exists(), "the refusal must come before any write"
    argv = ["add", "--proj", str(tmp_path), "--title", FACT["title"], "--hook", FACT["hook"],
            "--body", FACT["body"], "--type", "feedback"]
    assert ME.main(argv) == 2
    assert sig.MEMORY_WRITES_OFF_LINE in capsys.readouterr().out
    assert not (tmp_path / "CLAUDE.local.md").exists()
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    assert ME.main(argv) == 0, "control: the same add works with the switch unset"
    assert (tmp_path / "CLAUDE.local.md").exists()


@pytest.mark.parametrize("verb", sorted(ME.WRITE_VERBS))
def test_every_write_verb_is_refused_at_the_cli(verb, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert ME.main([verb]) == 2, "the refusal precedes argparse, so required arguments never matter"
    assert "! refused:" in capsys.readouterr().out


def test_heal_is_a_silent_no_op_when_off(tmp_path, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    report = ME.heal(str(tmp_path))
    assert report["skipped"] == sig.MEMORY_WRITES_OFF_LINE and report["healed"] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fn, args", [
    (ME.move_entry, ("a", "b", "slug")),
    (ME.relocate_entry, ("a", "b", "slug")),
    (ME.rename_entry, ("a", "slug", "slug2")),
    (ME.retitle_entry, ("a", "slug", "Title")),
    (ME.ensure_all_trees, ()),
])
def test_library_write_functions_raise_first(fn, args, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        fn(*args)


@pytest.mark.parametrize("fn", [ME.upsert_entry, ME.add_or_update_entry], ids=lambda f: f.__name__)
def test_single_entry_write_path_refuses_when_off_and_writes_when_on(fn, tmp_path, monkeypatch):
    """The two-function entry write path every skill script calls directly (reconcile, migrate):
    guarding only the CLI verbs and add_with_advice left these open."""
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        fn(str(tmp_path), **FACT)
    assert list(tmp_path.iterdir()) == [], "the refusal must come before any write"
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    fn(str(tmp_path), **FACT)
    assert (tmp_path / "CLAUDE.local.md").is_file(), "control: the same call writes with the switch unset"


# The other library writers a caller outside the CLI can reach: `_commit_store` is the pointer
# commit reconcile's archive uses directly; `ensure_level` and `scaffold` write level files with
# no entry. Each takes a level under tmp_path, so an unguarded arm writes there and is caught.
_LEVEL_WRITERS = [
    ("_commit_store", lambda level: ME._commit_store(level, "scope", [], {})),
    ("ensure_level", lambda level: ME.ensure_level(level, scope_default="scope")),
    ("scaffold", lambda level: ME.scaffold(level)),
]


@pytest.mark.parametrize("name, call", _LEVEL_WRITERS, ids=[n for n, _c in _LEVEL_WRITERS])
def test_level_writers_raise_first_when_off_and_write_when_on(name, call, tmp_path, monkeypatch):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    level = tmp_path / "level"
    level.mkdir()
    with pytest.raises(sig.MemoryWritesOff):
        call(str(level))
    assert list(tmp_path.rglob("*")) == [level], "%s wrote before refusing" % name
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    call(str(level))
    assert (level / "CLAUDE.local.md").is_file(), "control: %s writes with the switch unset" % name


# ---- end to end through the shipped skill scripts that call the engine library directly ---------
_SKILL_DIR = Path(ME.__file__).resolve().parents[1] / "skills" / "meta-self-improve"


def _tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _script(script, args, tmp_path, off):
    """Run a shipped script as a real process, HOME confined under tmp_path."""
    env = {k: v for k, v in os.environ.items() if k != "BITRANOX_MEMORY_WRITES"}
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONUTF8="1")
    if off:
        env["BITRANOX_MEMORY_WRITES"] = "off"
    return subprocess.run([sys.executable, str(_SKILL_DIR / script), *args], env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=120)


def _tree_with_fact(tmp_path, monkeypatch):
    """A one-level tree holding one fact, written by the engine with the switch unset."""
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "CLAUDE.md").write_text("# tree\n", encoding="utf-8")
    slug = ME.add_or_update_entry(str(tree), **FACT)
    return tree, slug


def _dangling_tree(tmp_path, monkeypatch):
    """The tree plus a second body no pointer names: what reconcile --rehome re-attaches through
    ME.add_or_update_entry."""
    tree, slug = _tree_with_fact(tmp_path, monkeypatch)
    facts = tree / ".claude-memory" / "facts"
    text = (facts / (slug + ".md")).read_text(encoding="utf-8")
    (facts / "feedback-dangling-probe.md").write_text(
        text.replace("name: %s" % slug, "name: feedback-dangling-probe"), encoding="utf-8")
    return tree


@pytest.mark.parametrize("off", [True, False], ids=["off", "on-control"])
def test_reconcile_rehome_end_to_end(off, tmp_path, monkeypatch):
    tree = _dangling_tree(tmp_path, monkeypatch)
    before = _tree_bytes(tree)
    r = _script("reconcile_memory_index.py", [str(tree), "--rehome"], tmp_path, off)
    if off:
        assert r.returncode == 2, r.stdout + r.stderr
        assert sig.MEMORY_WRITES_OFF_LINE in r.stderr and "Traceback" not in r.stderr
        assert _tree_bytes(tree) == before
    else:
        assert r.returncode == 0, r.stdout + r.stderr
        assert "re-homed: feedback-dangling-probe" in r.stdout
        assert _tree_bytes(tree) != before


@pytest.mark.parametrize("off", [True, False], ids=["off", "on-control"])
def test_reconcile_archive_end_to_end(off, tmp_path, monkeypatch):
    """archive moves the body BEFORE its pointer commit, so a guard on the commit alone would
    strand the body in .archive/ with its pointer still in place; it must refuse before the move."""
    tree, slug = _tree_with_fact(tmp_path, monkeypatch)
    before = _tree_bytes(tree)
    r = _script("reconcile_memory_index.py", [str(tree), "--archive", slug], tmp_path, off)
    body = tree / ".claude-memory" / "facts" / (slug + ".md")
    if off:
        assert r.returncode == 2, r.stdout + r.stderr
        assert sig.MEMORY_WRITES_OFF_LINE in r.stderr and "Traceback" not in r.stderr
        assert _tree_bytes(tree) == before
    else:
        assert r.returncode == 0, r.stdout + r.stderr
        assert not body.exists() and list((tree / ".claude-memory" / ".archive").glob("*.md"))


@pytest.mark.parametrize("off", [True, False], ids=["off", "on-control"])
def test_migrate_restore_end_to_end(off, tmp_path, monkeypatch):
    """--restore rewrites store paths from a manifest without the engine; under the switch it must
    refuse before touching them."""
    tree, slug = _tree_with_fact(tmp_path, monkeypatch)
    target = tree / "CLAUDE.local.md"
    backup = tmp_path / "backup"
    backup.mkdir()
    item = {"path": str(target), "kind": "file", "restore": True, "existed": False, "copy": None}
    (backup / "manifest.json").write_text(json.dumps({"version": 1, "items": [item]}), encoding="utf-8")
    before = _tree_bytes(tree)
    r = _script("migrate_memory.py", ["--restore", str(backup)], tmp_path, off)
    if off:
        assert r.returncode == 2, r.stdout + r.stderr
        assert sig.MEMORY_WRITES_OFF_LINE in r.stderr
        assert _tree_bytes(tree) == before
    else:
        assert r.returncode == 0, r.stdout + r.stderr
        assert not target.exists(), "control: the manifest's restore removes the file"


@pytest.mark.parametrize("off", [True, False], ids=["off", "on-control"])
def test_migrate_apply_end_to_end(off, tmp_path, monkeypatch, capsys):
    """--apply takes an out-of-tree backup, then places each native entry through
    ME.add_or_update_entry. Under the switch it refuses before the backup: nothing under HOME but
    the native store, the target level untouched. Run in-process, because the target sits under
    the temp dir, which migrate excludes unless its prefix list is emptied as its own suite does."""
    monkeypatch.syspath_prepend(str(_SKILL_DIR))
    migrate = importlib.import_module("migrate_memory")
    monkeypatch.setattr(migrate, "_EXCLUDE_PREFIXES", ())
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    slug = "-media-probe-moved-proj"
    native = home / ".claude" / "projects" / slug / "memory"
    native.mkdir(parents=True)
    (native / "MEMORY.md").write_text("# Memory index\n", encoding="utf-8")
    (native / "a.md").write_text("---\nname: project-a\ndescription: fact a\nmetadata:\n  type: project\n"
                                 "---\nBody A.\n", encoding="utf-8")
    target = tmp_path / "target"
    target.mkdir()
    home_before = sorted(home.rglob("*"))
    if off:
        monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    else:
        monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    rc = migrate.main(["--apply", "--slug=" + slug, "--redirect=%s=%s" % (slug, target)])
    if off:
        assert rc == 2
        assert sig.MEMORY_WRITES_OFF_LINE in capsys.readouterr().err
        assert list(target.iterdir()) == []
        assert sorted(home.rglob("*")) == home_before, "no backup, no receipt"
    else:
        assert rc == 0
        assert (target / "CLAUDE.local.md").is_file()


def _bridge(monkeypatch, capsys, tool, payload):
    request = json.dumps({"tool": tool, "input": payload}).encode("utf-8")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(request), encoding="utf-8"))
    rc = mod_bridge.main()
    return rc, json.loads(capsys.readouterr().out)


def test_mod_memory_add_refuses_when_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "memory_add",
                      {"level": str(tmp_path), "title": "T", "hook": "When x, do y.", "body": "b", "type": "feedback"})
    assert rc == 1 and out["ok"] is False and out["error"]["kind"] == "MemoryWritesOff"
    assert not (tmp_path / "CLAUDE.local.md").exists()


def test_mod_contrib_add_refuses_when_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "contrib_add", {"what": "w", "target": "skill:x", "why": "y"})
    assert rc == 1 and out["error"]["kind"] == "MemoryWritesOff"
    assert not list((tmp_path / ".claude").rglob("*.contrib.jsonl"))


def test_mod_contrib_add_queues_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    rc, out = _bridge(monkeypatch, capsys, "contrib_add", {"what": "w", "target": "skill:x", "why": "y"})
    assert rc == 0 and out["data"]["queued"] is True
    assert list((tmp_path / ".claude").rglob("*.contrib.jsonl"))


# ---- Task 7: the nudges and capture hooks stay quiet -------------------------------------------
# The transcript carries a signal for EACH capture hook, so the ON control proves every hook really
# prints or writes for it; without that, an OFF arm on a quiet transcript passes with no change.
#   gate:     the last user message is a strict correction -> a block decision on stdout
#   audit:    the first two messages are broad-but-not-strict candidates -> an audit file
#   subagent: an assistant self-admission in the agent transcript -> a buffered learning
_SIGNAL_TURNS = [
    ("user", "why did you skip the tests again?"),
    ("assistant", "let me reconsider the parser approach"),
    ("user", "No, that's wrong, from now on always use --tree"),
    ("assistant", "I was wrong - the real cause is the stale venv"),
]


def _event(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("".join(json.dumps({"type": role, "message": {"role": role, "content": text}}) + "\n"
                                  for role, text in _SIGNAL_TURNS), encoding="utf-8")
    return {"transcript_path": str(transcript), "cwd": str(tmp_path / "proj"), "session_id": "s1",
            "hook_event_name": "Stop", "agent_id": "a1", "agent_type": "general-purpose",
            "agent_transcript_path": str(transcript)}


def _run_hook(hook, tmp_path, monkeypatch):
    """Run `hook.main()` with HOME and the gate's tempdir state confined under `tmp_path`.

    Returns the dirs a hook may write to; both start empty."""
    home, state = tmp_path / "home", tmp_path / "state"
    home.mkdir()
    state.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(state))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_event(tmp_path))))
    assert hook.main() == 0
    return home, state


def _written(*dirs):
    return [p for d in dirs for p in d.rglob("*")]


CAPTURE_HOOKS = [self_improve_gate, self_improve_audit, subagent_capture]


@pytest.mark.parametrize("hook", CAPTURE_HOOKS, ids=lambda h: h.__name__)
def test_capture_hooks_are_silent_when_off(hook, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    home, state = _run_hook(hook, tmp_path, monkeypatch)
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    assert _written(home, state) == [], "no audit file, no state file"


def test_gate_blocks_when_on(tmp_path, monkeypatch, capsys):
    """Control for the gate's OFF arm: the same event with the switch unset blocks."""
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    _run_hook(self_improve_gate, tmp_path, monkeypatch)
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_audit_writes_its_report_when_on(tmp_path, monkeypatch):
    """Control for the audit's OFF arm: the same event with the switch unset writes the report."""
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    _run_hook(self_improve_audit, tmp_path, monkeypatch)
    assert sig.audit_file(str(tmp_path / "proj")).is_file()


def test_subagent_capture_buffers_when_on(tmp_path, monkeypatch):
    """Control for subagent-capture's OFF arm: the same event with the switch unset buffers it."""
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    _run_hook(subagent_capture, tmp_path, monkeypatch)
    assert sig.read_subagent_learnings("s1")


def _session_start_home(tmp_path, monkeypatch):
    """A HOME where the dream is due and an audit report is pending for `proj`."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    proj = str(tmp_path / "proj")
    mem = sig.memory_dir(proj)
    mem.mkdir(parents=True)
    (mem / "a.md").write_text("x", encoding="utf-8")       # memory exists, never dreamed -> due
    report = sig.audit_file(proj)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<SELF-IMPROVE-AUDIT>pending</SELF-IMPROVE-AUDIT>", encoding="utf-8")
    return proj, report


def test_session_start_dream_nudge_is_quiet_when_off(tmp_path, monkeypatch):
    proj, _report = _session_start_home(tmp_path, monkeypatch)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert session_start.dream_nudge(proj) is None


def test_session_start_audit_context_is_quiet_when_off(tmp_path, monkeypatch):
    proj, report = _session_start_home(tmp_path, monkeypatch)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert not session_start.audit_context(proj)
    assert report.is_file(), "the pending report is left in place, not consumed"


def test_session_start_dream_and_audit_fire_when_on(tmp_path, monkeypatch):
    """Control: the same HOME with the switch unset yields the nudge and the report."""
    proj, _report = _session_start_home(tmp_path, monkeypatch)
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    assert session_start.dream_nudge(proj)
    assert "pending" in session_start.audit_context(proj)


def test_session_start_heal_is_quiet_when_off_and_heals_when_on(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    off, on = tmp_path / "off", tmp_path / "on"
    off.mkdir()
    on.mkdir()
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    session_start._self_heal(str(off))
    assert list(off.iterdir()) == []
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    session_start._self_heal(str(on))
    assert list(on.iterdir()), "control: heal writes the level files with the switch unset"


def _newproject_inputs(tmp_path, monkeypatch):
    """A fresh project for which the new-project nudge would fire: the collect skill is installed
    under CLAUDE_PLUGIN_ROOT, HOME holds a sibling project's native memory to seed from, and `proj`
    itself has no facts and no seeded marker."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    plugin_root = tmp_path / "plugin"
    skill = plugin_root / "skills" / "meta-collect-knowledge" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: meta-collect-knowledge\n---\n\nB\n", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    other = sig.memory_dir(str(tmp_path / "other"))
    other.mkdir(parents=True)
    (other / "note.md").write_text("a useful note", encoding="utf-8")
    proj = tmp_path / "fresh"
    proj.mkdir()
    return str(proj)


def test_session_start_newproject_nudge_is_quiet_when_off(tmp_path, monkeypatch):
    proj = _newproject_inputs(tmp_path, monkeypatch)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert session_start.newproject_nudge(proj) is None
    assert not sig.seeded_file(proj).exists(), "the seeded marker is not written"


def test_session_start_newproject_nudge_fires_when_on(tmp_path, monkeypatch):
    """Control: the same inputs with the switch unset yield the nudge and mark the project seeded."""
    proj = _newproject_inputs(tmp_path, monkeypatch)
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    assert "BITRANOX-NEW-PROJECT" in session_start.newproject_nudge(proj)
    assert sig.seeded_file(proj).exists()
