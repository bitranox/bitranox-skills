"""Tests for mem_levels: enumerate a curated memory tree's levels and the slugs at each.

The chore this replaces is a hand-rolled walk of every `CLAUDE.local.md` with a `mem:` regex, and
the regex is the trap: a slug may contain a DOT (`...-ps7.6-assemblies`), so the intuitive
`[a-z0-9-]+` matches nothing on that line at all - the pointer becomes invisible and its body reads
as an orphan. That misreading is the reason this tool exists, so it is the first test.

All content ASCII.
"""

from pathlib import Path

import pytest

import mem_levels

DOTTED = "reference-pwshpy-tier-b-hosting-reuse-installed-ps7.6-assemblies"

BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->
<!-- bitranox:self-learning -->
WHAT: a level
<!-- /bitranox:self-learning -->

## Memory index
{rows}
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


def _row(slug, title="T", hook="When x, do y."):
    return f"- [{title}](mem:{slug}) - {hook}"


def _tree(root: Path, levels: dict[str, list[str]], bodies: list[str] | None = None) -> Path:
    """Build a memory tree: {relative level dir: [slugs]} plus optional central body slugs."""
    for rel, slugs in levels.items():
        d = root / rel if rel != "." else root
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        (d / "CLAUDE.local.md").write_text(
            BLOCK.format(rows="\n".join(_row(s) for s in slugs)), encoding="utf-8")
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True, exist_ok=True)
    for slug in (bodies if bodies is not None else [s for v in levels.values() for s in v]):
        (facts / f"{slug}.md").write_text("---\nname: %s\n---\n\nbody\n" % slug, encoding="utf-8")
    return root


def test_a_dotted_slug_is_found(tmp_path):
    """The regression this tool exists for: a naive [a-z0-9-]+ misses the line entirely."""
    root = _tree(tmp_path / "t", {".": [DOTTED, "plain-slug"]})

    report = mem_levels.scan(root)

    assert set(report.levels["."]) == {DOTTED, "plain-slug"}


def test_levels_are_enumerated_with_their_slugs(tmp_path):
    root = _tree(tmp_path / "t", {".": ["top-fact"], "sub": ["sub-fact"], "sub/deep": []})

    report = mem_levels.scan(root)

    assert report.levels["."] == ["top-fact"]
    assert report.levels["sub"] == ["sub-fact"]
    assert report.levels["sub/deep"] == []          # a curated level with no facts still counts


def test_slug_lookup_reports_the_owning_level(tmp_path):
    root = _tree(tmp_path / "t", {".": ["top-fact"], "sub": ["sub-fact"]})

    report = mem_levels.scan(root)

    assert report.level_of("sub-fact") == ["sub"]
    assert report.level_of("nope") == []


def test_a_slug_pointed_at_from_two_levels_is_flagged(tmp_path):
    """Slugs are tree-unique; two pointers is the violation --check-tree exists to catch."""
    root = _tree(tmp_path / "t", {".": ["shared"], "sub": ["shared"]})

    report = mem_levels.scan(root)

    assert report.duplicates == {"shared": [".", "sub"]}


def test_a_body_with_no_pointer_is_reported_as_dangling(tmp_path):
    root = _tree(tmp_path / "t", {".": ["pointed"]}, bodies=["pointed", "orphan"])

    report = mem_levels.scan(root)

    assert report.dangling == ["orphan"]


def test_a_pointer_with_no_body_is_reported(tmp_path):
    root = _tree(tmp_path / "t", {".": ["pointed", "bodyless"]}, bodies=["pointed"])

    report = mem_levels.scan(root)

    assert report.bodyless == ["bodyless"]


def test_cli_lists_levels_and_exits_zero(tmp_path, capsys):
    root = _tree(tmp_path / "t", {".": ["top-fact"]})

    rc = mem_levels.main(["--root", str(root)])

    assert rc == 0
    assert "top-fact" in capsys.readouterr().out


def test_cli_slug_lookup_exits_one_when_absent(tmp_path, capsys):
    """0 yes / 1 no / 2 error - a format-independent exit code, so it works in a gate."""
    root = _tree(tmp_path / "t", {".": ["top-fact"]})

    assert mem_levels.main(["--root", str(root), "--slug", "top-fact"]) == 0
    assert mem_levels.main(["--root", str(root), "--slug", "absent"]) == 1


def test_cli_exits_two_on_a_missing_root(tmp_path, capsys):
    rc = mem_levels.main(["--root", str(tmp_path / "nope")])

    assert rc == 2
    assert "nope" in capsys.readouterr().err


def test_cli_json_is_machine_readable(tmp_path, capsys):
    import json as _json
    root = _tree(tmp_path / "t", {".": ["top-fact"], "sub": ["sub-fact"]})

    rc = mem_levels.main(["--root", str(root), "--json"])

    assert rc == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["levels"]["sub"] == ["sub-fact"]


def test_json_still_emitted_on_failure(tmp_path, capsys):
    import json as _json
    rc = mem_levels.main(["--root", str(tmp_path / "nope"), "--json"])

    assert rc == 2
    assert _json.loads(capsys.readouterr().out)["ok"] is False


def test_a_suffixed_venv_is_pruned_like_a_plain_one(tmp_path):
    """`.venv-win`, `.venv-3.13`, `venv-<user>` and `venv_<project>` are all real names on this
    fleet, and an exact-match prune set covers none of them.

    The plugin vendors CLAUDE.local.md into site-packages, so an install into any of those makes
    a vendored copy read as a real memory level - inflating the level count with files nobody
    can edit. srccount.py in this same skill already carries the tested filter for these shapes;
    this keeps its sibling from disagreeing with it.
    """
    real = tmp_path / "proj"
    real.mkdir()
    (real / "CLAUDE.local.md").write_text("- [T](mem:a-slug) - hook\n", encoding="utf-8")
    for venv in (".venv", ".venv-win", ".venv-3.13", "venv-alice", "venv_thing"):
        vendored = tmp_path / venv / "lib" / "site-packages" / "pkg"
        vendored.mkdir(parents=True)
        (vendored / "CLAUDE.local.md").write_text("- [V](mem:vendored) - hook\n",
                                                  encoding="utf-8")
    report = mem_levels.scan(tmp_path)
    levels = sorted(report.levels)
    assert [lvl for lvl in levels if "venv" in lvl] == [], f"vendored copies leaked in: {levels}"
    # Control: exactly one level survives, so a filter that pruned EVERYTHING cannot pass this.
    assert len(levels) == 1, levels


# ==== rank-10 skill-script audit: legacy pointers, unreadable levels, the anchor check ==========

import json
import os
import subprocess
import sys

LEGACY_UUID = "5f0e1c2a-0000-5000-8000-000000000001"


def _legacy_row(slug, uuid=LEGACY_UUID):
    return f"- [Old fact](uuid:{uuid}) - When old, do old. <!-- bx:slug={slug} -->"


def _level(root: Path, rel: str, rows: list[str]) -> Path:
    d = root / rel if rel != "." else root
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLAUDE.local.md").write_text(BLOCK.format(rows="\n".join(rows)), encoding="utf-8")
    return d / "CLAUDE.local.md"


def test_a_legacy_uuid_pointer_is_a_fact_at_its_level(tmp_path, capsys):
    root = _tree(tmp_path / "t", {".": []}, bodies=[])
    _level(root, ".", [_legacy_row("old-fact")])
    shard = root / ".claude-memory" / "facts" / LEGACY_UUID[:2]
    shard.mkdir(parents=True)
    (shard / f"{LEGACY_UUID}.md").write_text("---\nname: old-fact\n---\nbody\n", encoding="utf-8")

    rc = mem_levels.main(["--root", str(root), "--slug", "old-fact"])

    assert rc == 0 and capsys.readouterr().out.split() == ["."]
    assert mem_levels.scan(root).bodyless == []


def test_a_legacy_pointer_without_its_sharded_body_is_bodyless(tmp_path):
    root = _tree(tmp_path / "t", {".": ["kept"]})
    _level(root, ".", [_row("kept"), _legacy_row("old-fact")])

    assert mem_levels.scan(root).bodyless == ["old-fact"]


def _sharded_body(root: Path, uuid: str = LEGACY_UUID, name: str = "old-fact") -> Path:
    shard = root / ".claude-memory" / "facts" / uuid[:2]
    shard.mkdir(parents=True, exist_ok=True)
    body = shard / f"{uuid}.md"
    body.write_text(f"---\nname: {name}\n---\nbody\n", encoding="utf-8")
    return body


def test_a_sharded_body_no_pointer_names_is_dangling(tmp_path, capsys):
    # A pre-pivot body the migration left behind (or whose pointer was deleted) is loaded by
    # nothing - exactly what a flat orphan is - but only facts/*.md was ever listed.
    root = _tree(tmp_path / "t", {".": ["kept"]})
    _sharded_body(root)

    report = mem_levels.scan(root)
    rc = mem_levels.main(["--root", str(root)])

    assert report.dangling == [f"{LEGACY_UUID[:2]}/{LEGACY_UUID}"]
    assert rc == 0 and f"dangling body (no pointer at any level): {LEGACY_UUID[:2]}/" in (
        capsys.readouterr().out)


def test_a_sharded_body_its_legacy_pointer_names_is_not_dangling(tmp_path):
    # The control: the same body with the pre-pivot pointer that reads it is healthy.
    root = _tree(tmp_path / "t", {".": ["kept"]})
    _level(root, ".", [_row("kept"), _legacy_row("old-fact")])
    _sharded_body(root)

    report = mem_levels.scan(root)

    assert report.dangling == [] and report.bodyless == []


def test_a_sharded_body_is_dangling_even_when_its_slug_has_a_flat_pointer(tmp_path):
    # Migrated: the pointer is `mem:old-fact` and the flat body exists, so nothing reads the
    # sharded copy any more. Matching on the slug in its frontmatter would call it pointed.
    root = _tree(tmp_path / "t", {".": ["old-fact"]})
    _sharded_body(root, name="old-fact")

    assert mem_levels.scan(root).dangling == [f"{LEGACY_UUID[:2]}/{LEGACY_UUID}"]


def test_a_file_in_a_non_shard_subdir_is_not_a_body(tmp_path):
    # Only facts/<first 2 chars of the uuid>/<uuid>.md is where the engine reads a legacy body;
    # anything else under facts/ is not a fact, so it cannot be an orphaned one.
    root = _tree(tmp_path / "t", {".": ["kept"]})
    notes = root / ".claude-memory" / "facts" / "notes"
    notes.mkdir()
    (notes / "readme.md").write_text("x\n", encoding="utf-8")

    assert mem_levels.scan(root).dangling == []


@pytest.mark.skipif(sys.platform == "win32" or getattr(os, "geteuid", lambda: 1)() == 0,
                    reason="needs POSIX mode bits and a non-root user to make a shard unreadable")
def test_an_unreadable_shard_is_an_error_not_a_clean_answer(tmp_path, capsys):
    root = _tree(tmp_path / "t", {".": ["kept"]})
    shard = _sharded_body(root).parent
    shard.chmod(0)
    try:
        rc = mem_levels.main(["--root", str(root)])
        err = capsys.readouterr().err
    finally:
        shard.chmod(0o755)
    assert rc == 2 and LEGACY_UUID[:2] in err


def test_an_empty_store_still_reports_every_pointer_as_bodyless(tmp_path):
    root = _tree(tmp_path / "t", {".": ["gone-fact"]}, bodies=[])

    report = mem_levels.scan(root)

    assert report.bodyless == ["gone-fact"]


def test_a_root_without_a_store_is_refused(tmp_path, capsys):
    """A sub-level passed as --root used to report clean, with the body check silently off."""
    level = tmp_path / "sub"
    _level(tmp_path, "sub", [_row("gone-fact")])

    rc = mem_levels.main(["--root", str(level)])

    assert rc == 2
    assert ".claude-memory" in capsys.readouterr().err


def test_a_root_without_a_store_is_refused_in_json_too(tmp_path, capsys):
    _level(tmp_path, ".", [_row("gone-fact")])

    rc = mem_levels.main(["--root", str(tmp_path), "--json", "--slug", "gone-fact"])

    cap = capsys.readouterr()
    assert rc == 2 and json.loads(cap.out)["ok"] is False


@pytest.mark.skipif(sys.platform == "win32" or getattr(os, "geteuid", lambda: 1)() == 0,
                    reason="needs POSIX mode bits and a non-root user to make a level unreadable")
@pytest.mark.parametrize("what", ["file", "dir"])
def test_an_unreadable_level_is_an_error_not_a_no(tmp_path, capsys, what):
    root = _tree(tmp_path / "t", {".": ["top-fact"], "sub": ["hidden-fact"]})
    target = root / "sub" / "CLAUDE.local.md" if what == "file" else root / "sub"
    target.chmod(0)
    try:
        slug_rc = mem_levels.main(["--root", str(root), "--slug", "hidden-fact"])
        slug_err = capsys.readouterr().err
        list_rc = mem_levels.main(["--root", str(root)])
        list_err = capsys.readouterr().err
    finally:
        target.chmod(0o755 if what == "dir" else 0o644)
    assert slug_rc == 2 and list_rc == 2
    assert "sub" in slug_err and "sub" in list_err


def test_slug_json_found_and_absent(tmp_path, capsys):
    root = _tree(tmp_path / "t", {"sub": ["sub-fact"]})

    found_rc = mem_levels.main(["--root", str(root), "--slug", "sub-fact", "--json"])
    found = capsys.readouterr()
    absent_rc = mem_levels.main(["--root", str(root), "--slug", "nope-fact", "--json"])
    absent = capsys.readouterr()

    assert found_rc == 0 and json.loads(found.out) == {
        "ok": True, "command": "mem_levels", "data": {"slug": "sub-fact", "levels": ["sub"]}}
    assert found.err == ""
    assert absent_rc == 1 and json.loads(absent.out)["data"]["levels"] == []
    assert "no level points at nope-fact" in absent.err


def test_slug_text_absent_names_the_slug_on_stderr(tmp_path, capsys):
    root = _tree(tmp_path / "t", {".": ["top-fact"]})

    rc = mem_levels.main(["--root", str(root), "--slug", "absent-fact"])

    cap = capsys.readouterr()
    assert rc == 1 and cap.out == "" and "no level points at absent-fact" in cap.err


def test_a_non_ascii_level_survives_a_cp1252_stdout(tmp_path):
    root = _tree(tmp_path / "t", {"Проект": ["ru-fact"]})
    script = Path(mem_levels.__file__).resolve()
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    for extra in (["--slug", "ru-fact"], []):
        proc = subprocess.run([sys.executable, str(script), "--root", str(root), *extra],
                              capture_output=True, env=env)
        assert proc.returncode == 0, proc.stderr
        assert "Проект" in proc.stdout.decode("utf-8")


def test_a_bom_does_not_hide_the_first_pointer(tmp_path):
    """The pointer regex is anchored at ^, so a BOM glued to line 1 made its pointer invisible."""
    root = _tree(tmp_path / "t", {".": []}, bodies=["a-fact"])
    (root / "CLAUDE.local.md").write_bytes(
        b"\xef\xbb\xbf" + (_row("a-fact") + "\n" + _row("b-fact") + "\n").encode("utf-8"))

    assert mem_levels.scan(root).levels["."] == ["a-fact", "b-fact"]


def test_an_unexpected_crash_exits_2_not_the_gate_answer_1(tmp_path, capsys, monkeypatch):
    """1 is the gate's "no level holds it". stdout is the external edge that fails here."""
    class Broken:
        def write(self, _):
            raise RuntimeError("stream gone")

        def flush(self):
            pass

    root = _tree(tmp_path / "t", {".": ["top-fact"]})
    monkeypatch.setattr(sys, "stdout", Broken())
    rc = mem_levels.main(["--root", str(root), "--slug", "top-fact"])
    assert rc == 2 and "stream gone" in capsys.readouterr().err
