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
