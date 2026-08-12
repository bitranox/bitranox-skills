"""Tests for claudemd_variance.py - measure duplicated '## ' sections across CLAUDE.md files.

The tool's whole reason to exist is enumerating by a filesystem WALK rather than the session's
gitignore-aware `grep`, which silently drops ignored files. The tests in
`TestGitignoredFilesAreFound` are the ones that prove that claim rather than assert it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import claudemd_variance as CV

CLI = str(Path(__file__).resolve().parent.parent / "scripts" / "claudemd_variance.py")
CLI_TIMEOUT = 60

GIT = "git"


def run_cli(*args, cwd=None):
    """Spawn the CLI the way a caller would: sys.executable (never a bare python3, which does
    not resolve on every platform), an explicit encoding (without one, capture decodes with the
    machine's locale codec and fails differently per platform), and a timeout."""
    return subprocess.run(
        [sys.executable, CLI, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CLI_TIMEOUT,
        cwd=cwd,
        check=False,
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


SECTION_A = "## Common Make Targets\n\nRun `make help` for the current list.\n"
SECTION_A_TRAILING_WS = "## Common Make Targets   \n   \nRun `make help` for the current list.   \n"
SECTION_A_EXTRA_BLANKS = "## Common Make Targets\n\n\n\nRun `make help` for the current list.\n"
SECTION_A_DIFFERENT = "## Common Make Targets\n\nRun `make list` for the current list.\n"
SECTION_A_INDENTED = "## Common Make Targets\n\n  Run `make help` for the current list.\n"


# --------------------------------------------------------------------------------------------
# split_sections
# --------------------------------------------------------------------------------------------


class TestSplitSections:
    def test_splits_two_level2_headings(self):
        text = "# Title\n\n## First\nbody one\n\n## Second\nbody two\n"
        sections = CV.split_sections(text)
        assert [h for h, _, _ in sections] == ["First", "Second"]
        assert sections[0][1] == "body one\n"
        assert sections[1][1] == "body two\n"

    def test_text_before_first_heading_is_dropped(self):
        text = "---\nname: x\n---\n\n# Title\n\npreamble\n\n## Only\nbody\n"
        sections = CV.split_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "Only"

    def test_level3_heading_stays_inside_its_parent_section(self):
        text = "## Parent\n\n### Child\nchild body\n\n## Next\nnext body\n"
        sections = CV.split_sections(text)
        assert [h for h, _, _ in sections] == ["Parent", "Next"]
        assert "### Child" in sections[0][1]
        assert "child body" in sections[0][1]

    def test_indented_hash_hash_is_not_a_heading(self):
        text = "## Real\n\n    ## not a heading, inside a code block\nmore body\n"
        sections = CV.split_sections(text)
        assert len(sections) == 1
        assert sections[0][0] == "Real"
        assert "## not a heading" in sections[0][1]

    def test_trailing_hashes_on_the_heading_line_are_stripped(self):
        text = "## Closed Heading ##\nbody\n"
        sections = CV.split_sections(text)
        assert sections[0][0] == "Closed Heading"

    def test_no_level2_heading_yields_nothing(self):
        assert CV.split_sections("# Title\n\njust a paragraph\n") == []

    def test_start_line_is_1_indexed_and_points_at_the_heading(self):
        text = "line1\nline2\n## Heading\nbody\n"
        sections = CV.split_sections(text)
        assert sections[0][2] == 3


# --------------------------------------------------------------------------------------------
# normalize_body / section_hash - the whitespace-normalisation definition
# --------------------------------------------------------------------------------------------


class TestWhitespaceNormalisation:
    def test_trailing_whitespace_does_not_change_the_hash(self):
        a = CV.split_sections(SECTION_A)[0][1]
        b = CV.split_sections(SECTION_A_TRAILING_WS)[0][1]
        assert a != b  # the raw bodies really do differ
        assert CV.section_hash(a) == CV.section_hash(b)

    def test_blank_line_run_length_does_not_change_the_hash(self):
        a = CV.split_sections(SECTION_A)[0][1]
        b = CV.split_sections(SECTION_A_EXTRA_BLANKS)[0][1]
        assert a != b
        assert CV.section_hash(a) == CV.section_hash(b)

    def test_crlf_vs_lf_does_not_change_the_hash(self):
        a = CV.split_sections(SECTION_A)[0][1]
        b = CV.split_sections(SECTION_A.replace("\n", "\r\n"))[0][1]
        assert CV.section_hash(a) == CV.section_hash(b)

    def test_real_content_difference_changes_the_hash(self):
        a = CV.split_sections(SECTION_A)[0][1]
        b = CV.split_sections(SECTION_A_DIFFERENT)[0][1]
        assert CV.section_hash(a) != CV.section_hash(b)

    def test_indentation_is_not_normalised_and_changes_the_hash(self):
        """Leading indentation is defined as CONTENT, not formatting noise - a nested list or a
        code fence changes meaning when its indentation changes, so this must NOT collapse."""
        a = CV.split_sections(SECTION_A)[0][1]
        b = CV.split_sections(SECTION_A_INDENTED)[0][1]
        assert CV.section_hash(a) != CV.section_hash(b)

    def test_leading_and_trailing_blank_lines_are_trimmed(self):
        assert CV.normalize_body("\n\n\nbody\n\n\n") == "body"

    def test_normalize_body_is_idempotent(self):
        once = CV.normalize_body(SECTION_A_TRAILING_WS)
        twice = CV.normalize_body(once)
        assert once == twice


# --------------------------------------------------------------------------------------------
# common_ancestor
# --------------------------------------------------------------------------------------------


class TestCommonAncestor:
    def test_single_member_ancestor_is_its_own_parent_directory(self, tmp_path):
        f = write(tmp_path / "a" / "b" / "CLAUDE.md", "x")
        assert CV.common_ancestor([f]) == (tmp_path / "a" / "b").resolve()

    def test_single_member_ancestor_is_not_the_filesystem_root(self, tmp_path):
        f = write(tmp_path / "deep" / "CLAUDE.md", "x")
        ancestor = CV.common_ancestor([f])
        assert ancestor != Path(ancestor.anchor)

    def test_two_members_under_a_shared_parent(self, tmp_path):
        f1 = write(tmp_path / "shared" / "CLAUDE.md", "x")
        f2 = write(tmp_path / "shared" / "sub" / "CLAUDE.md", "x")
        # f2's own ancestor test: common_ancestor works on FILE paths, one per member
        assert CV.common_ancestor([f1, f2]) == (tmp_path / "shared").resolve()

    def test_members_on_different_branches_find_the_true_shared_directory(self, tmp_path):
        f1 = write(tmp_path / "root" / "left" / "CLAUDE.md", "x")
        f2 = write(tmp_path / "root" / "right" / "deep" / "CLAUDE.md", "x")
        f3 = write(tmp_path / "root" / "CLAUDE.md", "x")
        assert CV.common_ancestor([f1, f2, f3]) == (tmp_path / "root").resolve()

    def test_never_silently_returns_the_walk_root_when_a_deeper_directory_would_do(self, tmp_path):
        """Regression guard for the exact bug the brief warns about: an implementation that
        computes the ancestor from the WALK root rather than from the actual members would pass
        every other test here and still be wrong. Members share a directory two levels below
        tmp_path; the answer must be THAT directory, not tmp_path."""
        f1 = write(tmp_path / "x" / "y" / "a" / "CLAUDE.md", "1")
        f2 = write(tmp_path / "x" / "y" / "b" / "CLAUDE.md", "2")
        ancestor = CV.common_ancestor([f1, f2])
        assert ancestor == (tmp_path / "x" / "y").resolve()
        assert ancestor != tmp_path.resolve()

    def test_no_common_directory_raises_instead_of_returning_root(self, tmp_path):
        """Exercises the defensive branch deterministically (a real cross-drive path pair cannot
        be constructed on this OS) by injecting a stub that reports what os.path.commonpath
        itself reports for genuinely disjoint roots."""

        def boom(_parts):
            raise ValueError("no common path")

        f1 = write(tmp_path / "a" / "CLAUDE.md", "1")
        f2 = write(tmp_path / "b" / "CLAUDE.md", "2")
        with pytest.raises(ValueError, match="no common ancestor"):
            CV.common_ancestor([f1, f2], _commonpath=boom)

    def test_empty_input_raises(self):
        with pytest.raises(ValueError):
            CV.common_ancestor([])


# --------------------------------------------------------------------------------------------
# iter_claude_md - the walk, and the gitignore claim
# --------------------------------------------------------------------------------------------


def make_git_repo(root: Path) -> None:
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(root / "gitconfig"),
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    subprocess.run([GIT, "init", "-q"], cwd=root, env=env, check=True, timeout=30)
    subprocess.run(
        [GIT, "config", "user.email", "t@example.com"], cwd=root, env=env, check=True, timeout=30
    )
    subprocess.run([GIT, "config", "user.name", "t"], cwd=root, env=env, check=True, timeout=30)


needs_git = pytest.mark.skipif(
    subprocess.run([GIT, "--version"], capture_output=True).returncode != 0,
    reason="git is not installed",
)


class TestWalkEnumeration:
    def test_finds_files_at_multiple_depths(self, tmp_path):
        f1 = write(tmp_path / "CLAUDE.md", "## A\nbody\n")
        f2 = write(tmp_path / "sub" / "deep" / "CLAUDE.md", "## A\nbody\n")
        found = set(CV.iter_claude_md(tmp_path))
        assert found == {f1, f2}

    def test_does_not_descend_into_dot_git(self, tmp_path):
        write(tmp_path / ".git" / "CLAUDE.md", "should not be found")
        real = write(tmp_path / "CLAUDE.md", "## A\nbody\n")
        assert set(CV.iter_claude_md(tmp_path)) == {real}

    def test_custom_filenames_are_respected(self, tmp_path):
        write(tmp_path / "CLAUDE.md", "x")
        local = write(tmp_path / "CLAUDE.local.md", "x")
        found = set(CV.iter_claude_md(tmp_path, filenames=("CLAUDE.local.md",)))
        assert found == {local}

    def test_does_not_follow_a_symlinked_directory_loop(self, tmp_path):
        if not hasattr(os, "symlink"):
            pytest.skip("platform cannot create symlinks")
        real = write(tmp_path / "real" / "CLAUDE.md", "## A\nbody\n")
        loop = tmp_path / "real" / "loop"
        try:
            loop.symlink_to(tmp_path / "real", target_is_directory=True)
        except OSError:
            pytest.skip("cannot create a symlink here")
        # Must terminate at all (a loop would hang os.walk with followlinks=True) and must not
        # silently multiply the real file's discovery.
        found = list(CV.iter_claude_md(tmp_path))
        assert found == [real]

    def test_max_files_bound_stops_and_warns(self, tmp_path):
        for i in range(5):
            write(tmp_path / f"d{i}" / "CLAUDE.md", "x")
        warnings = []
        found = list(CV.iter_claude_md(tmp_path, max_files=2, warn=warnings.append))
        assert len(found) == 2
        assert any("stopped walk" in w for w in warnings)

    def test_never_calls_a_subprocess(self, tmp_path, monkeypatch):
        """The enumeration must not shell out to grep OR to git - it is a plain filesystem walk.
        Any subprocess call at all is a design regression back toward the grep-based tool this
        exists to replace."""
        write(tmp_path / "CLAUDE.md", "## A\nbody\n")

        def forbidden(*_args, **_kwargs):
            raise AssertionError("iter_claude_md must never spawn a subprocess")

        monkeypatch.setattr(subprocess, "run", forbidden)
        monkeypatch.setattr(subprocess, "Popen", forbidden)
        found = list(CV.iter_claude_md(tmp_path))
        assert len(found) == 1

    @needs_git
    def test_a_gitignored_claude_md_is_still_found(self, tmp_path):
        """The tool's whole reason to exist. A grep-based enumeration built on a
        gitignore-aware backend drops this file silently; the walk must not."""
        make_git_repo(tmp_path)
        write(tmp_path / ".gitignore", "ignored/\n")
        ignored_file = write(tmp_path / "ignored" / "CLAUDE.md", "## Secret\nbody\n")

        # Control: prove the fixture is REALLY gitignored, not just placed in a folder that
        # happens to share a name.
        check = subprocess.run(
            [GIT, "check-ignore", "-q", "ignored/CLAUDE.md"],
            cwd=tmp_path,
            capture_output=True,
            timeout=30,
        )
        assert check.returncode == 0, "fixture setup is broken: git does not consider this ignored"

        found = set(CV.iter_claude_md(tmp_path))
        assert ignored_file in found

    @needs_git
    def test_a_git_grep_based_enumeration_would_have_missed_it(self, tmp_path):
        """Demonstrates the failure mode directly rather than only asserting the walk avoids it.
        `git grep` (gitignore-and-tracking aware, like the session's own grep tool) searches
        tracked content only - so on this exact fixture it finds nothing, while the walk finds
        the file. That contrast is the tool's headline claim."""
        make_git_repo(tmp_path)
        write(tmp_path / ".gitignore", "ignored/\n")
        write(tmp_path / "ignored" / "CLAUDE.md", "## Secret\nunique-marker-token\n")

        grep = subprocess.run(
            [GIT, "grep", "-l", "unique-marker-token"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert grep.returncode != 0  # git grep: no match, because the file is untracked+ignored
        assert "CLAUDE.md" not in (grep.stdout or "")

        found = list(CV.iter_claude_md(tmp_path))
        assert any("ignored" in p.parts for p in found)


# --------------------------------------------------------------------------------------------
# read_claude_md - decode-error handling
# --------------------------------------------------------------------------------------------


class TestReadClaudeMd:
    def test_valid_utf8_is_returned(self, tmp_path):
        f = write(tmp_path / "CLAUDE.md", "## A\nbody with an umlaut: ü\n")
        warnings = []
        assert CV.read_claude_md(f, warn=warnings.append) is not None
        assert warnings == []

    def test_invalid_utf8_is_skipped_not_raised(self, tmp_path):
        f = tmp_path / "CLAUDE.md"
        f.write_bytes(b"## Heading\n\xff\xfe not valid utf-8\n")
        warnings = []
        result = CV.read_claude_md(f, warn=warnings.append)
        assert result is None
        assert any("cannot decode" in w for w in warnings)

    def test_unreadable_path_is_skipped_not_raised(self, tmp_path):
        missing = tmp_path / "does-not-exist" / "CLAUDE.md"
        warnings = []
        assert CV.read_claude_md(missing, warn=warnings.append) is None
        assert any("cannot read" in w for w in warnings)


# --------------------------------------------------------------------------------------------
# analyze / grouping - largest-variant share, common ancestor wiring, min-members
# --------------------------------------------------------------------------------------------


class TestAnalyze:
    def test_three_identical_copies_form_one_variant_covering_100_percent(self, tmp_path):
        for name in ("a", "b", "c"):
            write(tmp_path / name / "CLAUDE.md", SECTION_A)
        report = CV.analyze([tmp_path])
        assert report.files_matched == 3
        groups = {g.heading: g for g in report.heading_groups}
        group = groups["Common Make Targets"]
        assert group.total_members == 3
        assert len(group.variants) == 1
        assert group.largest_variant_share == 1.0
        assert group.variants[0].lift_candidate is True  # 3 members, default threshold 3

    def test_dominant_plus_one_off_variant_reports_a_partial_share(self, tmp_path):
        for name in ("a", "b", "c"):
            write(tmp_path / name / "CLAUDE.md", SECTION_A)
        write(tmp_path / "d" / "CLAUDE.md", SECTION_A_DIFFERENT)
        report = CV.analyze([tmp_path])
        group = next(g for g in report.heading_groups if g.heading == "Common Make Targets")
        assert group.total_members == 4
        assert len(group.variants) == 2
        assert group.largest_variant_share == pytest.approx(0.75)
        sizes = sorted(v.size for v in group.variants)
        assert sizes == [1, 3]

    def test_common_ancestor_is_computed_per_variant(self, tmp_path):
        write(tmp_path / "left" / "a" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "left" / "b" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "right" / "CLAUDE.md", SECTION_A_DIFFERENT)
        report = CV.analyze([tmp_path])
        group = next(g for g in report.heading_groups if g.heading == "Common Make Targets")
        big = max(group.variants, key=lambda v: v.size)
        assert big.common_ancestor == (tmp_path / "left").resolve()

    def test_min_members_hides_single_copy_headings_by_default(self, tmp_path):
        write(tmp_path / "only" / "CLAUDE.md", "## Unique To One File\nbody\n")
        report = CV.analyze([tmp_path])
        assert report.heading_groups == ()

    def test_min_members_1_reveals_single_copy_headings_with_a_real_ancestor(self, tmp_path):
        write(tmp_path / "only" / "sub" / "CLAUDE.md", "## Unique To One File\nbody\n")
        report = CV.analyze([tmp_path], min_members=1)
        assert len(report.heading_groups) == 1
        group = report.heading_groups[0]
        assert group.total_members == 1
        variant = group.variants[0]
        assert variant.common_ancestor == (tmp_path / "only" / "sub").resolve()
        assert variant.common_ancestor.anchor != str(variant.common_ancestor)  # not the fs root

    def test_lift_threshold_is_configurable(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "b" / "CLAUDE.md", SECTION_A)
        report = CV.analyze([tmp_path], min_members=1, lift_threshold=2)
        group = report.heading_groups[0]
        assert group.variants[0].lift_candidate is True
        report_default = CV.analyze([tmp_path], min_members=1)
        assert report_default.heading_groups[0].variants[0].lift_candidate is False

    def test_overlapping_roots_do_not_double_count_a_file(self, tmp_path):
        write(tmp_path / "sub" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "other" / "CLAUDE.md", SECTION_A)
        report = CV.analyze([tmp_path, tmp_path / "sub"], min_members=1)
        assert report.files_matched == 2
        group = report.heading_groups[0]
        assert group.total_members == 2

    def test_a_file_with_no_level2_heading_contributes_nothing(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", "# Title only\n\nno sections here\n")
        report = CV.analyze([tmp_path])
        assert report.files_matched == 1
        assert report.section_count == 0

    def test_one_decode_failure_does_not_stop_the_others(self, tmp_path):
        write(tmp_path / "good" / "CLAUDE.md", SECTION_A)
        (tmp_path / "bad").mkdir()
        (tmp_path / "bad" / "CLAUDE.md").write_bytes(b"## X\n\xff\xfe bad bytes\n")
        warnings = []
        report = CV.analyze([tmp_path], min_members=1, warn=warnings.append)
        assert report.files_matched == 2
        assert report.files_read == 1
        assert report.files_skipped == 1
        assert any("cannot decode" in w for w in warnings)

    def test_report_as_dict_round_trips_to_json(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "b" / "CLAUDE.md", SECTION_A)
        report = CV.analyze([tmp_path])
        json.dumps(report.as_dict())  # must not raise


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


class TestCli:
    def test_json_envelope_shape(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "b" / "CLAUDE.md", SECTION_A)
        proc = run_cli("--root", str(tmp_path), "--json")
        assert proc.returncode == 0
        payload = json.loads(proc.stdout)
        assert set(payload) == {"ok", "command", "skipped", "data"}
        assert payload["ok"] is True
        assert payload["command"] == "claudemd_variance"
        assert payload["data"]["heading_groups"][0]["heading"] == "Common Make Targets"

    def test_exit_2_when_root_does_not_exist(self, tmp_path):
        proc = run_cli("--root", str(tmp_path / "nope"))
        assert proc.returncode == 2
        assert "does not exist" in proc.stderr

    def test_exit_1_when_root_has_no_matching_files(self, tmp_path):
        proc = run_cli("--root", str(tmp_path))
        assert proc.returncode == 1

    def test_exit_0_with_files_but_no_duplicates(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", "## Solo\nbody\n")
        proc = run_cli("--root", str(tmp_path))
        assert proc.returncode == 0

    def test_warnings_go_to_stderr_not_stdout_in_json_mode(self, tmp_path):
        write(tmp_path / "good" / "CLAUDE.md", SECTION_A)
        (tmp_path / "bad").mkdir()
        (tmp_path / "bad" / "CLAUDE.md").write_bytes(b"## X\n\xff\xfe bad\n")
        proc = run_cli("--root", str(tmp_path), "--json", "--min-members", "1")
        payload = json.loads(proc.stdout)  # must parse cleanly - no warning text mixed in
        assert any("cannot decode" in w for w in payload["skipped"])
        assert "cannot decode" in proc.stderr

    def test_help_documents_the_whitespace_normalisation_definition(self):
        proc = run_cli("--help")
        assert proc.returncode == 0
        text = proc.stdout.lower()
        assert "trailing whitespace" in text
        assert "blank line" in text or "blank-line" in text or "blank lines" in text
        assert "indentation" in text
        assert "not normalised" in text or "not touched" in text

    def test_help_documents_the_common_ancestor_definition(self):
        proc = run_cli("--help")
        text = proc.stdout.lower()
        assert "common ancestor" in text
        assert "parent directory" in text

    def test_default_root_is_the_current_directory(self, tmp_path):
        write(tmp_path / "CLAUDE.md", "## Solo\nbody\n")
        proc = run_cli(cwd=tmp_path)
        assert proc.returncode == 0

    def test_multiple_root_flags_are_all_walked(self, tmp_path):
        write(tmp_path / "one" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "two" / "CLAUDE.md", SECTION_A)
        proc = run_cli("--root", str(tmp_path / "one"), "--root", str(tmp_path / "two"), "--json")
        payload = json.loads(proc.stdout)
        assert payload["data"]["files_matched"] == 2

    def test_custom_filename_flag(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.local.md", SECTION_A)
        write(tmp_path / "b" / "CLAUDE.local.md", SECTION_A)
        proc = run_cli("--root", str(tmp_path), "--filename", "CLAUDE.local.md", "--json")
        payload = json.loads(proc.stdout)
        assert payload["data"]["files_matched"] == 2

    def test_paths_render_posix_style_in_json(self, tmp_path):
        write(tmp_path / "a" / "CLAUDE.md", SECTION_A)
        write(tmp_path / "b" / "CLAUDE.md", SECTION_A)
        proc = run_cli("--root", str(tmp_path), "--json")
        payload = json.loads(proc.stdout)
        member = payload["data"]["heading_groups"][0]["variants"][0]["members"][0]
        assert "\\" not in member
