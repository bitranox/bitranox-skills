"""Why the UNEXAMINED list must say WHICH KIND of unexamined each entry is.

The baseline answers one question - "has anybody checked this hook?" - and reports every "no" in
one flat list headed UNEXAMINED. Three very different situations answer no, and the flat list
renders them identically:

* the hook was cleared and then EDITED, so the old verdict expired (an edit is usually a
  correction, so the thing to re-read is the edit, not the whole claim);
* the fact was WRITTEN AFTER the level was last swept, so nobody could have checked it - this is
  freshness, not rot;
* the fact predates the sweep and no verdict was ever recorded - the only bucket that is actually
  a backlog of unchecked claims.

Measured 2026-09-03 on the softdev tree: 22 entries reported UNEXAMINED, of which 7 were
re-surfaced edits and 10 were written after the baseline, leaving 4 genuinely unchecked. A
session read the flat 22 as "22 misleading claims", ranked a day of work on it, and a
three-entry sample found nothing stale. The list was accurate and its SHAPE was the lie.

The properties below are the ones that stop the new report lying in turn. The direction of
failure matters most: an entry whose age cannot be established must fall back to NEVER-CHECKED,
because keeping a checked entry on the worklist costs a re-read, while filing an unchecked one
as "just written" hides it for good.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import statusrot  # noqa: E402

TOOL = Path(statusrot.__file__).resolve()

OLD = "- [T](mem:oldfact) - When you need X, know it is DEPLOYED to the host and shipped."
OLD_EDITED = "- [T](mem:oldfact) - When you need X, know it is NOT STARTED and still open."
FRESH = "- [T2](mem:freshfact) - When you need Y, know it was shipped in the last release."
STALE_UNCHECKED = "- [T3](mem:unchecked) - When you need Z, know the migration is DEPLOYED."


def _git(root: Path, *args: str, when: str | None = None) -> None:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@e",
           "PATH": "/usr/bin:/bin", "HOME": str(root)}
    if when:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(["git", "-C", str(root), *args], check=True,
                   capture_output=True, text=True, env=env)


def _store(tmp_path: Path) -> Path:
    """A tree whose .claude-memory store is a git repo, so fact ages are answerable."""
    store = tmp_path / ".claude-memory"
    (store / "facts").mkdir(parents=True)
    _git(store, "init", "-q", "-b", "main")
    return tmp_path


def _index(root: Path, *lines: str) -> None:
    root.joinpath("CLAUDE.local.md").write_text(
        "# Memory index\n\n## Memory index\n" + "\n".join(lines) + "\n", encoding="utf-8")


def _add_fact(root: Path, slug: str, when: str) -> None:
    body = root / ".claude-memory" / "facts" / f"{slug}.md"
    body.write_text(f"---\nname: {slug}\n---\n\nbody\n", encoding="utf-8")
    _git(root / ".claude-memory", "add", f"facts/{slug}.md", when=when)
    _git(root / ".claude-memory", "commit", "-q", "-m", f"add {slug}", when=when)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _scan(root: Path) -> dict:
    out = _run("scan", "--chain", str(root), "--json")
    assert out.returncode in (0, 1), out.stderr
    return json.loads(out.stdout)["data"]


def _triage(root: Path) -> dict:
    data = _scan(root)
    assert "pending_triage" in data, \
        "the UNEXAMINED list must be triaged, not reported flat"
    return data["pending_triage"]


class TestTheThreeKindsAreDistinguished:
    def test_an_edited_cleared_hook_reads_as_RESURFACED(self, tmp_path: Path):
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _index(root, OLD_EDITED)
        t = _triage(root)
        assert t["resurfaced"] == ["oldfact"], t
        assert "oldfact" not in t["never_checked"], \
            "a hook somebody cleared is not an unchecked claim; only its edit is unread"

    def test_a_fact_written_after_the_sweep_reads_as_WRITTEN_SINCE(self, tmp_path: Path):
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _add_fact(root, "freshfact", "2036-01-01T00:00:00")
        _index(root, OLD, FRESH)
        t = _triage(root)
        assert t["written_since"] == ["freshfact"], t
        assert t["never_checked"] == [], \
            "nobody could have checked a fact that did not exist at sweep time"

    def test_a_fact_predating_the_sweep_and_never_cleared_reads_as_NEVER_CHECKED(
            self, tmp_path: Path):
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _add_fact(root, "unchecked", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _index(root, OLD, STALE_UNCHECKED)
        t = _triage(root)
        assert t["never_checked"] == ["unchecked"], t
        assert t["written_since"] == [], t


class TestItFailsTowardMoreWorkNotLess:
    def test_an_unknowable_age_falls_back_to_NEVER_CHECKED(self, tmp_path: Path):
        """No fact body committed, so git can answer nothing. The safe read is 'still to check'."""
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _index(root, OLD, FRESH)          # freshfact has NO committed body
        t = _triage(root)
        assert t["never_checked"] == ["freshfact"], t
        assert t["written_since"] == [], \
            "an unanswerable age must never be filed as freshness - that hides it for good"

    def test_a_store_that_is_not_a_git_repo_still_reports_every_pending_entry(
            self, tmp_path: Path):
        (tmp_path / ".claude-memory" / "facts").mkdir(parents=True)
        _index(tmp_path, OLD, FRESH)
        t = _triage(tmp_path)
        assert sorted(t["never_checked"]) == ["freshfact", "oldfact"], t


class TestTheBucketsCannotLoseAnEntry:
    def test_the_three_buckets_partition_the_pending_list_exactly(self, tmp_path: Path):
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _add_fact(root, "unchecked", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _add_fact(root, "freshfact", "2036-01-01T00:00:00")
        _index(root, OLD_EDITED, FRESH, STALE_UNCHECKED)
        data = _scan(root)
        t = data["pending_triage"]
        got = t["resurfaced"] + t["written_since"] + t["never_checked"]
        assert sorted(got) == sorted(data["new_or_changed"]), \
            f"buckets must cover the pending list exactly: {got!r} vs {data['new_or_changed']!r}"
        assert len(got) == len(set(got)), "an entry may not appear in two buckets"


class TestKnownNegative:
    def test_the_triage_can_actually_return_different_buckets(self, tmp_path: Path):
        """A control: prove it discriminates rather than always answering never_checked."""
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _add_fact(root, "freshfact", "2036-01-01T00:00:00")
        _index(root, OLD_EDITED, FRESH)
        t = _triage(root)
        assert t["resurfaced"] == ["oldfact"] and t["written_since"] == ["freshfact"], \
            f"one input must produce two different buckets, got {t!r}"


class TestTheRenderedReportSaysWhichKind:
    def _three_bucket_tree(self, tmp_path: Path) -> Path:
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _add_fact(root, "unchecked", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _add_fact(root, "freshfact", "2036-01-01T00:00:00")
        _index(root, OLD_EDITED, FRESH, STALE_UNCHECKED)
        return root

    def test_the_text_report_names_the_buckets_and_their_counts(self, tmp_path: Path):
        out = _run("scan", "--chain", str(self._three_bucket_tree(tmp_path)))
        assert out.returncode in (0, 1), out.stderr
        text = out.stdout
        assert "RE-SURFACED" in text and "WRITTEN SINCE" in text and "NEVER CHECKED" in text, text
        assert "UNEXAMINED since the baseline: 3" in text, text

    def test_an_empty_bucket_is_not_printed(self, tmp_path: Path):
        """The report must not pad itself with headings for kinds that have no entries: a dream
        pass exists to shrink noise, and a standing 'NEVER CHECKED: 0' trains the reader to skim
        the one heading that matters most."""
        root = _store(tmp_path)
        _add_fact(root, "oldfact", "2026-01-01T00:00:00")
        _index(root, OLD)
        _run("clear", "--chain", str(root), "--note", "checked")
        _index(root, OLD_EDITED)
        text = _run("scan", "--chain", str(root)).stdout
        assert "RE-SURFACED" in text, text
        assert "WRITTEN SINCE" not in text and "NEVER CHECKED" not in text, text
