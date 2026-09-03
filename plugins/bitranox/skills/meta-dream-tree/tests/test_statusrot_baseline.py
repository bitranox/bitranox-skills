"""The verified-baseline: it may only ever say "already cleared" about text it has actually seen.

The scanner reports CANDIDATES, and on a mature chain almost all of them are entries somebody
already checked against their owner and found sound. Re-reporting those every run is what makes
the output unreadable, so the baseline records which hooks were cleared and when.

The whole feature is one dangerous claim - "you already looked at this" - so the properties that
matter are the ones that stop it lying:

* a hook EDITED after being cleared must come back, or the baseline becomes a way to hide new rot
  behind an old verdict (it is keyed on a hash of the hook text for exactly this reason);
* an entry never cleared must read as NEW, and a MISSING baseline must make everything new -
  "no record" must never render as "all clear";
* clearing must be explicit, so nothing enters the baseline as a side effect of scanning.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import statusrot  # noqa: E402

TOOL = Path(statusrot.__file__).resolve()

SHIPPED = "- [T](mem:alpha) - When you need X, know it is DEPLOYED to the host and shipped."
SHIPPED_EDITED = "- [T](mem:alpha) - When you need X, know it is NOT STARTED and still open."
OTHER = "- [T2](mem:beta) - When you need Y, know it was shipped in the last release."
CLEAN = "- [T3](mem:gamma) - When you parse a chain, walk up from the narrowest level."


def _tree(tmp_path: Path, *lines: str) -> Path:
    """A directory carrying a CLAUDE.local.md and a .claude-memory store beside it."""
    (tmp_path / ".claude-memory" / "facts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "CLAUDE.local.md").write_text(
        "# Memory index\n\n## Memory index\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def _scan_json(root: Path) -> dict:
    out = _run("scan", "--chain", str(root), "--json")
    assert out.returncode in (0, 1), out.stderr
    return json.loads(out.stdout)["data"]


class TestStoreDiscovery:
    def test_finds_the_store_by_walking_up(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED)
        deep = root / "a" / "b"
        deep.mkdir(parents=True)
        assert statusrot.baseline_path(deep) == root / ".claude-memory" / "statusrot-baseline.json"

    def test_returns_none_when_no_store_exists(self, tmp_path: Path):
        (tmp_path / "CLAUDE.local.md").write_text("# x\n", encoding="utf-8")
        assert statusrot.baseline_path(tmp_path) is None


class TestClearIsExplicit:
    def test_scanning_alone_never_writes_a_baseline(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED)
        _scan_json(root)
        assert not (root / ".claude-memory" / "statusrot-baseline.json").exists(), \
            "scan must not enter anything into the baseline as a side effect"

    def test_clear_records_the_flagged_entries(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED, OTHER, CLEAN)
        assert _run("clear", "--chain", str(root), "--note", "checked").returncode == 0
        rec = json.loads((root / ".claude-memory" / "statusrot-baseline.json").read_text())
        assert set(rec["cleared"]) == {"alpha", "beta"}, "only flagged entries are recorded"
        assert rec["cleared"]["alpha"]["note"] == "checked"
        assert rec["cleared"]["alpha"]["hook_sha256"]


class TestBaselineCannotHideRot:
    def test_an_unchanged_cleared_hook_is_not_reported_as_new(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED, OTHER)
        _run("clear", "--chain", str(root))
        data = _scan_json(root)
        assert data["distinct_flagged"] == 2, "still a candidate, just not an unexamined one"
        assert data["new_or_changed"] == []

    def test_an_EDITED_cleared_hook_comes_back(self, tmp_path: Path):
        """The property the whole feature rests on."""
        root = _tree(tmp_path, SHIPPED, OTHER)
        _run("clear", "--chain", str(root))
        (root / "CLAUDE.local.md").write_text(
            "# Memory index\n\n## Memory index\n" + "\n".join([SHIPPED_EDITED, OTHER]) + "\n",
            encoding="utf-8")
        data = _scan_json(root)
        assert "alpha" in data["new_or_changed"], "an edited hook must NOT stay cleared"
        assert "beta" not in data["new_or_changed"], "its untouched neighbour stays cleared"

    def test_an_entry_never_cleared_is_new(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED)
        _run("clear", "--chain", str(root))
        (root / "CLAUDE.local.md").write_text(
            "# Memory index\n\n## Memory index\n" + "\n".join([SHIPPED, OTHER]) + "\n",
            encoding="utf-8")
        assert _scan_json(root)["new_or_changed"] == ["beta"]

    def test_a_missing_baseline_makes_everything_new(self, tmp_path: Path):
        """No record must never render as all-clear."""
        root = _tree(tmp_path, SHIPPED, OTHER)
        data = _scan_json(root)
        assert sorted(data["new_or_changed"]) == ["alpha", "beta"]
        assert data["baseline"] is None

    def test_a_cleared_entry_that_stops_being_flagged_just_disappears(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED)
        _run("clear", "--chain", str(root))
        (root / "CLAUDE.local.md").write_text(
            "# Memory index\n\n## Memory index\n" + CLEAN + "\n", encoding="utf-8")
        data = _scan_json(root)
        assert data["distinct_flagged"] == 0
        assert data["new_or_changed"] == []


class TestKnownNegative:
    def test_the_changed_detector_can_actually_fire(self, tmp_path: Path):
        """A control: prove the comparison distinguishes, rather than always saying cleared."""
        root = _tree(tmp_path, SHIPPED)
        _run("clear", "--chain", str(root))
        unchanged = _scan_json(root)["new_or_changed"]
        (root / "CLAUDE.local.md").write_text(
            "# Memory index\n\n## Memory index\n" + SHIPPED_EDITED + "\n", encoding="utf-8")
        changed = _scan_json(root)["new_or_changed"]
        assert unchanged == [] and changed == ["alpha"], \
            f"detector must say different things: {unchanged!r} vs {changed!r}"


class TestAPartialAdjudicationIsRecordable:
    """A scan reports N candidates and a human adjudicates a SUBSET of them - the normal case once
    a chain is mature. Without a per-slug selector the only two moves are a bulk clear that falsely
    certifies the candidates nobody read, or leaving the baseline untouched and re-doing the work
    next time; the tool's own guidance (never bulk-clear) forces the second.
    """

    def test_clearing_one_slug_leaves_the_others_flagged(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED, OTHER)
        out = _run("clear", "--chain", str(root), "--slug", "alpha", "--json",
                   "--note", "checked against TODO.md")
        assert out.returncode == 0, out.stderr
        assert json.loads(out.stdout)["data"]["recorded"] == 1
        cleared = json.loads((root / ".claude-memory" / "statusrot-baseline.json")
                             .read_text(encoding="utf-8"))["cleared"]
        assert set(cleared) == {"alpha"}
        assert _scan_json(root)["new_or_changed"] == ["beta"]

    def test_the_selector_is_repeatable(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED, OTHER)
        out = _run("clear", "--chain", str(root), "--slug", "alpha", "--slug", "beta", "--json")
        assert out.returncode == 0, out.stderr
        assert json.loads(out.stdout)["data"]["recorded"] == 2
        assert _scan_json(root)["new_or_changed"] == []

    def test_a_slug_that_is_not_a_candidate_is_refused_and_nothing_is_written(self, tmp_path: Path):
        # A name that records nothing is the failure this selector exists to avoid: it exits 0,
        # reports a clean sweep, and certifies neither the typo nor the entry it was aimed at.
        root = _tree(tmp_path, SHIPPED, OTHER, CLEAN)
        out = _run("clear", "--chain", str(root), "--slug", "alpha", "--slug", "aplha", "--json")
        assert out.returncode == 2
        payload = json.loads(out.stdout)
        assert payload["ok"] is False and "aplha" in payload["error"]
        assert not (root / ".claude-memory" / "statusrot-baseline.json").exists()

    def test_an_unflagged_slug_is_refused_too_not_silently_recorded(self, tmp_path: Path):
        # `gamma` is a real pointer that the scan did NOT flag. Recording it would put a verdict in
        # the baseline for a claim nobody was asked about.
        root = _tree(tmp_path, SHIPPED, CLEAN)
        out = _run("clear", "--chain", str(root), "--slug", "gamma", "--json")
        assert out.returncode == 2
        assert "gamma" in json.loads(out.stdout)["error"]

    def test_no_selector_still_clears_every_flagged_entry(self, tmp_path: Path):
        root = _tree(tmp_path, SHIPPED, OTHER)
        out = _run("clear", "--chain", str(root), "--json")
        assert out.returncode == 0
        assert json.loads(out.stdout)["data"]["recorded"] == 2
