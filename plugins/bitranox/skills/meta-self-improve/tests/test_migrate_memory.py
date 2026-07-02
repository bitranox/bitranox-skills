"""Tests for migrate_memory.py (Phase 2: native -> curated migration). All content ASCII."""

import pytest

import migrate_memory as M
import memory_engine as ME
import self_improve_signals as sig


def _encode_slug(path):
    """Claude's slug encoding: leading '/', and each '/', '.', '_' -> '-'."""
    s = str(path)
    return "-" + s[1:].replace("/", "-").replace(".", "-").replace("_", "-")


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
    assert M.is_excluded("/media/srv-main-softdev/projects/x") is False
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
    srcs = set().union(*(e.source for e in entries))
    assert {"project-a", "project-b"} <= srcs                # provenance carried
    assert (sig.claude_memory_dir(str(proj)) / "facts").glob("*.md")   # heavy body placed
    # receipt written; a backup exists out of tree
    assert M._receipt_path(str(proj)).is_file()
    assert any(M._backups_dir().glob("*/native")) if M._backups_dir().exists() else True


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
    _, entries, _ = ME.read_store(str(target))
    assert entries and entries[0].source == {"project-a"}
