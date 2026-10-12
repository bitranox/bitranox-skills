"""Tests for user-decision-log.py (PostToolUse AskUserQuestion: log every answered question).

Driven end to end: real git repositories in tmp_path, the hook run as a subprocess exactly as
Claude Code runs it, and git itself asked whether the log is ignored. The event shape is the one
a probe recorded on interactive CLI 2.1.296: tool_response carries the questions (label and
description per option), `answers` mapping each question to the chosen label, and `annotations`.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import self_improve_signals as sig
import user_decision_log as U

_HOOK = Path(__file__).resolve().parent.parent / "user-decision-log.py"

_QUESTION = {
    "question": "Where should the logger write?",
    "header": "Logger file",
    "multiSelect": False,
    "options": [
        {"label": "Own JSONL file (Recommended)", "description": "One JSON line per answer."},
        {"label": "Append to review log", "description": "Markdown under the user heading."},
    ],
}


def _event(cwd, *, answers=None, annotations=None, questions=None, tool="AskUserQuestion"):
    questions = questions if questions is not None else [_QUESTION]
    body = {
        "questions": questions,
        "answers": answers if answers is not None else {_QUESTION["question"]: _QUESTION["options"][0]["label"]},
        "annotations": annotations if annotations is not None else {},
    }
    return {
        "hook_event_name": "PostToolUse", "tool_name": tool, "session_id": "sess-42",
        "cwd": str(cwd), "tool_input": body, "tool_response": body,
    }


def _run(event, home):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    stdin = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=stdin, capture_output=True, text=True,
        encoding="utf-8", check=False, env=env,
    )


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    assert _git(root, "init", "-q", "-b", "main").returncode == 0
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "T")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "README.md")
    assert _git(root, "commit", "-q", "-m", "init").returncode == 0
    return root


def _records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_an_answered_question_is_appended_verbatim_at_the_repo_root(repo, tmp_path):
    sub = repo / "src"
    sub.mkdir()
    r = _run(_event(sub), tmp_path / "home")
    assert r.returncode == 0 and r.stdout.strip() == ""
    [rec] = _records(repo / U.LOG_NAME)
    assert rec["question"] == _QUESTION["question"]
    assert rec["header"] == "Logger file"
    assert rec["options"] == _QUESTION["options"]
    assert rec["chosen"] == "Own JSONL file (Recommended)"
    assert rec["chosen_options"] == [_QUESTION["options"][0]]
    assert rec["session_id"] == "sess-42"
    assert rec["ts"].endswith("Z") or "+" in rec["ts"]


def test_the_log_is_ignored_through_the_exclude_file_and_never_shows_in_status(repo, tmp_path):
    _run(_event(repo), tmp_path / "home")
    assert (repo / U.LOG_NAME).is_file()
    assert _git(repo, "check-ignore", "-q", U.LOG_NAME).returncode == 0
    assert _git(repo, "status", "--porcelain").stdout.strip() == ""
    assert not (repo / ".gitignore").exists()


def test_the_log_stays_ignored_even_when_track_private_is_set(repo, tmp_path):
    """Must NOT make the log committable: track_private is about the memory store, not this log."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps({"track_private": True}),
                                                           encoding="utf-8")
    _run(_event(repo), home)
    assert _git(repo, "check-ignore", "-q", U.LOG_NAME).returncode == 0


def test_a_second_answer_appends_and_the_exclude_line_is_written_once(repo, tmp_path):
    _run(_event(repo), tmp_path / "home")
    _run(_event(repo, answers={_QUESTION["question"]: "Append to review log"}), tmp_path / "home")
    assert [r["chosen"] for r in _records(repo / U.LOG_NAME)] == [
        "Own JSONL file (Recommended)", "Append to review log"]
    exclude = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").stdout.strip())
    assert exclude.read_text(encoding="utf-8").count(U.LOG_NAME) == 1


def test_an_already_ignored_name_adds_nothing_to_the_exclude_file(repo, tmp_path):
    (repo / ".gitignore").write_text(f"{U.LOG_NAME}\n", encoding="utf-8")
    exclude = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude").stdout.strip())
    before = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    _run(_event(repo), tmp_path / "home")
    after = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    assert after == before


def test_a_linked_worktree_logs_to_the_main_checkout_so_removal_keeps_it(repo, tmp_path):
    wt = tmp_path / "wt"
    assert _git(repo, "worktree", "add", "-q", str(wt), "-b", "topic").returncode == 0
    _run(_event(wt), tmp_path / "home")
    assert (repo / U.LOG_NAME).is_file()
    assert not (wt / U.LOG_NAME).exists()
    assert _git(wt, "status", "--porcelain").stdout.strip() == ""


def test_outside_a_repo_it_falls_back_to_the_audit_dir(tmp_path):
    home = tmp_path / "home"
    plain = tmp_path / "plain"
    plain.mkdir()
    r = _run(_event(plain), home)
    assert r.returncode == 0
    target = home / ".claude" / "self-improve-audit" / (sig.project_slug(str(plain)) + "." + U.LOG_NAME)
    assert [rec["chosen"] for rec in _records(target)] == ["Own JSONL file (Recommended)"]
    assert not (plain / U.LOG_NAME).exists()


def test_notes_and_a_free_text_answer_are_kept(repo, tmp_path):
    annotations = {_QUESTION["question"]: {"notes": "only for public repos"}}
    _run(_event(repo, answers={_QUESTION["question"]: "something else entirely"},
                annotations=annotations), tmp_path / "home")
    [rec] = _records(repo / U.LOG_NAME)
    assert rec["chosen"] == "something else entirely"
    assert rec["chosen_options"] == []
    assert rec["annotation"] == {"notes": "only for public repos"}


def test_a_multi_select_answer_maps_every_chosen_label(repo, tmp_path):
    q = {**_QUESTION, "multiSelect": True}
    labels = [o["label"] for o in q["options"]]
    _run(_event(repo, questions=[q], answers={q["question"]: ", ".join(labels)}), tmp_path / "home")
    [rec] = _records(repo / U.LOG_NAME)
    assert rec["chosen_options"] == q["options"]


def test_each_question_of_a_batch_gets_its_own_line(repo, tmp_path):
    q2 = {**_QUESTION, "question": "And the format?", "header": "Format"}
    answers = {_QUESTION["question"]: "Append to review log", "And the format?": "Own JSONL file (Recommended)"}
    _run(_event(repo, questions=[_QUESTION, q2], answers=answers), tmp_path / "home")
    assert [r["question"] for r in _records(repo / U.LOG_NAME)] == [_QUESTION["question"], "And the format?"]


def test_non_ascii_text_survives_unescaped(repo, tmp_path):
    q = {**_QUESTION, "question": "Welche Datei - Grüße, 日本?"}
    _run(_event(repo, questions=[q], answers={q["question"]: "Append to review log"}), tmp_path / "home")
    raw = (repo / U.LOG_NAME).read_text(encoding="utf-8")
    assert "Grüße, 日本" in raw


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]"])
def test_junk_stdin_writes_nothing_and_exits_zero(repo, tmp_path, stdin):
    r = _run(stdin, tmp_path / "home")
    assert r.returncode == 0 and r.stdout.strip() == ""
    assert not (repo / U.LOG_NAME).exists()


def test_an_unanswered_or_foreign_event_writes_nothing(repo, tmp_path):
    _run(_event(repo, answers={}), tmp_path / "home")
    _run(_event(repo, tool="Bash"), tmp_path / "home")
    assert not (repo / U.LOG_NAME).exists()


def test_hooks_json_registers_it_for_posttooluse_askuserquestion():
    groups = json.loads((_HOOK.parent / "hooks.json").read_text(encoding="utf-8"))["hooks"]["PostToolUse"]
    matchers = [g["matcher"] for g in groups
                for h in g["hooks"] if h["command"].endswith('/hooks/user-decision-log.py"')]
    assert matchers == ["AskUserQuestion"]
