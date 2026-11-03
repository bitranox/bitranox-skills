"""factedit apply under BITRANOX_MEMORY_WRITES=off refuses before it stages a file."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import factedit
import pytest
from test_factedit import make_engine_dir, make_tree, run_cli, sys_tmp

SKILL_DIR = Path(factedit.__file__).resolve().parent


def test_apply_refuses_before_staging(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    body = tmp_path / "body.md"
    body.write_text("new body\n", encoding="utf-8")
    stage = tmp_path / "stage"
    rc = factedit.main(["apply", "--slug", "no-such-fact", "--body-file", str(body),
                        "--stage-dir", str(stage), "--from", str(tmp_path)])
    assert rc == 2
    assert "BITRANOX_MEMORY_WRITES=off" in capsys.readouterr().err
    assert not stage.exists(), "the refusal must precede the staging copy"


def _dry_run_args(tmp_path, eng, level, stage):
    """A dry-run apply on a REAL fact: without the switch it stages files, so a missing stage
    dir under the switch is the refusal's doing, not an earlier lookup failure."""
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    return ["apply", "--engine", str(eng), "--slug", "feedback-demo", "--from", str(level),
            "--hook-file", str(hookfile), "--stage-dir", str(stage), "--dry-run"]


def test_without_the_switch_the_same_apply_stages_its_files(tmp_path, monkeypatch):
    # The control for the next test: it proves this argv reaches the staging copy at all.
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    eng, level, stage = make_engine_dir(tmp_path), make_tree(tmp_path), tmp_path / "stage"
    r = run_cli(_dry_run_args(tmp_path, eng, level, stage), tmp_path)
    assert r.returncode == 0, r.stderr
    assert (stage / "feedback-demo.hook.txt").is_file()


def test_the_script_refuses_a_real_fact_before_staging_it(tmp_path, monkeypatch):
    # Run as a real process, so the hooks-dir import works without tests/conftest.py's sys.path.
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    eng, level, stage = make_engine_dir(tmp_path), make_tree(tmp_path), tmp_path / "stage"
    r = run_cli(_dry_run_args(tmp_path, eng, level, stage) + ["--json"], tmp_path)
    assert r.returncode == 2
    envelope = json.loads(r.stdout)
    assert envelope["ok"] is False and "BITRANOX_MEMORY_WRITES=off" in envelope["error"]
    assert not stage.exists()
    assert not (eng.parent / "memory_engine.py.called").exists()


def test_a_batch_apply_refuses_before_reading_its_entries(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    batch = tmp_path / "batch.jsonl"
    batch.write_text(json.dumps({"slug": "feedback-demo", "body_file": "b.md"}) + "\n",
                     encoding="utf-8")
    rc = factedit.main(["apply", "--batch", str(batch), "--from", str(make_tree(tmp_path))])
    assert rc == 2
    assert "BITRANOX_MEMORY_WRITES=off" in capsys.readouterr().err


def test_a_direct_batch_apply_refuses_before_it_stages_anything(tmp_path, monkeypatch):
    # cmd_apply's own guard runs first through main(), so only a DIRECT call reaches the batch
    # guard alone. The batch is valid and a dry run, so without that guard it would stage and
    # return 0: the refusal below can only come from the guard itself.
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    eng, level, stage = make_engine_dir(tmp_path), make_tree(tmp_path), tmp_path / "stage"
    body = tmp_path / "b.md"
    body.write_text("A new body.\n", encoding="utf-8")
    batch = tmp_path / "batch.jsonl"
    batch.write_text(json.dumps({"slug": "feedback-demo", "body_file": str(body)}) + "\n",
                     encoding="utf-8")
    args = factedit.build_parser().parse_args(
        ["apply", "--engine", str(eng), "--from", str(level), "--batch", str(batch),
         "--dry-run", "--stage-dir", str(stage)])
    rules = factedit.load_rules(eng)
    with pytest.raises(factedit.BadInput, match="BITRANOX_MEMORY_WRITES=off"):
        factedit.cmd_apply_batch(args, rules)
    assert not stage.exists()


def _outside_copy(tmp_path: Path) -> Path:
    """factedit.py and its sibling tree_support.py copied OUTSIDE the plugin, the documented mode
    where the engine comes from --engine, $BITRANOX_MEMORY_ENGINE or the cache, never the
    hooks dir beside it - which a copy does not have."""
    d = tmp_path / "outside"
    d.mkdir()
    for name in ("factedit.py", "tree_support.py"):
        shutil.copy2(SKILL_DIR / name, d / name)
    assert not (d.parents[1] / "hooks").exists(), "the copy must have no hooks dir to fall back on"
    return d / "factedit.py"


def _run_isolated(script: Path, args, tmp_path: Path, **extra_env):
    t = str(sys_tmp(tmp_path))
    env = {k: v for k, v in os.environ.items()
           if k not in ("BITRANOX_MEMORY_ENGINE", "BITRANOX_MEMORY_WRITES", "PYTHONPATH")}
    env.update(TMPDIR=t, TEMP=t, TMP=t, **extra_env)
    return subprocess.run([sys.executable, "-I", str(script)] + args, capture_output=True,
                          text=True, encoding="utf-8", check=False, env=env, cwd=str(tmp_path))


def test_a_copy_outside_the_plugin_still_runs_a_read_only_verb(tmp_path):
    r = _run_isolated(_outside_copy(tmp_path), ["show", "--help"], tmp_path)
    assert r.returncode == 0, r.stderr


def test_a_copy_outside_the_plugin_honours_the_switch_through_its_engine(tmp_path):
    script = _outside_copy(tmp_path)
    eng, level, stage = make_engine_dir(tmp_path), make_tree(tmp_path), tmp_path / "stage"
    r = _run_isolated(script, _dry_run_args(tmp_path, eng, level, stage), tmp_path,
                      BITRANOX_MEMORY_WRITES="off")
    assert r.returncode == 2, r.stderr
    assert "BITRANOX_MEMORY_WRITES=off" in r.stderr
    assert not stage.exists()
    assert not (eng.parent / "memory_engine.py.called").exists()
