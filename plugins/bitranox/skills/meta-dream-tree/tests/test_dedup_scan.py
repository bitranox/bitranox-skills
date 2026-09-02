"""Tests for dedup_scan.py - near-duplicate CANDIDATES across a curated memory tree.

The dream needs this twice per run and has always hand-rolled it, which is the problem: a
similarity scorer that silently cannot fire returns zero candidates, and zero candidates is
exactly what a clean tree returns too. So the two states are indistinguishable at the moment
you most want to believe the good one.

Three properties make the difference, and they are what most of this file pins:

- A PLANTED POSITIVE runs through the same code path every time. If the scanner cannot find a
  duplicate it inserted itself, the run is an instrument failure and not a clean bill of health.
- The SCORE DISTRIBUTION is reported, so a pair sitting just under the threshold is visible
  rather than silently dropped.
- The output is CANDIDATES. The tool never says two facts are duplicates; it says which two
  bodies to read.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import dedup_scan as DS

TOOL = Path(__file__).resolve().parents[1] / "dedup_scan.py"

NEAR_A = ("When a gate reports success, read its exit code from the log rather than from the "
          "job notification, because the notification reports the last command's status.")
NEAR_B = ("When a gate reports success, read the exit code out of the log instead of the job "
          "notification, since the notification carries the last command's status.")
FAR = ("When provisioning a Proxmox container, set the run identity explicitly and verify the "
       "output file permissions as the target user before trusting the unit.")


def facts(*pairs) -> list[DS.Fact]:
    return [DS.Fact(slug=s, level="/lvl", title=s.replace("-", " "), text=t) for s, t in pairs]


# ---- the scorer ------------------------------------------------------------------------------

def test_identical_text_scores_one_and_is_symmetric():
    assert DS.similarity(NEAR_A, NEAR_A) == 1.0
    assert DS.similarity(NEAR_A, FAR) == DS.similarity(FAR, NEAR_A)


def test_a_paraphrase_scores_far_above_an_unrelated_fact():
    """The gap is the whole signal. If a paraphrase and an unrelated fact land close together,
    no threshold can separate them and the tool is noise at every setting."""
    assert DS.similarity(NEAR_A, NEAR_B) > 0.5
    assert DS.similarity(NEAR_A, FAR) < 0.2
    assert DS.similarity(NEAR_A, NEAR_B) > DS.similarity(NEAR_A, FAR) + 0.4


def test_scoring_ignores_case_and_punctuation():
    assert DS.similarity("When X, do Y.", "when x do y") == 1.0


# ---- the planted control ----------------------------------------------------------------------

def test_the_planted_positive_is_detected_on_a_working_scorer():
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5)
    assert result.control.detected
    assert result.control.score > 0.5


def test_the_planted_positive_is_a_near_duplicate_not_a_reordering():
    """Measured on the real store: the control scored exactly 1.00, because the paraphrase only
    REORDERED words and the scorer compares word SETS - so the plant was an identical input.

    Such a control proves the scorer is not string equality and nothing more. It would fire
    happily on an instrument that misses every real near-duplicate, which is the one thing the
    control exists to rule out. A genuine plant must differ in WORDS: high, but under 1.0.
    """
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5)
    assert 0.5 < result.control.score < 1.0


def test_a_scorer_that_cannot_fire_is_reported_as_an_instrument_failure_not_a_clean_tree():
    """The failure this tool exists to make visible: a broken scorer and a clean tree both
    return zero candidates, and only the control tells them apart."""
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5,
                    scorer=lambda x, y: 0.0)
    assert result.candidates == []
    assert not result.control.detected
    assert result.instrument_failed


def test_a_clean_tree_reports_zero_candidates_with_the_control_still_passing():
    """The other side of the same coin: zero candidates is only trustworthy while the control
    fired, so both facts must be reported together."""
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.95)
    assert result.candidates == []
    assert result.control.detected and not result.instrument_failed


def test_the_planted_pair_never_appears_among_the_candidates():
    result = DS.run(facts(("a", NEAR_A), ("b", NEAR_B)), threshold=0.5)
    slugs = {s for c in result.candidates for s in (c.a.slug, c.b.slug)}
    assert not any(s.startswith(DS.CONTROL_PREFIX) for s in slugs)


# ---- candidates -------------------------------------------------------------------------------

def test_a_near_duplicate_pair_is_reported_with_both_slugs_and_a_score():
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("other", FAR)), threshold=0.5)
    assert len(result.candidates) == 1
    cand = result.candidates[0]
    assert {cand.a.slug, cand.b.slug} == {"first", "second"}
    assert cand.score > 0.5


def test_candidates_are_sorted_by_score_descending():
    mid = NEAR_A.replace("exit code", "return code").replace("notification", "message")
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("third", mid)), threshold=0.3)
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_a_pair_is_reported_once_not_in_both_orders():
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B)), threshold=0.5)
    assert len(result.candidates) == 1


def test_the_distribution_is_reported_so_a_near_miss_under_the_threshold_is_visible():
    """A pair at 0.49 against a 0.50 threshold is the one a reader most needs to see. Dropping
    it silently is how a threshold becomes a way of not looking."""
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("other", FAR)), threshold=0.99)
    assert result.candidates == []
    assert sum(result.distribution.values()) >= 1
    assert any(bucket >= 0.5 for bucket, n in result.distribution.items() if n)


# ---- reading a real tree ------------------------------------------------------------------------

def make_tree(root: Path) -> None:
    (root / ".claude-memory" / "facts").mkdir(parents=True)
    (root / "CLAUDE.local.md").write_text(
        "# Memory index\n"
        "- [First](mem:first-slug) - When first, do first.\n"
        "- [Second](mem:second-slug) - When second, do second.\n", encoding="utf-8")
    for slug, body in (("first-slug", NEAR_A), ("second-slug", NEAR_B)):
        (root / ".claude-memory" / "facts" / f"{slug}.md").write_text(
            f"---\nname: {slug}\ndescription: d\n---\n\n{body}\n", encoding="utf-8")


def test_facts_are_loaded_with_their_level_so_a_candidate_can_be_opened(tmp_path):
    make_tree(tmp_path)
    loaded = DS.load_facts(tmp_path)
    assert {f.slug for f in loaded} == {"first-slug", "second-slug"}
    assert all(f.level.endswith(str(tmp_path)) or str(tmp_path) in f.level for f in loaded)


def run_cli(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False, cwd=str(cwd))


def test_cli_exits_1_and_frames_the_output_as_candidates(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--json"], tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert "candidates" in env["data"]
    assert env["data"]["control"]["detected"] is True
    assert env["data"]["candidates"][0]["score"] > 0.5


def test_cli_exits_0_on_a_tree_with_nothing_near_duplicate(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.99", "--json"], tmp_path)
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["candidates"] == []


def test_cli_exits_2_when_there_is_no_tree(tmp_path):
    r = run_cli(["--from", str(tmp_path / "nope"), "--json"], tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False
