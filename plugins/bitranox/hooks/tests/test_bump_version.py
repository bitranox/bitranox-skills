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


# ---- --rebase: a peer took the version this commit bumped to ---------------------------------


def _my_bump_commit(repo: Path, version: str = "1.2.4", message: str = "Fix the widget; 1.2.4") -> str:
    """One unpushed commit: a real change plus the bump of all three files to `version`."""
    (repo / "widget.txt").write_text("fixed\n", encoding="utf-8", newline="\n")
    pj = repo / PJ
    pj.write_text(pj.read_text(encoding="utf-8").replace('"1.2.3"', '"%s"' % version), encoding="utf-8", newline="\n")
    pp = repo / "pyproject.toml"
    pp.write_text(pp.read_text(encoding="utf-8").replace('version = "1.2.3"', 'version = "%s"' % version),
                  encoding="utf-8", newline="\n")
    cl = repo / "CHANGELOG.md"
    cl.write_text(cl.read_text(encoding="utf-8").replace(
        "## [1.2.3]", "## [%s]\n\n### Fixed\n\n- mine: the widget.\n\n## [1.2.3]" % version),
        encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _peer_takes(tmp_path: Path, version: str = "1.2.4", extra: str = "peer.txt") -> str:
    peer = _clone(tmp_path / "origin.git", tmp_path / ("peer-" + version))
    (peer / extra).write_text("peer work\n", encoding="utf-8", newline="\n")
    cl = peer / "CHANGELOG.md"
    _write_release(peer, version)
    cl.write_text(CHANGELOG.format(version="1.2.3").replace(
        "## [1.2.3]", "## [%s]\n\n### Added\n\n- peer: theirs.\n\n## [1.2.3]" % version),
        encoding="utf-8", newline="\n")
    _git(peer, "add", "-A")
    _git(peer, "commit", "-q", "-m", "peer release %s" % version)
    _git(peer, "push", "-q", "origin", "master")
    return _git(peer, "rev-parse", "HEAD")


def test_rebase_renumbers_a_taken_version_onto_origin(repo: Path, tmp_path: Path) -> None:
    mine = _my_bump_commit(repo)
    theirs = _peer_takes(tmp_path)
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 0
    assert _git(repo, "rev-parse", "HEAD^") == theirs
    assert _versions(repo) == ("1.2.5", "1.2.5")
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.index("## [1.2.5]\n\n### Fixed\n\n- mine: the widget.") < text.index("## [1.2.4]\n\n### Added")
    assert text.count("- mine: the widget.") == 1
    assert (repo / "widget.txt").read_text(encoding="utf-8") == "fixed\n"
    assert (repo / "peer.txt").exists()
    assert _git(repo, "log", "-1", "--format=%s") == "Fix the widget; 1.2.5"
    assert _git(repo, "rev-parse", "refs/bump-version/pre-rebase") == mine
    assert _git(repo, "status", "--porcelain") == ""


def test_rebase_refuses_when_the_version_was_not_taken(repo: Path, tmp_path: Path) -> None:
    mine = _my_bump_commit(repo, "1.2.5", "Fix; 1.2.5")
    _peer_takes(tmp_path, "1.2.4")
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 1
    assert _git(repo, "rev-parse", "HEAD") == mine


def test_rebase_refuses_a_dirty_tree(repo: Path, tmp_path: Path) -> None:
    mine = _my_bump_commit(repo)
    _peer_takes(tmp_path)
    (repo / "widget.txt").write_text("uncommitted\n", encoding="utf-8", newline="\n")
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 1
    assert _git(repo, "rev-parse", "HEAD") == mine
    assert (repo / "widget.txt").read_text(encoding="utf-8") == "uncommitted\n"


def test_rebase_refuses_more_than_one_unpushed_commit(repo: Path, tmp_path: Path) -> None:
    (repo / "first.txt").write_text("one\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "first.txt")
    _git(repo, "commit", "-q", "-m", "first")
    mine = _my_bump_commit(repo)
    _peer_takes(tmp_path)
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 1
    assert _git(repo, "rev-parse", "HEAD") == mine


def test_rebase_restores_the_commit_when_the_change_conflicts(repo: Path, tmp_path: Path) -> None:
    mine = _my_bump_commit(repo)
    _peer_takes(tmp_path, extra="widget.txt")          # the peer wrote the same file differently
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 1
    assert _git(repo, "rev-parse", "HEAD") == mine
    assert _git(repo, "status", "--porcelain") == ""
    assert (repo / "widget.txt").read_text(encoding="utf-8") == "fixed\n"


def test_rebase_without_part_or_changelog_is_accepted_but_a_plain_bump_still_needs_them(repo: Path) -> None:
    with pytest.raises(SystemExit):
        bump_version.main(["--root", str(repo), "--part", "patch"])        # no --changelog


@pytest.mark.parametrize(("message", "expected"), [
    ("Fix the widget; 1.2.4", "Fix the widget; 1.2.5"),
    ("Release 1.2.4.\n\nBody names 1.2.4 and 11.2.4 and 1.2.45 and 1.2.4.1.",
     "Release 1.2.5.\n\nBody names 1.2.5 and 11.2.4 and 1.2.45 and 1.2.4.1."),
])
def test_the_message_renumbers_only_whole_word_mentions(message: str, expected: str) -> None:
    assert bump_version.renumber_message(message, "1.2.4", "1.2.5") == expected


def test_rebase_carries_a_non_utf8_change_byte_for_byte(repo: Path, tmp_path: Path) -> None:
    # The patch goes from `git diff` to `git apply` as BYTES: decoding it with errors="replace"
    # turned a latin-1 byte into U+FFFD, and text-mode stdin turns \n into \r\n on Windows.
    (repo / "legacy.txt").write_bytes(b"caf\xe4\r\nline two\n")
    mine = _my_bump_commit(repo)
    _peer_takes(tmp_path)
    assert bump_version.main(["--root", str(repo), "--rebase"]) == 0
    assert _git(repo, "rev-parse", "refs/bump-version/pre-rebase") == mine
    assert (repo / "legacy.txt").read_bytes() == b"caf\xe4\r\nline two\n"
    assert _git(repo, "status", "--porcelain") == ""
