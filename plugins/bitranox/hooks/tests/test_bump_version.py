"""Tests for bump_version.py: the maintainer jig that bumps plugin.json, pyproject.toml and CHANGELOG.md.

Every test builds a throwaway repo with a real bare `origin`, so the fetch, the `git show` of
origin's manifest and the refusal when a peer pushed a bump all run against real git.
"""

import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

import bump_version

PJ = Path("plugins/bitranox/.claude-plugin/plugin.json")
PYPROJECT = """[build-system]
requires = ["hatchling"]

[project]
name = "demo"
# Kept equal to plugin.json; this comment must survive the bump.
version = "{version}"
description = "a demo"  # trailing comment

[tool.other]
version = "9.9.9"
"""
CHANGELOG = """# Changelog

Preamble text.

## Versioning

Not a release heading.

## [{version}]

### Fixed

- the previous release.
"""

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, check=True,
                          encoding="utf-8", errors="replace")
    return proc.stdout.strip()


def _write_release(root: Path, version: str) -> None:
    pj = root / PJ
    pj.parent.mkdir(parents=True, exist_ok=True)
    pj.write_text(json.dumps({"name": "bitranox", "version": version, "license": "MIT"}, indent=2) + "\n",
                  encoding="utf-8", newline="\n")
    (root / "pyproject.toml").write_text(PYPROJECT.format(version=version), encoding="utf-8", newline="\n")
    (root / "CHANGELOG.md").write_text(CHANGELOG.format(version=version), encoding="utf-8", newline="\n")


def _clone(remote: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", "-q", str(remote), str(dest)], check=True, capture_output=True)
    _git(dest, "config", "user.email", "t@example.invalid")
    _git(dest, "config", "user.name", "t")
    return dest


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A clone at 1.2.3 whose origin (a bare repo beside it) is at 1.2.3 too."""
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "master", str(remote)], check=True, capture_output=True)
    work = _clone(remote, tmp_path / "work")
    _git(work, "checkout", "-q", "-b", "master")
    _write_release(work, "1.2.3")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "release 1.2.3")
    _git(work, "push", "-q", "origin", "master")
    return work


@pytest.fixture
def notes(tmp_path: Path) -> Path:
    path = tmp_path / "notes.md"
    path.write_text("### Fixed\n\n- the thing that broke.\n", encoding="utf-8", newline="\n")
    return path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {name: (root / name).read_bytes() for name in (str(PJ), "pyproject.toml", "CHANGELOG.md")}


def _versions(root: Path) -> tuple[str, str]:
    pj = json.loads((root / PJ).read_text(encoding="utf-8"))["version"]
    pp = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    return pj, pp


# ---- the bump itself ------------------------------------------------------------------------


@pytest.mark.parametrize(("part", "expected"), [("patch", "1.2.4"), ("minor", "1.3.0"), ("major", "2.0.0")])
def test_a_part_bump_raises_all_three_files_together(repo: Path, notes: Path, part: str, expected: str) -> None:
    rc = bump_version.main(["--root", str(repo), "--part", part, "--changelog", str(notes)])
    assert rc == 0
    assert _versions(repo) == (expected, expected)
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [%s]\n\n### Fixed\n\n- the thing that broke.\n\n## [1.2.3]" % expected in text


def test_an_explicit_target_is_used_as_given(repo: Path, notes: Path) -> None:
    assert bump_version.main(["--root", str(repo), "--to", "1.10.0", "--changelog", str(notes)]) == 0
    assert _versions(repo) == ("1.10.0", "1.10.0")


def test_the_pyproject_edit_changes_only_the_project_version_line(repo: Path, notes: Path) -> None:
    before = (repo / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 0
    after = (repo / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    changed = [(a, b) for a, b in zip(before, after, strict=True) if a != b]
    assert changed == [('version = "1.2.3"', 'version = "1.2.4"')]


def test_plugin_json_keeps_its_key_order_and_layout(repo: Path, notes: Path) -> None:
    before = (repo / PJ).read_text(encoding="utf-8")
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 0
    assert (repo / PJ).read_text(encoding="utf-8") == before.replace('"1.2.3"', '"1.2.4"')


def test_the_section_goes_above_the_first_release_heading_not_the_first_heading(repo: Path, notes: Path) -> None:
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 0
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.index("## Versioning") < text.index("## [1.2.4]") < text.index("## [1.2.3]")


@pytest.mark.parametrize("editor", ["stdlib", "tomlkit"])
def test_both_toml_editors_write_the_same_bytes(editor: str) -> None:
    if editor == "tomlkit" and not bump_version.HAVE_TOMLKIT:
        pytest.skip("tomlkit is not installed in this interpreter; the stdlib editor is the one in use")
    text = PYPROJECT.format(version="1.2.3")
    assert bump_version.set_pyproject_version(text, "1.2.4", editor=editor) == PYPROJECT.format(version="1.2.4")


def test_the_stdlib_editor_refuses_a_version_it_cannot_place_unambiguously() -> None:
    text = '[project]\nname = "x"\nversion = "1.0.0"\nversion = "1.0.0"\n'
    with pytest.raises(bump_version.BumpRefused):
        bump_version.set_pyproject_version(text, "1.0.1", editor="stdlib")


def test_json_output_names_old_and_new(repo: Path, notes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes), "--json"])
    envelope = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert envelope["ok"] is True
    assert envelope["data"] == {"origin": "1.2.3", "new": "1.2.4", "ref": "origin/master"}


# ---- refusals: nothing is written -----------------------------------------------------------


def test_a_peer_bump_on_origin_is_refused_after_the_fetch(repo: Path, notes: Path, tmp_path: Path) -> None:
    peer = _clone(tmp_path / "origin.git", tmp_path / "peer")
    _write_release(peer, "1.2.4")
    _git(peer, "commit", "-q", "-am", "peer release 1.2.4")
    _git(peer, "push", "-q", "origin", "master")
    before = _snapshot(repo)
    rc = bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)])
    assert rc == 1
    assert _snapshot(repo) == before


def test_control_without_the_fetch_the_stale_ref_hides_the_peer_bump(repo: Path, notes: Path, tmp_path: Path) -> None:
    # Pins that the fetch is what catches the peer: the stale ref alone still says 1.2.3.
    peer = _clone(tmp_path / "origin.git", tmp_path / "peer")
    _write_release(peer, "1.2.4")
    _git(peer, "commit", "-q", "-am", "peer release 1.2.4")
    _git(peer, "push", "-q", "origin", "master")
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes), "--no-fetch"]) == 0


def test_a_working_copy_already_bumped_is_refused(repo: Path, notes: Path) -> None:
    _write_release(repo, "1.2.4")
    before = _snapshot(repo)
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 1
    assert _snapshot(repo) == before


def test_a_pyproject_that_disagrees_with_plugin_json_is_refused(repo: Path, notes: Path) -> None:
    (repo / "pyproject.toml").write_text(PYPROJECT.format(version="1.2.2"), encoding="utf-8", newline="\n")
    before = _snapshot(repo)
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 1
    assert _snapshot(repo) == before


def test_a_target_not_above_origin_is_refused(repo: Path, notes: Path) -> None:
    assert bump_version.main(["--root", str(repo), "--to", "1.2.3", "--changelog", str(notes)]) == 1
    assert bump_version.main(["--root", str(repo), "--to", "1.1.9", "--changelog", str(notes)]) == 1
    assert _versions(repo) == ("1.2.3", "1.2.3")


def test_a_target_already_in_the_changelog_is_refused(repo: Path, notes: Path) -> None:
    path = repo / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n## [1.2.4]\n\n- stray.\n", encoding="utf-8", newline="\n")
    before = _snapshot(repo)
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 1
    assert _snapshot(repo) == before


@pytest.mark.parametrize("body", ["", "  \n\n", "## [1.2.4]\n\n- carries its own heading.\n"])
def test_an_empty_or_self_headed_section_is_refused(repo: Path, tmp_path: Path, body: str) -> None:
    notes = tmp_path / "bad.md"
    notes.write_text(body, encoding="utf-8", newline="\n")
    before = _snapshot(repo)
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 1
    assert _snapshot(repo) == before


# ---- could not run --------------------------------------------------------------------------


def test_a_missing_ref_is_a_could_not_run(repo: Path, notes: Path) -> None:
    rc = bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes),
                            "--no-fetch", "--ref", "origin/nope"])
    assert rc == 2


def test_an_unreachable_remote_is_a_could_not_run(repo: Path, notes: Path, tmp_path: Path) -> None:
    _git(repo, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(notes)]) == 2
    assert _versions(repo) == ("1.2.3", "1.2.3")


def test_a_missing_changelog_file_is_a_could_not_run(repo: Path, tmp_path: Path) -> None:
    assert bump_version.main(["--root", str(repo), "--part", "patch", "--changelog", str(tmp_path / "no.md")]) == 2
