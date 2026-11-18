"""Tests for decision-claim-guard.py: a review-log claim that something is not the user's decision.

Driven end to end: real git repositories in tmp_path, a real USER-DECISIONS.jsonl in the record
shape user-decision-log.py writes, and the hook run as a subprocess with the event on stdin exactly
as Claude Code runs it. The hook's state lives under CLAUDE_CONFIG_DIR, which each test points at
its own directory.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parent.parent / "decision-claim-guard.py"
_REVIEW = "EXECUTION-USER-REVIEW.md"

_CHOSEN = {
    "label": "Subtable 50071 (Recommended)",
    "description": ("Parameters as rows: key, order no., name, value. Upside: no limit on number or "
                    "total length, each value up to 250. Downside: a second table to import."),
}
_UNCHOSEN = {
    "label": "One text field",
    "description": "All parameters in one Text 250 field. Upside: one table. Downside: a hard cap of 250 characters.",
}
_RECORD = {
    "ts": "2026-11-17T19:03:26Z", "session_id": "s", "cwd": "/x",
    "question": "How should table 50070 hold a call's parameters?", "header": "Parameters",
    "multiSelect": False, "options": [_CHOSEN, _UNCHOSEN],
    "chosen": _CHOSEN["label"], "chosen_options": [_CHOSEN], "annotation": None,
}

_CLAIM = "- 2026-11-18 12:14 the cap of 100 replaces the plan's \"no limit\", which was my own wording, not a user decision.\n"


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


def _log(root, *records):
    with open(root / "USER-DECISIONS.jsonl", "w", encoding="utf-8") as handle:
        for record in records or (_RECORD,):
            handle.write(json.dumps(record) + "\n")


def _run(event, tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["CLAUDE_CONFIG_DIR"] = str(tmp_path / "claude-config")
    return subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event), capture_output=True,
                          text=True, encoding="utf-8", check=False, env=env)


def _post(event, tmp_path):
    """The block reason a PostToolUse run printed, "" when it did not block. It always exits 0."""
    r = _run(event, tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r
    if not r.stdout.strip():
        return ""
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    return out["reason"]


def _write(path, content, cwd=None):
    return {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(cwd or path.parent),
            "tool_input": {"file_path": str(path), "content": content}}


def _edit(path, old, new):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(path.parent),
            "tool_input": {"file_path": str(path), "old_string": old, "new_string": new}}


def _shell(hook, cwd, command="python3 - <<'EOF'\n...\nEOF"):
    return {"hook_event_name": hook, "tool_name": "Bash", "cwd": str(cwd),
            "tool_input": {"command": command}, "tool_response": {"stdout": "", "stderr": ""}}


def test_a_trigger_without_a_marker_is_refused_with_how_to_add_one(repo, tmp_path):
    _log(repo)
    r = _run(_write(repo / _REVIEW, "# Review\n\n" + _CLAIM), tmp_path)
    assert r.returncode == 2
    assert 'decision-check: "' in r.stderr
    assert str(repo / "USER-DECISIONS.jsonl") in r.stderr
    assert "Parameters: Subtable 50071 (Recommended)" in r.stderr      # the recent answers are listed
    assert "NOTHING in this call ran" in r.stderr                         # PreToolUse: shared footer


def test_a_marker_hitting_a_chosen_option_is_refused_with_the_quote(repo, tmp_path):
    _log(repo)
    entry = _CLAIM.rstrip("\n") + ' decision-check: "no limit"\n'
    r = _run(_write(repo / _REVIEW, entry), tmp_path)
    assert r.returncode == 2
    assert "[Parameters] chose 'Subtable 50071 (Recommended)'" in r.stderr
    assert "Upside: no limit on number or total length, each value up to 250." in r.stderr
    assert "the claim is false" in r.stderr


def test_a_marker_term_found_only_in_an_unchosen_option_is_allowed(repo, tmp_path):
    _log(repo)
    entry = "- the hard cap of 250 is not a user decision. decision-check: \"hard cap\"\n"
    r = _run(_write(repo / _REVIEW, entry), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_an_entry_without_a_trigger_is_allowed(repo, tmp_path):
    _log(repo)
    r = _run(_write(repo / _REVIEW, "- 2026-11-18 the cap of 100 is mine (my reading).\n"), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_a_first_person_decision_record_is_no_trigger(repo, tmp_path):
    _log(repo)
    text = "- F2 LOW, FIX (my call, not asked): two passes.\n- (my reading) no new dependency.\n"
    r = _run(_write(repo / _REVIEW, text), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


@pytest.mark.parametrize("phrase", [
    "not a user decision", "Not the user's decision", "not the user\u2019s decision",
    "no user decision", "my own wording", "my decision, not the user's", "MY DECISION, NOT THE USER\u2019S",
    "the user never decided", "not decided by the user",
])
def test_trigger_phrases_cover_both_apostrophes(repo, tmp_path, phrase):
    _log(repo)
    r = _run(_write(repo / _REVIEW, "- the row cap is %s.\n" % phrase), tmp_path)
    assert r.returncode == 2, phrase


def test_a_trigger_wrapped_across_lines_still_counts(repo, tmp_path):
    _log(repo)
    r = _run(_write(repo / _REVIEW, "- the cap was my amendment, not a user\n  decision.\n"), tmp_path)
    assert r.returncode == 2


def test_a_marker_on_a_continuation_line_belongs_to_the_entry(repo, tmp_path):
    _log(repo)
    text = "- the hard cap is not a user decision.\n  decision-check: \"hard cap\"\n- next entry\n"
    r = _run(_write(repo / _REVIEW, text), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_a_marker_in_another_entry_does_not_count(repo, tmp_path):
    _log(repo)
    text = "- the hard cap is not a user decision.\n- decision-check: \"hard cap\" hard cap\n"
    r = _run(_write(repo / _REVIEW, text), tmp_path)
    assert r.returncode == 2


def test_a_marker_term_absent_from_the_entry_is_refused(repo, tmp_path):
    _log(repo)
    r = _run(_write(repo / _REVIEW, "- the cap is not a user decision. decision-check: \"xyzzy\"\n"), tmp_path)
    assert r.returncode == 2
    assert "does not occur in the entry outside the marker" in r.stderr


def test_another_file_is_ignored(repo, tmp_path):
    _log(repo)
    r = _run(_write(repo / "NOTES.md", _CLAIM), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_no_decision_log_allows_silently(repo, tmp_path):
    r = _run(_write(repo / _REVIEW, _CLAIM), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_an_edit_adding_a_hitting_claim_is_refused(repo, tmp_path):
    _log(repo)
    review = repo / _REVIEW
    review.write_text("# Review\n\n- old entry\n", encoding="utf-8")
    new = "- old entry\n" + _CLAIM.rstrip("\n") + ' decision-check: "no limit"'
    r = _run(_edit(review, "- old entry", new), tmp_path)
    assert r.returncode == 2 and "the claim is false" in r.stderr


def test_an_edit_adding_text_beside_an_old_claim_is_allowed(repo, tmp_path):
    _log(repo)
    review = repo / _REVIEW
    review.write_text("# Review\n\n" + _CLAIM, encoding="utf-8")
    old = _CLAIM.rstrip("\n")
    r = _run(_edit(review, old, old + "\n  CORRECTION: the chosen option says no limit; asked the user."), tmp_path)
    assert (r.returncode, r.stderr) == (0, "")


def test_a_free_text_answer_counts_as_chosen(repo, tmp_path):
    record = dict(_RECORD, chosen="Keep the row cap at 100 for now", chosen_options=[])
    _log(repo, record)
    r = _run(_write(repo / _REVIEW, "- the row cap is not a user decision. decision-check: \"row cap\"\n"), tmp_path)
    assert r.returncode == 2 and "Keep the row cap at 100" in r.stderr


def test_a_linked_worktree_reads_the_main_checkout_log(repo, tmp_path):
    _log(repo)
    linked = tmp_path / "linked"
    assert _git(repo, "worktree", "add", "-q", str(linked), "-b", "side").returncode == 0
    entry = _CLAIM.rstrip("\n") + ' decision-check: "no limit"\n'
    r = _run(_write(linked / _REVIEW, entry), tmp_path)
    assert r.returncode == 2 and "the claim is false" in r.stderr


def test_bash_post_reports_the_added_entry_once(repo, tmp_path):
    _log(repo)
    review = repo / _REVIEW
    review.write_text("# Review\n\n- an old claim: not a user decision.\n", encoding="utf-8")
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    with open(review, "a", encoding="utf-8") as handle:
        handle.write(_CLAIM)
    reason = _post(_shell("PostToolUse", repo), tmp_path)
    assert "entry at line 4" in reason and "an old claim" not in reason
    assert "fix the entry now" in reason
    # judged once: the next command leaves the file alone, or adds an unrelated entry
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    assert _post(_shell("PostToolUse", repo), tmp_path) == ""
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    with open(review, "a", encoding="utf-8") as handle:
        handle.write("- an unrelated entry\n")
    assert _post(_shell("PostToolUse", repo), tmp_path) == ""


def test_a_post_with_no_pre_between_does_not_re_report(repo, tmp_path):
    # Monitor has no PreToolUse snapshot: the state the reporting post stored is what stops it.
    _log(repo)
    review = repo / _REVIEW
    review.write_text("# Review\n", encoding="utf-8")
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    with open(review, "a", encoding="utf-8") as handle:
        handle.write(_CLAIM)
    assert "DECISION CLAIM CHECK" in _post(_shell("PostToolUse", repo), tmp_path)
    with open(review, "a", encoding="utf-8") as handle:
        handle.write("- an unrelated entry\n")
    monitor = dict(_shell("PostToolUse", repo), tool_name="Monitor")
    assert _post(monitor, tmp_path) == ""


def test_bash_post_quotes_a_hit(repo, tmp_path):
    _log(repo)
    review = repo / _REVIEW
    review.write_text("# Review\n", encoding="utf-8")
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    with open(review, "a", encoding="utf-8") as handle:
        handle.write(_CLAIM.rstrip("\n") + ' decision-check: "no limit"\n')
    assert "Upside: no limit on number" in _post(_shell("PostToolUse", repo), tmp_path)


def test_bash_post_judges_a_log_the_command_created(repo, tmp_path):
    _log(repo)
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    (repo / _REVIEW).write_text("# Review\n\n" + _CLAIM, encoding="utf-8")
    assert "DECISION CLAIM CHECK" in _post(_shell("PostToolUse", repo), tmp_path)


def test_bash_post_without_a_snapshot_seeds_silently(repo, tmp_path):
    _log(repo)
    (repo / _REVIEW).write_text("# Review\n\n" + _CLAIM, encoding="utf-8")
    assert _post(_shell("PostToolUse", repo), tmp_path) == ""


def test_bash_finds_a_log_the_command_names_outside_the_cwd(repo, tmp_path):
    _log(repo)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    review = repo / _REVIEW
    command = "python3 -c 'open(\"%s\", \"a\").write(\"x\")'" % review
    assert _run(_shell("PreToolUse", elsewhere, command), tmp_path).returncode == 0
    review.write_text(_CLAIM, encoding="utf-8")
    assert "DECISION CLAIM CHECK" in _post(_shell("PostToolUse", elsewhere, command), tmp_path)


def test_bash_post_in_a_repo_without_a_decision_log_is_silent(repo, tmp_path):
    assert _run(_shell("PreToolUse", repo), tmp_path).returncode == 0
    (repo / _REVIEW).write_text(_CLAIM, encoding="utf-8")
    assert _post(_shell("PostToolUse", repo), tmp_path) == ""


def test_bad_stdin_fails_open(tmp_path):
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path / "c")}
    r = subprocess.run([sys.executable, str(_HOOK)], input="not json", capture_output=True,
                       text=True, encoding="utf-8", check=False, env=env)
    assert (r.returncode, r.stderr) == (0, "")


def test_an_empty_dot_git_dir_is_no_work_tree_root(tmp_path):
    # A stray empty .git directory in the cwd (git ignores it: no HEAD) must not be taken as the
    # work tree root, or the review log at the real root is never snapshotted.
    real = tmp_path / "real"
    real.mkdir()
    assert _git(real, "init", "-q", "-b", "main").returncode == 0
    _log(real)
    sub = real / "sub"
    (sub / ".git").mkdir(parents=True)
    assert _run(_shell("PreToolUse", sub), tmp_path).returncode == 0
    (real / _REVIEW).write_text(_CLAIM, encoding="utf-8")
    assert "DECISION CLAIM CHECK" in _post(_shell("PostToolUse", sub), tmp_path)
