"""--repair-appended-type against a concurrent writer: the title and hook it keeps are the stored
ones at the moment of its write, never the ones its walk read before.

The repair walks every level for the pointer of each damaged body, then re-reads the body, then
writes. A retitle (or a hook change) landing between that walk and the write was undone when the
walk's title and hook were passed to the write. Each test drives the other writer in a real second
process.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

import reconcile_memory_index as R

import memory_engine as ME  # reconcile put hooks/ on sys.path at import
import uuid_store as us

HOOKS = str(Path(ME.__file__).resolve().parent)

RULE_BODY = "---\nA body that opens with a horizontal rule.\n\n---\n\nMore prose below.\n"


def _old_retype(text: str, type_: str) -> str:
    """The damaging re-type as it ran before the frontmatter fix (the same fixture as
    test_reconcile_memory_index.py uses), so the body carries the real damage."""
    head = (text or "").lstrip()
    end = head.find("\n---", 3)
    front, rest = (head[:end], head[end:]) if end > 0 else (head, "")
    return front + "\nmetadata:\n  type: %s" % type_ + rest


def _tree(tmp_path: Path) -> str:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    return str(root)


def _damage(level: str, slug: str) -> Path:
    """Write the appended-type damage over `slug`'s body, under the level lock every engine
    writer of that level takes, so it never interleaves with a write in flight."""
    p = us.body_path(Path(ME.anchor_dir(level)), slug)
    with ME.sig.memory_lock(ME.sig.claude_local_md_path(level)):
        p.write_text(_old_retype(RULE_BODY, "feedback") + "\n", encoding="utf-8", newline="")
    return p


def _line(level: str, slug: str) -> us.Pointer:
    text = Path(level, "CLAUDE.local.md").read_text(encoding="utf-8")
    return next(p for p in us.parse_pointer_index(text)[1] if p.slug == slug)


def _run_engine(code: str, level: str) -> None:
    """Run `code` in a second Python process with the engine imported as E and LEVEL bound."""
    script = "import sys\nsys.path.insert(0, %r)\nimport memory_engine as E\nLEVEL = %r\n%s\n" % (
        HOOKS, level, code)
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def test_a_retitle_between_the_walk_and_the_write_is_kept(tmp_path):
    """The other process retitles the fact after the repair's walk read the pointer and before it
    writes (the body re-read is that moment). The repaired fact keeps the new title, in the
    pointer line and in the body's `title:`."""
    level = _tree(tmp_path)
    slug = ME.add_or_update_entry(level, "Old title", "When ruled, do ruled.", body="placeholder")
    p = _damage(level, slug)

    def reread_after_a_retitle(path: str | os.PathLike[str]) -> str:
        _run_engine("E.retitle_entry(LEVEL, %r, 'New title')" % slug, level)
        return ME.read_store_text(path)

    repaired, skipped = R.repair_appended_type(level, read=reread_after_a_retitle)
    assert (repaired, skipped) == ([(slug, "feedback")], [])
    assert _line(level, slug).title == "New title"
    assert ME.body_title(p.read_text(encoding="utf-8")) == "New title"
    assert R.appended_type_damage(p.read_text(encoding="utf-8")) is None


def test_a_hook_change_between_the_walk_and_the_write_is_kept(tmp_path):
    """The same window for the hook: a concurrent update of the hook alone stands."""
    level = _tree(tmp_path)
    slug = ME.add_or_update_entry(level, "Ruled", "When ruled, do ruled.", body="placeholder")
    p = _damage(level, slug)

    def reread_after_a_hook_change(path: str | os.PathLike[str]) -> str:
        _run_engine("E.upsert_entry(LEVEL, '', 'When ruled anew, do it anew.', slug=%r, "
                    "must_exist=True)" % slug, level)
        return ME.read_store_text(path)

    assert R.repair_appended_type(level, read=reread_after_a_hook_change)[0] == [(slug, "feedback")]
    assert _line(level, slug).hook == "When ruled anew, do it anew."
    assert ME.body_description(p.read_text(encoding="utf-8")) == "When ruled anew, do it anew."


def test_a_fact_whose_line_left_after_the_walk_is_skipped_not_created_anew(tmp_path):
    """A fact archived (its line dropped) after the walk read it: the update-only write refuses
    it, the repair reports it as skipped, and no line comes back."""
    level = _tree(tmp_path)
    slug = ME.add_or_update_entry(level, "Ruled", "When ruled, do ruled.", body="placeholder")
    _damage(level, slug)

    def reread_after_a_drop(path: str | os.PathLike[str]) -> str:
        _run_engine("E.drop_pointer(LEVEL, %r)" % slug, level)
        return ME.read_store_text(path)

    repaired, skipped = R.repair_appended_type(level, read=reread_after_a_drop)
    assert repaired == []
    assert [name for name, _why in skipped] == [slug]
    assert "left" in skipped[0][1] and "run the repair again" in skipped[0][1]
    assert slug not in {e.slug for e in ME.read_store(level)[1]}


_RETITLER = r'''
import json, os, random, sys, time
from pathlib import Path
hooks, level, slug, progress, stop = sys.argv[1:6]
sys.path.insert(0, hooks)
import memory_engine as E
import uuid_store as us


def title_now():
    text = Path(level, "CLAUDE.local.md").read_text(encoding="utf-8")
    return int(next(p for p in us.parse_pointer_index(text)[1] if p.slug == slug).title[1:])


n = stale = 0
while not os.path.exists(stop):
    # nothing but this process changes the title, so a title below n, read before the next
    # retitle or right after this one, is an older title another writer put back
    stale += title_now() < n
    n += 1
    E.retitle_entry(level, slug, "T%d" % n)
    stale += title_now() < n
    Path(progress).write_text(str(n), encoding="utf-8")
    # paced: re-taking the level lock at once starves the other process's poll
    time.sleep(random.uniform(0.0, 0.005))
print(json.dumps({"retitles": n, "stale": stale}))
'''

RETITLES_TO_MEET = 200
"""How many retitles the worker makes before the repairs stop: counted, not timed."""


def _progress(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8") or 0)
    except (OSError, ValueError):
        return 0


def test_repairs_racing_a_retitler_never_undo_a_title(tmp_path):
    """A real process retitles the fact in a loop and reads each title back; this one damages the
    body and repairs it, over and over. The retitler must never read a title older than the one
    it just wrote."""
    level = _tree(tmp_path)
    slug = ME.add_or_update_entry(level, "T0", "When racing, keep the title.", body="placeholder")
    worker, progress, stop = tmp_path / "retitler.py", tmp_path / "progress", tmp_path / "stop"
    worker.write_text(_RETITLER, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(worker), HOOKS, level, slug, str(progress),
                             str(stop)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    repairs = 0
    try:
        while _progress(progress) < 1:
            assert proc.poll() is None, proc.communicate()
            time.sleep(0.002)
        while _progress(progress) < RETITLES_TO_MEET and repairs < 20000:
            _damage(level, slug)
            repaired, skipped = R.repair_appended_type(level)
            assert skipped == [], skipped
            repairs += len(repaired)
            time.sleep(random.uniform(0.0, 0.005))
        stop.write_text("x", encoding="utf-8")
        out, err = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    res = json.loads(out.strip().splitlines()[-1])
    assert res["retitles"] >= RETITLES_TO_MEET and repairs >= 10, (res, repairs)
    assert res["stale"] == 0, "%d of %d retitles were undone by %d repairs" % (
        res["stale"], res["retitles"], repairs)
