"""Tests for subagent-brief-must-not-nudge.py (PreToolUse on Task|Agent|SendMessage).

Contract: a dispatch whose brief carries a Must-NOT the user's logged decisions do not hold, or
that repeats the controller's own "(my reading)" note without its label, gets
hookSpecificOutput.additionalContext saying so (exit 0, NO permissionDecision). A Must-NOT quoting
the user's option, prose that merely contains "must not", a quoted mention of the label, a report
to `main`, a probe dispatch and every malformed event get silence.

Driven end to end: a real git repository in tmp_path, its USER-DECISIONS.jsonl written by the
REAL user-decision-log hook from an AskUserQuestion event, and the hook under test run as a
subprocess exactly as Claude Code runs it. The shapes below come from the replay recorded in the
hook's docstring (the four real firings are reproduced in miniature).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import subagent_brief_must_not_nudge as N

_HOOKS = Path(__file__).resolve().parent.parent
_HOOK = _HOOKS / "subagent-brief-must-not-nudge.py"
_LOGGER = _HOOKS / "user-decision-log.py"

_QUESTION = {
    "question": "How should a JSON array --data file be read?",
    "header": "JSON array",
    "multiSelect": False,
    "options": [
        {"label": "Stream the array (Recommended)",
         "description": "Parse the array one element at a time from the bytes already held; "
                        "peak = the file's bytes plus one record."},
        {"label": "Cap the file size",
         "description": "Refuse a JSON array file larger than a settings key allows."},
    ],
}
_CHOSEN = "Stream the array (Recommended)"

_REVIEW = """# Execution review

- 2026-11-03 22:1x, [20] perf Issue 1, user chose "Stream the array (Recommended)". Must NOT (from
  the rejected options): a size cap or a refusal as the fix. (my reading) no new dependency.
- 2026-11-03 11:5x, chat: the user said "keep the 30 s default; nobody waits longer than that"
  for stored_names_wait.
- 2026-11-03 12:00, [21] reader design (my reading) the reader keeps a byte cursor per element.
"""


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False)


def _env(home):
    return {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}


def _run(event, home):
    stdin = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run([sys.executable, str(_HOOK)], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", check=False, env=_env(home))


@pytest.fixture
def home(tmp_path):
    path = tmp_path / "home"
    (path / ".claude").mkdir(parents=True)
    return path


@pytest.fixture
def repo(tmp_path, home):
    """A repository whose decision log the real user-decision-log hook wrote, plus a review file."""
    root = tmp_path / "repo"
    root.mkdir()
    assert _git(root, "init", "-q", "-b", "main").returncode == 0
    answered = {"questions": [_QUESTION], "answers": {_QUESTION["question"]: _CHOSEN},
                "annotations": {}}
    logged = subprocess.run(
        [sys.executable, str(_LOGGER)], capture_output=True, text=True, encoding="utf-8",
        check=False, env=_env(home),
        input=json.dumps({"hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion",
                          "session_id": "s", "cwd": str(root), "tool_input": answered,
                          "tool_response": answered}))
    assert logged.returncode == 0
    assert (root / N.DECISIONS_NAME).is_file()
    (root / N.REVIEW_NAME).write_text(_REVIEW, encoding="utf-8")
    return root


def _dispatch(cwd, prompt, **extra):
    tool_input = {"description": "d", "prompt": prompt, "subagent_type": "general-purpose", **extra}
    return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "cwd": str(cwd),
            "tool_input": tool_input}


def _context(result):
    """The additionalContext the hook printed, or None for silence; asserts the nudge contract."""
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return None
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in out          # a nudge, never a deny
    return out["additionalContext"]


# ---------------------------------------------------------------- untraced

def test_an_invented_must_not_is_reported_untraced(repo, home):
    note = _context(_run(_dispatch(repo, "Do it.\n\nMust NOT: touch the serial transport layer."),
                         home))
    assert note and "line 3" in note and "found in neither" in note
    assert "touch the serial transport layer" in note          # inline text may be quoted


def test_a_must_not_quoting_the_chosen_option_passes(repo, home):
    prompt = ('Must NOT: change "Parse the array one element at a time from the bytes already '
              'held".')
    assert _context(_run(_dispatch(repo, prompt), home)) is None


def test_a_must_not_naming_the_rejected_option_passes(repo, home):
    assert _context(_run(_dispatch(repo, "- Must NOT: cap the file size."), home)) is None


def test_a_must_not_copied_from_the_review_file_passes_across_its_wrap(repo, home):
    """The review line wraps after "(from"; read line by line, the relay looked invented."""
    prompt = "Must NOT (from the rejected options): a size cap or a refusal as the fix."
    assert _context(_run(_dispatch(repo, prompt), home)) is None


def test_a_must_not_matching_only_a_my_reading_note_is_untraced(repo, home):
    """The review file's own "(my reading)" spans are cut out before matching: they are the
    controller's inference, so a Must-NOT traced to one is exactly the defect."""
    note = _context(_run(_dispatch(repo, "Must NOT: drop the byte cursor the reader keeps."), home))
    assert note and "found in neither" in note


def test_a_quote_holding_its_own_semicolon_is_still_one_quote(repo, home):
    # The framing words after the quote are in no source, so a split at the quoted ";" leaves a
    # half that only the whole quote could have traced. (A quote inside the label's own
    # parenthetical is never judged at all, so this one sits in the body.)
    prompt = ('MUST NOT TOUCH: "keep the 30 s default; nobody waits longer than that", quoted '
              'exactly from the 11:5x answer.')
    assert _context(_run(_dispatch(repo, prompt), home)) is None


def test_a_clause_added_after_a_verbatim_quote_is_still_judged(repo, home):
    prompt = ('MUST NOT TOUCH (verbatim: "keep the 30 s default; nobody waits longer than '
              'that"): the default; a status read also never retries a refused connection.')
    assert "found in neither" in (_context(_run(_dispatch(repo, prompt), home)) or "")


@pytest.mark.parametrize("prompt", [
    "Behaviour must not change: every error message stays byte-identical.",
    "Tests must not monkeypatch our own internals.",
    "Check the rules a later session\n   must not break: from the design and the ledger.",
    "1. The Must NOT lines: can any path send a byte before the check?",
], ids=["leading-word", "prose", "wrapped-lowercase", "reviewer-question"])
def test_a_must_not_that_is_not_a_relay_label_stays_silent(repo, home, prompt):
    assert _context(_run(_dispatch(repo, prompt), home)) is None


def test_no_must_not_line_means_no_output(repo, home):
    assert _context(_run(_dispatch(repo, "Refactor the reader. Run the gate."), home)) is None


# ---------------------------------------------------------------- my-reading

def test_a_must_not_labelled_my_reading_is_reported(repo, home):
    note = _context(_run(_dispatch(repo, "- Must NOT (my reading): add a dependency."), home))
    assert note and "labelled as your own reading" in note


@pytest.mark.parametrize("label", ["My reading:", "Coordinator's reading:"])
def test_the_other_reading_labels_count_too(repo, home, label):
    note = _context(_run(_dispatch(repo, f"Must NOT: retry forever. {label} that is what A means."),
                         home))
    assert note and "labelled as your own reading" in note


def test_a_quoted_mention_of_the_label_is_not_a_label(repo, home):
    prompt = 'A brief line must not be labelled "(my reading)" and still be briefed as a rule.'
    assert _context(_run(_dispatch(repo, prompt), home)) is None


# ---------------------------------------------------------------- relayed-reading

def test_a_negative_note_relayed_without_its_label_is_reported(repo, home):
    """The 2026-11-03 datamax-dpl brief line, which carries no must-not word at all."""
    prompt = ("Issue 1: stream the array, one element at a time; the rejected options stay out.\n"
              "No size cap as the fix, no new dependency.")
    note = _context(_run(_dispatch(repo, prompt), home))
    assert note and "line 1" in note and "without its label" in note
    assert f"{N.REVIEW_NAME} line 3" in note


def test_the_same_phrase_in_a_brief_about_something_else_stays_silent(repo, home):
    """A short note is a common phrase; only a brief on the note's own topic is relaying it."""
    prompt = "Reword the cutter section of the README. No new dependency, no code change."
    assert _context(_run(_dispatch(repo, prompt), home)) is None


# Each brief is on the note's own topic, so only the rule named in its id keeps it silent.
_ON_TOPIC = "Issue 1: stream the array, one element at a time; the rejected options stay out. "


@pytest.mark.parametrize("tail", [
    "No size cap as the fix; (my reading) no new dependency.",
    'No size cap as the fix. The log says "(my reading) no new dependency", never the user\'s.',
    "No size cap as the fix, and no new dependencyless reader exists.",
], ids=["labelled", "quoted", "not-whole-words"])
def test_a_relay_that_keeps_the_label_quotes_or_only_overlaps_stays_silent(repo, home, tail):
    assert _context(_run(_dispatch(repo, _ON_TOPIC + tail), home)) is None


def test_a_hit_in_a_referenced_brief_file_is_cited_by_position_not_quoted(repo, home, tmp_path):
    brief = tmp_path / "brief-impl.md"
    brief.write_text("# Brief\n\nBuild the reader.\n\nMust NOT: rename the secret_widget key.\n",
                     encoding="utf-8")
    note = _context(_run(_dispatch(repo, f"Read your brief and follow it: {brief}"), home))
    assert note and "brief-impl.md line 5" in note
    assert "secret_widget" not in note          # read before approval: position only


def test_a_referenced_file_not_named_as_a_brief_is_not_read(repo, home, tmp_path):
    other = tmp_path / "notes.md"
    other.write_text("Must NOT: rename the secret_widget key.\n", encoding="utf-8")
    assert _context(_run(_dispatch(repo, f"Background: {other}"), home)) is None


# ---------------------------------------------------------------- which calls are briefs

def test_a_sendmessage_to_a_subagent_is_judged(repo, home):
    event = {"hook_event_name": "PreToolUse", "tool_name": "SendMessage", "cwd": str(repo),
             "tool_input": {"to": "fix6", "message": "Must NOT: touch the serial transport."}}
    assert "found in neither" in (_context(_run(event, home)) or "")


@pytest.mark.parametrize("tool_input", [
    {"to": "main", "message": "Must NOT: touch the serial transport."},
    {"to": "fix6", "message": {"type": "shutdown_response", "approve": True}},
], ids=["report-to-main", "structured-message"])
def test_a_sendmessage_that_is_not_a_brief_stays_silent(repo, home, tool_input):
    event = {"hook_event_name": "PreToolUse", "tool_name": "SendMessage", "cwd": str(repo),
             "tool_input": tool_input}
    assert _context(_run(event, home)) is None


@pytest.mark.parametrize("atype", ["bitranox:baseline-probe", "probe-effort-low"])
def test_a_probe_dispatch_gets_no_context(repo, home, atype):
    event = _dispatch(repo, "Must NOT: touch the serial transport.", subagent_type=atype)
    assert _context(_run(event, home)) is None


def test_outside_a_repository_the_audit_dir_log_is_the_source(tmp_path, home):
    plain = tmp_path / "plain"
    plain.mkdir()
    log = home / ".claude" / "self-improve-audit" / (N.project_slug(str(plain)) + "."
                                                     + N.DECISIONS_NAME)
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"ts": "2026-11-03T00:00:00Z", "question": "q", "options": [
        {"label": "Keep the port", "description": "Port 9100 stays the default."}],
        "chosen": "Keep the port"}) + "\n", encoding="utf-8")
    assert _context(_run(_dispatch(plain, "Must NOT: change the port 9100 default."), home)) is None
    assert "found in neither" in (_context(_run(_dispatch(plain, "Must NOT: drop the cutter."),
                                                home)) or "")


def test_a_repository_with_no_decision_source_judges_no_untraced_line(tmp_path, home):
    bare = tmp_path / "bare"
    bare.mkdir()
    assert _git(bare, "init", "-q", "-b", "main").returncode == 0
    assert _context(_run(_dispatch(bare, "Must NOT: drop the cutter."), home)) is None


# ---------------------------------------------------------------- fail open, bounded output

@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", json.dumps({"tool_name": ["Agent"]}),
                                   json.dumps({"tool_name": "Agent", "tool_input": "x"})])
def test_a_malformed_event_is_silent_and_exits_zero(stdin, home):
    assert _context(_run(stdin, home)) is None


def test_an_unreadable_source_fails_open(repo, home):
    (repo / N.DECISIONS_NAME).unlink()
    (repo / N.DECISIONS_NAME).mkdir()          # a directory where the log should be
    result = _run(_dispatch(repo, "Must NOT: drop the cutter."), home)
    assert result.returncode == 0


def test_the_advice_stays_under_the_shared_context_cap():
    found = [("untraced", f"line {n}", "Must NOT: " + "x" * 5000) for n in range(40)]
    note = N.advice(found)
    assert len(note) < 2000
    assert f"and {40 - N.MAX_REPORTED} more" in note


def test_the_paragraph_reader_joins_a_wrap_and_splits_at_a_list_item():
    text = "- first item\n  wrapped on\n- second\n\nplain\nparagraph\n# heading"
    assert N.paragraphs(text) == [(1, "- first item wrapped on"), (3, "- second"),
                                  (5, "plain paragraph"), (7, "# heading")]
