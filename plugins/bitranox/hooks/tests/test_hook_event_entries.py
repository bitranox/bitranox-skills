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
from types import ModuleType
from typing import Any, TypeIs

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
    "block-pgrep-self-match.py", "block-sed-structured-files.py", "commit-tell-sweep.py",
    "enter-worktree-first-refusal.py", "git-commit-branch-guard.py", "retry-with-a-flag-nudge.py",
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
    "block-pgrep-self-match.py": ("Bash", "pgrep -f nginx"),
    "block-sed-structured-files.py": ("Bash", "sed -i 's/a/b/' config.json"),
    "commit-tell-sweep.py": ("Bash", 'git commit -m "Fix ' + chr(0x2014) + ' properly"'),
    "enter-worktree-first-refusal.py": ("EnterWorktree", "unused"),
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

_LOADED: dict[str, ModuleType] = {}
_RUNS = itertools.count()


def _load(name: str) -> ModuleType:
    """The hook module at `name`, loaded once under a private alias."""
    if name not in _LOADED:
        alias = "hook_entry_" + name[:-3].replace("-", "_")
        spec = importlib.util.spec_from_file_location(alias, HOOKS_DIR / name)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load the hook {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        spec.loader.exec_module(module)
        _LOADED[name] = module
    return _LOADED[name]


def _pre_tool_use_event(tmp_path: Path, name: str | None = None) -> dict[str, Any]:
    tool_name, command = FIRING.get(name or "", ("Bash", _COMMAND))
    return {"hook_event_name": "PreToolUse", "session_id": "entry-test", "cwd": str(tmp_path),
            "transcript_path": str(tmp_path / "absent.jsonl"), "tool_use_id": "toolu_entry",
            "tool_name": tool_name,
            "tool_input": {"command": command, "run_in_background": True, "description": "d"}}


def _with(event: dict[str, Any], path: tuple[str, ...], value: object) -> dict[str, Any]:
    changed = copy.deepcopy(event)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return changed


def _without(event: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    changed = copy.deepcopy(event)
    target = changed
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    return changed


def _fresh_home(monkeypatch: pytest.MonkeyPatch) -> Path:
    """A new, empty HOME, config dir and temp dir for the runs that follow; returns the HOME.

    Several hooks speak once per session and record that they did, so a run sharing an earlier
    run's state would be silent for that reason alone.
    """
    home = Path(os.environ["HOME"]).parent / f"home{next(_RUNS)}"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(home / ".claude"))
    # self-improve-gate keeps its per-project state under the temp dir
    monkeypatch.setattr(tempfile, "tempdir", str(home))
    return home


def _run(
    module: ModuleType,
    event: object,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    code = module.main()
    out, err = capsys.readouterr()
    return code, out, err


def _drive(
    module: ModuleType,
    event: object,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) of one `main()` run reading `event` on stdin, in a fresh home."""
    _fresh_home(monkeypatch)
    return _run(module, event, monkeypatch, capsys)


def _is_object(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict)


def _state(home: Path) -> dict[str, object]:
    """{relative path: content} of every file under `home`, the run's own home spelled <HOME>.

    A JSON object loses its `ts` key, the one value two runs never share.
    """
    files: dict[str, object] = {}
    for path in sorted(p for p in home.rglob("*") if p.is_file()):
        text = path.read_text(encoding="utf-8", errors="replace").replace(str(home), "<HOME>")
        try:
            value: object = json.loads(text)
        except ValueError:
            value = text
        if _is_object(value):
            value.pop("ts", None)
        files[path.relative_to(home).as_posix()] = value
    return files


def _drive_state(
    module: ModuleType,
    event: object,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str, str, dict[str, object]]:
    """(exit code, stdout, stderr, files written) of one run, for a hook whose effect is state."""
    home = _fresh_home(monkeypatch)
    return (*_run(module, event, monkeypatch, capsys), _state(home))


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
def test_a_wrong_typed_pre_tool_use_field_behaves_as_absent(
    name: str,
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load(name)
    event = _pre_tool_use_event(isolated, name)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", sorted(set(FIRING) | SPEAKS_ON_THE_COMMON_COMMAND))
def test_the_well_typed_event_makes_the_hook_speak(
    name: str,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The comparison above is only worth something where the full event gets an answer."""
    code, out, err = _drive(_load(name), _pre_tool_use_event(isolated, name), monkeypatch, capsys)
    assert code != 0 or out or err


@pytest.mark.parametrize("name", PRE_TOOL_USE_HOOKS)
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_payload_that_is_not_an_object_is_ignored(
    name: str,
    payload: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def _post_tool_use_event(work: Path) -> dict[str, Any]:
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
def test_a_wrong_typed_post_tool_use_field_behaves_as_absent(
    name: str,
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load(name)
    absent = _drive(module, _without(_post_tool_use_event(isolated), path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(_post_tool_use_event(isolated), path, wrong), monkeypatch,
                         capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", POST_TOOL_USE_HOOKS)
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_post_tool_use_payload_that_is_not_an_object_is_ignored(
    name: str,
    payload: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def _transcript(work: Path) -> Path:
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


def _stop_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "Stop", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(_transcript(work)), "stop_hook_active": False,
            "last_assistant_message": "Done: I chose the second option and pushed it."}


@pytest.mark.parametrize("path,wrong", STOP_FIELDS, ids=lambda v: str(v))
@pytest.mark.parametrize("name", STOP_HOOKS)
def test_a_wrong_typed_stop_field_behaves_as_absent(
    name: str,
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load(name)
    absent = _drive(module, _without(_stop_event(isolated), path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(_stop_event(isolated), path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


def test_an_active_stop_hook_flag_still_silences_the_stop_hooks(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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


def _user_prompt_submit_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "UserPromptSubmit", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(_transcript(work)),
            "prompt": "<task-notification><task-id>other</task-id><status>completed</status>"
                      "</task-notification>"}


@pytest.mark.parametrize("path,wrong", USER_PROMPT_SUBMIT_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_user_prompt_submit_field_behaves_as_absent(
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load("forgotten-backstop-nudge.py")
    event = _user_prompt_submit_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", STOP_HOOKS + ["forgotten-backstop-nudge.py"])
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_stop_or_prompt_payload_that_is_not_an_object_is_ignored(
    name: str,
    payload: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _drive(_load(name), payload, monkeypatch, capsys) == (0, "", "")


# --- Agent/Task dispatches (PreToolUse) ---

DISPATCH_HOOKS = [
    "subagent-backstop-nudge.py", "subagent-brief-fetch-nudge.py",
    "subagent-brief-pyright-nudge.py", "subagent-model-gate.py",
    "subagent-probe-capability-gate.py",
]

# The probe gate refuses a NAMED probe; every other dispatch hook has something to say about the
# common dispatch below (a named agent never told to SendMessage, a cross-repo read with no fetch,
# an unpinned pyright, a sonnet model).
DISPATCH_FIRING = {
    "subagent-probe-capability-gate.py": {"subagent_type": "bitranox:baseline-probe"},
}

DISPATCH_FIELDS = [
    (("tool_name",), ["Agent"]),
    (("tool_input",), "Review the diff"),
    (("tool_input", "prompt"), ["review"]),
    (("tool_input", "subagent_type"), 4),
    (("tool_input", "name"), {"n": 1}),
    (("tool_input", "model"), 0),
    (("tool_input", "effort"), True),
    (("tool_input", "description"), 2.5),
    (("session_id",), ["s"]),
    (("cwd",), 5),
]


def _dispatch_event(work: Path, name: str | None = None) -> dict[str, Any]:
    tool_input = {"description": "Review the release diff", "subagent_type": "general-purpose",
                  "name": "reviewer", "model": "sonnet", "effort": "high",
                  "prompt": "Across the templates, compare the bmk floor each pyproject.toml "
                            "carries. Then run `.venv/bin/pyright` and report."}
    tool_input.update(DISPATCH_FIRING.get(name or "", {}))
    return {"hook_event_name": "PreToolUse", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(work / "absent.jsonl"), "tool_use_id": "toolu_entry",
            "tool_name": "Agent", "tool_input": tool_input}


@pytest.mark.parametrize("path,wrong", DISPATCH_FIELDS, ids=lambda v: str(v))
@pytest.mark.parametrize("name", DISPATCH_HOOKS)
def test_a_wrong_typed_dispatch_field_behaves_as_absent(
    name: str,
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load(name)
    event = _dispatch_event(isolated, name)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", DISPATCH_HOOKS)
def test_the_well_typed_dispatch_makes_the_hook_speak(
    name: str,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, err = _drive(_load(name), _dispatch_event(isolated, name), monkeypatch, capsys)
    assert code != 0 or out or err


# --- PostToolUse: a Write that brings in a non-ASCII character ---

NON_ASCII_FIELDS = [
    (("tool_name",), 3),
    (("tool_input",), "x = 1"),
    (("tool_input", "file_path"), ["a.py"]),
    (("tool_input", "content"), {"c": 1}),
    (("tool_response",), "written"),
    (("tool_response", "originalFile"), 7),
]


def _non_ascii_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "PostToolUse", "session_id": "entry-test", "cwd": str(work),
            "tool_name": "Write",
            "tool_input": {"file_path": str(work / "mod.py"),
                           "content": "NAME = 'caf" + chr(0xE9) + "'\n"},
            "tool_response": {"type": "create", "originalFile": "NAME = 'x'\n"}}


@pytest.mark.parametrize("path,wrong", NON_ASCII_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_write_field_behaves_as_absent(
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load("non-ascii-introduced.py")
    event = _non_ascii_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


def test_the_well_typed_write_makes_the_non_ascii_hook_speak(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, _out, err = _drive(_load("non-ascii-introduced.py"), _non_ascii_event(isolated),
                             monkeypatch, capsys)
    assert code == 2 and "U+00E9" in err


def test_a_write_over_a_file_already_holding_the_character_is_quiet(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`originalFile` still reaches the hook: the character the file already had is not new."""
    event = _non_ascii_event(isolated)
    event["tool_response"]["originalFile"] = "NAME = 'caf" + chr(0xE9) + "s'\n"
    assert _drive(_load("non-ascii-introduced.py"), event, monkeypatch, capsys) == (0, "", "")


# --- PostToolUseFailure, then the PreToolUse retry it is compared with ---

FAILURE_FIELDS = [
    (("hook_event_name",), 1),
    (("tool_name",), ["Bash"]),
    (("tool_input",), "rsync -a src dst"),
    (("tool_input", "command"), ["rsync"]),
    (("is_interrupt",), "yes"),
    (("error",), 5),
    (("session_id",), 9),
]


def _failure_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "PostToolUseFailure", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(work / "absent.jsonl"), "tool_name": "Bash",
            "tool_input": {"command": "rsync -a src dst"}, "error": "boom", "is_interrupt": False}


def _retry_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "PreToolUse", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(work / "absent.jsonl"), "tool_name": "Bash",
            "tool_input": {"command": "rsync -a -z src dst"}}


def _after_failure(
    failure: dict[str, Any],
    work: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[tuple[int, str, str], tuple[int, str, str]]:
    """What the retry hook says about the retried command once `failure` has been recorded."""
    module = _load("retry-with-a-flag-nudge.py")
    _fresh_home(monkeypatch)
    recorded = _run(module, failure, monkeypatch, capsys)
    return recorded, _run(module, _retry_event(work), monkeypatch, capsys)


@pytest.mark.parametrize("path,wrong", FAILURE_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_failure_field_behaves_as_absent(
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    event = _failure_event(isolated)
    absent = _after_failure(_without(event, path), isolated, monkeypatch, capsys)
    wrong_typed = _after_failure(_with(event, path, wrong), isolated, monkeypatch, capsys)
    assert wrong_typed == absent


def test_a_recorded_failure_makes_the_retry_nudge_speak(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorded, retried = _after_failure(_failure_event(isolated), isolated, monkeypatch, capsys)
    assert recorded == (0, "", "") and retried[1]


def test_an_interrupt_is_still_not_recorded(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The one failure field whose value decides: True still means the user, not a failure."""
    event = _with(_failure_event(isolated), ("is_interrupt",), True)
    assert _after_failure(event, isolated, monkeypatch, capsys)[1] == (0, "", "")


# --- PostToolBatch ---

BATCH_FIELDS = [
    (("hook_event_name",), 1),
    (("tool_calls",), {"tool_name": "Edit"}),
    (("session_id",), 2),
    (("cwd",), ["w"]),
]


def _batch_event(work: Path) -> dict[str, Any]:
    failed_edit = {"tool_name": "Edit", "tool_use_id": "e1",
                   "tool_input": {"file_path": str(work / "CHANGELOG.md"), "old_string": "a",
                                  "new_string": "b"},
                   "tool_response": "<tool_use_error>File has not been read yet. Read it first "
                                    "before writing to it.</tool_use_error>"}
    commit = {"tool_name": "Bash", "tool_use_id": "b1",
              "tool_input": {"command": "git commit -q -F /tmp/msg.txt"},
              "tool_response": "abc1234 fix(x): y"}
    return {"hook_event_name": "PostToolBatch", "session_id": "entry-test", "cwd": str(work),
            "tool_calls": [failed_edit, commit]}


@pytest.mark.parametrize("path,wrong", BATCH_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_batch_field_behaves_as_absent(
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load("publish-after-failed-edit-note.py")
    event = _batch_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


def test_the_well_typed_batch_makes_the_note_speak(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _err = _drive(_load("publish-after-failed-edit-note.py"), _batch_event(isolated),
                             monkeypatch, capsys)
    assert code == 0 and "PostToolBatch" in out


# --- SubagentStart, PostCompact and the Stop half of the decision log ---

SUBAGENT_START_FIELDS = [
    (("agent_type",), ["general-purpose"]),
    (("agent_id",), 3),
    (("session_id",), 4),
    (("hook_event_name",), None),
]


def _subagent_start_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "SubagentStart", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(work / "absent.jsonl"), "agent_id": "a1",
            "agent_type": "general-purpose"}


@pytest.mark.parametrize("path,wrong", SUBAGENT_START_FIELDS, ids=lambda v: str(v))
def test_a_wrong_typed_subagent_start_field_behaves_as_absent(
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load("subagent-brief.py")
    event = _subagent_start_event(isolated)
    absent = _drive(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


def test_the_well_typed_subagent_start_is_briefed(
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, _err = _drive(_load("subagent-brief.py"), _subagent_start_event(isolated),
                             monkeypatch, capsys)
    assert code == 0 and "SubagentStart" in out


# These two hooks only record state, so the files they write are compared too.
STATE_HOOKS = {
    "post-compact-nudge.py": [
        (("cwd",), 5),
        (("session_id",), 3),
        (("transcript_path",), ["t"]),
        (("hook_event_name",), 2),
    ],
    "user-decision-log.py": STOP_FIELDS,
}


def _post_compact_event(work: Path) -> dict[str, Any]:
    return {"hook_event_name": "PostCompact", "session_id": "entry-test", "cwd": str(work),
            "transcript_path": str(_transcript(work)), "trigger": "auto"}


_STATE_EVENTS = {"post-compact-nudge.py": _post_compact_event, "user-decision-log.py": _stop_event}


@pytest.mark.parametrize("name,path,wrong",
                         [(name, path, wrong) for name, fields in STATE_HOOKS.items()
                          for path, wrong in fields], ids=lambda v: str(v))
def test_a_wrong_typed_field_of_a_state_hook_behaves_as_absent(
    name: str,
    path: tuple[str, ...],
    wrong: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load(name)
    event = _STATE_EVENTS[name](isolated)
    absent = _drive_state(module, _without(event, path), monkeypatch, capsys)
    wrong_typed = _drive_state(module, _with(event, path, wrong), monkeypatch, capsys)
    assert wrong_typed == absent


@pytest.mark.parametrize("name", sorted(STATE_HOOKS))
def test_the_well_typed_event_makes_the_state_hook_write(
    name: str,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    *_, files = _drive_state(_load(name), _STATE_EVENTS[name](isolated), monkeypatch, capsys)
    assert files


@pytest.mark.parametrize("name", DISPATCH_HOOKS + sorted(STATE_HOOKS) + [
    "non-ascii-introduced.py", "publish-after-failed-edit-note.py", "subagent-brief.py"])
@pytest.mark.parametrize("payload", [[], "text", 3, None])
def test_a_payload_of_the_other_events_that_is_not_an_object_is_ignored(
    name: str,
    payload: object,
    isolated: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _drive_state(_load(name), payload, monkeypatch, capsys)[:3] == (0, "", "")
