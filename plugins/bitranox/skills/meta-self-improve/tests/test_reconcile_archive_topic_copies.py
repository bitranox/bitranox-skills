"""Tests for archiving a fact that is placed by topic: every line of it goes, the body is
archived once, and whatever still names it blocks the archive as for a last pointer. A failure
part way never moves the body while a line of the fact remains, and its message names the
routes that finish or undo it; each route is run here as given, from a cwd outside the tree.
All content ASCII.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import reconcile_memory_index as R

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)
import self_improve_signals as sig  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}
PLUGIN = Path(R.__file__).resolve().parents[2]

# chmod a-w stops a write only for a user the OS holds to file modes
needs_modes = pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                                 reason="root writes a read-only file")


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/")) if rel else Path(anchor)
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert ME.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a level"]) == 0
    if topics is not None:
        ME.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, body=None):
    ME.add_or_update_entry(level, title="T " + slug, hook=HOOK, body=body or "body of " + slug,
                           type_="feedback", slug=slug)
    if topics is not None:
        ME.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _tree(tmp_path, specs):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    out = {rel: _level(str(anchor), rel, topics) for rel, topics in specs}
    _fact(out[""], "feedback-py-rule", ("python",))
    _fact(out[""], "feedback-plain")
    ME.render_topics(out[""])
    return out


@pytest.fixture
def levels(tmp_path):
    out = _tree(tmp_path, (("", None), ("a", ("python",)), ("b", ("python",)), ("c", ("rust",))))
    assert _slugs(out["a"]) == _slugs(out["b"]) == ["feedback-py-rule"]
    return out


@pytest.fixture
def three(tmp_path):
    """The python rule placed at a, b and d."""
    out = _tree(tmp_path, (("", None), ("a", ("python",)), ("b", ("python",)),
                           ("d", ("python",))))
    assert _slugs(out["a"]) == _slugs(out["b"]) == _slugs(out["d"]) == ["feedback-py-rule"]
    return out


def _outside(tmp_path):
    out = tmp_path / "outside"
    out.mkdir(exist_ok=True)
    return out


def _cli(tmp_path, script, argv):
    """Run a plugin script as a real process from a cwd outside the tree."""
    return subprocess.run([sys.executable, str(PLUGIN / script), *argv], cwd=str(_outside(tmp_path)),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          check=False)


# ---- placed_copies: the engine's placed rule, the other levels, level order ---------------------

def test_placed_copies_names_the_other_levels_in_level_order(three):
    assert R.placed_copies(three[""], three["d"], "feedback-py-rule") == [three["a"], three["b"]]
    assert R.placed_copies(three[""], three["a"], "feedback-py-rule") == [three["b"], three["d"]]


class _Listing:
    """What os.scandir returns, over entries in an order the test chose."""

    def __init__(self, entries):
        self._entries = entries

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def __iter__(self):
        return iter(self._entries)

    def close(self):
        pass


@pytest.mark.parametrize("descending", [False, True])
def test_level_order_does_not_follow_the_filesystem_listing(three, monkeypatch, descending):
    """The listing order of a directory is the filesystem's (the one external edge here), so the
    anchor's listing is served in both orders and the answer must not change."""
    real = os.scandir
    anchor = os.path.abspath(three[""])

    def scandir(path="."):
        it = real(path)
        if os.path.abspath(os.fspath(path)) != anchor:
            return it
        with it:
            entries = sorted(it, key=lambda e: e.name, reverse=descending)
        return _Listing(entries)

    monkeypatch.setattr(os, "scandir", scandir)
    assert R.placed_copies(three[""], three["d"], "feedback-py-rule") == [three["a"], three["b"]]


def test_placed_copies_compares_levels_lexically_never_through_a_link(three, tmp_path):
    """A level reached through a symlinked path is another level key, as everywhere in the engine."""
    link = tmp_path / "alias"
    try:
        os.symlink(three["a"], str(link), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this platform cannot make a directory symlink here")
    assert three["a"] in R.placed_copies(three[""], str(link), "feedback-py-rule")


@pytest.mark.parametrize("shape", ["pinned-elsewhere", "untitled", "unbound"])
def test_a_fact_the_renderer_does_not_manage_has_no_placed_copies(levels, shape):
    anchor = levels[""]
    if shape == "pinned-elsewhere":
        us.add_pointer(levels["c"], "feedback-py-rule", "T feedback-py-rule", HOOK, pin=True)
    elif shape == "untitled":
        path = us.body_path(anchor, "feedback-py-rule")
        text = path.read_text(encoding="utf-8")
        us.put_body(anchor, "feedback-py-rule",
                    "\n".join(line for line in text.split("\n") if not line.startswith("title:")))
    else:
        path = us.body_path(anchor, "feedback-py-rule")
        us.put_body(anchor, "feedback-py-rule", ME._with_topics(path.read_text(encoding="utf-8"), ()))
    assert R.placed_copies(anchor, levels["a"], "feedback-py-rule") == []
    # archived one pointer at a time, as any duplicate: the body stays for the line at b
    assert R.archive_entry(levels["a"], "feedback-py-rule") is True
    assert "feedback-py-rule" in _slugs(levels["b"])
    assert us.body_path(anchor, "feedback-py-rule").is_file()


# ---- the archive ---------------------------------------------------------------------------------

def test_archiving_a_placed_fact_drops_every_line_and_archives_the_body_once(levels, capsys):
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", levels["a"]]) == 0
    out = capsys.readouterr().out
    assert "archived feedback-py-rule (pointer dropped at %s and at the 1 other level(s) its topics " \
           "place it at: %s)" % (levels["a"], levels["b"]) in out
    assert _slugs(levels["a"]) == _slugs(levels["b"]) == []
    store = Path(levels[""], us.STORE_DIRNAME)
    assert not us.body_path(levels[""], "feedback-py-rule").exists()
    assert [p.name for p in (store / ".archive").iterdir()] == ["feedback-py-rule.md"]
    assert R.main(["--check-tree", levels[""]]) == 0


def test_the_archive_runs_as_a_process_from_outside_the_tree(three, tmp_path):
    done = _cli(tmp_path, "skills/meta-self-improve/reconcile_memory_index.py",
                ["--archive", "feedback-py-rule", three["b"]])
    assert done.returncode == 0, done.stdout + done.stderr
    assert ("at the 2 other level(s) its topics place it at: %s, %s)"
            % (three["a"], three["d"])) in done.stdout
    assert _slugs(three["a"]) == _slugs(three["b"]) == _slugs(three["d"]) == []
    assert not us.body_path(three[""], "feedback-py-rule").exists()


def test_a_dry_run_names_every_level_and_writes_nothing(levels, capsys):
    before = _snapshot(levels[""])
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", "--dry-run", levels["b"]]) == 0
    out = capsys.readouterr().out
    assert ("would archive feedback-py-rule (pointer would be dropped at %s and at the 1 other "
            "level(s) its topics place it at: %s) - dry run, nothing written"
            % (levels["b"], levels["a"])) in out
    assert _snapshot(levels[""]) == before


def test_a_fact_that_still_names_it_blocks_the_archive_at_any_of_its_levels(levels, capsys):
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    before = _snapshot(levels[""])
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", levels["a"]]) == 1
    assert "! refused" in capsys.readouterr().out and _snapshot(levels[""]) == before
    with pytest.raises(R.ArchiveBlocked):
        R.archive_entry(levels["b"], "feedback-py-rule")
    with pytest.raises(R.ArchiveBlocked):
        R.archive_entry(levels["b"], "feedback-py-rule", dry_run=True)
    assert _snapshot(levels[""]) == before
    assert R.main(["--archive", "feedback-py-rule", "--force", levels["a"]]) == 0
    out = capsys.readouterr().out
    assert "--force: these still name feedback-py-rule" in out and "feedback-citer" in out
    assert _slugs(levels["b"]) == []


def test_an_unbound_duplicate_is_archived_one_pointer_at_a_time_as_before(levels):
    us.add_pointer(levels["c"], "feedback-plain", "T feedback-plain", HOOK)
    assert R.placed_copies(levels[""], levels["c"], "feedback-plain") == []
    assert R.archive_entry(levels["c"], "feedback-plain") is True
    assert _slugs(levels[""]) == ["feedback-plain"]
    assert us.body_path(levels[""], "feedback-plain").is_file()


def test_an_invalid_slug_is_no_entry_and_no_crash(levels, capsys):
    capsys.readouterr()
    assert R.main(["--archive", "../feedback-py-rule", levels["a"]]) == 1
    assert "! no such entry: ../feedback-py-rule" in capsys.readouterr().out
    assert _slugs(levels["a"]) == ["feedback-py-rule"]


# ---- a failure part way: never a body moved while a line remains; the routes it names run --------

@needs_modes
def test_a_failed_drop_at_another_level_leaves_the_body_and_this_levels_line(levels, capsys):
    blocked = sig.claude_local_md_path(levels["b"])
    os.chmod(blocked, 0o444)
    try:
        with pytest.raises(OSError) as err:
            R.archive_entry(levels["a"], "feedback-py-rule")
        assert not isinstance(err.value, R.ArchiveIncomplete)
        capsys.readouterr()
        assert R.main(["--archive", "feedback-py-rule", levels["a"]]) == 2
        assert "its pointer and body are unchanged" in capsys.readouterr().err
    finally:
        os.chmod(blocked, 0o644)
    assert us.body_path(levels[""], "feedback-py-rule").is_file()
    assert _slugs(levels["a"]) == _slugs(levels["b"]) == ["feedback-py-rule"]


_ARCHIVE_RX = re.compile(r"(skills/meta-self-improve/reconcile_memory_index\.py) "
                         r"(--archive \S+ \S+) once")
_RENDER_RX = re.compile(r"(hooks/memory_engine\.py) (render-topics --proj \S+ --scope tree)")


def _fail_part_way(three, capsys, monkeypatch):
    """Archive at a while d refuses its write: b is dropped, d and a keep their lines. The CLI is
    given a as a path relative to the cwd: the routes it names must work from anywhere."""
    blocked = sig.claude_local_md_path(three["d"])
    os.chmod(blocked, 0o444)
    try:
        with pytest.raises(R.ArchiveIncomplete) as err:
            R.archive_entry(three["a"], "feedback-py-rule")
        assert err.value.dropped == [three["b"]]
        assert err.value.remaining == [three["a"], three["d"]]
        capsys.readouterr()
        us.add_pointer(three["b"], "feedback-py-rule", "T feedback-py-rule", HOOK)
        monkeypatch.chdir(three[""])
        assert R.main(["--archive", "feedback-py-rule", "a"]) == 2
        out = capsys.readouterr()
    finally:
        os.chmod(blocked, 0o644)
    assert out.out == ""
    msg = out.err
    assert "its pointer and body are unchanged" not in msg, msg
    assert ("could not finish archiving feedback-py-rule" in msg and "line(s) at %s are dropped"
            % three["b"] in msg and "its body and its line(s) at %s, %s are unchanged"
            % (three["a"], three["d"]) in msg), msg
    assert us.body_path(three[""], "feedback-py-rule").is_file()
    assert _slugs(three["b"]) == [] and _slugs(three["a"]) == _slugs(three["d"]) == ["feedback-py-rule"]
    return msg


@needs_modes
def test_a_drop_failing_part_way_names_the_rerun_that_finishes_it(three, capsys, tmp_path,
                                                                 monkeypatch):
    msg = _fail_part_way(three, capsys, monkeypatch)
    routes = _ARCHIVE_RX.findall(msg)
    assert len(routes) == 1, msg
    script, argv = routes[0]
    done = _cli(tmp_path, script, argv.split())
    assert done.returncode == 0, done.stdout + done.stderr
    assert _slugs(three["a"]) == _slugs(three["b"]) == _slugs(three["d"]) == []
    assert not us.body_path(three[""], "feedback-py-rule").exists()
    assert R.main(["--check-tree", three[""]]) == 0


@needs_modes
def test_a_drop_failing_part_way_names_the_render_that_puts_the_lines_back(three, capsys, tmp_path,
                                                                          monkeypatch):
    msg = _fail_part_way(three, capsys, monkeypatch)
    routes = _RENDER_RX.findall(msg)
    assert len(routes) == 1, msg
    script, argv = routes[0]
    assert argv.split()[2] == three[""]
    done = _cli(tmp_path, script, argv.split())
    assert done.returncode == 0, done.stdout + done.stderr
    assert _slugs(three["a"]) == _slugs(three["b"]) == _slugs(three["d"]) == ["feedback-py-rule"]
    assert R.main(["--check-tree", three[""]]) == 0


@needs_modes
def test_a_level_given_relative_to_the_cwd_is_named_absolute_in_the_routes(three, monkeypatch):
    """archive_entry takes the level as its caller gives it; the re-run it names must work from
    any cwd, so the level is named as an absolute path."""
    blocked = sig.claude_local_md_path(three["d"])
    os.chmod(blocked, 0o444)
    monkeypatch.chdir(three[""])
    try:
        with pytest.raises(R.ArchiveIncomplete) as err:
            R.archive_entry("a", "feedback-py-rule")
    finally:
        os.chmod(blocked, 0o644)
    assert err.value.remaining == [three["a"], three["d"]]
    assert "--archive feedback-py-rule %s once" % three["a"] in str(err.value)


@needs_modes
def test_a_failed_pointer_write_after_the_drops_puts_the_body_back(levels, capsys):
    """Every other line is dropped, the body moved, then this level's write fails: the body goes
    back, so the fact keeps this line and its body, and the message says b was dropped."""
    blocked = sig.claude_local_md_path(levels["a"])
    os.chmod(blocked, 0o444)
    try:
        with pytest.raises(R.ArchiveIncomplete) as err:
            R.archive_entry(levels["a"], "feedback-py-rule")
    finally:
        os.chmod(blocked, 0o644)
    assert err.value.dropped == [levels["b"]] and err.value.remaining == [levels["a"]]
    assert us.body_path(levels[""], "feedback-py-rule").is_file()
    assert not (Path(levels[""], us.STORE_DIRNAME) / ".archive").exists() or \
        list((Path(levels[""], us.STORE_DIRNAME) / ".archive").iterdir()) == []
    assert _slugs(levels["a"]) == ["feedback-py-rule"] and _slugs(levels["b"]) == []


def test_a_body_that_cannot_be_put_back_names_the_dropped_lines_too(levels):
    def refuse(*_a, **_k):
        raise OSError("disk gone")

    calls = []

    def move_once(src, dest):
        calls.append((src, dest))
        if len(calls) > 1:
            raise OSError("cannot move it back")
        os.replace(src, dest)

    with pytest.raises(R.ArchiveRollbackFailed) as err:
        R.archive_entry(levels["a"], "feedback-py-rule", move=move_once, commit=refuse)
    assert "dropped" in str(err.value) and levels["b"] in str(err.value)

