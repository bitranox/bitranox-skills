"""Every hook that narrows its stdin event with hook_event treats a wrong-typed field as absent.

Each hook's real `main()` is driven with a real event read from stdin twice: once with one field
holding the wrong type, once with that field removed. The two runs must agree on the exit code and
on everything written, and neither may raise. Before the narrowing, a wrong-typed field reached the
hook's helpers as it arrived: a `tool_input` that is a string raised AttributeError at its first
`.get`, a list command raised inside the shell parser, and the hook's own top-level `except`
swallowed it, so the run looked clean while judging nothing.

stdin, HOME, CLAUDE_CONFIG_DIR and the working directory are the process edges the hooks read;
they are the only things substituted.
"""
import copy
import importlib.util
import io
import itertools
import json
import os
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent

# A command several guards and nudges react to, so most hooks have something to judge.
_COMMAND = ("nohup make test > g.log 2>&1 & sleep 30; pkill -f worker; "
            "find / -name x; pyright src; git rev-parse HEAD")

PRE_TOOL_USE_HOOKS = [
    "arbitrary-sleep-nudge.py", "block-cmd-if-chain.py", "block-commit-beside-sibling-gate.py",
    "block-env-dump.py", "block-git-semicolon-chain.py", "block-index-splice.py",
    "block-masked-gate-exit.py", "block-partial-typecheck.py", "block-unbounded-find.py",
    "block-write-after-sibling-cd.py", "bmk-gate-nudge.py", "gated-prep-nudge.py",
    "git-footgun-guard.py", "git-ls-files-tracking-nudge.py", "git-path-not-here-nudge.py",
    "git-revparse-nudge.py", "git-wrong-repo-nudge.py", "jig-repetition-nudge.py",
    "make-push-args-nudge.py", "missing-mechanism-nudge.py", "pct-path-nudge.py",
    "raw-char-arg-nudge.py", "recovery-retry-gate.py", "sed-line1-range-nudge.py",
    "sha-literal-nudge.py", "shell-prefix-selfref-guard.py", "stamp-clock-nudge.py",
    "tail-obsolete-count-nudge.py", "toolbox-nudge.py", "unbuffered-python-nudge.py",
    "venv-guard.py", "warn-inline-powershell.py", "warn-ps1-copy.py",
]

# (path into the event, a value of the wrong type for it)
PRE_TOOL_USE_FIELDS = [
    (("tool_name",), 7),
    (("tool_input",), "ls -la"),
    (("tool_input", "command"), ["make", "test"]),
    (("tool_input", "run_in_background"), "yes"),
    (("cwd",), 5),
    (("session_id",), ["s"]),
    (("transcript_path",), {"p": 1}),
]

_LOADED = {}
_RUNS = itertools.count()


def _load(name):
    """The hook module at `name`, loaded once under a private alias."""
    if name not in _LOADED:
        alias = "hook_entry_" + name[:-3].replace("-", "_")
        spec = importlib.util.spec_from_file_location(alias, HOOKS_DIR / name)
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
        _LOADED[name] = module
    return _LOADED[name]


def _pre_tool_use_event(tmp_path):
    return {"hook_event_name": "PreToolUse", "session_id": "entry-test", "cwd": str(tmp_path),
            "transcript_path": str(tmp_path / "absent.jsonl"), "tool_use_id": "toolu_entry",
            "tool_name": "Bash",
            "tool_input": {"command": _COMMAND, "run_in_background": True, "description": "d"}}


def _with(event, path, value):
    changed = copy.deepcopy(event)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return changed


def _without(event, path):
    changed = copy.deepcopy(event)
    target = changed
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return changed


def _drive(module, event, monkeypatch, capsys):
    """(exit code, stdout, stderr) of one `main()` run reading `event` on stdin.

    Each run gets a fresh, empty config dir: several hooks speak once per session and record that
    they did, so a second run sharing the first one's state would be silent for that reason alone.
    """
    home = Path(os.environ["HOME"]).parent / f"home{next(_RUNS)}"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / ".claude"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    code = module.main()
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    home = tmp_path / "home"
    work = tmp_path / "work"
    home.mkdir()
    work.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / ".claude"))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(work)
    return work


@pytest.mark.parametrize("path,wrong", PRE_TOOL_USE_FIELDS, ids=lambda v: str(v))
@pytest.mark.parametrize("name", PRE_TOOL_USE_HOOKS)
def test_a_wrong_typed_pre_tool_use_field_behaves_as_absent(name, path, wrong, isolated,
                                                            monkeypatch, capsys):
    module = _load(name)
    event = _pre_tool_use_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", PRE_TOOL_USE_HOOKS)
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_payload_that_is_not_an_object_is_ignored(name, payload, isolated, monkeypatch, capsys):
    assert _drive(_load(name), payload, monkeypatch, capsys) == (0, "", "")
