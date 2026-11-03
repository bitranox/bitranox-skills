"""factedit apply under BITRANOX_MEMORY_WRITES=off refuses before it stages a file."""
import json

import factedit
from test_factedit import make_engine_dir, make_tree, run_cli


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
