"""Tests for the approval-claim rule of decision-claim-guard.py (and the backlog_add bridge).

A claim that the USER approved something, written into OPEN-WORK.md, a handover.md or a commit
message, must carry the user's own words in quotes (checked against what the person typed in the
session transcript) or a `decision-check: "<term>"` marker that resolves in USER-DECISIONS.jsonl.
A bare paraphrase is refused. A claim that passes but reaches past its quote, or touches an
iron-rule area, gets an advisory (additionalContext), never a block.

Driven end to end like test_decision_claim_guard.py: real git repositories in tmp_path, a real
transcript in the record shapes Claude Code writes, and the hook run as a subprocess with the
event on stdin. ASCII only.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import approval_claims as AC

_HOOKS = Path(__file__).resolve().parent.parent
_HOOK = _HOOKS / "decision-claim-guard.py"
_BRIDGE = _HOOKS / "mod_bridge.py"

_TYPED = "yes, merge and push"
_TYPED_DE = "Approval-Guard: dein Vorschlag passt, bau ihn"

_CHOSEN = {"label": "Subtable 50071 (Recommended)",
           "description": "Parameters as rows. Upside: no limit on number or total length."}
_RECORD = {"ts": "2026-11-17T19:03:26Z", "session_id": "s", "cwd": "/x",
           "question": "How should table 50070 hold a call's parameters?", "header": "Parameters",
           "multiSelect": False, "options": [_CHOSEN], "chosen": _CHOSEN["label"],
           "chosen_options": [_CHOSEN], "annotation": None}


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


def _typed(text):
    return {"type": "user", "origin": {"kind": "human"}, "uuid": "u-" + text[:8],
            "message": {"role": "user", "content": text}}


def _teammate(text):
    body = '<teammate-message teammate_id="lead">%s</teammate-message>' % text
    return {"type": "user", "uuid": "t-" + text[:8], "message": {"role": "user", "content": body}}


def _assistant(text):
    return {"type": "assistant", "message": {"role": "assistant",
                                             "content": [{"type": "text", "text": text}]}}


@pytest.fixture
def transcript(tmp_path):
    """A session transcript in its project dir: a typed prompt, a reply, a teammate message."""
    project = tmp_path / "claude-config" / "projects" / "-x"
    project.mkdir(parents=True)
    path = project / "sess-1.jsonl"
    records = [_typed("please check the branch"), _assistant("Merge and push it?"),
               _typed(_TYPED), _typed(_TYPED_DE), _teammate("yes ship it"), _assistant("ok")]
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def _log(root):
    (root / "USER-DECISIONS.jsonl").write_text(json.dumps(_RECORD) + "\n", encoding="utf-8")


def _env(tmp_path, **extra):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and k != "CLAUDE_CODE_SESSION_ID"}
    env["CLAUDE_CONFIG_DIR"] = str(tmp_path / "claude-config")
    env.update(extra)
    return env


def _run(event, tmp_path):
    return subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event), capture_output=True,
                          text=True, encoding="utf-8", check=False, env=_env(tmp_path))


def _write(path, content, transcript_path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Write", "cwd": str(path.parent),
            "transcript_path": str(transcript_path),
            "tool_input": {"file_path": str(path), "content": content}}


def _edit(path, old, new, transcript_path):
    return {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": str(path.parent),
            "transcript_path": str(transcript_path),
            "tool_input": {"file_path": str(path), "old_string": old, "new_string": new}}


def _bash(hook, cwd, command, transcript_path):
    return {"hook_event_name": hook, "tool_name": "Bash", "cwd": str(cwd),
            "transcript_path": str(transcript_path), "tool_input": {"command": command},
            "tool_response": {"stdout": "", "stderr": ""}}


def _advice(r):
    """The additionalContext an allowed run printed, "" when it printed nothing."""
    assert r.returncode == 0, r
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


_ITEM = "- [20] USER merge the topic branch | size: 1 | open: %s | next: merge\n"


# ---- duty 1: faithfulness -------------------------------------------------------------------


def test_a_bare_paraphrase_of_an_approval_is_refused_with_quote_remedy(repo, transcript, tmp_path):
    r = _run(_write(repo / "OPEN-WORK.md", _ITEM % "the user approved the release as is", transcript),
             tmp_path)
    assert r.returncode == 2, r
    assert "APPROVAL CLAIM CHECK" in r.stderr
    assert "quote the user's own words" in r.stderr
    assert 'decision-check: "' in r.stderr


def test_a_real_user_quote_passes_silently(repo, transcript, tmp_path):
    entry = _ITEM % ('the user approved the merge ("%s")' % _TYPED)
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_a_fabricated_quote_is_refused_naming_the_nearest_real_message(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved the merge ("yes, merge everything and push")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r
    assert "never typed" in r.stderr
    assert _TYPED in r.stderr                       # the nearest real user message is named


def test_a_quote_only_a_teammate_sent_is_not_the_users_words(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved the merge ("yes ship it")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r
    assert "never typed" in r.stderr


def test_a_quote_with_an_ellipsis_matches_its_fragments_in_order(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved it ("dein Vorschlag passt ... bau ihn")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


def test_a_quote_typed_in_an_earlier_session_of_the_project_passes(repo, transcript, tmp_path):
    earlier = transcript.parent / "sess-0.jsonl"
    earlier.write_text(json.dumps(_typed("ok, keep the subtable")) + "\n", encoding="utf-8")
    entry = _ITEM % 'the user approved the layout ("ok, keep the subtable")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


# With neither a transcript nor a decision log readable the quote cannot be checked. It still
# passes (user decision 2026-11-21: let it through, with a notice), but the reader is told so.
_UNCHECKED = "passed unchecked"


def _says_unchecked(text):
    """True when `text` carries the notice naming both sources that could not be read."""
    return _UNCHECKED in text and "session transcript" in text and "USER-DECISIONS.jsonl" in text


def test_an_unchecked_quote_passes_with_a_notice_naming_both_missing_sources(repo, tmp_path):
    entry = _ITEM % 'the user approved the merge ("anything at all")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, tmp_path / "missing.jsonl"), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r
    assert _says_unchecked(_advice(r)), r


def test_an_unchecked_quote_in_a_commit_message_passes_with_the_notice(repo, tmp_path):
    msg = repo / "msg.txt"
    msg.write_text('Merge topic\n\nThe user approved the merge ("anything at all").\n', encoding="utf-8")
    r = _run(_bash("PreToolUse", repo, _commit_f(msg), tmp_path / "missing.jsonl"), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r
    assert _says_unchecked(_advice(r)), r


def test_a_quote_checked_against_the_decision_log_alone_carries_no_notice(repo, tmp_path):
    _log(repo)
    entry = _ITEM % 'the user approved the layout ("%s")' % _CHOSEN["label"]
    r = _run(_write(repo / "OPEN-WORK.md", entry, tmp_path / "missing.jsonl"), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), r


def test_a_bare_paraphrase_with_nothing_readable_is_still_refused(repo, tmp_path):
    r = _run(_write(repo / "OPEN-WORK.md", _ITEM % "the user approved the merge",
                    tmp_path / "missing.jsonl"), tmp_path)
    assert r.returncode == 2, r
    assert "quote the user's own words" in r.stderr
    assert _UNCHECKED not in r.stderr + r.stdout


def test_a_resolving_decision_check_marker_passes(repo, transcript, tmp_path):
    _log(repo)
    entry = _ITEM % 'the user approved the subtable layout. decision-check: "subtable"'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


def test_a_marker_that_resolves_nowhere_is_refused(repo, transcript, tmp_path):
    _log(repo)
    entry = _ITEM % 'the user approved the xyzzy layout. decision-check: "xyzzy"'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r
    assert "no option the user chose" in r.stderr


def test_a_marker_term_absent_from_the_entry_is_refused(repo, transcript, tmp_path):
    _log(repo)
    entry = _ITEM % 'the user approved the layout. decision-check: "subtable"'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r
    assert "does not occur in the entry outside the marker" in r.stderr


def test_a_handover_is_judged_like_the_backlog(repo, transcript, tmp_path):
    r = _run(_write(repo / "handover.md", "# Handover\n\n- release: user-approved.\n", transcript),
             tmp_path)
    assert r.returncode == 2, r


def test_another_file_is_not_judged(repo, transcript, tmp_path):
    r = _run(_write(repo / "NOTES.md", _ITEM % "the user approved the release", transcript), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_an_edit_beside_an_old_approval_line_is_not_judged(repo, transcript, tmp_path):
    backlog = repo / "OPEN-WORK.md"
    old = _ITEM % "the user approved the release"
    backlog.write_text(old, encoding="utf-8")
    r = _run(_edit(backlog, old, old + "- [30] FOUND tidy the docs | size: 1 | open: o | next: n\n",
                   transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


@pytest.mark.parametrize("claim", [
    "the user approved the plan", "The user has approved it", "the user agreed", "the user accepted it",
    "user said yes", "as the user approved", "user-approved text",
    "der Benutzer hat den Plan freigegeben", "der Nutzer hat zugestimmt", "vom Benutzer freigegeben",
])
def test_approval_phrases_trigger(claim):
    assert AC.APPROVAL.search(claim), claim


@pytest.mark.parametrize("text", [
    "NOT yet approved by the user", "not approved by the user", "needs user approval",
    "until the user approves", "the user has not approved it", "ask whether the user agrees",
    "the user never approved", "the user said no", "doubling the mails past what the user approved",
])
def test_non_claims_do_not_trigger(text):
    assert not AC.APPROVAL.search(text), text


@pytest.mark.parametrize("text", ["plan approved by the user", "pushed with the user's go"])
def test_passive_and_go_forms_are_deliberately_no_triggers(text):
    # Outside the requested phrase list; the replay priced them: see the module docstring.
    assert not AC.APPROVAL.search(text), text


def test_a_quote_wrapped_onto_the_next_line_still_counts(repo, transcript, tmp_path):
    entry = '- merged: the user approved it ("yes, merge\n  and push"), CI green\n'
    r = _run(_write(repo / "handover.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


def _tool_result(tool_id, content, result, is_error=False):
    return {"type": "user", "uuid": "r-" + tool_id, "toolUseResult": result,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id,
                                                     "content": content, "is_error": is_error}]}}


def _append(transcript, *records):
    with open(transcript, "a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def test_an_answer_chosen_in_ask_user_question_counts_as_the_users_words(repo, transcript, tmp_path):
    option = {"label": "Ship 0.5.1 (Recommended)", "description": "Then gate, push and a 0.5.1 release."}
    other = {"label": "Wait", "description": "Hold the release."}
    question = {"question": "Release now?", "header": "Release", "options": [option, other],
                "multiSelect": False}
    _append(transcript, _tool_result("toolu_q1", 'Your questions have been answered: "Release now?"="%s"'
                                     % option["label"],
                                     {"questions": [question], "answers": {"Release now?": option["label"]}}))
    entry = _ITEM % 'the user approved the release ("then gate, push and a 0.5.1 release")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


def test_an_unchosen_ask_user_question_option_is_not_the_users_words(repo, transcript, tmp_path):
    option = {"label": "Ship 0.5.1 (Recommended)", "description": "Then gate, push and a 0.5.1 release."}
    other = {"label": "Wait", "description": "Hold the release."}
    question = {"question": "Release now?", "header": "Release", "options": [option, other],
                "multiSelect": False}
    _append(transcript, _tool_result("toolu_q2", "answered", {"questions": [question],
                                                              "answers": {"Release now?": "Wait"}}))
    entry = _ITEM % 'the user approved the release ("then gate, push and a 0.5.1 release")'
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r


def test_a_plan_approved_in_plan_mode_passes_when_the_entry_names_its_file(repo, transcript, tmp_path):
    plan = "/opt/claude/plans/quiet-river-plan.md"
    _append(transcript, _tool_result("toolu_p1", "User has approved your plan.",
                                     {"plan": "# Merge the topic branch\n", "filePath": plan,
                                      "isAgent": False, "hasTaskTool": True}))
    entry = _ITEM % ("the user approved the plan %s" % plan)
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stderr) == (0, ""), r


def test_a_plan_the_user_rejected_in_plan_mode_does_not_pass(repo, transcript, tmp_path):
    plan = "/opt/claude/plans/quiet-river-plan.md"
    _append(transcript, _tool_result("toolu_p2", "The user doesn't want to proceed with this tool use.",
                                     "Error: rejected", is_error=True))
    entry = _ITEM % ("the user approved the plan %s" % plan)
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert r.returncode == 2, r


# ---- commit messages ------------------------------------------------------------------------


def _commit_f(msg):
    """`git commit -F <msg>` as the Bash tool takes it on every OS.

    The Bash tool is a POSIX command line even on Windows (Git Bash), so an unquoted `C:\\...` path
    loses its backslashes and names no file: the hook then reads no message and allows the call,
    which a refusal test sees as a failure and a pass test cannot see at all. Quote a forward-slash
    path, as tests/test_commit_tell_sweep.py does.
    """
    return 'git commit -F "%s"' % msg.as_posix()


def test_a_commit_message_file_with_a_paraphrase_is_refused_without_echoing_it(repo, transcript, tmp_path):
    msg = repo / "msg.txt"
    msg.write_text("Release 1.2\n\nThe user approved the quuxfrob release.\n", encoding="utf-8")
    r = _run(_bash("PreToolUse", repo, _commit_f(msg), transcript), tmp_path)
    assert r.returncode == 2, r
    assert "APPROVAL CLAIM CHECK" in r.stderr
    assert "quuxfrob" not in r.stderr                # a -F file's content is never quoted back


def test_a_commit_message_file_with_a_real_quote_passes(repo, transcript, tmp_path):
    msg = repo / "msg.txt"
    # Liveness first: the same command on a paraphrase is refused, so the hook reads this path and
    # the pass below is the quote's doing, not a message file it never found.
    msg.write_text("Merge topic\n\nThe user approved the merge.\n", encoding="utf-8")
    assert _run(_bash("PreToolUse", repo, _commit_f(msg), transcript), tmp_path).returncode == 2
    msg.write_text('Merge topic\n\nThe user approved the merge ("%s").\n' % _TYPED, encoding="utf-8")
    r = _run(_bash("PreToolUse", repo, _commit_f(msg), transcript), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), r


def test_an_inline_commit_message_with_a_paraphrase_is_refused(repo, transcript, tmp_path):
    r = _run(_bash("PreToolUse", repo, 'git commit -m "release: the user approved it"', transcript),
             tmp_path)
    assert r.returncode == 2, r


def test_a_commit_without_an_approval_claim_passes(repo, transcript, tmp_path):
    r = _run(_bash("PreToolUse", repo, 'git commit -m "fix: tidy the parser"', transcript), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), r


# ---- a shell command writing the backlog ----------------------------------------------------


def test_a_shell_written_paraphrase_is_reported_after_the_command(repo, transcript, tmp_path):
    backlog = repo / "OPEN-WORK.md"
    backlog.write_text("# Backlog\n", encoding="utf-8")
    cmd = "python3 open_work.py add"
    assert _run(_bash("PreToolUse", repo, cmd, transcript), tmp_path).returncode == 0
    backlog.write_text("# Backlog\n" + _ITEM % "the user approved the release", encoding="utf-8")
    r = _run(_bash("PostToolUse", repo, cmd, transcript), tmp_path)
    assert r.returncode == 0 and r.stdout.strip(), r
    out = json.loads(r.stdout)
    assert out["decision"] == "block"
    assert "APPROVAL CLAIM CHECK" in out["reason"]


# ---- duty 2: critical review of what the claim covers (advisory) ----------------------------


def test_a_claim_reaching_past_its_quote_gets_an_advisory_not_a_block(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved the merge as is, everything included ("%s")' % _TYPED
    advice = _advice(_run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path))
    assert "APPROVAL CLAIM REVIEW" in advice
    assert "as is" in advice and "everything" in advice
    assert "recommend" in advice.lower()


def test_a_claim_touching_an_iron_rule_area_the_quote_never_named_gets_an_advisory(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved the force push ("%s")' % _TYPED
    advice = _advice(_run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path))
    assert "force push" in advice


def test_a_claim_naming_only_what_the_quote_names_gets_no_advisory(repo, transcript, tmp_path):
    entry = _ITEM % 'the user approved the merge and the push ("%s")' % _TYPED
    r = _run(_write(repo / "OPEN-WORK.md", entry, transcript), tmp_path)
    assert (r.returncode, r.stdout, r.stderr) == (0, "", ""), r


# ---- the backlog_add tool (mod bridge) ------------------------------------------------------


@pytest.fixture
def bridge_env(tmp_path, transcript):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return _env(tmp_path, HOME=str(home), USERPROFILE=str(home), CLAUDE_CODE_SESSION_ID="sess-1")


def _bridge(cwd, env, item):
    p = subprocess.run([sys.executable, str(_BRIDGE)],
                       input=json.dumps({"tool": "backlog_add", "input": item}).encode("utf-8"),
                       capture_output=True, cwd=cwd, env=env, check=False)
    return p.returncode, json.loads(p.stdout.decode("ascii"))


_BRIDGE_ITEM = {"rank": 20, "origin": "USER", "what": "merge the topic branch", "size": "1",
                "next": "merge"}


def test_backlog_add_refuses_a_bare_paraphrase(repo, bridge_env):
    rc, out = _bridge(repo, bridge_env, {**_BRIDGE_ITEM, "open": "the user approved the release as is"})
    assert (rc, out["ok"]) == (1, False), out
    assert (rc, out["ok"], out["error"]["kind"]) == (1, False, "ApprovalClaimRefused"), out
    assert "quote the user's own words" in out["error"]["message"]
    assert not (repo / "OPEN-WORK.md").exists()


def test_backlog_add_accepts_a_real_quote_and_carries_the_advisory(repo, bridge_env):
    rc, out = _bridge(repo, bridge_env,
                      {**_BRIDGE_ITEM, "open": 'the user approved the release as is ("%s")' % _TYPED})
    assert (rc, out["ok"]) == (0, True), out
    assert "APPROVAL CLAIM REVIEW" in out["data"].get("advice", "")


def test_backlog_add_refuses_a_fabricated_quote_found_through_the_session_id(repo, bridge_env):
    rc, out = _bridge(repo, bridge_env, {**_BRIDGE_ITEM, "open": 'the user approved it ("ship all of it")'})
    assert (rc, out["ok"]) == (1, False), out
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out
    assert "never typed" in out["error"]["message"]


# The claude process itself does not carry CLAUDE_CODE_SESSION_ID (only its Bash-tool children do),
# so the mod hands the bridge the session id on stdin, beside the tool's input. The fixture lays a
# decision log in the repo: with neither a transcript nor a log readable a quote passes unchecked
# by design (with a notice), so a lost session id would pass for the wrong reason. With the log readable and no
# transcript found, a typed quote is refused as never typed: the false refusal seen live.


@pytest.fixture
def no_session_env(tmp_path, transcript, repo):
    _log(repo)
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return _env(tmp_path, HOME=str(home), USERPROFILE=str(home))


def _bridge_request(cwd, env, request):
    p = subprocess.run([sys.executable, str(_BRIDGE)], input=json.dumps(request).encode("utf-8"),
                       capture_output=True, cwd=cwd, env=env, check=False)
    return p.returncode, json.loads(p.stdout.decode("ascii"))


_TYPED_CLAIM = {**_BRIDGE_ITEM, "open": 'the user approved the release as is ("%s")' % _TYPED}


def test_backlog_add_finds_the_typed_quote_through_the_session_id_on_stdin(repo, no_session_env):
    assert "CLAUDE_CODE_SESSION_ID" not in no_session_env
    request = {"tool": "backlog_add", "input": _TYPED_CLAIM, "session_id": "sess-1"}
    rc, out = _bridge_request(repo, no_session_env, request)
    assert (rc, out["ok"]) == (0, True), out
    assert (repo / "OPEN-WORK.md").is_file()


def test_the_stdin_session_id_wins_over_a_different_env_one(repo, no_session_env):
    env = {**no_session_env, "CLAUDE_CODE_SESSION_ID": "sess-other"}
    request = {"tool": "backlog_add", "input": _TYPED_CLAIM, "session_id": "sess-1"}
    rc, out = _bridge_request(repo, env, request)
    assert (rc, out["ok"]) == (0, True), out


def test_backlog_add_with_a_session_id_neither_way_refuses_a_typed_quote(repo, no_session_env):
    rc, out = _bridge_request(repo, no_session_env, {"tool": "backlog_add", "input": _TYPED_CLAIM})
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out
    assert "never typed" in out["error"]["message"]
    assert not (repo / "OPEN-WORK.md").exists()


@pytest.mark.parametrize("sid", ["*", "../-x/sess-1", "sess-1\n", "", 7, None, ["sess-1"]])
def test_a_malformed_stdin_session_id_finds_no_transcript_and_refuses(repo, no_session_env, sid):
    request = {"tool": "backlog_add", "input": _TYPED_CLAIM, "session_id": sid}
    rc, out = _bridge_request(repo, no_session_env, request)
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out
    assert not (repo / "OPEN-WORK.md").exists()


def test_a_bare_paraphrase_is_refused_with_no_session_id_either_way(repo, no_session_env):
    item = {**_BRIDGE_ITEM, "open": "the user approved the release as is"}
    rc, out = _bridge_request(repo, no_session_env, {"tool": "backlog_add", "input": item})
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out
    assert "quote the user's own words" in out["error"]["message"]
    assert not (repo / "OPEN-WORK.md").exists()


@pytest.fixture
def nothing_readable_env(tmp_path, repo):
    """No session id either way, no transcript and no decision log: nothing to check a quote against."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    env = _env(tmp_path, HOME=str(home), USERPROFILE=str(home))
    assert "CLAUDE_CODE_SESSION_ID" not in env
    assert not (repo / "USER-DECISIONS.jsonl").exists()
    return env


def test_backlog_add_passes_an_unchecked_quote_with_the_notice(repo, nothing_readable_env):
    item = {**_BRIDGE_ITEM, "open": 'the user approved the merge ("anything at all")'}
    rc, out = _bridge_request(repo, nothing_readable_env, {"tool": "backlog_add", "input": item})
    assert (rc, out["ok"]) == (0, True), out
    assert _says_unchecked(out["data"].get("advice", "")), out
    assert (repo / "OPEN-WORK.md").is_file()


def test_backlog_add_refuses_a_bare_paraphrase_with_nothing_readable(repo, nothing_readable_env):
    item = {**_BRIDGE_ITEM, "open": "the user approved the merge"}
    rc, out = _bridge_request(repo, nothing_readable_env, {"tool": "backlog_add", "input": item})
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out
    assert "quote the user's own words" in out["error"]["message"]
    assert not (repo / "OPEN-WORK.md").exists()


def test_backlog_add_with_a_checked_quote_carries_no_notice(repo, bridge_env):
    item = {**_BRIDGE_ITEM, "open": 'the user approved the merge and the push ("%s")' % _TYPED}
    rc, out = _bridge(repo, bridge_env, item)
    assert (rc, out["ok"]) == (0, True), out
    assert "advice" not in out["data"], out


def test_a_session_id_inside_the_tool_input_is_not_trusted(repo, no_session_env):
    # The input is the model's to fill; only the mod, outside it, may name the session.
    request = {"tool": "backlog_add", "input": {**_TYPED_CLAIM, "session_id": "sess-1"}}
    rc, out = _bridge_request(repo, no_session_env, request)
    assert (rc, out.get("error", {}).get("kind")) == (1, "ApprovalClaimRefused"), out


def test_a_quoted_span_without_a_word_is_no_quote():
    # Measured in the replay: a commit message's "+" matched a "+" somewhere in the user's typing
    # and passed an approval claim; punctuation names nothing the user agreed to.
    assert AC.quoted_spans('the user approved "+" and "--" and "yes, go"') == ["yes, go"]


import decision_claim_guard as guard  # noqa: E402 - conftest registers the hyphenated hook


def _approval_named(command, cwd, os_name, tool="Bash"):
    """The approval-claim files `command` names, without the work-root ones the cwd adds."""
    event = {"tool_name": tool, "cwd": str(cwd), "tool_input": {"command": command}}
    roots = set(guard.approval_candidates({**event, "tool_input": {"command": ""}}, os_name=os_name))
    return [p for p in guard.approval_candidates(event, os_name=os_name) if p not in roots]


def test_a_git_bash_drive_path_to_a_handover_is_read_as_its_drive(tmp_path):
    # Git Bash reads /c/w/... as drive C; pathlib alone joins it onto the cwd's drive, a file the
    # command never wrote, so the real handover would never be snapshotted or judged.
    named = _approval_named("echo x >> /c/w/handover.md", tmp_path, "nt")
    assert [p.as_posix().endswith("C:/w/handover.md") for p in named] == [True], named


def test_a_git_bash_mount_path_to_a_backlog_names_no_candidate(tmp_path):
    assert _approval_named("echo x >> /tmp/w/OPEN-WORK.md", tmp_path, "nt") == []


def test_review_log_candidates_stay_review_logs_only(tmp_path):
    # The approval files have their own candidate function, so `candidates` (the review-log
    # reader another change also edits) keeps its original output.
    event = {"tool_name": "Bash", "cwd": str(tmp_path),
             "tool_input": {"command": "echo x >> OPEN-WORK.md handover.md"}}
    assert all(p.name == "EXECUTION-USER-REVIEW.md" for p in guard.candidates(event))
    assert {p.name for p in guard.shell_candidates(event)} >= {"OPEN-WORK.md", "handover.md"}
