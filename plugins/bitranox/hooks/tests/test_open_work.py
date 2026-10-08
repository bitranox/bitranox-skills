"""open_work: OPEN-WORK.md as data. ASCII only.

Driven against real files in tmp_path and the repo's own live backlog; nothing of ours is patched.
"""
import datetime
import os
import re
import subprocess
from pathlib import Path

import pytest

import open_work as ow

REPO = Path(__file__).resolve().parents[4]
LIVE = REPO / "OPEN-WORK.md"
_ANY_ITEM = re.compile(r"-\s*\[[ xX]\]\s*\([^)]*\)\s*\[\d+\]")


def _item(rank, state=" ", origin="USER", what="x"):
    return "- [%s] (2026-10-01) [%d] %s: %s | size: 1 | open: o | next: n" % (state, rank, origin, what)


def _backlog(tmp_path, *lines):
    p = tmp_path / "OPEN-WORK.md"
    p.write_text(ow.HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_every_item_line_of_the_live_backlog_parses():
    lines = LIVE.read_text(encoding="utf-8").split("\n")
    raw = [ln for ln in lines if _ANY_ITEM.match(ln.strip())]
    items = [it for _, it in ow.iter_items(lines)]
    assert len(raw) > 50                      # the live file, not an empty stand-in
    assert len(items) == len(raw)
    assert all(it["what"] for it in items)
    # an extraction that shares nothing with the parser's regexes: plain string positions
    for line, it in zip(raw, items):
        s = line.strip()
        after_box = s[s.index("[") + 1:]
        state_char, rest = after_box[0], after_box[after_box.index("]") + 1:]
        raised = rest[rest.index("(") + 1:rest.index(")")]
        tail = rest[rest.index(")") + 1:]
        rank = tail[tail.index("[") + 1:tail.index("]")]
        origin = tail[tail.index("]") + 1:].split(":", 1)[0].strip()
        assert (it["state"] == "open") == (state_char == " ")
        assert (it["raised"], it["rank"], it["origin"]) == (raised, int(rank), origin)


def test_a_full_line_parses_into_its_fields():
    it = ow.parse_line("- [ ] (2026-10-05) [17] USER: build it | size: 3 | open: why | next: do")
    assert it == {"rank": 17, "raised": "2026-10-05", "state": "open", "origin": "USER",
                  "what": "build it", "size": "3", "open": "why", "next": "do", "closed": None}


def test_a_closed_line_carries_its_reason():
    it = ow.parse_line(_item(10, "x") + " | closed: done in 8.5.0")
    assert it["state"] == "closed" and it["closed"] == "done in 8.5.0"


def test_a_label_repeated_inside_a_field_stays_in_that_field():
    it = ow.parse_line("- [ ] (2026-10-05) [3] FOUND: a | size: 1 | open: see | next: x | next: y")
    assert it["next"] == "x | next: y"


def test_prose_and_the_fenced_template_are_not_items(tmp_path):
    p = _backlog(tmp_path, "```", "- [ ] (2026-01-01) [40] USER: inside a fence", "```", _item(10))
    assert [it["rank"] for it in ow.list_items(p, state="all")] == [10]


def test_list_filters_by_state(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20, "x"), _item(30))
    assert [it["rank"] for it in ow.list_items(p)] == [10, 30]
    assert [it["rank"] for it in ow.list_items(p, state="closed")] == [20]
    assert [it["rank"] for it in ow.list_items(p, state="all")] == [10, 20, 30]


def test_a_missing_backlog_lists_nothing(tmp_path):
    assert ow.list_items(tmp_path / "OPEN-WORK.md") == []


def test_an_unknown_state_is_refused(tmp_path):
    with pytest.raises(ow.MalformedField):
        ow.list_items(_backlog(tmp_path, _item(10)), state="done")


def _git_init(path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)


def test_backlog_path_is_the_git_top_level(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    deep = repo / "a" / "b"
    deep.mkdir(parents=True)
    _git_init(repo)
    # a push from a linked worktree exports GIT_DIR; it must not steer the answer
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nowhere"))
    assert ow.backlog_path(deep).resolve() == (repo / "OPEN-WORK.md").resolve()


def test_backlog_path_outside_a_repo_is_refused(tmp_path):
    with pytest.raises(ow.NotARepo):
        ow.backlog_path(tmp_path)


def _lines(p):
    return p.read_text(encoding="utf-8").split("\n")


def _add(p, rank, **kw):
    args = dict(origin="USER", what="w", size="1", open_="o", next_="n",
                today=datetime.date(2026, 10, 8))
    args.update(kw)
    return ow.add_item(p, rank, **args)


def test_a_rank_held_by_a_closed_line_is_refused_with_free_tens(tmp_path):
    p = _backlog(tmp_path, _item(10, "x"))
    with pytest.raises(ow.RankTaken, match="20"):
        _add(p, 10)


def test_a_new_line_goes_after_the_largest_smaller_rank(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(30), _item(20))      # unsorted, as the live file is
    _add(p, 25)
    ranks = [it["rank"] for _, it in ow.iter_items(_lines(p))]
    assert ranks == [10, 30, 20, 25]


def test_a_rank_below_every_item_goes_before_the_first(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    _add(p, 5)
    assert [it["rank"] for _, it in ow.iter_items(_lines(p))] == [5, 10, 20]
    assert p.read_text(encoding="utf-8").startswith(ow.HEADER)


def test_an_add_grows_the_file_by_exactly_one_line(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    before = len(_lines(p))
    _add(p, 15)
    assert len(_lines(p)) == before + 1


def test_a_missing_raised_is_today_with_a_question_mark(tmp_path):
    p = _backlog(tmp_path, _item(10))
    out = _add(p, 20)
    assert out["line"].startswith("- [ ] (2026-10-08?) [20] USER: w | size: 1")


def test_a_written_line_parses_back_to_what_was_given(tmp_path):
    p = _backlog(tmp_path)
    _add(p, 40, origin="FOUND", what="a thing", size="2 files", open_="why", next_="do it",
         raised="2026-09-30")
    assert ow.list_items(p) == [{"rank": 40, "raised": "2026-09-30", "state": "open",
                                 "origin": "FOUND", "what": "a thing", "size": "2 files",
                                 "open": "why", "next": "do it", "closed": None}]


def test_a_missing_file_is_created_with_the_header(tmp_path):
    p = tmp_path / "OPEN-WORK.md"
    _add(p, 10)
    text = p.read_text(encoding="utf-8")
    assert text.startswith(ow.HEADER) and text.endswith("\n")
    assert [it["rank"] for it in ow.list_items(p)] == [10]


@pytest.mark.parametrize("field,value", [
    ("what", "two\nlines"),
    ("what", ""),
    ("size", "1 | next: smuggled"),
    ("next_", "   "),
])
def test_a_malformed_field_is_refused_and_nothing_is_written(tmp_path, field, value):
    p = _backlog(tmp_path, _item(10))
    before = p.read_bytes()
    with pytest.raises(ow.MalformedField):
        _add(p, 20, **{field: value})
    assert p.read_bytes() == before


@pytest.mark.parametrize("kw", [{"origin": "ME"}, {"raised": "yesterday"},
                                {"raised": "2026-02-30"}, {"raised": "2026-10-08\n"},
                                {"raised": "\u0662026-10-08"}, {"origin": ["USER"]}])
def test_a_bad_origin_or_date_is_refused(tmp_path, kw):
    with pytest.raises(ow.MalformedField):
        _add(_backlog(tmp_path), 10, **kw)


@pytest.mark.parametrize("rank", [0, -10, "10", True, 2.5])
def test_a_rank_that_is_not_a_positive_integer_is_refused(tmp_path, rank):
    with pytest.raises(ow.MalformedField):
        _add(_backlog(tmp_path), rank)


def test_close_keeps_the_line_and_appends_the_reason(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    before = len(_lines(p))
    out = ow.close_item(p, 10, "shipped in 8.6.0")
    assert out["line"] == _item(10, "x") + " | closed: shipped in 8.6.0"
    assert len(_lines(p)) == before
    assert ow.list_items(p, state="closed")[0]["closed"] == "shipped in 8.6.0"


def test_close_refuses_unknown_closed_and_ambiguous_ranks(tmp_path):
    p = _backlog(tmp_path, _item(10, "x"), _item(20), _item(20))
    with pytest.raises(ow.UnknownRank):
        ow.close_item(p, 30, "r")
    with pytest.raises(ow.AlreadyClosed):
        ow.close_item(p, 10, "r")
    with pytest.raises(ow.AmbiguousRank):
        ow.close_item(p, 20, "r")


@pytest.mark.parametrize("raised", ["unknown", "2026-09-30?"])
def test_a_valid_raised_is_written_as_given(tmp_path, raised):
    p = _backlog(tmp_path, _item(10))
    out = _add(p, 20, raised=raised)
    assert out["line"].startswith("- [ ] (%s) [20]" % raised)


def test_a_refusal_for_raised_with_newline_leaves_file_unchanged(tmp_path):
    p = _backlog(tmp_path, _item(10))
    before = p.read_bytes()
    with pytest.raises(ow.MalformedField):
        _add(p, 20, raised="2026-10-08\n")
    assert p.read_bytes() == before


def test_close_without_a_reason_is_refused(tmp_path):
    with pytest.raises(ow.MalformedField):
        ow.close_item(_backlog(tmp_path, _item(10)), 10, " ")


# Every character str.splitlines() treats as a line break, built with chr() so no escape is typed.
_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029)]


@pytest.mark.parametrize("brk", _BREAKS, ids=lambda b: "U+%04X" % ord(b))
def test_require_line_refuses_every_line_separator(brk):
    with pytest.raises(ow.MalformedField):
        ow.require_line("a" + brk + "b", "what")


@pytest.mark.parametrize("brk", _BREAKS, ids=lambda b: "U+%04X" % ord(b))
def test_add_item_refuses_a_separator_and_writes_nothing(tmp_path, brk):
    p = _backlog(tmp_path, _item(10))
    before = p.read_text(encoding="utf-8")
    inj = "real" + brk + "- [ ] (2026-01-01) [1] USER: injected item, top of the list"
    with pytest.raises(ow.MalformedField):
        ow.add_item(p, 50, "FOUND", inj, "1", "o", "n")
    assert p.read_text(encoding="utf-8") == before


def test_a_lone_surrogate_is_a_refusal_and_leaves_no_temp_file(tmp_path):
    _backlog(tmp_path, _item(10))
    with pytest.raises(ow.MalformedField):
        ow.add_item(tmp_path / "OPEN-WORK.md", 50, "FOUND", "bad" + chr(0xD800), "1", "o", "n")
    assert sorted(f.name for f in tmp_path.iterdir()) == ["OPEN-WORK.md"]


def test_a_failed_write_leaves_no_temp_file(tmp_path):
    # a directory squatting on the target makes os.replace fail after the temp file was written
    target = tmp_path / "sub"
    target.mkdir()
    (target / "keep").write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        ow._write(target, ["a", "b"])
    assert sorted(f.name for f in tmp_path.iterdir()) == ["sub"]


def test_a_rank_above_the_ceiling_is_refused(tmp_path):
    p = _backlog(tmp_path, _item(10))
    with pytest.raises(ow.MalformedField):
        ow.add_item(p, 1000000, "FOUND", "w", "1", "o", "n")
    assert ow.add_item(p, 999999, "FOUND", "w", "1", "o", "n")["rank"] == 999999


def test_an_existing_empty_file_gets_the_header(tmp_path):
    p = tmp_path / "OPEN-WORK.md"
    p.write_text("", encoding="utf-8")
    ow.add_item(p, 10, "USER", "w", "1", "o", "n")
    assert p.read_text(encoding="utf-8").startswith(ow.HEADER)
