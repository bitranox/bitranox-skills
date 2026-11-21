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
import tempfile
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

# A call each of these hooks reacts to (refuses or advises), from its own tests, so its
# wrong-typed runs are compared against a run that has something to say. The other hooks react to
# `_COMMAND`, or to nothing a stateless event can show (a transcript, a recorded state).
FIRING = {
    "block-cmd-if-chain.py": ("PowerShell", 'ssh win "if exist x del x & echo'),
    "block-env-dump.py": ("Bash", "env >&2"),
    "block-git-semicolon-chain.py": ("Bash", "git commit -m x\ngit push"),
    "block-index-splice.py": ("Bash", "python3 - <<'PY'\ns = p.read_text()\n"
                              "a = s.index('<' * 7 + ' ours\\n')\n"
                              "b = s.index('>>>>>>> theirs\\n') + len('>>>>>>> theirs\\n')\n"
                              "p.write_text(s[:a] + KEEP + s[b:])\nPY\n"),
    "block-write-after-sibling-cd.py": ("Bash", "cd /opt && lane1 & ./lane2 & wait"),
    "bmk-gate-nudge.py": ("Bash", "bmk test"),
    "gated-prep-nudge.py": ("Bash", "git pull && git push"),
    "git-footgun-guard.py": ("Bash", "git rev-parse --short A B"),
    "git-ls-files-tracking-nudge.py": ("Bash", "git ls-files a.md && exit 0"),
    "make-push-args-nudge.py": ("Bash", "make push x\\|y"),
    "missing-mechanism-nudge.py": ("Bash", 'memory_engine.py add --hook "There is no caller for this path."'),
    "pct-path-nudge.py": ("Bash", "pct exec 101 -- env PATH=%s uv"),
    "sed-line1-range-nudge.py": ("Bash", "sed 1,/^---$/d f.md"),
    "sha-literal-nudge.py": ("Bash", 'gh run list --commit "fb3330b${SHA:7}"'),
    "shell-prefix-selfref-guard.py": ("Bash", 'X="a b" cmd "$X"'),
    "tail-obsolete-count-nudge.py": ("Bash", "tail +2 a b"),
    "unbuffered-python-nudge.py": ("Bash", "ssh host python3 probe.py"),
    "warn-inline-powershell.py": ("Bash", "ssh host 'powershell -Command x'"),
    "warn-ps1-copy.py": ("Bash", "scp /tmp/x.ps1 winhost:/tmp/"),
}
SPEAKS_ON_THE_COMMON_COMMAND = {"arbitrary-sleep-nudge.py", "block-masked-gate-exit.py",
                                "block-unbounded-find.py", "git-revparse-nudge.py",
                                "toolbox-nudge.py"}

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


def _pre_tool_use_event(tmp_path, name=None):
    tool_name, command = FIRING.get(name, ("Bash", _COMMAND))
    return {"hook_event_name": "PreToolUse", "session_id": "entry-test", "cwd": str(tmp_path),
            "transcript_path": str(tmp_path / "absent.jsonl"), "tool_use_id": "toolu_entry",
            "tool_name": tool_name,
            "tool_input": {"command": command, "run_in_background": True, "description": "d"}}


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
    # self-improve-gate keeps its per-project state under the temp dir
    monkeypatch.setattr(tempfile, "tempdir", str(home))
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
    event = _pre_tool_use_event(isolated, name)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", sorted(set(FIRING) | SPEAKS_ON_THE_COMMON_COMMAND))
def test_the_well_typed_event_makes_the_hook_speak(name, isolated, monkeypatch, capsys):
    """The comparison above is only worth something where the full event gets an answer."""
    code, out, err = _drive(_load(name), _pre_tool_use_event(isolated, name), monkeypatch, capsys)
    assert code != 0 or out or err


@pytest.mark.parametrize("name", PRE_TOOL_USE_HOOKS)
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_payload_that_is_not_an_object_is_ignored(name, payload, isolated, monkeypatch, capsys):
    assert _drive(_load(name), payload, monkeypatch, capsys) == (0, "", "")


POST_TOOL_USE_HOOKS = [
    "ci-watch-nudge.py", "decision-claim-guard.py", "grep-ignored-empty-nudge.py",
    "reformat-md-tables.py", "tell-sweep.py", "touched-paths.py", "validate-structured-files.py",
]

POST_TOOL_USE_FIELDS = PRE_TOOL_USE_FIELDS + [
    (("hook_event_name",), 1),
    (("tool_input", "file_path"), 9),
    (("tool_response",), ["out"]),
    (("tool_response", "stdout"), 0),
    (("tool_response", "interrupted"), "no"),
]


def _post_tool_use_event(work):
    # A markdown file holding a typographic tell and a misaligned table, so the file hooks judge.
    doc = work / "OPEN-WORK.md"
    doc.write_text("# Notes " + chr(0x2014) + " x\n\n|a|b|\n|-|-|\n|long cell|c|\n", encoding="utf-8")
    event = _pre_tool_use_event(work)
    event["hook_event_name"] = "PostToolUse"
    event["tool_name"] = "Bash"
    event["tool_input"]["command"] = "grep -r needle . ; git push"
    event["tool_input"]["run_in_background"] = False
    event["tool_input"]["file_path"] = str(doc)
    event["tool_response"] = {"stdout": "", "stderr": "", "interrupted": False}
    return event


@pytest.mark.parametrize("path,wrong", POST_TOOL_USE_FIELDS, ids=lambda v: str(v))
@pytest.mark.parametrize("name", POST_TOOL_USE_HOOKS)
def test_a_wrong_typed_post_tool_use_field_behaves_as_absent(name, path, wrong, isolated,
                                                             monkeypatch, capsys):
    module = _load(name)
    absent = _drive(module, _without(_post_tool_use_event(isolated), path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(_post_tool_use_event(isolated), path, wrong), monkeypatch,
                         capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", POST_TOOL_USE_HOOKS)
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_post_tool_use_payload_that_is_not_an_object_is_ignored(name, payload, isolated,
                                                                  monkeypatch, capsys):
    assert _drive(_load(name), payload, monkeypatch, capsys) == (0, "", "")


STOP_HOOKS = ["ci-watch-gate.py", "decision-review-nudge.py", "self-improve-gate.py"]

STOP_FIELDS = [
    (("stop_hook_active",), "false"),
    (("last_assistant_message",), ["Done."]),
    (("session_id",), 3),
    (("transcript_path",), ["t"]),
    (("cwd",), {"d": 1}),
    (("hook_event_name",), 2),
]


def _transcript(work):
    records = [
        {"type": "user", "origin": {"kind": "human"},
         "message": {"role": "user", "content": "From now on always run the gate before a push, "
                                                "remember this. Which decisions are shaky?"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_bg", "name": "Bash",
             "input": {"command": "sleep 100", "run_in_background": True}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Done: I chose the second option and pushed it."}]}},
    ]
    path = work / "session.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def _stop_event(work):
    return {"hook_event_name": "Stop", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(_transcript(work)), "stop_hook_active": False,
            "last_assistant_message": "Done: I chose the second option and pushed it."}


@pytest.mark.parametrize("path,wrong", STOP_FIELDS, ids=lambda v: str(v))
@pytest.mark.parametrize("name", STOP_HOOKS)
def test_a_wrong_typed_stop_field_behaves_as_absent(name, path, wrong, isolated, monkeypatch,
                                                    capsys):
    module = _load(name)
    absent = _drive(module, _without(_stop_event(isolated), path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(_stop_event(isolated), path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


def test_an_active_stop_hook_flag_still_silences_the_stop_hooks(isolated, monkeypatch, capsys):
    """The one Stop field whose value, not presence, decides: True still means stand down."""
    for name in STOP_HOOKS:
        event = _with(_stop_event(isolated), ("stop_hook_active",), True)
        assert _drive(_load(name), event, monkeypatch, capsys) == (0, "", "")


USER_PROMPT_SUBMIT_FIELDS = [
    (("prompt",), ["<task-notification>"]),
    (("session_id",), 3),
    (("transcript_path",), 1.5),
    (("cwd",), None),
]


def _user_prompt_submit_event(work):
    return {"hook_event_name": "UserPromptSubmit", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(_transcript(work)),
            "prompt": "<task-notification><task-id>other</task-id><status>completed</status>"
                      "</task-notification>"}


@pytest.mark.parametrize("path,wrong", USER_PROMPT_SUBMIT_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_user_prompt_submit_field_behaves_as_absent(path, wrong, isolated,
                                                                  monkeypatch, capsys):
    module = _load("forgotten-backstop-nudge.py")
    event = _user_prompt_submit_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", STOP_HOOKS + ["forgotten-backstop-nudge.py"])
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_stop_or_prompt_payload_that_is_not_an_object_is_ignored(name, payload, isolated,
                                                                   monkeypatch, capsys):
    assert _drive(_load(name), payload, monkeypatch, capsys) == (0, "", "")
