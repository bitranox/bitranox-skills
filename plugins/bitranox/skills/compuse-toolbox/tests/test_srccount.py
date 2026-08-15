"""Tests for srccount.

The regression these exist for: a hand-rolled `find -name '*.py' -not -path '*/.venv/*'`
returned 271423 .py for one subtree against a true 4859, because the filter covered `.venv`
and missed `venv-*/`, `venv_*/` and `site-packages/`. The inflated figure was then quoted as
evidence. So the load-bearing test is not "does it count" but "does it catch EVERY venv shape",
plus a known-negative that must report zero.

Every tree here is planted explicitly under tmp_path - nothing reads ambient machine state.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import srccount


def plant(root: Path, rel_files: list[str]) -> None:
    """Create each relative path under root as a file with one line of content."""
    for rel in rel_files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x = 1\n", encoding="utf-8")


# A marker is only a marker if its CONTENT validates, so these write the real thing and each
# call site names which kind it is planting. plant() deliberately does NOT special-case the
# filenames: a helper that silently substitutes valid content hides what the fixture contains,
# and hid eight fixtures that were planting markers the validator correctly rejected.
def mark_venv(directory: Path) -> Path:
    """Make `directory` a virtualenv the way python -m venv does (PEP 405 `home` key)."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "pyvenv.cfg"
    target.write_text("home = /usr/bin\ninclude-system-site-packages = false\n", encoding="utf-8")
    return target


def mark_cache(directory: Path) -> Path:
    """Make `directory` a cache dir the way cargo does (bford.info signature line)."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "CACHEDIR.TAG"
    target.write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n# written by a build tool\n",
        encoding="utf-8")
    return target


@pytest.fixture
def mixed_tree(tmp_path: Path) -> Path:
    """3 real source files and 8 excluded, one per venv shape MEASURED in this tree.

    `.venv_*` is deliberately absent: it occurs nowhere here, so it was dropped from the
    exclusion list and from this fixture rather than kept as an invented shape.
    """
    root = tmp_path / "proj"
    plant(root, [
        # first-party source
        "src/app.py",
        "src/util.py",
        "tests/test_app.py",
        # vendored, one per shape that the naive filter missed
        ".venv/lib/dep_a.py",
        "venv/lib/dep_b.py",
        "venv-py311/lib/dep_c.py",
        "venv_navision/lib/dep_d.py",
        ".venv-win/lib/dep_e.py",
        "other/site-packages/dep_g.py",
        "web/node_modules/dep_h.py",
        "third_party/dep_i.py",
    ])
    return root


def test_counts_only_first_party_source(mixed_tree: Path) -> None:
    """The whole point: excluded files must not land in the source count."""
    result = srccount.count_tree(mixed_tree, extensions=[".py"])
    assert result.source == 3, f"expected 3 first-party files, got {result.source}"


def test_every_venv_shape_is_recognised(mixed_tree: Path) -> None:
    """The actual defect. A filter covering only `.venv` leaves 8 of 9 files counted."""
    result = srccount.count_tree(mixed_tree, extensions=[".py"])
    assert result.excluded == 8, f"expected 8 excluded files, got {result.excluded}"


def test_excluded_share_makes_the_inflation_visible(mixed_tree: Path) -> None:
    """The magnitude signal - 8 of 11 is 72.7%, and the report must say so."""
    result = srccount.count_tree(mixed_tree, extensions=[".py"])
    assert result.total == 11
    assert result.excluded_share == pytest.approx(72.7, abs=0.1)


def test_known_negative_a_clean_tree_reports_zero_excluded(tmp_path: Path) -> None:
    """CONTROL. A detector that cannot say 'nothing excluded here' proves nothing at 75%."""
    root = tmp_path / "clean"
    plant(root, ["src/a.py", "src/b.py", "docs/conf.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 3
    assert result.excluded == 0
    assert result.excluded_share == pytest.approx(0.0)


def test_a_dir_merely_starting_with_venv_is_not_excluded(tmp_path: Path) -> None:
    """Guard the opposite bias: over-excluding invents the mirror of the bug being fixed."""
    root = tmp_path / "proj"
    plant(root, ["venvironment_helpers/a.py", "vendored_by_us_on_purpose/b.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.excluded == 0, "only exact names and venv-/venv_ prefixes are excluded"
    assert result.source == 2


def test_reports_which_pattern_excluded_what(mixed_tree: Path) -> None:
    """The exclusion list IS the instrument, so it has to be auditable, not implicit."""
    result = srccount.count_tree(mixed_tree, extensions=[".py"])
    assert result.by_pattern["site-packages"] == 1
    assert result.by_pattern["node_modules"] == 1
    assert sum(result.by_pattern.values()) == result.excluded


def test_several_extensions(mixed_tree: Path) -> None:
    plant(mixed_tree, ["scripts/run.sh", ".venv/bin/activate.sh"])
    result = srccount.count_tree(mixed_tree, extensions=[".py", ".sh"])
    assert result.source == 4
    assert result.excluded == 9


def test_extra_exclude_is_honoured(mixed_tree: Path) -> None:
    plant(mixed_tree, ["generated/pb2.py"])
    result = srccount.count_tree(mixed_tree, extensions=[".py"], extra_excludes=["generated"])
    assert result.source == 3
    assert result.by_pattern["generated"] == 1


def test_empty_tree_does_not_divide_by_zero(tmp_path: Path) -> None:
    """A real input here: some top-level dirs (Navision, NavEtkPrint) hold no source at all."""
    root = tmp_path / "empty"
    root.mkdir()
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.total == 0
    assert result.excluded_share == pytest.approx(0.0)


def test_extension_accepts_a_bare_suffix(tmp_path: Path) -> None:
    """`--ext py` is what a hand types; it must mean the same as `--ext .py`."""
    root = tmp_path / "proj"
    plant(root, ["a.py", "b.py"])
    assert srccount.count_tree(root, extensions=["py"]).source == 2


def test_missing_root_is_an_error_not_a_zero(tmp_path: Path) -> None:
    """A count of 0 for a path that does not exist is the silent-wrong-answer shape."""
    with pytest.raises(FileNotFoundError):
        srccount.count_tree(tmp_path / "nope", extensions=[".py"])


# --- the default extension set -----------------------------------------------------------
# A tool for COMPARING subtrees that defaults to one language reports 0 for a tree written in
# another, and 0 reads as "no code here" rather than "wrong flag" - the same confidently-wrong
# number this tool exists to prevent, arriving from the other direction.

def test_default_extensions_span_more_than_python(tmp_path: Path) -> None:
    root = tmp_path / "poly"
    plant(root, ["a.py", "b.sh", "c.ps1", "d.rs", "e.ts", "f.pl"])
    result = srccount.count_tree(root, extensions=None)
    assert result.source == 6, f"default set missed some: {result.by_ext}"


def test_default_set_does_not_count_prose_as_source(tmp_path: Path) -> None:
    """CONTROL for the default set - it must exclude something, or it is not a source filter."""
    root = tmp_path / "docs"
    plant(root, ["README.md", "notes.txt", "data.json", "real.py"])
    result = srccount.count_tree(root, extensions=None)
    assert result.source == 1


def test_per_extension_breakdown(tmp_path: Path) -> None:
    """A zero has to be interpretable: which extensions were actually looked for."""
    root = tmp_path / "poly"
    plant(root, ["a.py", "b.py", "c.sh"])
    result = srccount.count_tree(root, extensions=[".py", ".sh"])
    assert result.by_ext == {".py": 2, ".sh": 1}


def test_a_zero_count_still_names_what_was_searched(tmp_path: Path) -> None:
    """The LinuxTreasureTrove case: a docs tree must not read as 'no code' with no explanation."""
    root = tmp_path / "prose"
    plant(root, ["a.md", "b.md"])
    done = run_cli("--root", str(root), "--ext", ".py")
    assert ".py" in done.stdout, "a 0 with no extension list is unreadable"


# --- CLI ---------------------------------------------------------------------------------

def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    tool = Path(srccount.__file__)
    return subprocess.run(
        [sys.executable, str(tool), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def test_cli_json_envelope(mixed_tree: Path) -> None:
    done = run_cli("--root", str(mixed_tree), "--ext", ".py", "--json")
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "srccount"
    assert payload["data"]["extensions"] == [".py"]
    row = payload["data"]["roots"][0]
    assert row["source"] == 3
    assert row["excluded"] == 8
    assert row["by_ext"] == {".py": 3}


def test_a_high_excluded_share_is_normal_and_exits_zero(mixed_tree: Path) -> None:
    """A 75% (or 98%) excluded share means the tool worked, not that anything is wrong.

    Gating an exit code on it fired on every real tree measured, which trains a reader to
    ignore the signal. The share is reported; it is not a verdict.
    """
    done = run_cli("--root", str(mixed_tree), "--ext", ".py")
    assert done.returncode == 0, done.stderr
    assert "72.7" in done.stdout


def test_the_retired_share_threshold_flag_is_gone(mixed_tree: Path) -> None:
    """Retired deliberately - fail loudly on a stale invocation rather than silently ignoring it."""
    done = run_cli("--root", str(mixed_tree), "--max-vendored-share", "50")
    assert done.returncode == 2
    assert "max-vendored-share" in done.stderr


def test_cli_bad_root_exits_two(tmp_path: Path) -> None:
    done = run_cli("--root", str(tmp_path / "nope"))
    assert done.returncode == 2
    assert done.stdout.strip() == "" or "nope" in done.stderr


# --- symlinks: measured, not assumed ------------------------------------------------------

def test_symlinked_dir_is_not_descended_symlinked_file_is_counted(tmp_path: Path) -> None:
    """Measured 2026-08-15: rglob+is_file() and os.walk agree exactly on this, so the switch
    to os.walk did not change what gets counted. Encoded so a future walk change cannot
    silently diverge - the counts would drift on any tree holding a symlinked directory."""
    outside = tmp_path / "outside"
    plant(outside, ["b.py"])
    root = tmp_path / "proj"
    plant(root, ["sub/a.py"])
    (root / "linked_dir").symlink_to(outside, target_is_directory=True)
    (root / "linked_file.py").symlink_to(outside / "b.py")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 2, "sub/a.py + linked_file.py; the symlinked DIR is not descended"


# --- the default extension set: state the principle, then pin the boundary ----------------

def test_default_set_members_are_executed_or_compiled(tmp_path: Path) -> None:
    """The membership principle: a file a human writes that the machine runs or compiles."""
    root = tmp_path / "poly"
    members = ["a.py", "b.sh", "c.ps1", "d.rs", "e.ts", "f.pl", "g.go", "h.c", "i.java", "j.sql"]
    plant(root, members)
    assert srccount.count_tree(root, extensions=None).source == len(members)


def test_default_set_excludes_prose_data_and_markup(tmp_path: Path) -> None:
    """The other half of the boundary. Without this the set has no stated edge, only members."""
    root = tmp_path / "notsource"
    plant(root, ["a.md", "b.txt", "c.json", "d.yaml", "e.yml", "f.toml", "g.csv", "h.rst",
                 "i.html", "j.css", "k.lock", "l.cfg", "m.ini"])
    result = srccount.count_tree(root, extensions=None)
    assert result.source == 0, f"non-source counted: {result.by_ext}"


# --- generated output dirs (measured against the real trees) ------------------------------

def test_tool_written_generated_dirs_are_excluded(tmp_path: Path) -> None:
    """Every member is a fixed name a NAMED tool writes, is not a plausible first-party
    package name, AND was measured present in this tree. `coverage/` fails the second rule
    and `.next/` the third, so both stay counted (guard tests below)."""
    root = tmp_path / "web"
    plant(root, [
        "src/app.js",
        ".docusaurus/y.js",
        ".pytest_cache/a.js",
        ".ruff_cache/b.js",
        "__pycache__/c.js",
    ])
    result = srccount.count_tree(root, extensions=[".js"])
    assert result.source == 1, f"generated output counted as source: {result.by_pattern}"


def test_ambiguous_build_dirs_are_NOT_excluded(tmp_path: Path) -> None:
    """`build`, `dist`, `target` and `out` are as often real package names as generated dirs.
    Guessing costs first-party source silently; the per-directory breakdown surfaces them
    instead, and `--exclude build` is one flag away."""
    root = tmp_path / "proj"
    plant(root, ["build/gen.py", "dist/gen.py", "target/gen.py", "out/gen.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 4, "over-excluding is the mirror of the bug this tool fixes"


# --- per-directory decomposition ----------------------------------------------------------

def test_source_is_broken_down_by_top_directory(tmp_path: Path) -> None:
    """A dominant SUBTREE must be as visible as a dominant extension: one measured tree read
    87696 source, of which 36689 .c sat in a single vendored upstream kernel checkout."""
    root = tmp_path / "proj"
    plant(root, ["upstream/a.py", "upstream/b.py", "upstream/c.py", "mine/d.py", "top.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.by_top_dir["upstream"] == 3
    assert result.by_top_dir["mine"] == 1
    assert result.by_top_dir["."] == 1


def test_the_total_is_never_printed_without_its_decomposition(tmp_path: Path) -> None:
    """The headline is only safe to read beside where it came from - an upstream checkout
    the exclusion list cannot see by name is otherwise invisible in the total."""
    root = tmp_path / "proj"
    plant(root, ["upstream/a.py", "upstream/b.py", "mine/c.py"])
    done = run_cli("--root", str(root), "--ext", ".py")
    assert done.returncode == 0, done.stderr
    assert "upstream=2" in done.stdout
    assert "by directory" in done.stdout


# --- exit codes: 0 yes / 1 no / 2 error ---------------------------------------------------

def test_no_source_found_anywhere_exits_one(tmp_path: Path) -> None:
    """The wrong-extension failure fix 1 was about, now answerable by a script.
    0 yes / 1 no: nothing matched anywhere almost always means a wrong --ext or path."""
    root = tmp_path / "prose"
    plant(root, ["a.md", "b.md"])
    done = run_cli("--root", str(root), "--ext", ".py")
    assert done.returncode == 1
    assert "no source" in done.stderr.lower()


def test_one_empty_root_among_several_is_data_not_failure(tmp_path: Path) -> None:
    """CONTROL, and the reason the gate is all-roots not any-root: a genuinely empty tree
    (Navision holds no source at all) is a real answer, not an error."""
    empty = tmp_path / "empty"
    empty.mkdir()
    full = tmp_path / "full"
    plant(full, ["a.py"])
    done = run_cli("--root", str(empty), "--root", str(full), "--ext", ".py")
    assert done.returncode == 0, done.stderr


# --- the exclusion list cannot grow by intuition -------------------------------------------
# Three rounds of fixes to this tool each added a new unverified NAME LIST: the venv filter,
# then the extension set, then the generated-output dirs. A name-based classifier is made of
# exactly that, so the list is gated structurally rather than by remembering to be careful.

def test_every_excluded_name_carries_a_stated_reason(tmp_path: Path) -> None:
    """The set is DERIVED from the justification map, so a name cannot be added without one."""
    assert set(srccount.EXCLUDED_EXACT) == set(srccount.EXCLUDED_REASONS)
    for name, reason in srccount.EXCLUDED_REASONS.items():
        assert len(reason) > 15, f"{name} has no real justification: {reason!r}"
    for glob in srccount.EXCLUDED_GLOBS:
        assert glob in srccount.EXCLUDED_GLOB_REASONS, f"{glob} has no stated reason"


def test_names_that_could_be_first_party_packages_are_never_excluded(tmp_path: Path) -> None:
    """The guard that stops a careless addition. `coverage` is a real PyPI package name, and
    the rest are ordinary source directory names - excluding any of them costs first-party
    source silently, which is the mirror of the bug this tool exists to fix."""
    plausible = [
        "build", "dist", "target", "out", "coverage", "src", "lib", "app", "core",
        "common", "utils", "docs", "tests", "tools", "scripts", "bin", "data", "web",
    ]
    for name in plausible:
        assert name not in srccount.EXCLUDED_EXACT, f"{name} would silently eat first-party source"


def test_a_first_party_coverage_package_is_counted(tmp_path: Path) -> None:
    """The concrete case: coverage.py's own source tree, or any project with a coverage
    package. Generated JS coverage output is surfaced by the per-directory breakdown and
    removed with `--exclude coverage`, not by guessing."""
    root = tmp_path / "proj"
    plant(root, ["coverage/__init__.py", "coverage/control.py", "src/app.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 3, "a coverage/ package must not vanish"
    assert result.by_top_dir["coverage"] == 2


def test_excluding_it_explicitly_still_works(tmp_path: Path) -> None:
    """CONTROL for the above - the escape hatch has to actually work, or dropping the name
    from the default set just loses the capability."""
    root = tmp_path / "proj"
    plant(root, ["coverage/lcov-report/x.py", "src/app.py"])
    result = srccount.count_tree(root, extensions=[".py"], extra_excludes=["coverage"])
    assert result.source == 1
    assert result.by_pattern["coverage"] == 1


# --- the list is only what the tree actually contains ---------------------------------------
# The list had grown to 23 names of which 11 occur NOWHERE in this tree - kept on the strength
# of a plausible-sounding reason, which gates effort rather than correctness. A local jig's
# exclusion list is evidence, not a taxonomy of every build tool that exists.

ABSENT_FROM_THIS_TREE = [
    ".eggs", ".gradle", ".mypy_cache", ".next", ".nox", ".nuxt",
    ".parcel-cache", ".terraform", ".tox", "dist-packages", "htmlcov",
]


def test_names_absent_from_this_tree_are_not_in_the_list() -> None:
    """Measured over 455074 directories: each of these occurs zero times."""
    for name in ABSENT_FROM_THIS_TREE:
        assert name not in srccount.EXCLUDED_EXACT, f"{name} was never measured here"
    assert ".venv_*" not in srccount.EXCLUDED_GLOBS, "zero matches; .venv-* covers the real ones"


def test_the_names_that_survived_are_the_ones_that_occur() -> None:
    """The other half of the boundary - a shrink that removed everything would also pass the
    test above. These twelve were each measured present."""
    for name in (".docusaurus", ".git", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__",
                 "node_modules", "site-packages", "third_party", "thirdparty", "vendor", "venv"):
        assert name in srccount.EXCLUDED_EXACT, f"{name} occurs here and must stay excluded"
    for glob in ("venv-*", "venv_*", ".venv-*", "*.egg-info"):
        assert glob in srccount.EXCLUDED_GLOBS


def test_a_dropped_name_is_counted_and_the_breakdown_surfaces_it(tmp_path: Path) -> None:
    """What makes the shrink safe: a dropped name is not invisible, it is VISIBLE and one flag
    from being excluded. This is the decomposition doing the work the classifier used to."""
    root = tmp_path / "proj"
    plant(root, [".next/gen_a.js", ".next/gen_b.js", "src/app.js"])
    result = srccount.count_tree(root, extensions=[".js"])
    assert result.source == 3
    assert result.by_top_dir[".next"] == 2, "a dropped name must show up, not hide in the total"
    narrowed = srccount.count_tree(root, extensions=[".js"], extra_excludes=[".next"])
    assert narrowed.source == 1
    assert narrowed.by_pattern[".next"] == 2


def test_an_unmeasured_venv_shape_is_counted_and_visible(tmp_path: Path) -> None:
    """`.venv_alt` was in the fixture and in the list until it was measured at zero. Dropping
    it does not hide anything: it is counted, it shows in the per-directory breakdown, and one
    --exclude removes it. That is what makes shrinking the classifier safe."""
    root = tmp_path / "proj"
    plant(root, [".venv_alt/lib/dep.py", "src/app.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 2
    assert result.by_top_dir[".venv_alt"] == 1
    assert srccount.count_tree(root, extensions=[".py"], extra_excludes=[".venv_alt"]).source == 1


# --- --audit: the tool checks its own exclusion list against the tree ----------------------
# Rule 3 says every member must be measured present here, but nothing re-measured as the tree
# changed, so the rule was a comment. --audit makes it something the tool checks about itself.

def test_audit_reports_a_member_that_matches_nothing(tmp_path: Path) -> None:
    """Half one: members that have stopped occurring are drop candidates."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", ".venv/lib/dep.py"])
    report = srccount.audit([root], extensions=[".py"])
    assert "node_modules" in report.unused_members
    assert "vendor" in report.unused_members


def test_audit_does_not_report_a_member_that_does_occur(tmp_path: Path) -> None:
    """CONTROL. An audit that lists every member is not measuring anything."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", ".venv/lib/dep.py", "web/node_modules/x.py"])
    report = srccount.audit([root], extensions=[".py"])
    assert ".venv" not in report.unused_members
    assert "node_modules" not in report.unused_members


def test_audit_finds_a_virtualenv_the_name_list_misses(tmp_path: Path) -> None:
    """Half two, and the point: identify a MISSED dependency tree by CONTENT, never by
    guessing another name. `pyvenv.cfg` is the file python -m venv writes to mark a venv,
    so a directory holding one IS a virtualenv whatever it is called."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", "myenv/lib/dep.py"])
    mark_venv(root / "myenv")
    report = srccount.audit([root], extensions=[".py"])
    assert any(p.name == "myenv" for p in report.content_only)


def test_audit_does_not_flag_an_already_excluded_venv(tmp_path: Path) -> None:
    """CONTROL for the content check - it must be able to come back empty."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", ".venv/lib/dep.py"])
    mark_venv(root / ".venv")
    report = srccount.audit([root], extensions=[".py"])
    assert report.content_only == []


def test_audit_ranks_directory_names_by_counted_source(tmp_path: Path) -> None:
    """Half three: no classification at all, just where the counted files actually are, so a
    generated tree the list cannot name still surfaces for a human to judge."""
    root = tmp_path / "proj"
    plant(root, [f"generated/f{i}.py" for i in range(5)] + ["src/app.py"])
    report = srccount.audit([root], extensions=[".py"])
    assert report.top_counted_dirs[0] == ("generated", 5)


def test_audit_exits_one_on_a_content_proven_miss(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    plant(root, ["src/a.py", "myenv/lib/dep.py"])
    mark_venv(root / "myenv")
    done = run_cli("--audit", "--root", str(root), "--ext", ".py")
    assert done.returncode == 1
    assert "myenv" in done.stdout


def test_audit_exits_zero_when_nothing_is_content_proven(tmp_path: Path) -> None:
    """CONTROL for the exit code. Unused members alone are INFORMATION, not a failure - on a
    partial tree almost every member is unused, and a gate that always fires is ignored."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", ".venv/lib/dep.py"])
    mark_venv(root / ".venv")
    done = run_cli("--audit", "--root", str(root), "--ext", ".py")
    assert done.returncode == 0, done.stdout + done.stderr


def test_audit_json_envelope(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    plant(root, ["src/a.py", "myenv/lib/dep.py"])
    mark_venv(root / "myenv")
    done = run_cli("--audit", "--root", str(root), "--ext", ".py", "--json")
    payload = json.loads(done.stdout)
    assert payload["command"] == "srccount --audit"
    assert payload["data"]["content_only"]
    assert "unused_members" in payload["data"]


# --- content beats names: the classifier stops being the only defence ----------------------
# --audit found two real misses (a venv named agent-sdk-venv holding 1099 .py, and a cargo
# target/ holding 7538) that NO name pattern would catch. Detecting them and leaving them
# counted is half a fix, so the content check now runs during COUNTING, not only in the audit.

def test_a_venv_is_excluded_by_content_whatever_its_name(tmp_path: Path) -> None:
    """The measured case: ~/.claude/security/agent-sdk-venv matches none of venv, venv-*,
    venv_*, .venv* - a name list can never catch it, `pyvenv.cfg` always does."""
    root = tmp_path / "proj"
    plant(root, ["src/app.py", "agent-sdk-venv/lib/dep.py"])
    mark_venv(root / "agent-sdk-venv")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 1
    assert result.by_pattern["content:pyvenv.cfg"] == 1


def test_a_build_cache_is_excluded_by_content(tmp_path: Path) -> None:
    """CACHEDIR.TAG is the published convention cargo and the tool caches write so a tool can
    identify a cache dir by content. Measured here: 264 of them, every one a cache, venv or
    target - not one first-party source dir."""
    root = tmp_path / "proj"
    plant(root, ["src/app.py", "target/doc/gen.py"])
    mark_cache(root / "target")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 1
    assert result.by_pattern["content:CACHEDIR.TAG"] == 1


def test_content_exclusion_reaches_the_whole_subtree(tmp_path: Path) -> None:
    """The marker sits at the top of the tree, so exclusion has to propagate downward."""
    root = tmp_path / "proj"
    plant(root, ["myenv/a/b/c/deep.py", "myenv/lib/x.py", "src/app.py"])
    mark_venv(root / "myenv")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 1
    assert result.by_pattern["content:pyvenv.cfg"] == 2


def test_a_dir_without_the_marker_is_not_excluded(tmp_path: Path) -> None:
    """CONTROL. Without this the content check could just be excluding everything."""
    root = tmp_path / "proj"
    plant(root, ["myenv/lib/dep.py", "src/app.py"])
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 2, "no marker, no exclusion"
    assert result.by_pattern == {}


def test_the_marker_file_itself_does_not_need_a_matching_extension(tmp_path: Path) -> None:
    """pyvenv.cfg and CACHEDIR.TAG are never .py, so the check must look at filenames, not
    at the counted set."""
    root = tmp_path / "proj"
    plant(root, ["myenv/dep.js"])
    mark_venv(root / "myenv")
    assert srccount.count_tree(root, extensions=[".js"]).source == 0


def test_audit_reports_what_only_content_caught(tmp_path: Path) -> None:
    """The audit's job shifts: a content-only exclusion is now a NAME-LIST BLIND SPOT that the
    content check covered, not an uncaught miss."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", "agent-sdk-venv/lib/d.py"])
    mark_venv(root / "agent-sdk-venv")
    report = srccount.audit([root], extensions=[".py"])
    assert any(p.name == "agent-sdk-venv" for p in report.content_only)


def test_audit_content_only_is_empty_when_the_name_list_covers_it(tmp_path: Path) -> None:
    """CONTROL - a venv the NAME list already knows is not a blind spot."""
    root = tmp_path / "proj"
    plant(root, ["src/a.py", ".venv/lib/d.py"])
    mark_venv(root / ".venv")
    report = srccount.audit([root], extensions=[".py"])
    assert report.content_only == []


def test_audit_ranked_list_says_when_it_truncated(tmp_path: Path) -> None:
    """A silent cap in a report whose whole purpose is visibility. Same shape as the
    never-head-cap-an-enumeration rule."""
    root = tmp_path / "proj"
    plant(root, [f"d{i}/f.py" for i in range(20)])
    done = run_cli("--audit", "--root", str(root), "--ext", ".py")
    assert "more" in done.stdout, "a truncated ranking must say it truncated"


def test_top_flag_widens_the_ranking_the_message_points_at(tmp_path: Path) -> None:
    """The truncation note says `rerun with --top N`, so that flag has to exist and work -
    an instruction a reader cannot follow is worse than no instruction."""
    root = tmp_path / "proj"
    plant(root, [f"d{i}/f.py" for i in range(20)])
    capped = run_cli("--audit", "--root", str(root), "--ext", ".py")
    assert "more" in capped.stdout
    widened = run_cli("--audit", "--root", str(root), "--ext", ".py", "--top", "20")
    assert "more" not in widened.stdout, "at --top 20 nothing is withheld"
    assert widened.stdout.count("=1") >= 20


# --- a marker must PROVE it, not just be named that -----------------------------------------
# "proven, not plausible" was doing work the code did not do: only the FILENAME was checked, so
# any directory holding an unrelated file called CACHEDIR.TAG was silently excluded - and since
# content exclusion runs during every count and covers the whole subtree, that removes real
# source from the number invisibly.

def test_a_cachedir_tag_without_the_signature_does_not_exclude(tmp_path: Path) -> None:
    """The spec requires the file to BEGIN with the signature line. Anything else is a file
    that happens to share the name."""
    root = tmp_path / "proj"
    plant(root, ["target/gen.py", "src/app.py"])
    (root / "target" / "CACHEDIR.TAG").write_text("notes to self\n", encoding="utf-8")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 2, "an unsigned CACHEDIR.TAG must not remove real source"


def test_a_valid_cachedir_tag_does_exclude(tmp_path: Path) -> None:
    """CONTROL for the above - the validator must still accept the real thing."""
    root = tmp_path / "proj"
    plant(root, ["target/gen.py", "src/app.py"])
    (root / "target" / "CACHEDIR.TAG").write_text(
        "Signature: 8a477f597d28d172789f06886806bc55\n# written by cargo\n", encoding="utf-8")
    result = srccount.count_tree(root, extensions=[".py"])
    assert result.source == 1
    assert result.by_pattern["content:CACHEDIR.TAG"] == 1


def test_a_pyvenv_cfg_without_the_home_key_does_not_exclude(tmp_path: Path) -> None:
    """PEP 405 defines the file by its `home` key; a stray file of that name is not a venv."""
    root = tmp_path / "proj"
    plant(root, ["myenv/dep.py", "src/app.py"])
    (root / "myenv" / "pyvenv.cfg").write_text("# placeholder\n", encoding="utf-8")
    assert srccount.count_tree(root, extensions=[".py"]).source == 2


def test_a_real_pyvenv_cfg_does_exclude(tmp_path: Path) -> None:
    """CONTROL. Measured: the one file this marker rescues in the whole corpus is a venv's
    bin/Activate.ps1 - venv files OUTSIDE site-packages, which no other rule reaches."""
    root = tmp_path / "proj"
    plant(root, ["myenv/bin/Activate.ps1", "src/app.py"])
    (root / "myenv" / "pyvenv.cfg").write_text(
        "home = /usr/bin\ninclude-system-site-packages = false\n", encoding="utf-8")
    result = srccount.count_tree(root, extensions=[".ps1", ".py"])
    assert result.source == 1
    assert result.by_pattern["content:pyvenv.cfg"] == 1


def test_every_content_marker_has_a_reason_and_a_validator() -> None:
    """Same structural gate the name list got: a marker cannot be added without saying what
    writes it AND how to prove the file is really that, so 'proven' stays true."""
    for name, marker in srccount.CONTENT_MARKERS.items():
        assert len(marker.reason) > 15, f"{name} has no real justification"
        assert callable(marker.validate), f"{name} has no validator"
        assert len(marker.measured) > 10, f"{name} records no measurement of what it catches"


def test_a_directory_named_like_a_marker_is_not_a_marker(tmp_path: Path) -> None:
    """Renamed from a fail-open test it never was: a directory of that name never reaches the
    validator at all (os.walk puts it in dirnames, not filenames), so this pins a different
    real case and the fail-open path is covered by the three tests below."""
    root = tmp_path / "proj"
    plant(root, ["target/gen.py"])
    (root / "target" / "CACHEDIR.TAG").mkdir()
    assert srccount.count_tree(root, extensions=[".py"]).source == 1


# Fail-open is the safety property the whole content mechanism rests on: an unreadable or
# unrecognised marker must leave the directory COUNTED, because a counted file is visible in
# the breakdown while a wrongly excluded one is gone from the number with nothing to notice.
#
# There are TWO paths, not one, and they need separate mutants - the first draft of this
# comment claimed all three tests reached the same branch, and the mutation run disproved it:
#   * the exception arm (`except OSError`) - reached by the unreadable-path and the
#     denied-by-permissions tests; making that arm re-raise kills exactly those two.
#   * the validator returning False on readable-but-wrong content - reached by the
#     unrecognised-marker test plus the two without-the-signature / without-the-home-key
#     tests; making the validators always accept kills exactly those three, and not the
#     other two.

def test_validator_returns_false_on_an_unreadable_path(tmp_path: Path) -> None:
    """Directly exercises the `except OSError` arm - read_bytes/read_text on a directory
    raises IsADirectoryError, an OSError subclass."""
    d = tmp_path / "notafile"
    d.mkdir()
    assert srccount._is_cachedir_tag(d) is False
    assert srccount._is_pyvenv_cfg(d) is False


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="root can read a 000 file, so the permission arm cannot be reached")
def test_a_marker_denied_by_permissions_leaves_the_tree_counted(tmp_path: Path) -> None:
    """The real-world shape: the file exists and is a genuine marker, but cannot be read."""
    root = tmp_path / "proj"
    plant(root, ["target/gen.py", "src/app.py"])
    tag = mark_cache(root / "target")
    tag.chmod(0o000)
    try:
        assert srccount.count_tree(root, extensions=[".py"]).source == 2
    finally:
        tag.chmod(0o644)


def test_an_unrecognised_marker_leaves_the_tree_counted(tmp_path: Path) -> None:
    """Readable but not the real thing - binary junk under a marker filename."""
    root = tmp_path / "proj"
    plant(root, ["target/gen.py", "src/app.py"])
    (root / "target" / "CACHEDIR.TAG").write_bytes(b"\x00\x01\x02not a signature")
    assert srccount.count_tree(root, extensions=[".py"]).source == 2
