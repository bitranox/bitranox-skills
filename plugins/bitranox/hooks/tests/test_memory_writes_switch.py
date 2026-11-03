"""BITRANOX_MEMORY_WRITES=off: every write path refuses with one line, every nudge stays quiet.

One test per path. Each pair has a GREEN control (writes on) beside the RED arm (writes off), so a
test that passes because the path is broken for another reason cannot pass both.
"""
import io
import json
import sys

import pytest

import memory_engine as ME
import mod_bridge
import self_improve_audit
import self_improve_gate
import self_improve_signals as sig
import session_start
import subagent_capture

OFF = {"BITRANOX_MEMORY_WRITES": "off"}


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


FACT = dict(title="Probe fact", hook="When probing the switch, expect a refusal.", body="body", type_="feedback")


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
