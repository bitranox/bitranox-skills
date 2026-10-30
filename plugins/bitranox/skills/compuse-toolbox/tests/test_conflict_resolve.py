"""Tests for conflict_resolve.py - resolve git merge-conflict hunks one by one. ASCII only.

Every refusal test also asserts the file's bytes are unchanged: a refusal that wrote half a
resolution is the failure this tool exists to prevent.
"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import conflict_resolve as R

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "conflict_resolve.py"

TWO_HUNKS = (
    "head\n"
    "<<<<<<< HEAD\n"
    "ours one\n"
    "=======\n"
    "theirs one\n"
    ">>>>>>> feature\n"
    "middle\n"
    "<<<<<<< HEAD\n"
    "ours two a\n"
    "ours two b\n"
    "=======\n"
    "theirs two\n"
    ">>>>>>> feature\n"
    "tail\n"
)

DIFF3 = (
    "a\n"
    "<<<<<<< ours-label\n"
    "mine\n"
    "||||||| merged common ancestors\n"
    "original\n"
    "=======\n"
    "yours\n"
    ">>>>>>> theirs-label\n"
    "z\n"
)


def _run(*args, cwd=None):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", cwd=cwd)


def _file(tmp_path, text, name="f.txt"):
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
    return p


# --- parsing ----------------------------------------------------------------------------------

def test_parse_finds_each_hunk_with_its_line_range_labels_and_sides():
    hunks = R.parse_hunks(TWO_HUNKS)
    assert [h.n for h in hunks] == [1, 2]
    first, second = hunks
    assert (first.start, first.end) == (2, 6)
    assert (second.start, second.end) == (8, 13)
    assert (first.ours_label, first.theirs_label) == ("HEAD", "feature")
    assert first.ours == ["ours one\n"] and first.theirs == ["theirs one\n"]
    assert second.ours == ["ours two a\n", "ours two b\n"]
    assert first.base is None


def test_parse_reads_a_diff3_base_section():
    (hunk,) = R.parse_hunks(DIFF3)
    assert hunk.base == ["original\n"]
    assert hunk.base_label == "merged common ancestors"
    assert hunk.ours == ["mine\n"] and hunk.theirs == ["yours\n"]


def test_a_marker_needs_exactly_seven_chars_then_a_space_or_end():
    # eight '<' is not a marker, and neither is '<<<<<<<x'; both are ordinary text
    assert R.parse_hunks("<<<<<<<< not\n<<<<<<<x not\n") == []


@pytest.mark.parametrize("text, why", [
    ("<<<<<<< a\nx\n=======\ny\n", "unclosed"),
    ("<<<<<<< a\nx\n>>>>>>> b\n", "no separator"),
    ("<<<<<<< a\n<<<<<<< b\nx\n=======\ny\n>>>>>>> c\n", "nested open"),
    ("x\n>>>>>>> b\n", "stray close"),
    ("x\n||||||| base\n", "stray base"),
    ("<<<<<<< a\nx\n=======\ny\n=======\nz\n>>>>>>> b\n", "second separator"),
    ("<<<<<<< a\nx\n=======\ny\n||||||| base\n>>>>>>> b\n", "base after separator"),
    ("before\n=======\nafter\n", "half-resolved lone separator"),
])
def test_malformed_markers_are_refused(text, why):
    with pytest.raises(R.Refusal):
        R.parse_hunks(text)


def test_a_setext_heading_underline_outside_a_hunk_is_text():
    assert R.parse_hunks("Title\n=======\n\nbody\n") == []


# --- rules --------------------------------------------------------------------------------------

@pytest.mark.parametrize("rule, expected", [
    ("ours", "head\nours one\nmiddle\n"),
    ("theirs", "head\ntheirs one\nmiddle\n"),
    ("both", "head\nours one\ntheirs one\nmiddle\n"),
    ("both-theirs-first", "head\ntheirs one\nours one\nmiddle\n"),
])
def test_each_side_rule(rule, expected):
    text = "head\n<<<<<<< HEAD\nours one\n=======\ntheirs one\n>>>>>>> b\nmiddle\n"
    out = R.resolve_text(text, R.assign_rules(R.parse_hunks(text), by_number={1: R.parse_rule(rule)}))
    assert out == expected


def test_base_rule_on_a_diff3_hunk():
    hunks = R.parse_hunks(DIFF3)
    assert R.resolve_text(DIFF3, R.assign_rules(hunks, default=R.parse_rule("base"))) == \
        "a\noriginal\nz\n"


@pytest.mark.parametrize(("rule", "expected"), [
    ("both", "a\nmine\nyours\nz\n"),
    ("both-theirs-first", "a\nyours\nmine\nz\n"),
])
def test_both_rules_on_a_diff3_hunk_drop_the_base_section(rule, expected):
    hunks = R.parse_hunks(DIFF3)
    assert R.resolve_text(DIFF3, R.assign_rules(hunks, default=R.parse_rule(rule))) == expected


def test_base_rule_on_a_plain_hunk_is_refused():
    hunks = R.parse_hunks(TWO_HUNKS)
    with pytest.raises(R.Refusal, match="base"):
        R.assign_rules(hunks, default=R.parse_rule("base"))


def test_file_rule_replaces_the_hunk_with_that_file_converting_its_line_endings(tmp_path):
    repl = tmp_path / "r.txt"
    repl.write_bytes(b"merged a\nmerged b")      # LF, and no final newline
    text = "x\r\n<<<<<<< HEAD\r\nours\r\n=======\r\ntheirs\r\n>>>>>>> b\r\ny\r\n"
    rules = R.assign_rules(R.parse_hunks(text), by_number={1: R.parse_rule("file:%s" % repl)})
    # the replacement takes the hunk's own CRLF and gains the terminator it needs to stay a line
    assert R.resolve_text(text, rules) == "x\r\nmerged a\r\nmerged b\r\ny\r\n"


@pytest.mark.parametrize("bad", ["", "mine", "file:", "both-ours-first"])
def test_an_unknown_rule_is_a_usage_error(bad):
    with pytest.raises(R.UsageError):
        R.parse_rule(bad)


def test_split_match_spec_keeps_an_equals_sign_inside_the_regex():
    regex, rule = R.split_match_spec("a=b=theirs")
    assert regex == "a=b" and rule.kind == "theirs"
    regex, rule = R.split_match_spec("x=file:/p/a=b.txt")
    assert regex == "x" and rule.kind == "file" and rule.path == "/p/a=b.txt"
    # the one spelling where first and last valid split differ: the LAST one is documented
    regex, rule = R.split_match_spec("k=file:a=theirs")
    assert regex == "k=file:a" and rule.kind == "theirs"


def test_all_is_a_fallback_an_explicit_rule_overrides():
    hunks = R.parse_hunks(TWO_HUNKS)
    rules = R.assign_rules(hunks, by_number={2: R.parse_rule("ours")}, default=R.parse_rule("theirs"))
    assert [r.kind for r in rules] == ["theirs", "ours"]


def test_match_selects_a_hunk_by_the_text_of_either_side():
    hunks = R.parse_hunks(TWO_HUNKS)
    rules = R.assign_rules(hunks, by_match=[("theirs two", R.parse_rule("ours")),
                                            ("^ours one$", R.parse_rule("theirs"))])
    assert [r.kind for r in rules] == ["theirs", "ours"]


@pytest.mark.parametrize("kwargs, needle", [
    ({"by_number": {3: "ours"}}, "no hunk 3"),
    ({"by_number": {0: "ours"}}, "no hunk 0"),
    ({"by_number": {1: "ours"}}, "no rule"),                       # hunk 2 has none
    ({"by_number": {1: "ours", 2: "ours"}, "by_match": [("theirs two", "theirs")]}, "more than one"),
    ({"by_match": [("nowhere", "ours")], "default": "theirs"}, "matches no hunk"),
    ({"by_match": [("ours", "ours")], "default": "theirs"}, "matches 2 hunks"),
])
def test_assignment_refusals(kwargs, needle):
    hunks = R.parse_hunks(TWO_HUNKS)
    conv = {"by_number": {k: R.parse_rule(v) for k, v in kwargs.get("by_number", {}).items()},
            "by_match": [(rx, R.parse_rule(v)) for rx, v in kwargs.get("by_match", [])],
            "default": R.parse_rule(kwargs["default"]) if "default" in kwargs else None}
    with pytest.raises(R.Refusal, match=needle):
        R.assign_rules(hunks, **conv)


# --- line endings -------------------------------------------------------------------------------

def test_crlf_file_is_preserved_byte_for_byte(tmp_path):
    raw = TWO_HUNKS.replace("\n", "\r\n").encode()
    p = _file(tmp_path, raw)
    proc = _run(p, "--all", "theirs")
    assert proc.returncode == 0, proc.stderr
    assert p.read_bytes() == b"head\r\ntheirs one\r\nmiddle\r\ntheirs two\r\ntail\r\n"


def test_a_hunk_at_the_end_of_a_file_with_no_final_newline_keeps_it_that_way(tmp_path):
    p = _file(tmp_path, "a\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> b")
    proc = _run(p, "--hunk", "1=both")
    assert proc.returncode == 0, proc.stderr
    assert p.read_bytes() == b"a\nours\ntheirs"


def test_a_file_without_a_final_newline_after_the_hunk_keeps_it(tmp_path):
    p = _file(tmp_path, "<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> b\nlast")
    assert _run(p, "--all", "ours").returncode == 0
    assert p.read_bytes() == b"ours\nlast"


def test_a_utf8_bom_and_non_utf8_bytes_survive(tmp_path):
    raw = b"\xef\xbb\xbf<<<<<<< HEAD\ncaf\xe9\n=======\nx\n>>>>>>> b\n\xff tail\n"
    p = _file(tmp_path, raw)
    assert _run(p, "--all", "ours").returncode == 0
    assert p.read_bytes() == b"\xef\xbb\xbfcaf\xe9\n\xff tail\n"


# --- the CLI: writes, refusals, list, json ----------------------------------------------------

def test_cli_resolves_and_reports_clean(tmp_path):
    p = _file(tmp_path, TWO_HUNKS)
    proc = _run(p, "--hunk", "1=ours", "--hunk", "2=theirs", "--expect-hunks", "2")
    assert proc.returncode == 0, proc.stderr
    assert p.read_text() == "head\nours one\nmiddle\ntheirs two\ntail\n"
    assert "hunk 1" in proc.stdout and "no markers remain" in proc.stdout


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows has no POSIX mode bits: os.chmod(0o750) only clears read-only and reads back as 0o666")
def test_cli_preserves_the_file_mode(tmp_path):
    p = _file(tmp_path, TWO_HUNKS)
    os.chmod(p, 0o750)
    assert _run(p, "--all", "ours").returncode == 0
    assert stat.S_IMODE(p.stat().st_mode) == 0o750


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs a privilege on Windows")
def test_cli_writes_through_a_symlink_and_keeps_the_link(tmp_path):
    real = _file(tmp_path, TWO_HUNKS, "real.txt")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    assert _run(link, "--all", "ours").returncode == 0
    assert link.is_symlink()
    assert real.read_text() == "head\nours one\nmiddle\nours two a\nours two b\ntail\n"


@pytest.mark.parametrize("args", [
    ["--expect-hunks", "3", "--all", "ours"],
    ["--hunk", "5=ours", "--all", "ours"],
    ["--hunk", "1=ours"],
    ["--hunk", "1=ours", "--match", "ours one=theirs", "--all", "ours"],
    ["--match", "nothing here=ours", "--all", "ours"],
    ["--match", "ours=ours", "--all", "theirs"],
    ["--all", "base"],
    [],
])
def test_cli_refusals_write_nothing_and_exit_2(tmp_path, args):
    p = _file(tmp_path, TWO_HUNKS)
    before = p.read_bytes()
    proc = _run(p, *args)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert p.read_bytes() == before
    assert "refused" in proc.stderr
    assert not [x for x in tmp_path.iterdir() if x.name != "f.txt"]   # no temp file left behind


def test_cli_malformed_file_is_refused_and_untouched(tmp_path):
    p = _file(tmp_path, "<<<<<<< a\nx\n=======\ny\n")
    before = p.read_bytes()
    proc = _run(p, "--all", "ours", "--json")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and payload["data"]["refused"] is True
    assert p.read_bytes() == before


def test_cli_list_writes_nothing_and_shows_each_hunk(tmp_path):
    p = _file(tmp_path, TWO_HUNKS)
    before = p.read_bytes()
    proc = _run(p, "--list")
    assert proc.returncode == 0, proc.stderr
    assert p.read_bytes() == before
    out = proc.stdout
    assert "hunk 1" in out and "lines 2-6" in out and "HEAD" in out and "feature" in out
    assert "ours two b" in out and "theirs two" in out


def test_cli_list_shows_only_the_first_three_lines_of_a_side(tmp_path):
    text = "<<<<<<< HEAD\n1\n2\n3\nFOURTH\n=======\nt\n>>>>>>> b\n"
    proc = _run(_file(tmp_path, text), "--list", "--json")
    assert proc.returncode == 0
    (hunk,) = json.loads(proc.stdout)["data"]["hunks"]
    assert hunk["ours"] == ["1", "2", "3"] and hunk["ours_lines"] == 4
    assert hunk["base"] is None and hunk["labels"] == {"ours": "HEAD", "base": None, "theirs": "b"}


def test_cli_list_refuses_to_combine_with_rules(tmp_path):
    assert _run(_file(tmp_path, TWO_HUNKS), "--list", "--all", "ours").returncode == 2


def test_cli_json_envelope_shape(tmp_path):
    p = _file(tmp_path, TWO_HUNKS)
    proc = _run(p, "--all", "theirs", "--hunk", "1=ours", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert list(payload) == ["ok", "command", "data", "skipped"]
    assert payload["ok"] is True and payload["command"] == "conflict_resolve"
    assert payload["data"]["hunks"] == [{"n": 1, "rule": "ours", "lines": [2, 6]},
                                        {"n": 2, "rule": "theirs", "lines": [8, 13]}]
    assert payload["data"]["remaining_markers"] == []


def test_cli_zero_hunks_is_exit_0_and_leaves_the_file_alone(tmp_path):
    p = _file(tmp_path, "clean\n")
    mtime = p.stat().st_mtime_ns
    proc = _run(p, "--all", "ours", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["data"]["hunks"] == [] and payload["data"]["written"] is False
    assert "no conflict hunks" in payload["data"]["note"]
    assert p.stat().st_mtime_ns == mtime


def test_cli_rescan_reports_markers_left_by_a_replacement_and_exits_1(tmp_path):
    repl = tmp_path / "r.txt"
    repl.write_text("<<<<<<< still here\n", encoding="utf-8")
    p = _file(tmp_path, TWO_HUNKS)
    proc = _run(p, "--hunk", "1=file:%s" % repl, "--hunk", "2=ours", "--json")
    assert proc.returncode == 1, proc.stderr
    data = json.loads(proc.stdout)["data"]
    assert data["written"] is True
    assert data["remaining_markers"] == [{"line": 2, "text": "<<<<<<< still here"}]


def test_cli_unreadable_file_is_exit_2(tmp_path):
    proc = _run(tmp_path / "missing.txt", "--all", "ours", "--json")
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["ok"] is False


def test_cli_unreadable_replacement_file_is_exit_2_and_writes_nothing(tmp_path):
    p = _file(tmp_path, TWO_HUNKS)
    before = p.read_bytes()
    proc = _run(p, "--all", "file:%s" % (tmp_path / "nope.txt"))
    assert proc.returncode == 2
    assert p.read_bytes() == before


def test_cli_bad_rule_is_a_usage_error_with_an_envelope(tmp_path):
    proc = _run(_file(tmp_path, TWO_HUNKS), "--all", "mine", "--json")
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["ok"] is False


def test_changelog_both_sides_newer_first(tmp_path):
    # the CHANGELOG case: both branches added an entry under the same heading; keep both, the
    # incoming (newer) one on top
    text = ("# Changelog\n"
            "<<<<<<< HEAD\n## 1.2.0\n- ours\n"
            "=======\n## 1.3.0\n- theirs\n"
            ">>>>>>> release\n"
            "## 1.1.0\n")
    p = _file(tmp_path, text, "CHANGELOG.md")
    assert _run(p, "--all", "both-theirs-first", "--expect-hunks", "1").returncode == 0
    assert p.read_text() == "# Changelog\n## 1.3.0\n- theirs\n\n## 1.2.0\n- ours\n## 1.1.0\n"


# --- joining two Markdown sides keeps a heading's separating blank line -------------------------
# Measured: both-theirs-first on a CHANGELOG hunk (a new '### Fixed' block against an upstream
# '## [1.15.3]' block) left '...alike.\n## [1.15.3]'; the tool said no markers remain and a
# formatter check passed, and only reading the result caught it.

CHANGELOG_HUNK = ("<<<<<<< HEAD\n## [1.15.3] - 2026-10-01\n- upstream fix\n"
                  "=======\n### Fixed\n- both platforms alike.\n"
                  ">>>>>>> topic\n")


def _joined(rule, markdown, text=CHANGELOG_HUNK):
    return R.resolve_text(text, [R.parse_rule(rule)], markdown=markdown)


def test_joining_markdown_sides_puts_a_blank_line_before_a_heading():
    assert _joined("both-theirs-first", True) == (
        "### Fixed\n- both platforms alike.\n\n## [1.15.3] - 2026-10-01\n- upstream fix\n")


def test_joining_markdown_sides_puts_a_blank_line_after_a_closing_heading():
    text = "<<<<<<< a\n## [Unreleased]\n=======\n- an item\n>>>>>>> b\n"
    assert _joined("both", True, text) == "## [Unreleased]\n\n- an item\n"


def test_sides_already_separated_get_no_second_blank_line():
    text = "<<<<<<< a\n## 1.2.0\n- ours\n\n=======\n## 1.3.0\n- theirs\n>>>>>>> b\n"
    assert _joined("both", True, text) == "## 1.2.0\n- ours\n\n## 1.3.0\n- theirs\n"


def test_a_non_markdown_file_is_joined_unchanged():
    """A '#' line in Python is a comment, not a heading; its spacing is not this tool's call."""
    assert _joined("both-theirs-first", False) == (
        "### Fixed\n- both platforms alike.\n## [1.15.3] - 2026-10-01\n- upstream fix\n")


def test_the_blank_line_takes_the_hunks_line_ending():
    text = CHANGELOG_HUNK.replace("\n", "\r\n")
    assert "alike.\r\n\r\n## [1.15.3]" in _joined("both-theirs-first", True, text)


def test_the_cli_treats_a_dot_md_file_as_markdown(tmp_path):
    p = _file(tmp_path, CHANGELOG_HUNK, "CHANGELOG.md")
    assert _run(p, "--all", "both-theirs-first").returncode == 0
    assert "alike.\n\n## [1.15.3]" in p.read_text()
    q = _file(tmp_path, CHANGELOG_HUNK, "notes.py")
    assert _run(q, "--all", "both-theirs-first").returncode == 0
    assert "alike.\n## [1.15.3]" in q.read_text()
