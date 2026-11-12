"""Tests for topic_tagging: the judge's questions and items are built from the store, and its rows
become an engine batch plus an unsure rest. The rows here are recorded in the shape `jev-judge`
writes; the tool never calls a judge. All content ASCII.
"""

import json
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

import topic_tagging as T

import memory_engine as ME  # noqa: E402  (topic_tagging put hooks/ on sys.path at import)
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}
SCRIPT = Path(T.__file__).resolve()
ENGINE = Path(ME.__file__).resolve()


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def tree(tmp_path):
    anchor = tmp_path / "tree"
    for rel in ("", "a", "a/py", "bare"):
        level = anchor / rel
        level.mkdir(parents=True, exist_ok=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    for rel in ("", "a", "a/py"):
        assert ME.main(["set-scope", "--proj", str(anchor / rel), "--scope",
                        "WHAT: level %s\nSTACK: python" % (rel or "top")]) == 0
    ME.set_level_topics(str(anchor / "a" / "py"), ("python",))
    for slug, pin in (("feedback-one", False), ("feedback-two", False), ("feedback-pinned", True)):
        ME.add_or_update_entry(str(anchor), title="T " + slug, hook=HOOK, body="body", slug=slug, pin=pin)
    ME.add_or_update_entry(str(anchor / "bare"), title="T x", hook=HOOK, body="body", slug="feedback-x")
    return anchor


@pytest.fixture
def outside(tmp_path):
    """A working directory outside the tree, for the routes run as a subprocess."""
    d = tmp_path / "outside"
    d.mkdir()
    return d


def _run(argv, cwd, script=SCRIPT):
    return subprocess.run([sys.executable, str(script), *argv], cwd=str(cwd), capture_output=True, check=False,
                          text=True, encoding="utf-8", errors="replace", env=dict(os.environ))


def _answer(value):
    return {"type": "noul", "value": value, "probabilities": {"true": value, "false": 1 - value},
            "confidence": abs(value - 0.5) * 2}


def _row(ident, python, rust, ok=True, **extra):
    row = {"id": ident, "ok": ok, "model": "jev", "reason": None,
           "answers": {"python": _answer(python), "rust": _answer(rust)}}
    row.update(extra)
    return row


def _rows_file(tmp_path, rows, name="rows.jsonl"):
    path = tmp_path / name
    path.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows),
                    encoding="utf-8")
    return str(path)


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def _decide(tmp_path, tree, rows, kind="facts", threshold="0.8", extra=()):
    out, unsure = tmp_path / "decided.jsonl", tmp_path / "unsure.jsonl"
    rc = T.main(["decide", "--from", str(tree), "--rows", _rows_file(tmp_path, rows), "--kind", kind,
                 "--threshold", threshold, "--out", str(out), "--unsure-out", str(unsure), *extra])
    return rc, out, unsure


def test_one_question_per_topic_with_the_topic_as_its_id(tree, tmp_path, capsys):
    out = tmp_path / "questions.json"
    assert T.main(["questions", "--from", str(tree / "a"), "--out", str(out)]) == 0
    questions = json.loads(out.read_text(encoding="utf-8"))
    assert [q["id"] for q in questions] == ["python", "rust"]
    assert all(q["type"] == "noul" and set(q["criteria"]) == {"true", "false"} for q in questions)
    assert LIST["rust"] in questions[1]["instructions"]
    assert json.loads(capsys.readouterr().out)["questions"] == 2


def test_fact_items_are_the_unpinned_lines_of_one_level(tree, tmp_path):
    out = tmp_path / "items.jsonl"
    assert T.main(["items", "--from", str(tree), "--facts-at", str(tree), "--out", str(out)]) == 0
    items = _lines(out)
    assert [i["id"] for i in items] == ["feedback-one", "feedback-two"]
    assert items[0]["state"] == {"title": "T feedback-one", "hook": HOOK}
    assert all(set(i) == {"id", "state"} for i in items)


def test_a_fact_already_placed_by_topic_is_an_item_once_at_its_level(tree, tmp_path, outside):
    batch = _rows_file(tmp_path, [{"slug": "feedback-one", "topics": ["python"]}], "bind.jsonl")
    assert ME.main(["set-topics", "--proj", str(tree), "--batch", batch]) == 0
    assert ME.main(["render-topics", "--proj", str(tree), "--scope", "tree"]) == 0
    level = tree / "a" / "py"
    placed = [p.slug for p in us.parse_pointer_index(
        (level / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]]
    assert placed.count("feedback-one") == 1
    out = tmp_path / "items.jsonl"
    assert T.main(["items", "--from", str(tree), "--facts-at", str(level), "--out", str(out)]) == 0
    assert [i["id"] for i in _lines(out)].count("feedback-one") == 1


def test_level_items_are_the_described_levels_below_the_top_without_their_topics_line(tree, tmp_path):
    out = tmp_path / "items.jsonl"
    assert T.main(["items", "--from", str(tree), "--levels", "--out", str(out)]) == 0
    items = _lines(out)
    assert [i["id"] for i in items] == ["a", "a/py"]
    assert items[1]["state"] == {"path": "a/py", "descriptor": "WHAT: level a/py\nSTACK: python"}


def test_decided_rows_become_a_batch_the_engine_takes(tree, tmp_path, capsys):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.95, 0.02),
                                              _row("feedback-two", 0.1, 0.05)])
    assert rc == 0 and _lines(unsure) == []
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]},
                           {"slug": "feedback-two", "topics": []}]
    assert json.loads(capsys.readouterr().out) == {
        "command": "decide", "rows": 2, "decided": 2, "unsure": 0, "out": str(out),
        "unsure_out": str(unsure)}
    assert ME.main(["set-topics", "--proj", str(tree), "--batch", str(out)]) == 0
    assert ME.read_body_topics(us.body_path(tree, "feedback-one")) == ("python",)
    assert ME.read_body_topics(us.body_path(tree, "feedback-two")) == ()


@pytest.mark.parametrize("row, reason", [
    (_row("feedback-one", 0.5, 0.0), "unsure about python (0.50)"),
    (_row("feedback-one", 0.9, 0.79), "unsure about rust (0.79)"),
    (_row("feedback-one", 0.9, 0.0, ok=False, reason="timeout"), "failed: timeout"),
    ({"id": "feedback-one", "ok": True, "answers": {"python": _answer(0.9)}}, "no answer for rust"),
    ({"id": "feedback-one", "ok": True, "answers": {"python": _answer(0.9), "rust": {"value": True}}},
     "no answer for rust"),
    ({"id": 7, "ok": True, "answers": {}}, "no string id"),
    ("not json", "line 1 is not a JSON object"),
])
def test_a_row_that_is_no_decision_goes_to_the_unsure_file_with_its_reason(tree, tmp_path, row, reason):
    rc, out, unsure = _decide(tmp_path, tree, [row])
    assert rc == 0 and _lines(out) == []
    assert [u["reason"] for u in _lines(unsure)] == [reason]


def test_the_band_bounds_are_decided_and_the_threshold_is_inclusive(tree, tmp_path):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.8, 0.2)])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}] and _lines(unsure) == []
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.6, 0.0)], threshold="0.6",
                              extra=["--band", "0.3", "0.5"])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}]


def test_a_second_row_for_one_id_is_unsure(tree, tmp_path):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.9, 0.0),
                                              _row("feedback-one", 0.0, 0.9)])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}]
    assert [u["reason"] for u in _lines(unsure)] == ["a second row for this id"]


def test_level_rows_are_keyed_by_level(tree, tmp_path):
    rc, out, _unsure = _decide(tmp_path, tree, [_row("a/py", 0.9, 0.0)], kind="levels")
    assert _lines(out) == [{"level": "a/py", "topics": ["python"]}]


def test_a_decided_fact_whose_batch_line_the_engine_would_refuse_is_unsure(tree, tmp_path):
    long_slug = "feedback-" + "a" * ME.MAX_TOPIC_BATCH_LINE_BYTES
    rc, out, unsure = _decide(tmp_path, tree, [_row(long_slug, 0.9, 0.0), _row("feedback-one", 0.9, 0.0)])
    assert rc == 0
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}]
    reasons = [u["reason"] for u in _lines(unsure)]
    assert len(reasons) == 1 and "over the %d bytes" % ME.MAX_TOPIC_BATCH_LINE_BYTES in reasons[0]
    assert ME.main(["set-topics", "--proj", str(tree), "--batch", str(out)]) == 0


def test_nothing_in_the_store_changes(tree, tmp_path):
    def snapshot():
        return {str(p): p.read_bytes() for p in sorted(tree.rglob("*"))
                if p.is_file() and not p.name.endswith(".lock")}
    before = snapshot()
    T.main(["questions", "--from", str(tree), "--out", str(tmp_path / "q.json")])
    T.main(["items", "--from", str(tree), "--levels", "--out", str(tmp_path / "i.jsonl")])
    _decide(tmp_path, tree, [_row("feedback-one", 0.9, 0.0)])
    assert snapshot() == before


@pytest.mark.parametrize("argv", [["questions"], ["items", "--levels"]])
def test_a_tree_without_a_topic_list_is_an_error(tmp_path, capsys, argv):
    anchor = tmp_path / "plain"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert T.main([*argv, "--from", str(anchor), "--out", str(tmp_path / "o")]) == 2
    captured = capsys.readouterr()
    assert "! error" in captured.err and "no topic list" in captured.err and captured.out == ""
    assert not (tmp_path / "o").exists()


def test_the_route_the_no_topic_list_error_names_works(tmp_path, outside):
    anchor = tmp_path / "plain"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    out = outside / "q.json"
    refused = _run(["questions", "--from", str(anchor), "--out", str(out)], outside)
    assert refused.returncode == 2 and "topics-set-list" in refused.stderr and not out.exists()
    spec = outside / "list.json"
    spec.write_text(json.dumps({"tagger": "jev", "topics": LIST}), encoding="utf-8")
    made = _run(["topics-set-list", "--proj", str(anchor), "--from-file", str(spec)], outside, ENGINE)
    assert made.returncode == 0, made.stderr
    done = _run(["questions", "--from", str(anchor), "--out", str(out)], outside)
    assert done.returncode == 0, done.stderr
    assert [q["id"] for q in json.loads(out.read_text(encoding="utf-8"))] == ["python", "rust"]


def test_a_missing_rows_file_and_a_bad_threshold_are_errors(tree, tmp_path, capsys):
    out, unsure = str(tmp_path / "d"), str(tmp_path / "u")
    base = ["decide", "--from", str(tree), "--kind", "facts", "--out", out, "--unsure-out", unsure]
    assert T.main([*base, "--rows", str(tmp_path / "none.jsonl"), "--threshold", "0.8"]) == 2
    assert "cannot read" in capsys.readouterr().err
    assert T.main([*base, "--rows", _rows_file(tmp_path, []), "--threshold", "1.5"]) == 2
    assert "probabilities" in capsys.readouterr().err


def _write_rows(path, count, start=0):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for n in range(start, start + count):
            fh.write(json.dumps(_row("feedback-n%06d" % n, 0.9, 0.0)) + "\n")


def test_rows_over_the_engine_batch_limit_are_refused_and_the_split_route_works(tree, outside):
    limit = ME.MAX_TOPIC_BATCH
    whole = outside / "rows.jsonl"
    _write_rows(whole, limit + 1)
    out, unsure = outside / "decided.jsonl", outside / "unsure.jsonl"
    common = ["--from", str(tree), "--kind", "facts", "--threshold", "0.8"]
    refused = _run(["decide", *common, "--rows", str(whole), "--out", str(out),
                    "--unsure-out", str(unsure)], outside)
    assert refused.returncode == 2 and refused.stdout == ""
    assert "! error" in refused.stderr and str(limit) in refused.stderr and "split" in refused.stderr
    assert not out.exists() and not unsure.exists()
    lines = whole.read_text(encoding="utf-8").splitlines(keepends=True)
    total = 0
    for part, chunk in enumerate((lines[:limit], lines[limit:]), 1):
        rows = outside / ("rows-%d.jsonl" % part)
        rows.write_text("".join(chunk), encoding="utf-8")
        done = _run(["decide", *common, "--rows", str(rows), "--out", str(out),
                     "--unsure-out", str(unsure)], outside)
        assert done.returncode == 0, done.stderr
        summary = json.loads(done.stdout)
        assert summary["decided"] == len(chunk) and summary["unsure"] == 0
        total += summary["decided"]
    assert total == limit + 1


def _dir_listing(d):
    return sorted(p.name for p in d.iterdir())


@pytest.mark.parametrize("how", ["over-the-row-limit", "a-line-over-the-byte-limit"])
def test_a_refused_decide_writes_nothing(tree, tmp_path, capsys, how):
    work = tmp_path / "work"
    work.mkdir()
    rows = work / "rows.jsonl"
    if how == "over-the-row-limit":
        _write_rows(rows, ME.MAX_TOPIC_BATCH + 1)
    else:
        with open(rows, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(_row("feedback-one", 0.9, 0.0)) + "\n")
            fh.write(json.dumps(_row("feedback-two", 0.9, 0.0, note="x" * T.MAX_ROW_BYTES)) + "\n")
    out, unsure = work / "decided.jsonl", work / "unsure.jsonl"
    out.write_bytes(b"old decided\n")
    listing = _dir_listing(work)
    assert T.main(["decide", "--from", str(tree), "--rows", str(rows), "--kind", "facts",
                   "--threshold", "0.8", "--out", str(out), "--unsure-out", str(unsure)]) == 2
    assert "! error" in capsys.readouterr().err
    assert out.read_bytes() == b"old decided\n" and not unsure.exists()
    assert _dir_listing(work) == listing


def test_a_failed_items_run_leaves_no_half_file(tree, tmp_path, capsys):
    broken = tree / "zz"
    broken.mkdir()
    (broken / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (broken / "CLAUDE.local.md").write_bytes(b"\xff\xfe not utf-8\n")
    work = tmp_path / "work"
    work.mkdir()
    out = work / "items.jsonl"
    out.write_bytes(b"old items\n")
    listing = _dir_listing(work)
    assert T.main(["items", "--from", str(tree), "--levels", "--out", str(out)]) == 2
    assert "! error" in capsys.readouterr().err
    assert out.read_bytes() == b"old items\n" and _dir_listing(work) == listing
    assert T.main(["items", "--from", str(tree), "--facts-at", str(broken), "--out", str(out)]) == 2
    assert out.read_bytes() == b"old items\n" and _dir_listing(work) == listing


def _decide_peak(tmp_path, tree, count):
    rows = tmp_path / ("rows-%d.jsonl" % count)
    with open(rows, "w", encoding="utf-8") as fh:
        for n in range(count):
            fh.write(json.dumps(_row("feedback-n%06d" % n, 0.9, 0.0, note="x" * 2000)) + "\n")
    tracemalloc.start()
    try:
        T.decide(str(rows), LIST, "facts", 0.8, (0.2, 0.8), str(tmp_path / "d"), str(tmp_path / "u"))
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_rows_are_streamed_and_only_their_ids_are_kept(tree, tmp_path):
    peak_small = _decide_peak(tmp_path, tree, 200)
    peak_large = _decide_peak(tmp_path, tree, 4000)
    # 4000 rows of 2 KB are 8 MB of text; what grows is one short id per row
    assert peak_large < 1_500_000 and peak_large < peak_small + 1_000_000
