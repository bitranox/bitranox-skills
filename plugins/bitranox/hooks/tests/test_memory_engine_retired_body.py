"""A body a rename or relocate retired but could not archive is never adopted by the next add.

Measured on the Windows dev box (Python 3.14): a reader holding the old body open for 3 s (past
the archive's 1 s wait) made rename and relocate leave it in `facts/` with a warning, and the next
body-less add of the old slug then took it as a dangling body: the old fact came back under its
old name, prose and all, where a create would have been refused as EmptyBody.

The retiring verb now writes a record (`.retiring/<slug>`) before it archives, and the next add
of the slug finishes the archive first, or refuses with RetiredBodyHeld while it still cannot.

On POSIX a rename of an open file succeeds, so the POSIX tests make the archive fail through a
real refusal of the operating system instead: an `.archive` dir the user may not write into. The
Windows tests hold the body open, as the reader did. All content ASCII.
"""

import json
import os
import stat
import sys
import threading
import time
from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us

HOOK = "When a fact is renamed, its old body is archived, never adopted."
ENGINE = Path(E.__file__).resolve()

posix_non_root = pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0,
    reason="a read-only dir refuses a rename on POSIX only for a user who is not root")
windows_only = pytest.mark.skipif(os.name != "nt", reason="Windows refuses to rename an open file")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


def _tree(root):
    proj = root / "proj"
    proj.mkdir(parents=True)
    for d in (root, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    return str(root), str(proj)


def _old_fact(tmp_path):
    anchor, proj = _tree(tmp_path / "tree")
    E.add_or_update_entry(proj, "Old title", HOOK, body="OLD PROSE", slug="old-slug")
    return anchor, proj


def _archive(anchor):
    return us.central_facts_dir(anchor).parent / ".archive"


def _record(anchor):
    return E._retiring_record(anchor, "old-slug")


class _ReadOnlyArchive:
    """The anchor's `.archive` dir, made unwritable for the block: a rename into it fails."""

    def __init__(self, anchor):
        self.dir = _archive(anchor)

    def __enter__(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        return self

    def __exit__(self, *exc):
        self.dir.chmod(stat.S_IRWXU)


def _archived_prose(anchor):
    return [p.read_text(encoding="utf-8") for p in sorted(_archive(anchor).glob("old-slug*.md"))]


def _rename(proj):
    rep = E.rename_entry(proj, "old-slug", "new-slug")
    assert rep.renamed, rep
    return rep.warnings


def _relocate(tmp_path, proj):
    _a2, p2 = _tree(tmp_path / "other")
    rep = E.relocate_entry(proj, p2, "old-slug")
    assert rep.relocated, rep
    return rep.warnings


@posix_non_root
@pytest.mark.parametrize("verb", ["rename", "relocate"])
def test_a_retired_body_the_archive_refused_is_never_adopted_by_the_next_add(tmp_path, verb):
    anchor, proj = _old_fact(tmp_path)
    body = us.body_path(anchor, "old-slug")
    with _ReadOnlyArchive(anchor):
        warnings = _rename(proj) if verb == "rename" else _relocate(tmp_path, proj)
        assert body.is_file()
        # still refused: the add says so and writes nothing, rather than adopting the old fact
        with pytest.raises(E.RetiredBodyHeld) as exc:
            E.add_or_update_entry(proj, "Fresh title", HOOK, slug="old-slug")
        assert str(_record(anchor)) in str(exc.value)
        assert any("recorded as retired" in w for w in warnings), warnings
        assert "old-slug" not in Path(proj, "CLAUDE.local.md").read_text(encoding="utf-8")
        assert "OLD PROSE" in body.read_text(encoding="utf-8")
    # once the archive works, the add archives the old body first: a body-less add is then a
    # create, refused as one, and an add with a body makes a NEW fact
    with pytest.raises(E.EmptyBody):
        E.add_or_update_entry(proj, "Fresh title", HOOK, slug="old-slug")
    assert not body.exists() and not _record(anchor).exists()
    assert _archived_prose(anchor) and "OLD PROSE" in _archived_prose(anchor)[0]
    slug, created = E.upsert_entry(proj, "Fresh title", HOOK, body="NEW PROSE", slug="old-slug")
    assert (slug, created) == ("old-slug", True)
    text = body.read_text(encoding="utf-8")
    assert "NEW PROSE" in text and "OLD PROSE" not in text


@posix_non_root
def test_the_cli_add_of_a_held_retired_body_exits_2_naming_the_record(tmp_path):
    import subprocess
    anchor, proj = _old_fact(tmp_path)
    with _ReadOnlyArchive(anchor):
        _rename(proj)
        done = subprocess.run([sys.executable, str(ENGINE), "add", "--proj", proj, "--title",
                               "Fresh title", "--hook", HOOK, "--slug", "old-slug"],
                              capture_output=True, text=True, encoding="utf-8", timeout=120,
                              check=False)
    assert done.returncode == 2, done.stdout + done.stderr
    assert done.stderr.startswith("! error: old-slug is the slug of a retired fact"), done.stderr
    assert str(_record(anchor)) in done.stderr


def test_a_stale_record_leaves_a_reused_slug_alone(tmp_path):
    """A record whose digest no longer matches the body names a body that has changed since it
    was retired: the slug was reused. The add drops the record and touches the body not."""
    anchor, proj = _old_fact(tmp_path)
    record = _record(anchor)
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"sha256": "0" * 64, "why": "renamed to elsewhere"}) + "\n",
                      encoding="utf-8")
    slug, created = E.upsert_entry(proj, "Old title", HOOK, body="MORE PROSE", slug="old-slug")
    assert (slug, created) == ("old-slug", False)
    assert not record.exists()
    assert "MORE PROSE" in us.body_path(anchor, "old-slug").read_text(encoding="utf-8")
    assert not _archive(anchor).exists() or _archived_prose(anchor) == []


def test_an_unreadable_record_refuses_rather_than_guess(tmp_path):
    anchor, proj = _old_fact(tmp_path)
    record = _record(anchor)
    record.parent.mkdir(parents=True)
    record.write_text("not json\n", encoding="utf-8")
    with pytest.raises(E.RetiredBodyHeld, match="cannot be read"):
        E.add_or_update_entry(proj, "Old title", HOOK, body="MORE PROSE", slug="old-slug")
    assert "OLD PROSE" in us.body_path(anchor, "old-slug").read_text(encoding="utf-8")


def test_a_rename_that_archives_leaves_no_record(tmp_path):
    anchor, proj = _old_fact(tmp_path)
    assert _rename(proj) == []
    assert not _record(anchor).exists()
    assert "OLD PROSE" in _archived_prose(anchor)[0]


def _hold_open(path, seconds, ready):
    with open(path, "rb"):               # Python opens without FILE_SHARE_DELETE on Windows
        ready.set()
        time.sleep(seconds)


@windows_only
@pytest.mark.parametrize("verb", ["rename", "relocate"])
def test_a_reader_holding_the_old_body_past_the_wait_does_not_bring_the_old_fact_back(tmp_path,
                                                                                    verb):
    anchor, proj = _old_fact(tmp_path)
    body = us.body_path(anchor, "old-slug")
    ready = threading.Event()
    reader = threading.Thread(target=_hold_open, args=(body, 5.0, ready))
    reader.start()
    try:
        assert ready.wait(30)
        warnings = _rename(proj) if verb == "rename" else _relocate(tmp_path, proj)
        assert any("recorded as retired" in w for w in warnings), warnings
        with pytest.raises(E.RetiredBodyHeld):       # still held: refused, nothing written
            E.add_or_update_entry(proj, "Fresh title", HOOK, slug="old-slug")
    finally:
        reader.join()
    with pytest.raises(E.EmptyBody):                  # let go: archived, then a plain create
        E.add_or_update_entry(proj, "Fresh title", HOOK, slug="old-slug")
    slug, created = E.upsert_entry(proj, "Fresh title", HOOK, body="NEW PROSE", slug="old-slug")
    assert (slug, created) == ("old-slug", True)
    assert "OLD PROSE" not in body.read_text(encoding="utf-8")
    assert "OLD PROSE" in _archived_prose(anchor)[0]


_FINISHER = r'''
import json, os, sys
from pathlib import Path
hooks, anchor, progress, stop = sys.argv[1:5]
sys.path.insert(0, hooks)
import memory_engine as E
n, held = 0, []
while not os.path.exists(stop):
    try:
        E._finish_retirement(anchor, "old-slug")
    except E.RetiredBodyHeld as exc:
        held.append(str(exc))
    n += 1
    if n % 50 == 0:
        Path(progress).write_text(str(n), encoding="utf-8")
print(json.dumps({"finishes": n, "held": held[:3], "held_count": len(held)}))
'''

RETIREMENTS = 400
"""How many retirements race the finisher: counted, not timed."""


def _count(path):
    try:
        return int(path.read_text(encoding="utf-8") or 0)
    except (OSError, ValueError):
        return 0


def test_an_add_racing_a_retirement_never_fails_on_the_record_or_body_vanishing(tmp_path):
    """A rename or relocate writes the record, archives the body and removes the record, while
    another session's add of the same slug finishes the retirement on its own. Each can take the
    record or the body away between the other's existence check and its read; that is a
    retirement finished, never an error. A real process runs the add's step in a loop while this
    one retires a fresh body of the slug over and over."""
    import subprocess
    anchor, _proj = _tree(tmp_path / "tree")
    hooks = str(Path(E.__file__).resolve().parent)
    worker, progress, stop = tmp_path / "finisher.py", tmp_path / "progress", tmp_path / "stop"
    worker.write_text(_FINISHER, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(worker), hooks, anchor, str(progress), str(stop)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    try:
        while _count(progress) < 50:
            assert proc.poll() is None, proc.communicate()
            time.sleep(0.002)
        for i in range(RETIREMENTS):
            us.put_body(anchor, "old-slug", "body %d" % i)
            assert E._retire_body(anchor, "old-slug", "renamed to new-slug") is None
            if proc.poll() is not None:
                break
        stop.write_text("x", encoding="utf-8")
        out, err = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode == 0, err
    res = json.loads(out.strip().splitlines()[-1])
    assert res["finishes"] >= 50 and res["held_count"] == 0, res
    assert not us.body_path(anchor, "old-slug").exists() and not _record(anchor).exists()
    assert len(list(_archive(anchor).glob("old-slug*.md"))) == RETIREMENTS


@posix_non_root
def test_heal_reports_a_held_retirement_and_finishes_it_once_the_archive_works(tmp_path):
    """A retirement no add of its slug ever finishes would otherwise sit in `facts/` for good:
    heal finishes every record of the tree, and reports one it still cannot finish."""
    anchor, proj = _old_fact(tmp_path)
    body = us.body_path(anchor, "old-slug")
    with _ReadOnlyArchive(anchor):
        _rename(proj)
        rep = E.heal(proj)
        assert rep.retirements_finished == []
        [(slug, why)] = rep.retirements_held
        assert slug == "old-slug" and "renamed" in why, why
        assert body.is_file() and _record(anchor).is_file()
    rep = E.heal(proj)
    assert (rep.retirements_finished, rep.retirements_held) == (["old-slug"], [])
    assert not body.exists() and not _record(anchor).exists()
    assert "OLD PROSE" in _archived_prose(anchor)[0]


@posix_non_root
def test_the_cli_heal_names_a_held_retirement(tmp_path):
    import subprocess
    anchor, proj = _old_fact(tmp_path)
    with _ReadOnlyArchive(anchor):
        _rename(proj)
        done = subprocess.run([sys.executable, str(ENGINE), "heal", "--proj", proj],
                              capture_output=True, text=True, encoding="utf-8", timeout=120,
                              check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "! retired body still in facts/, not archived: old-slug [" in done.stdout, done.stdout
