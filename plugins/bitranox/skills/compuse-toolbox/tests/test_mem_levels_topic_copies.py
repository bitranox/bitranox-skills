"""Tests for how mem_levels reports a fact held at several levels: one the engine places by topic
is listed as placed, anything else stays a duplicate pointer. All content ASCII.
"""

from pathlib import Path

import mem_levels

BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->
<!-- bitranox:self-learning -->
WHAT: a level
<!-- /bitranox:self-learning -->

## Memory index
{rows}
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


def _tree(root: Path, levels: dict[str, list[str]], frames: dict[str, str]) -> Path:
    """{relative level dir: [pointer lines]} plus {slug: extra frontmatter lines}."""
    for rel, rows in levels.items():
        d = root / rel if rel != "." else root
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.local.md").write_text(BLOCK.format(rows="\n".join(rows)), encoding="utf-8")
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True, exist_ok=True)
    for slug, extra in frames.items():
        (facts / (slug + ".md")).write_text("---\nname: %s\n%s---\n\nbody\ntopics: [prose]\n"
                                            % (slug, extra), encoding="utf-8")
    return root


# what the engine builds a pointer line from: without both it never places a fact by topic
LINE = "title: T\ndescription: When x, do y.\n"


def _row(slug, pin=False):
    return "- [T](mem:%s) - When x, do y.%s" % (slug, " <!-- bx:pin -->" if pin else "")


def test_a_topic_bound_fact_at_two_levels_is_placed_not_a_duplicate(tmp_path, capsys):
    root = _tree(tmp_path / "t", {"a": [_row("py-rule")], "b": [_row("py-rule")]},
                 {"py-rule": LINE + "topics: [python]\n"})
    report = mem_levels.scan(root)
    assert report.placed == {"py-rule": ["a", "b"]} and report.duplicates == {}
    assert report.as_dict()["placed"] == {"py-rule": ["a", "b"]}
    assert mem_levels.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "= placed by topic: py-rule at a, b" in out and "duplicate pointer" not in out


def test_an_untagged_an_unbound_and_a_pinned_fact_stay_duplicates(tmp_path):
    rows = {"a": [_row("plain"), _row("universal"), _row("pinned", pin=True)],
            "b": [_row("plain"), _row("universal"), _row("pinned")]}
    root = _tree(tmp_path / "t", rows, {"plain": LINE, "universal": LINE + "topics: []\n",
                                        "pinned": LINE + "topics: [python]\n"})
    report = mem_levels.scan(root)
    assert report.placed == {} and sorted(report.duplicates) == ["pinned", "plain", "universal"]


def test_a_topics_line_in_the_prose_is_no_binding(tmp_path):
    # a title and description in the frame, and a `topics:` line only in the prose below it
    root = _tree(tmp_path / "t", {"a": [_row("plain")], "b": [_row("plain")]}, {"plain": LINE})
    assert mem_levels.scan(root).duplicates == {"plain": ["a", "b"]}


def test_a_bound_fact_without_a_title_or_description_or_a_valid_topic_stays_a_duplicate(tmp_path):
    rows = {"a": [_row("untitled"), _row("undescribed"), _row("bad-tag"), _row("bare")],
            "b": [_row("untitled"), _row("undescribed"), _row("bad-tag"), _row("bare")]}
    root = _tree(tmp_path / "t", rows, {
        "untitled": "description: When x, do y.\ntopics: [python]\n",
        "undescribed": "title: T\ntopics: [python]\n",
        "bad-tag": LINE + "topics: [Not A Tag]\n",
        "bare": LINE + "topics: python\n"})
    report = mem_levels.scan(root)
    assert report.placed == {"bare": ["a", "b"]}
    assert sorted(report.duplicates) == ["bad-tag", "undescribed", "untitled"]
