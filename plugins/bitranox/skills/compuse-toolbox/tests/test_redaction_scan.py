"""Tests for redaction_scan.py - do the lines a change ADDS hold a name from a private list?

Every name here is INVENTED (Zorblax, Quuxhaven, Plinkett Labs). This is a public repo: no real
redaction list is ever copied or read by a test.

The two hand-rolled traps the jig replaces are pinned first: a bare `#` comment line in the list
matching every `#` in the change, and a `name==>replacement` rule searched as its whole text and
so never matching the name.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import redaction_scan as R

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "redaction_scan.py"
_GIT_TIMEOUT = 30
_CLI_TIMEOUT = 60

LIST_TEXT = ("# private names, never publish\n"
             "#\n"
             "\n"
             "Zorblax==>Room1\n"
             "  quuxhaven  ==> Site2\n"
             "Plinkett Labs\n")


def _diff(*lines: str, path: str = "doc.md") -> str:
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1,3 +1,3 @@\n"
            + "".join(f"{line}\n" for line in lines))


RULES = R.parse_rules(LIST_TEXT).rules


# ---- the list format -------------------------------------------------------------------------

def test_the_list_parses_comments_blanks_and_the_text_before_the_separator():
    parsed = R.parse_rules(LIST_TEXT)
    assert [r.pattern for r in parsed.rules] == ["Zorblax", "quuxhaven", "Plinkett Labs"]
    assert [r.list_line for r in parsed.rules] == [4, 5, 6]
    assert (parsed.comment_lines, parsed.blank_lines) == (2, 1)


def test_a_bare_hash_comment_line_does_not_match_every_hash():
    """`grep -Ff list` reads the `#` line as a pattern and hits every `#` in the change."""
    hits, read = R.scan_diff(_diff("+# a heading", "+x = 1  # a comment"), RULES)
    assert read == 2
    assert hits == []


def test_a_rule_with_a_replacement_matches_the_name_and_not_the_whole_rule():
    """`grep -Ff list` searches `Zorblax==>Room1` literally, which never appears."""
    hits, _ = R.scan_diff(_diff("+the Zorblax speaker"), RULES)
    assert [h.rule.pattern for h in hits] == ["Zorblax"]
    hits, _ = R.scan_diff(_diff("+only Room1 appears here"), RULES)
    assert hits == []


def test_matching_is_case_insensitive():
    hits, _ = R.scan_diff(_diff("+ZORBLAX and plinkett labs"), RULES)
    assert sorted(h.rule.pattern for h in hits) == ["Plinkett Labs", "Zorblax"]


def test_matching_is_literal_not_a_regex():
    rules = R.parse_rules("a.c\n").rules
    assert R.scan_diff(_diff("+abc"), rules)[0] == []
    assert len(R.scan_diff(_diff("+a.c"), rules)[0]) == 1


def test_a_rule_empty_before_the_separator_is_counted_and_never_used():
    parsed = R.parse_rules("==>Room1\n   ==>x\nZorblax\n")
    assert [r.pattern for r in parsed.rules] == ["Zorblax"]
    assert parsed.empty_rules == 2


# ---- only added lines count --------------------------------------------------------------------

def test_only_added_lines_count_never_removed_or_context_lines():
    diff = _diff(" context with Zorblax", "-removed Zorblax", "+added clean")
    hits, read = R.scan_diff(diff, RULES)
    assert hits == [] and read == 1


def test_an_added_hit_is_located_by_file_and_new_file_line():
    diff = ("diff --git a/a.md b/a.md\n--- a/a.md\n+++ b/a.md\n@@ -10,0 +11,2 @@\n"
            "+first\n+second Quuxhaven\n")
    hits, _ = R.scan_diff(diff, RULES)
    assert [(h.location, h.line, h.rule.index) for h in hits] == [("a.md", 12, 2)]


def test_the_file_header_is_not_an_added_line():
    diff = ("diff --git a/Zorblax.md b/Zorblax.md\n--- /dev/null\n+++ b/Zorblax.md\n"
            "@@ -0,0 +1 @@\n+ok\n")
    hits, read = R.scan_diff(diff, RULES)
    assert read == 1 and hits == []


# ---- the liveness control ----------------------------------------------------------------------

def test_the_control_passes_for_every_parsed_pattern():
    assert R.control_failures(RULES) == []


def test_the_control_names_every_rule_a_broken_matcher_cannot_see():
    """The control's own RED: a matcher that sees nothing fails every rule."""
    assert R.control_failures(RULES, lambda text, rules: []) == list(RULES)


def test_the_control_names_the_one_rule_a_partial_matcher_misses():
    def blind_to_the_second(text, rules):
        return [r for r in R.match_rules(text, rules) if r.index != 2]

    assert [r.index for r in R.control_failures(RULES, blind_to_the_second)] == [2]


def test_a_sharp_s_matches_its_capitalised_spelling():
    """casefold, not lower: lower() leaves the sharp s alone, so STRASSE never matched it."""
    rules = R.parse_rules("Hauptstra\u00dfe\n").rules
    assert len(R.scan_diff(_diff("+HAUPTSTRASSE 1"), rules)[0]) == 1
    assert R.control_failures(rules) == []


# ---- the CLI against a real repository --------------------------------------------------------

def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True,
                   timeout=_GIT_TIMEOUT)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.test")
    _git(repo, "config", "user.name", "t")
    (repo / "doc.md").write_text("old line mentioning Zorblax\nkeep\n", encoding="utf-8")
    _git(repo, "add", "doc.md")
    _git(repo, "commit", "-qm", "seed")
    return repo


def _list(tmp_path: Path, text: str = LIST_TEXT) -> Path:
    path = tmp_path / "names.txt"
    path.write_text(text, encoding="utf-8")
    return path


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", check=False, timeout=_CLI_TIMEOUT)


def test_cli_a_range_adding_a_name_exits_1_and_names_file_line_and_rule(tmp_path):
    repo = _repo(tmp_path)
    (repo / "doc.md").write_text("old line mentioning Zorblax\nkeep\nnew Quuxhaven line\n",
                                 encoding="utf-8")
    _git(repo, "commit", "-qam", "add a line")
    r = run_cli("--list", str(_list(tmp_path)), "--range", "HEAD~1..HEAD", "--json",
                cwd=repo)
    assert r.returncode == 1, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is True
    data = env["data"]
    assert data["patterns"] == 3 and data["comment_lines"] == 2 and data["control"] == "fired"
    assert data["added_lines_scanned"] == 1
    assert [(h["file"], h["line"], h["pattern_index"], h["pattern"]) for h in data["hits"]] \
        == [("doc.md", 3, 2, "quuxhaven")]


def test_cli_a_name_only_in_a_removed_line_is_clean(tmp_path):
    """The commit REMOVING a leak must not read as adding it."""
    repo = _repo(tmp_path)
    (repo / "doc.md").write_text("old line, now clean\nkeep\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "drop the name")
    r = run_cli("--list", str(_list(tmp_path)), "--range", "HEAD~1..HEAD", "--json", cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["data"]["hits"] == []


def test_cli_a_name_in_a_commit_message_is_a_hit(tmp_path):
    repo = _repo(tmp_path)
    (repo / "other.md").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "other.md")
    _git(repo, "commit", "-qm", "tune the Plinkett Labs speaker")
    r = run_cli("--list", str(_list(tmp_path)), "--range", "HEAD~1..HEAD", "--json", cwd=repo)
    assert r.returncode == 1, r.stdout + r.stderr
    hit = json.loads(r.stdout)["data"]["hits"][0]
    assert hit["file"].startswith("commit ") and hit["file"].endswith(" message")


def test_cli_redact_hits_prints_neither_the_pattern_nor_the_line(tmp_path):
    repo = _repo(tmp_path)
    (repo / "new.md").write_text("Quuxhaven\n", encoding="utf-8")
    _git(repo, "add", "new.md")
    for flag in ("--json-bare", None):
        args = ["--list", str(_list(tmp_path)), "--staged", "--redact-hits"]
        r = run_cli(*args, *([flag] if flag else []), cwd=repo)
        assert r.returncode == 1, r.stdout + r.stderr
        assert "quuxhaven" not in (r.stdout + r.stderr).lower()
    env = json.loads(run_cli("--list", str(_list(tmp_path)), "--staged", "--redact-hits",
                             "--json-bare", cwd=repo).stdout)
    hit = env["data"]["hits"][0]
    assert hit["pattern_index"] == 2 and hit["list_line"] == 5 and len(hit["pattern_hash"]) == 12
    assert "pattern" not in hit and "excerpt" not in hit


def test_cli_staged_scans_the_index_not_the_worktree(tmp_path):
    repo = _repo(tmp_path)
    (repo / "staged.md").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "staged.md")
    (repo / "loose.md").write_text("Zorblax\n", encoding="utf-8")        # untracked, not staged
    r = run_cli("--list", str(_list(tmp_path)), "--staged", "--json", cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    r = run_cli("--list", str(_list(tmp_path)), "--worktree", "--json", cwd=repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert [h["file"] for h in json.loads(r.stdout)["data"]["hits"]] == ["loose.md"]


def test_cli_worktree_skips_an_ignored_file(tmp_path):
    repo = _repo(tmp_path)
    (repo / ".gitignore").write_text("secret-*.txt\n", encoding="utf-8")
    (repo / "secret-local.txt").write_text("Zorblax\n", encoding="utf-8")
    r = run_cli("--list", str(_list(tmp_path)), "--worktree", "--json", cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["data"]["added_lines_scanned"] == 1        # the .gitignore line


def test_cli_an_empty_list_is_refused(tmp_path):
    repo = _repo(tmp_path)
    (repo / "new.md").write_text("Zorblax\n", encoding="utf-8")
    _git(repo, "add", "new.md")
    r = run_cli("--list", str(_list(tmp_path, "# only comments\n\n")), "--staged", "--json",
                cwd=repo)
    assert r.returncode == 2
    env = json.loads(r.stdout)
    assert env["ok"] is False and "zero patterns" in env["error"]


def test_cli_a_change_adding_nothing_is_refused_not_clean(tmp_path):
    repo = _repo(tmp_path)
    r = run_cli("--list", str(_list(tmp_path)), "--staged", "--json", cwd=repo)
    assert r.returncode == 2
    assert json.loads(r.stdout)["data"]["added_lines_scanned"] == 0


def test_cli_a_missing_list_is_refused_with_an_envelope(tmp_path):
    r = run_cli("--list", str(tmp_path / "absent.txt"), "--staged", "--json", cwd=tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


def test_cli_a_bad_range_is_refused(tmp_path):
    repo = _repo(tmp_path)
    r = run_cli("--list", str(_list(tmp_path)), "--range", "nope..HEAD", "--json", cwd=repo)
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


def test_cli_a_usage_error_still_prints_the_envelope(tmp_path):
    r = run_cli("--json-bare", "--staged", cwd=tmp_path)                 # --list missing
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


def test_cli_a_failing_control_refuses_rather_than_report_clean(tmp_path, capsys):
    """Through the matcher seam: with a blind matcher a clean answer must be impossible."""
    repo = _repo(tmp_path)
    (repo / "new.md").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "new.md")
    args = ["--list", str(_list(tmp_path)), "--staged", "--repo", str(repo)]
    assert R.execute(args) == 0                                           # control: it can pass
    assert R.execute(args, matcher=lambda text, rules: []) == 2
    assert "liveness control failed: a planted added line holding rule #1, #2, #3" \
        in capsys.readouterr().err


@pytest.mark.parametrize("bom", [b"\xef\xbb\xbf", b""])
def test_a_bom_does_not_glue_onto_the_first_pattern(tmp_path, bom):
    path = tmp_path / "bom.txt"
    path.write_bytes(bom + b"Zorblax\n")
    assert [r.pattern for r in R.parse_rules(R.read_list(str(path))).rules] == ["Zorblax"]
