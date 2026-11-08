"""_claude_config: the jigs' copy of the plugin's config-dir rule, and the jigs that default to it.

Claude Code moves its whole config dir to CLAUDE_CONFIG_DIR when that is set. A jig that defaults
to `~/.claude/projects` then reads a corpus no session writes, so every default here must follow
the variable, and the copy must answer exactly as `hooks/claude_paths.config_dir()` does.
"""
import importlib.util
from pathlib import Path

import _claude_config
import corpus_prompts
import guard_replay
import instrument_share
import pytest
import transcript_index

_RULE_FILE = Path(__file__).resolve().parents[3] / "hooks" / "claude_paths.py"


def _plugin_rule():
    """The plugin's own rule, loaded by path: the jigs cannot import it, the test can."""
    spec = importlib.util.spec_from_file_location("_claude_paths_for_parity", _RULE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def moved(tmp_path, monkeypatch):
    home, arm = tmp_path / "home", tmp_path / "arm"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    return home, arm


@pytest.mark.parametrize("value", ["ARM", "", "   ", None])
def test_the_copy_answers_like_the_plugin_rule(moved, monkeypatch, value):
    home, arm = moved
    if value is None:
        monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    else:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm) if value == "ARM" else value)
    expected = arm if value == "ARM" else home / ".claude"
    assert _claude_config.config_dir() == _plugin_rule().config_dir() == expected
    assert _claude_config.projects_dir() == expected / "projects"


def test_every_corpus_default_follows_the_variable(moved, capsys):
    _, arm = moved
    projects = str(arm / "projects")
    assert corpus_prompts._parse([]).root == projects
    assert guard_replay._parse(["--module", "m.py"]).root == projects
    assert transcript_index.projects_root() == arm / "projects"
    assert transcript_index.db_path() == arm / "transcript-index.db"
    # instrument_share builds its parser inside main(): the refusal names the path it defaulted to.
    assert instrument_share.main([]) == 2
    captured = capsys.readouterr()
    assert projects in captured.out + captured.err
