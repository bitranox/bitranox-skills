"""Tests for migrate_memory.py (Phase 2: native -> curated migration). All content ASCII."""

import sys
import pytest

import migrate_memory as M
import memory_engine as ME
import self_improve_signals as sig


def _encode_slug(path):
    """Claude's slug encoding, transcribed from the CLI binary (2.1.240):
        h1r(e) = e.replace(/[^a-zA-Z0-9]/g, "-")
    EVERY non-alphanumeric collapses to "-". The old version here replaced only "/", "." and
    "_", which happened to agree on all 239 real project paths on this machine but diverges the
    moment a component holds a space, "+" or "@" - and on Windows, where it mangled the drive
    letter into "-:" and the fixtures then failed at mkdir."""
    import re as _re
    return _re.sub(r"[^a-zA-Z0-9]", "-", str(path))


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(M, "_EXCLUDE_PREFIXES", ())   # pytest tmp_path is under /tmp; don't exclude it here
    return tmp_path, home


def test_is_excluded():
    import os
    assert M.is_excluded("/tmp") is True
    assert M.is_excluded("/tmp/whatever/proj") is True
    assert M.is_excluded(os.path.expanduser("~")) is True     # $HOME itself
    assert M.is_excluded("/data/projects/x") is False        # a normal project path (not /tmp, not $HOME)
    assert M.is_excluded(None) is False


def _native_store(home, slug, topics):
    d = home / ".claude" / "projects" / slug / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text("# Memory index\n", encoding="utf-8")
    for name, meta_name, desc, body in topics:
        (d / name).write_text(
            "---\nname: %s\ndescription: %s\nmetadata:\n  type: project\n---\n%s\n"
            % (meta_name, desc, body), encoding="utf-8")
    return d


# ---- slug resolution ---------------------------------------------------------------------------

def test_resolve_slug_slash_dot_underscore(env):
    tmp_path, _ = env
    proj = tmp_path / "grp" / "my.proj_dir"      # exercises '/', '.', and '_' all encoded to '-'
    proj.mkdir(parents=True)
    slug = _encode_slug(proj)
    assert str(proj.resolve()) in M.resolve_slug(slug)
    assert M.resolve_one(slug) == str(proj.resolve())


def test_resolve_unresolvable_is_none(env):
    assert M.resolve_one("-no-such-path-anywhere-xyz") is None


# ---- reading a native store --------------------------------------------------------------------

def test_read_native_entries(env):
    _tmp, home = env
    _native_store(home, "-x-proj", [
        ("a.md", "project-alpha", "the alpha fact", "Alpha body."),
        ("b.md", "project-beta", "the beta fact", "Beta body."),
    ])
    entries = M.read_native_entries(home / ".claude" / "projects" / "-x-proj" / "memory")
    assert {e["source"] for e in entries} == {"project-alpha", "project-beta"}
    assert all(e["type"] == "project" for e in entries)


# ---- migrate_store: dry-run, apply, idempotent, parked -----------------------------------------

def test_migrate_dry_run_writes_nothing(env):
    tmp_path, home = env
    proj = tmp_path / "repoA"
    proj.mkdir()
    slug = _encode_slug(proj)
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rep = M.migrate_store(slug, dry_run=True)
    assert rep["resolved"] == str(proj.resolve()) and rep["in"] == 1 and rep["placed"] == 1
    assert not sig.claude_memory_dir(str(proj)).exists()   # nothing written on dry-run


def test_migrate_apply_writes_curated_store_and_receipt(env):
    tmp_path, home = env
    proj = tmp_path / "repoB"
    proj.mkdir()
    slug = _encode_slug(proj)
    _native_store(home, slug, [
        ("a.md", "project-a", "fact a", "Body A."),
        ("b.md", "project-b", "fact b", "x" * 400),        # heavy -> facts/
    ])
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["placed"] == 2 and not rep["parked"]
    scope, entries, bodies = ME.read_store(str(proj))
    # provenance is no longer persisted anywhere (5.300.0); the migration still PLACES both
    # facts, which is what this test is for
    assert {e.slug for e in entries} == {"project-a", "project-b"}
    anchor = ME._anchor(str(proj))
    assert "x" * 400 in ME.us.body_path(anchor, "project-b").read_text(encoding="utf-8")
    assert "Body A." in ME.us.body_path(anchor, "project-a").read_text(encoding="utf-8")
    # receipt written; a backup of the native store exists out of tree
    assert M._receipt_path(str(proj)).is_file()
    backups = list(M._backups_dir().glob("*/*/native/a.md"))    # <run>/<proj key>/native
    assert len(backups) == 1 and "Body A." in backups[0].read_text(encoding="utf-8")


def test_migrate_apply_idempotent(env):
    tmp_path, home = env
    proj = tmp_path / "repoC"
    proj.mkdir()
    slug = _encode_slug(proj)
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    M.migrate_store(slug, dry_run=False)
    rep2 = M.migrate_store(slug, dry_run=False)              # re-run: source already in receipt
    assert rep2["placed"] == 0 and rep2["skipped"] == 1


def test_migrate_parked_when_unresolved(env):
    _tmp, home = env
    slug = "-media-does-not-exist-anywhere-proj"             # decodes to a nonexistent path
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["parked"] is True
    assert (M._parked_dir() / slug / "memory" / "a.md").is_file()   # parked copy, nothing lost


def test_main_dry_run_reports(env, capsys):
    tmp_path, home = env
    proj = tmp_path / "repoD"
    proj.mkdir()
    slug = _encode_slug(proj)
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rc = M.main(["--dry-run", "--slug=" + slug])   # slug starts with '-', so the =form is required
    out = capsys.readouterr().out
    assert rc == 0 and "DRY-RUN" in out and "TOTAL in=1" in out


# ---- gitignore safety (R11) --------------------------------------------------------------------

def test_ensure_gitignore_in_git_repo(env):
    import subprocess
    tmp_path, _ = env
    proj = tmp_path / "gitrepo"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=False)
    assert M.ensure_gitignore(str(proj)) == "gitignored"
    assert ".claude-bx-selflearning/" in (proj / ".gitignore").read_text(encoding="utf-8")
    assert M.ensure_gitignore(str(proj)) == "already ignored"      # idempotent


def test_ensure_gitignore_non_git_skips(env):
    tmp_path, _ = env
    d = tmp_path / "plain"
    d.mkdir()
    assert "skipped" in M.ensure_gitignore(str(d))


def test_ensure_gitignore_track_private_leaves_tracked(env):
    import subprocess
    tmp_path, _ = env
    sig.save_config({"track_private": True})
    proj = tmp_path / "gitrepo2"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=False)
    assert "left tracked" in M.ensure_gitignore(str(proj))
    assert not (proj / ".gitignore").exists()


def test_migrate_redirect_forces_target(env):
    tmp_path, home = env
    target = tmp_path / "renamed-target"
    target.mkdir()
    slug = "-media-old-removed-location-proj"          # would NOT resolve (renamed/moved)
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rep = M.migrate_store(slug, dry_run=False, redirect=str(target))
    assert rep["redirected"] and rep["placed"] == 1 and not rep["parked"]
    _, entries, bodies = ME.read_store(str(target))
    assert [e.slug for e in entries] == ["project-a"]
    assert "Body A." in bodies["project-a"]


def test_the_platform_temp_root_is_excluded_however_it_resolves():
    """The literal "/tmp" prefix was not enough: on macOS /tmp is a symlink to /private/tmp, so
    a resolved path never matched it and the transient root went entirely unexcluded there -
    exactly the case is_excluded() exists to catch. Windows has no /tmp at all."""
    import tempfile
    from pathlib import Path
    tmp_root = tempfile.gettempdir()
    assert M.is_excluded(tmp_root) is True
    assert M.is_excluded(str(Path(tmp_root).resolve())) is True
    assert M.is_excluded(str(Path(tmp_root).resolve() / "some" / "proj")) is True


def test_every_exclude_root_is_already_resolved():
    """A root stored unresolved can never match a resolved path, which is how the macOS gap
    stayed invisible: the comparison simply never fired."""
    from pathlib import Path
    for root in M._EXCLUDE_PREFIXES:
        assert root == str(Path(root).resolve()), root


# --------------------------------------------------------------------------
# Slug decoding, against the encoder Claude Code actually uses. Transcribed
# from the CLI binary (2.1.240):
#     h1r(e) = e.replace(/[^a-zA-Z0-9]/g, "-")
#     qY(e)  = h1r(e).length <= 200 ? h1r(e) : h1r(e).slice(0,200) + "-" + hash(e)
# so EVERY non-alphanumeric collapses to "-", not just "/", "." and "_".
# --------------------------------------------------------------------------


def _encode(path):
    """The real encoder, for building fixtures that match what Claude would write."""
    import re as _re
    return _re.sub(r"[^a-zA-Z0-9]", "-", str(path))


def test_slug_root_splits_a_posix_slug():
    root, tokens = M.slug_root_and_tokens("-home-bob-proj")
    assert root == "/" and tokens == ["home", "bob", "proj"]


def test_slug_root_splits_a_windows_drive_slug():
    """C:\\Users\\bob and C:/Users/bob both encode to C--Users-bob: ':' and both slashes
    all become '-', so the drive form needs no platform detection to recognise."""
    root, tokens = M.slug_root_and_tokens("C--Users-bob-proj")
    assert root == "C:\\" and tokens == ["Users", "bob", "proj"]


def test_slug_root_rejects_a_slug_that_is_neither():
    assert M.slug_root_and_tokens("home-bob") == (None, [])


def test_resolve_slug_decodes_a_component_holding_a_space(tmp_path):
    """The old decoder only tried '.', '-' and '_' as separators, so any other punctuation
    was undecodable - a path with a space resolved to nothing at all."""
    proj = tmp_path / "grp" / "my proj"
    proj.mkdir(parents=True)
    got = M.resolve_slug(_encode(proj))
    assert str(proj.resolve()) in got, got


def test_resolve_slug_decodes_a_component_holding_a_plus(tmp_path):
    proj = tmp_path / "grp" / "c++lib"
    proj.mkdir(parents=True)
    got = M.resolve_slug(_encode(proj))
    assert str(proj.resolve()) in got, got


def test_resolve_slug_still_decodes_dot_and_underscore(tmp_path):
    """The separators the old decoder did handle must keep working."""
    proj = tmp_path / "grp" / "my.proj_dir"
    proj.mkdir(parents=True)
    got = M.resolve_slug(_encode(proj))
    assert str(proj.resolve()) in got, got


def test_a_truncated_slug_is_reported_not_silently_mis_resolved():
    """Past 200 characters Claude truncates and appends a hash, so the tail is unrecoverable.
    Decoding that as if it were complete would resolve to the wrong directory."""
    assert M.is_truncated_slug("-" + "a" * 199 + "-deadbeefcafe") is True
    assert M.is_truncated_slug("-home-bob-proj") is False


# ---- placement: every native fact lands, none overwrites another ------------------------------

def _raw_store(home, slug, files):
    """A native store holding `files` ({filename: raw text or bytes}) verbatim."""
    d = home / ".claude" / "projects" / slug / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / "MEMORY.md").write_text("# Memory index\n", encoding="utf-8")
    for name, text in files.items():
        if isinstance(text, bytes):
            (d / name).write_bytes(text)
        else:
            (d / name).write_text(text, encoding="utf-8")
    return d


def _project(env, name):
    tmp_path, home = env
    proj = tmp_path / name
    proj.mkdir()
    return proj, _encode_slug(proj), home


def _placed_bodies(proj):
    _scope, entries, bodies = ME.read_store(str(proj))
    return {e.slug: bodies[e.slug] for e in entries}


def test_two_facts_with_the_same_derived_title_both_survive(env):
    proj, slug, home = _project(env, "repoCollide")
    _raw_store(home, slug, {
        "gitea_access.md": "---\nname: gitea_access\ndescription: gitea\n---\n# Notes\n\n"
                           "Use the gitea key.\n",
        "ssh_quirk.md": "---\nname: ssh_quirk\ndescription: ssh\n---\n# Notes\n\n"
                        "Always pass -tt to ssh.\n"})
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["placed"] == 2
    bodies = "\n".join(_placed_bodies(proj).values())
    assert "Use the gitea key." in bodies and "Always pass -tt to ssh." in bodies


def test_a_slug_taken_by_a_different_existing_fact_is_suffixed_not_overwritten(env):
    proj, slug, home = _project(env, "repoTaken")
    ME.add_or_update_entry(str(proj), "Notes", "an earlier fact", body="Earlier body.",
                           slug="notes")
    _raw_store(home, slug, {"notes.md": "---\nname: notes\ndescription: d\n---\nNew body.\n"})
    M.migrate_store(slug, dry_run=False)
    bodies = _placed_bodies(proj)
    assert "Earlier body." in bodies["notes"]
    assert any("New body." in b for s, b in bodies.items() if s != "notes")


def test_a_nested_metadata_type_is_read():
    raw = "---\nname: gitea_access\ndescription: d\nmetadata:\n  type: reference\n---\nBody.\n"
    assert M._native_type(*M.R.parse_frontmatter(raw)[:1], raw, "gitea_access") == "reference"


def test_read_native_entries_types_a_nested_metadata_fact(env):
    _tmp, home = env
    d = _raw_store(home, "-x-nested", {
        "gitea_access.md": "---\nname: gitea_access\ndescription: d\nmetadata:\n"
                           "  type: reference\n---\nBody.\n",
        "reference_other.md": "---\nname: reference_other\ndescription: d\n---\nBody.\n"})
    types = {e["name"]: e["type"] for e in M.read_native_entries(d)}
    assert types == {"gitea_access": "reference", "reference_other": "reference"}


def test_an_empty_topic_body_is_skipped_and_the_rest_placed_with_a_receipt(env, capsys):
    proj, slug, home = _project(env, "repoEmpty")
    _raw_store(home, slug, {"a.md": "---\nname: project-a\ndescription: d\n---\nBody A.\n",
                            "b.md": "---\nname: project-b\ndescription: d\n---\n\n"})
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["placed"] == 1 and len(rep["failed"]) == 1 and "b" in rep["failed"][0]
    assert list(_placed_bodies(proj)) == ["project-a"]
    assert M._receipt_path(str(proj)).is_file()
    assert M.main(["--apply", "--slug=" + slug]) == 1          # the failed entry is not "done"
    assert "b" in capsys.readouterr().out


def test_a_failed_backup_aborts_the_store_before_any_write(env, capsys):
    proj, slug, home = _project(env, "repoNoBackup")
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    (home / ".claude" / "self-improve-audit").write_text("a file, not a dir", encoding="utf-8")
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["error"] and "backup" in rep["error"]
    assert _placed_bodies(proj) == {}
    assert M.main(["--apply", "--slug=" + slug]) == 1


def test_a_backup_that_works_is_not_an_error(env):
    """Control for the failed-backup test."""
    proj, slug, home = _project(env, "repoBackupOk")
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rep = M.migrate_store(slug, dry_run=False)
    assert rep["error"] is None and rep["placed"] == 1


# ---- exit codes: 0 all placed, 1 something was not, 2 usage ------------------------------------

def test_a_parked_store_exits_1(env):
    _tmp, home = env
    slug = "-media-does-not-exist-anywhere-proj"
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    assert M.main(["--apply", "--slug=" + slug]) == 1


def test_a_slug_with_no_native_store_exits_2(env, capsys):
    assert M.main(["--dry-run", "--slug=-no-such-slug-typo"]) == 2
    assert "-no-such-slug-typo" in capsys.readouterr().err


@pytest.mark.parametrize("form", ["{slug}:{path}", "{slug}", "={path}"])
def test_a_malformed_redirect_exits_2(env, capsys, form):
    proj, slug, home = _project(env, "repoRedirMalformed")
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    rc = M.main(["--apply", "--slug=" + slug, "--redirect=" + form.format(slug=slug, path=proj)])
    assert rc == 2
    assert "--redirect" in capsys.readouterr().err
    assert _placed_bodies(proj) == {}


def test_a_redirect_to_a_missing_dir_exits_2_and_creates_nothing(env, capsys):
    tmp_path, home = env
    slug = "-media-old-removed-location-proj"
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    target = tmp_path / "does" / "not" / "exist"
    assert M.main(["--apply", "--slug=" + slug, "--redirect=%s=%s" % (slug, target)]) == 2
    assert not target.exists()


def test_a_valid_redirect_places_and_exits_0(env):
    tmp_path, home = env
    slug = "-media-old-removed-location-proj"
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    target = tmp_path / "moved"
    target.mkdir()
    assert M.main(["--apply", "--slug=" + slug, "--redirect=%s=%s" % (slug, target)]) == 0
    assert list(_placed_bodies(target)) == ["project-a"]


def test_dry_run_and_apply_together_are_refused(env, capsys):
    proj, slug, home = _project(env, "repoBoth")
    _native_store(home, slug, [("a.md", "project-a", "fact a", "Body A.")])
    with pytest.raises(SystemExit) as exc:
        M.main(["--dry-run", "--apply", "--slug=" + slug])
    assert exc.value.code == 2
    assert _placed_bodies(proj) == {}


# ---- reading: a BOM is not frontmatter-breaking, an undecodable file is reported ---------------

def test_a_bom_topic_file_keeps_its_frontmatter(env):
    _tmp, home = env
    d = _raw_store(home, "-x-bom", {
        "a.md": b"\xef\xbb\xbf---\nname: reference-a\ndescription: the hook\n---\nBody.\n"})
    (entry,) = M.read_native_entries(d)
    assert entry["hook"] == "the hook" and entry["type"] == "reference"


def test_an_undecodable_topic_file_is_reported_and_exits_1(env, capsys):
    proj, slug, home = _project(env, "repoBadBytes")
    _raw_store(home, slug, {"a.md": "---\nname: project-a\ndescription: d\n---\nBody A.\n",
                            "b.md": b"---\nname: project-b\ndescription: caf\xe9\n---\nB.\n"})
    assert M.main(["--apply", "--slug=" + slug]) == 1
    out = capsys.readouterr().out
    assert "b.md" in out
    assert list(_placed_bodies(proj)) == ["project-a"]


def test_a_cp1252_console_survives_a_slug_it_cannot_encode(env):
    import os
    import subprocess
    _tmp, home = env
    child = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    child.update(HOME=str(home), USERPROFILE=str(home), PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, M.__file__, "--dry-run", "--slug=-data-日本"],
                       env=child, capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stderr
    assert "UnicodeEncodeError" not in r.stderr
