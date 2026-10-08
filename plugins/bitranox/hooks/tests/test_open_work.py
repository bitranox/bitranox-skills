"""open_work: OPEN-WORK.md as data. ASCII only.

Driven against real files in tmp_path and the repo's own live backlog; nothing of ours is patched.
"""
import os
import re
import subprocess
import sys
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
