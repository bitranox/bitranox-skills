"""Tests for subagent-brief-fetch-nudge.py (PreToolUse on Task|Agent).

Contract: a dispatch whose brief asks the subagent to READ OR COMPARE state across more than one
repository, and nowhere says to fetch or read origin, gets hookSpecificOutput.additionalContext
telling the dispatcher to put "git fetch each repo first and read origin's state" in the brief
(exit 0, NO permissionDecision). A single-repo brief, a brief that already fetches, a multi-repo
brief that only WRITES, and prose that uses the same words in another sense get silence, and so do
every non-subagent tool, a probe dispatch and a bad event.

The positive shapes are real paragraphs from the transcript corpus (the 2026-11-18 report brief
first: it is the incident the hook exists for); the replay is described in the hook's docstring.
"""

import io
import json
import sys

import pytest

import subagent_brief_fetch_nudge as N


def run_main(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return N.main()


KNOWN_POSITIVE = (
    "4. That CLIs built on lib_cli_exit_tools run_cli get the broken-pipe fix on their next dependency "
    "resolve: state it and what the owner needs to do, if anything."
)

POSITIVE = {
    "dependents": KNOWN_POSITIVE,
    "each-template": "1. For each template: its CLAUDE.md section headings (## level) with byte size "
                     "each, and for each section whether it is template-generic.",
    "each-of-n-repos": "1. In each of the 3 repos: where the winrepair files live under root_volume "
                       "(list paths, e.g. root_volume/root/winrepair/*).",
    "sibling-mirrors": "4. Mirrored twin skills in sibling repos: run `repo-gate.py --mirrors` "
                       "(read-only audit) to get the list of twin repos, then grep each twin skill dir.",
    "sibling-grep": "Adjudicate every finding against the real tool it names (`--help`, grep the code "
                    "in sibling repos, read-only).",
    "clone-each": "2. Prove them: clone each repo into your scratch dir (`git clone --no-local <repo> "
                  "<dir>`), apply each task's code in order.",
    "clone-both": "Make your own dir with `mktemp -d` and clone both repos into it with "
                  "`git clone --no-local`.",
    "which-templates": "Which of the templates still floor lib_cli_exit_tools 2.4.1?",
    "across": "Across the templates, compare the bmk floor each pyproject.toml carries.",
    "both-templates": "Report whether both templates still lock the old version.",
    "templates-and-consumers": "Read the lib_log_rich floor in the templates and their consumers.",
}


@pytest.mark.parametrize("prompt", list(POSITIVE.values()), ids=list(POSITIVE))
def test_a_cross_repo_read_without_a_fetch_fires(prompt):
    assert N.cross_repo_hit(prompt) is not None
    message = N.assess("Agent", {"prompt": prompt})
    assert message and "git fetch each repo first" in message


def test_the_2026_11_18_incident_brief_fires_on_the_dependents_arm():
    hit = N.cross_repo_hit("You are assembling a report. Use git log in this repo.\n\n" + KNOWN_POSITIVE)
    assert hit is not None and hit.arm == "dependents"


@pytest.mark.parametrize("prompt", [
    "Read pyproject.toml in this repo and report the lib_cli_exit_tools floor.",
    "Grep src/ for every caller of resolve_key and list them.",
    "Compare the two functions in core.py and say which is still used.",
], ids=lambda p: p[:40])
def test_a_single_repo_brief_is_silent(prompt):
    assert N.cross_repo_hit(prompt) is None


@pytest.mark.parametrize("fetch_line", [
    "Run `git fetch` in each repo first.",
    "git -C <repo> fetch origin, then read it.",
    "Read the value with git show @{u}:pyproject.toml.",
    "Compare origin/master, not the checkout.",
    "Answer from origin's state.",
    "Use git ls-remote for the tags.",
    "Read what each repo holds after a fetch.",
    "git -C <repo> pull --ff-only first.",
    "Use git_state.py --fetch.",
    "Read the file through gh api repos/o/r/contents/pyproject.toml.",
], ids=lambda p: p[:30])
def test_a_brief_that_fetches_or_reads_origin_is_silent(fetch_line):
    prompt = "Which of the templates still floor lib_cli_exit_tools 2.4.1?\n\n" + fetch_line
    assert N.cross_repo_hit(prompt) is None


@pytest.mark.parametrize("prompt", [
    # A write across repos is not a read of their state.
    "Commit each repo separately with a pathspec (git status --porcelain first).",
    "Commit and push both repos to gitea.",
    # "sibling repos" as a test-layout fact, not something to read.
    "Its tests resolve sibling repos via Path(__file__).parents[2], so gate it in the main "
    "checkout and read the report.",
    # consumer / template / clone in their code senses.
    "2. Read whether every consumer of the calibration values uses effective values.",
    "_PLACEHOLDERS must list every template placeholder; read the packing code.",
    "The README embeds the token in each clone URL; list where.",
    # A possessive is the repo's own thing, not a sweep over repos.
    "These are each repo's OWN tests, so read the reference fix and compare.",
    "Read-only on every repo.",
], ids=lambda p: p[:40])
def test_prose_that_is_not_a_cross_repo_read_is_silent(prompt):
    assert N.cross_repo_hit(prompt) is None


def test_the_read_word_must_share_the_sentence_with_the_scope():
    # Replay: a paragraph-wide co-occurrence fired on write briefs whose read verb sat in another
    # sentence of the same paragraph; the sentence rule removed those and kept every real firing.
    prompt = ("So the file goes at root_volume/etc/x/config.toml in each node repo. Then read the "
              "report back.")
    assert N.cross_repo_hit(prompt) is None
    assert N.cross_repo_hit("Then read the config.toml in each node repo.") is not None


def test_a_brief_file_is_read_and_reported_by_name_never_quoted(tmp_path):
    brief = tmp_path / "sweep-brief.md"
    brief.write_text("# Sweep\n\nIntro line.\n\n" + KNOWN_POSITIVE + "\n", encoding="utf-8")
    message = N.assess("Agent", {"prompt": f"Read your brief at {brief} and carry it out."})
    assert message and "sweep-brief.md line 5" in message
    assert "run_cli get the broken-pipe fix" not in message


def test_a_fetch_line_in_the_brief_file_silences_it(tmp_path):
    brief = tmp_path / "brief.md"
    brief.write_text(KNOWN_POSITIVE + "\n\nRun git fetch in each repo first.\n", encoding="utf-8")
    assert N.assess("Agent", {"prompt": f"Read {brief}."}) is None


def test_a_file_whose_name_does_not_say_brief_is_not_read(tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text(KNOWN_POSITIVE + "\n", encoding="utf-8")
    assert N.assess("Agent", {"prompt": f"Read {notes}."}) is None


def test_brief_files_are_capped_in_count(tmp_path):
    paths = []
    for n in range(5):
        path = tmp_path / f"brief{n}.md"
        path.write_text("x\n", encoding="utf-8")
        paths.append(str(path))
    assert len(N.brief_files(" ".join(paths))) == N.MAX_BRIEF_FILES


def test_inline_excerpt_shows_the_line_it_means():
    message = N.assess("Agent", {"prompt": "x " * 120 + "\n\n" + KNOWN_POSITIVE + "\n\n" + "y " * 120})
    assert "CLIs built on lib_cli_exit_tools" in message
    assert len(message) < 1500


@pytest.mark.parametrize("subagent_type", ["bitranox:baseline-probe", "probe-effort-low"])
def test_a_probe_dispatch_is_silent(subagent_type):
    assert N.assess("Agent", {"subagent_type": subagent_type, "prompt": KNOWN_POSITIVE}) is None


@pytest.mark.parametrize("tool", ["Bash", "Edit", "SendMessage", None, 3, ["Agent"]])
def test_non_subagent_tools_are_silent(tool):
    assert N.assess(tool, {"prompt": KNOWN_POSITIVE}) is None


@pytest.mark.parametrize("tool_input", [None, "x", {}, {"prompt": None}, {"prompt": 7}, {"prompt": ""}])
def test_malformed_input_is_silent(tool_input):
    assert N.assess("Agent", tool_input) is None


def test_main_emits_non_blocking_additional_context(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"prompt": KNOWN_POSITIVE}})
    assert rc == 0
    hso = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "git show @{u}:<path>" in hso["additionalContext"]
    assert "permissionDecision" not in hso


def test_main_is_silent_on_a_clean_brief(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Agent", "tool_input": {"prompt": "Fix the typo in README.md."}})
    assert rc == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", "null"])
def test_main_fails_open_on_bad_stdin(monkeypatch, capsys, stdin):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    assert N.main() == 0
    assert capsys.readouterr().out == ""


def test_advice_is_ascii():
    assert N.assess("Agent", {"prompt": KNOWN_POSITIVE}).isascii()
