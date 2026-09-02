"""The status-rot scanner: it must find BOTH polarities, and it must be able to say "clean".

The tool exists because a memory pointer line is always-loaded while the thing it asserts is
owned elsewhere, so a ship-state claim rots silently. Two properties matter most:

* it must not be blind to one polarity - the first hand-rolled version looked only for TODO-ish
  words and so missed 33 of the 37 status claims on the chain it was pointed at;
* it must be able to report NOTHING, or it asserts nothing at all.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import statusrot  # noqa: E402

TOOL = Path(statusrot.__file__).resolve()


def _level(tmp_path: Path, *lines: str) -> Path:
    """Write a minimal CLAUDE.local.md carrying the given pointer lines."""
    p = tmp_path / "CLAUDE.local.md"
    p.write_text("# Memory index\n\n## Memory index\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return p


class TestParsePointers:
    def test_reads_title_slug_and_hook(self):
        line = "- [A title](mem:some-slug) - When X happens, do Y. <!-- bx:src=s -->"
        (ptr,) = statusrot.parse_pointers(line)
        assert ptr.slug == "some-slug"
        assert ptr.title == "A title"
        assert "When X happens" in ptr.hook
        assert "bx:src" not in ptr.hook, "the managed trailer is not part of the hook"

    def test_accepts_a_dotted_slug(self):
        # The engine's charset allows a dot; a hand-rolled [a-z0-9-]+ silently skips these.
        line = "- [T](mem:reference-pwshpy-tier-b-reuse-ps7.6-assemblies) - When X, do Y."
        (ptr,) = statusrot.parse_pointers(line)
        assert ptr.slug == "reference-pwshpy-tier-b-reuse-ps7.6-assemblies"

    def test_ignores_non_pointer_lines(self):
        assert statusrot.parse_pointers("## Memory index\nsome prose\n") == []


class TestClassify:
    def test_finds_the_positive_polarity(self):
        ptr = statusrot.Pointer("l", "s", "T", "When X, know it is deployed and folded into feat-net.")
        assert "SHIPPED" in statusrot.classify(ptr)

    def test_finds_the_unstarted_polarity(self):
        ptr = statusrot.Pointer("l", "s", "T", "When X, know this is TODO, not started.")
        assert "UNSTARTED" in statusrot.classify(ptr)

    def test_finds_a_bare_issue_id(self):
        ptr = statusrot.Pointer("l", "s", "T", "When X, do Y. Tracked as task #34.")
        assert "ID_REF" in statusrot.classify(ptr)

    def test_a_mechanism_hook_is_NOT_flagged(self):
        # The negative control. Without this the scanner could flag everything and still "pass".
        ptr = statusrot.Pointer(
            "l", "s", "T",
            "When a guest LSO frame goes to a TAP, recompute the IPv4 header checksum for every "
            "segmentation frame, because NDIS has the guest zero ip_check on LSO.")
        assert statusrot.classify(ptr) == set()


class TestSelfContradiction:
    def test_slug_says_blocked_while_hook_says_superseded(self):
        # The dm-linux-hotadd shape: title, hook and body were all corrected and the SLUG was not.
        ptr = statusrot.Pointer(
            "l", "dm-linux-hotadd-blocked-by-acpi-s4", "DM Linux hot-add works on stock firmware",
            "When you plan a DM hot-add test, know the ACPI-S4 blocker is SUPERSEDED: it works.")
        assert statusrot.self_contradiction(ptr) is not None

    def test_agreeing_slug_and_hook_are_not_flagged(self):
        ptr = statusrot.Pointer(
            "l", "project-net-tap-offload-contract-defaults-off", "net_tap offload contract",
            "When working on offloads, treat set_offloads(0) as the contract, not a gap.")
        assert statusrot.self_contradiction(ptr) is None


class TestScan:
    def test_counts_distinct_entries_not_hits(self, tmp_path):
        # One entry carrying TWO kinds must count once, or the population is overstated.
        lvl = _level(tmp_path, "- [T](mem:s) - When X, it is deployed. Tracked as task #34.")
        result = statusrot.scan([lvl])
        assert result.total_pointers == 1
        assert result.distinct_flagged == 1

    def test_a_clean_level_reports_nothing(self, tmp_path):
        lvl = _level(tmp_path, "- [T](mem:s) - When a TAP frame arrives, recompute the checksum.")
        result = statusrot.scan([lvl])
        assert result.distinct_flagged == 0
        assert result.contradictions == []


class TestCli:
    def test_exit_1_when_a_self_contradiction_is_found(self, tmp_path):
        lvl = _level(
            tmp_path,
            "- [T](mem:thing-blocked-by-x) - When X, know the blocker is SUPERSEDED, it works.")
        proc = subprocess.run(
            [sys.executable, str(TOOL), "scan", "--level", str(lvl), "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert proc.returncode == 1, proc.stdout + proc.stderr
        assert '"ok": true' in proc.stdout

    def test_exit_0_on_a_clean_level(self, tmp_path):
        lvl = _level(tmp_path, "- [T](mem:s) - When a frame arrives, recompute the checksum.")
        proc = subprocess.run(
            [sys.executable, str(TOOL), "scan", "--level", str(lvl), "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_exit_2_and_json_on_a_missing_level(self, tmp_path):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "scan", "--level", str(tmp_path / "nope.md"), "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert proc.returncode == 2
        assert '"ok": false' in proc.stdout, "a --json run must still emit JSON when it fails"


class TestSelfContradictionPrecision:
    """Measured false positives from the live chain, 2026-08-21: 5 of 5 flagged entries were
    wrong. A slug word like fails/works/done/deployed almost always names the TRIGGER or the
    SUBJECT, not an asserted state, so the rule needs an explicit REVERSAL marker in the hook
    and a slug token that is genuinely a state claim."""

    def test_deployed_in_a_slug_is_subject_matter(self):
        ptr = statusrot.Pointer(
            "l", "project-re-train-rerere-from-the-deployed-integration-for-a-safe-re-cut",
            "Re-train rerere",
            "When re-cutting after editing topics, do NOT clear .git/rr-cache; re-train rerere "
            "from the DEPLOYED integration, then re-cut.")
        assert statusrot.self_contradiction(ptr) is None

    def test_fails_in_a_slug_is_a_trigger_condition(self):
        ptr = statusrot.Pointer(
            "l", "seed-winre-when-reagentc-enable-fails-1614", "Seed WinRE",
            "When reagentc /enable fails 1614, the machine has no staged Winre.wim - normal "
            "after a recovery partition was deleted. Seed it from install media.")
        assert statusrot.self_contradiction(ptr) is None

    def test_works_in_a_slug_beside_a_cannot_in_the_hook(self):
        ptr = statusrot.Pointer(
            "l", "dm-linux-hotadd-works-on-stock-firmware-openvmm-clears-s4", "DM hot-add",
            "When you plan a DM hot-add test, know it works on STOCK firmware. Windows CLIENT "
            "still cannot hot-add (a Server feature).")
        assert statusrot.self_contradiction(ptr) is None

    def test_done_as_part_of_open_vs_done(self):
        ptr = statusrot.Pointer(
            "l", "feedback-status-hygiene-verify-open-vs-done-against-the-cited-doc", "Status hygiene",
            "When judging whether an item is still open, verify against ground truth, not TODO "
            "prose plus one grep.")
        assert statusrot.self_contradiction(ptr) is None

    def test_the_real_shape_is_still_caught(self):
        # The known positive must survive the precision fix, or the fix removed the tool's point.
        ptr = statusrot.Pointer(
            "l", "dm-linux-hotadd-blocked-by-acpi-s4", "DM Linux hot-add works on stock firmware",
            "When you plan a DM hot-add test, know the ACPI-S4 blocker is SUPERSEDED: openvmm "
            "clears S4 itself, so it works on stock MSVM.fd.")
        assert statusrot.self_contradiction(ptr) is not None
