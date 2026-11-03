"""_ablib: the shared helpers every abtest script uses."""
import json
import os
import sys
from pathlib import PurePosixPath

import _ablib as L
import pytest


def test_envelope_shape():
    d = json.loads(L.envelope("x", {"a": 1}, ok=False, skipped=["s"]))
    assert d == {"ok": False, "command": "x", "data": {"a": 1}, "skipped": ["s"]}


def test_envelope_defaults_to_ok_and_an_empty_skipped_list():
    assert json.loads(L.envelope("y", None)) == {"ok": True, "command": "y", "data": None, "skipped": []}


def test_run_never_raises_on_nonzero(tmp_path):
    # sys.executable rather than `sh -c`: the pure helpers run on every CI cell, Windows included.
    script = "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"
    proc = L.run([sys.executable, "-c", script], cwd=tmp_path)
    assert (proc.returncode, proc.stdout.strip(), proc.stderr.strip()) == (3, "out", "err")


def test_git_strips_inherited_git_vars(scratch_repo, monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/nonexistent-git-dir")
    expected = (scratch_repo / ".base").read_text(encoding="utf-8")
    assert L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip() == expected


def test_tree_hashes_skip_tests_caches_and_pyc(tmp_path):
    (tmp_path / "SKILL.md").write_text("a", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("b", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"c")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "s.py").write_text("d", encoding="utf-8")
    (tmp_path / "scripts" / "stray.pyc").write_bytes(b"e")
    (tmp_path / ".skillwriter").mkdir()
    (tmp_path / ".skillwriter" / "checklist.md").write_text("f", encoding="utf-8")
    assert sorted(L.tree_hashes(tmp_path)) == ["SKILL.md", "scripts/s.py"]
    assert L.tree_hashes(tmp_path)["SKILL.md"] == L.sha256_file(tmp_path / "SKILL.md")


def test_sha256_file_is_the_hex_digest_of_the_bytes(tmp_path):
    p = tmp_path / "f"
    p.write_bytes(b"abc")
    assert L.sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_rotated_schedule_rotates_the_start():
    assert L.rotated_schedule(["C", "V1", "V2"], 3) == [["C", "V1", "V2"], ["V1", "V2", "C"], ["V2", "C", "V1"]]
    with pytest.raises(ValueError):
        L.rotated_schedule([], 1)


def test_median_even_and_odd():
    assert L.median([3.0, 1.0, 2.0]) == 2.0
    assert L.median([4.0, 1.0, 3.0, 2.0]) == 2.5
    with pytest.raises(ValueError):
        L.median([])


def test_dashkey_replaces_every_non_alphanumeric():
    # A fixed POSIX path, so the expectation is the same string on every platform.
    assert L.dashkey(PurePosixPath("/srv/x/a.b_c d")) == "-srv-x-a-b-c-d"


def test_utc_now_is_an_iso_utc_second():
    stamp = L.utc_now()
    assert len(stamp) == 20 and stamp[10] == "T" and stamp.endswith("Z")


def test_jsonl_round_trip(tmp_path):
    p = tmp_path / "j.jsonl"
    L.append_jsonl(p, {"step": "a"})
    L.append_jsonl(p, {"step": "b"})
    assert L.read_jsonl(p) == [{"step": "a"}, {"step": "b"}]
    assert L.read_jsonl(tmp_path / "missing.jsonl") == []


def test_fake_claude_answers_version_and_install(fake_claude_path, skills_repo, tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    env = {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}", "CLAUDE_CONFIG_DIR": str(cfg)}
    assert L.run(["claude", "--version"], env=env).stdout.startswith("9.9.9")
    assert L.run(["claude", "plugin", "marketplace", "add", str(skills_repo), "--json"], env=env).returncode == 0
    reg = json.loads((cfg / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
    assert (reg["plugins"]["bitranox@bitranox-skills"][0]["installPath"]).endswith("0.0.1-fixture")


def test_fake_claude_replays_the_stream_and_commits_in_its_cwd(fake_claude_path, scratch_repo, tmp_path):
    stream = scratch_repo.parent / "stream-in.jsonl"
    stream.write_text('{"type":"system","subtype":"init"}\n', encoding="utf-8")
    env = dict(os.environ, PATH=f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}",
               CLAUDE_CONFIG_DIR=str(tmp_path), FAKE_CLAUDE_STREAM=str(stream))
    proc = L.run(["claude", "-p", "do the task"], cwd=scratch_repo, env=env)
    assert (proc.returncode, proc.stdout) == (0, '{"type":"system","subtype":"init"}\n')
    base = (scratch_repo / ".base").read_text(encoding="utf-8")
    assert L.git(scratch_repo, "rev-list", "--count", f"{base}..HEAD").stdout.strip() == "1"


def test_skills_repo_commits_the_hook_under_its_real_name(skills_repo):
    tracked = L.git(skills_repo, "ls-files").stdout.split()
    assert "hooks/self_improve_signals.py" in tracked
    assert not [p for p in tracked if p.endswith(".fixture")]
    hook = skills_repo / "hooks" / "self_improve_signals.py"
    assert "BITRANOX_MEMORY_WRITES" in hook.read_text(encoding="utf-8")
