"""contrib_queue add under BITRANOX_MEMORY_WRITES=off: one line, exit 2, nothing queued."""
import contrib_queue


def test_add_refuses_when_off_and_queues_when_on(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))      # the queue lives under ~/.claude; keep it here
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert contrib_queue.main(["add", "--what", "teach X", "--target", "skill:y", str(tmp_path)]) == 2
    assert "! refused:" in capsys.readouterr().err
    assert not list((tmp_path / ".claude").rglob("*.contrib.jsonl"))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES")
    assert contrib_queue.main(["add", "--what", "teach X", "--target", "skill:y", str(tmp_path)]) == 0
    assert len(list((tmp_path / ".claude").rglob("*.contrib.jsonl"))) == 1
